"""评估器校准（方案 7.1）：在多个种子的 mock 数据上，按真值类别统计各判据的通过率。

    python -m feval.calibrate --reps 20 --workers 3      # 报告写到 reports/calibration.md

L2 对所有候选都跑（不经 L1 过滤），所以 L2 判据的误放/漏放可以单独度量。
"""

from __future__ import annotations

import argparse
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

import numpy as np

from . import l2
from .mock import BASE, FEATURE_DOMAIN, POSITIVE_CONTROL, TRUTH, make_ctr_mock, probe_names
from .pipeline import evaluate
from .spec import TargetSpec

CLASSES = ["正对照", "增量", "增量（用户级）", "增量（非单调）", "与 c_strong 互为冗余", "弱增量", "行业专属",
           "冗余（基线已含）", "噪声", "噪声探针（样本级）", "噪声探针（用户×天级）", "噪声探针（用户级常量）",
           "漂移", "泄漏"]
# 定 δ_min 用的负对照：用户级常量探针可能充当用户 ID，不算干净的负对照，单独列出
CLEAN_NULLS = ["噪声", "噪声探针（样本级）", "噪声探针（用户×天级）"]
DELTAS = (0.0, 0.0005, 0.001)
MAX_FALSE_PASS = 0.05


def truth_map() -> dict[str, str]:
    return {**TRUTH, **probe_names(), POSITIVE_CONTROL: "正对照"}


def one_seed(seed: int, B: int, rows_per_day: int) -> list[dict]:
    truth = truth_map()
    df = make_ctr_mock(seed=seed, rows_per_day=rows_per_day)
    rows = evaluate(df, TargetSpec("CTR", online_score="p_online"), BASE, list(truth), B=B,
                    domains=FEATURE_DOMAIN, l2_for_all=True, compare_sample_bootstrap=True, seed=seed)
    return [{"seed": seed, "feature": c, "truth": truth[c], "l1": r["l1"]["grade"], "conclusion": r["conclusion"],
             "auc_offset": r["l1"]["auc_offset"], "auc_raw_offset": r["l1"]["auc_raw_offset"],
             "rho": r["l1"]["monotonic_rho"], "lgb": r["l2"]["lgb"]["auc"], "lgb_sample": r["l2_sample"]["auc"],
             "lr": r["l2"]["lr"]["auc"], "res": r["residual"]["auc"]} for c, r in rows.items()]


def _either(r: dict, d: float) -> bool:
    return r["lgb"][1] > d or r["lr"][1] > d


def _rate(recs: list[dict], pred) -> float:
    return float(np.mean([bool(pred(r)) for r in recs])) if recs else float("nan")


def _pct(x: float) -> str:
    return "—" if math.isnan(x) else f"{x:.0%}"


def _table(head: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|---" * len(head) + "|"] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]


def _v01_null_pass(h: float, eps: float = l2.EPS) -> float:
    """零增量特征在 v0.1 判据下的理论放行率：点估计 ~ N(0, σ²)，σ = h / 1.96，放行需点估计 ≥ max(0, h − ε)。"""
    sigma = h / 1.96
    return 0.5 * math.erfc(max(0.0, h - eps) / sigma / math.sqrt(2))


def render(recs: list[dict], reps: int, B: int, rows_per_day: int, seconds: float) -> str:
    by = {c: [r for r in recs if r["truth"] == c] for c in CLASSES}
    out = ["# 评估器校准报告（mock 数据）", "",
           f"- 参数：{reps} 个种子；每个种子 {rows_per_day * 8:,} 行（8 天、1500 用户，人均曝光重尾），"
           f"valid = 最后一天；bootstrap B={B}；耗时 {seconds / 60:.1f} 分钟。",
           "- 复现：`python -m feval.calibrate`；真值定义见 `feval/mock.py`。mock 上的数字不能直接当公司阈值，"
           "迁移的是方法：在真实数据上用同样的对照特征再校准一次。", ""]

    out += ["## 1. L1 等级分布（v0.2 判定表）", ""]
    grades = ["通过", "观察", "拒绝", "疑似泄漏"]
    out += _table(["真值类别", "次数"] + grades,
                  [[c, len(v)] + [_pct(_rate(v, lambda r, g=g: r["l1"] == g)) for g in grades] for c, v in by.items()])

    out += ["", "## 2. L2 判据的「建议入模」比例（L2 对全部候选都跑）", "",
            "v0.1 = LightGBM Δ≥0 且 CI 下界 > −0.0005（非劣效，样本级重采样）；v0.2 = CI 下界 > δ_min（优效）。"
            "「任一」= LightGBM 或 LR 任一代理满足；未注明重采样单位的均为按用户聚类。", ""]
    out += _table(["真值类别", "v0.1", "LGB δ=0·样本级", "LGB δ=0", "LR δ=0"]
                  + [f"任一 δ={d:g}" for d in DELTAS] + ["残差 CI 下界>0"],
                  [[c, _pct(_rate(v, lambda r: l2.decide_v01(r["lgb_sample"][0], r["lgb_sample"][1]) == "建议入模")),
                    _pct(_rate(v, lambda r: r["lgb_sample"][1] > 0)), _pct(_rate(v, lambda r: r["lgb"][1] > 0)),
                    _pct(_rate(v, lambda r: r["lr"][1] > 0))]
                   + [_pct(_rate(v, lambda r, d=d: _either(r, d))) for d in DELTAS]
                   + [_pct(_rate(v, lambda r: r["res"][1] > 0))] for c, v in by.items()])

    nulls = [r for c in CLEAN_NULLS for r in by[c]]
    worst = {d: max(_rate(by[c], lambda r, d=d: _either(r, d)) for c in CLEAN_NULLS) for d in DELTAS}
    ok = [d for d in DELTAS if worst[d] <= MAX_FALSE_PASS]
    pick = ok[0] if ok else None
    out += ["", f"**δ_min 建议**：干净负对照（{'、'.join(CLEAN_NULLS)}）各类误放率都 ≤ {MAX_FALSE_PASS:.0%} 的最小 δ_min = "
            + (f"**{pick:g}**；此时弱增量检出率 {_pct(_rate(by['弱增量'], lambda r: _either(r, pick)))}。"
               if pick is not None else "网格内无解，需放宽网格或加多窗一致性。")]
    h = float(np.median([(r["lgb_sample"][2] - r["lgb_sample"][1]) / 2 for r in nulls]))
    out += ["", f"**v0.1 判据随样本量变松**：本次负对照的样本级 CI 半宽中位数 h = {h:.4f}（ε = {l2.EPS}）。"
            f"零增量特征的理论放行率在 h 下为 {_v01_null_pass(h):.1%}（实测见上表 v0.1 列），"
            f"样本量 ×10 时为 {_v01_null_pass(h / math.sqrt(10)):.1%}，×30 时为 {_v01_null_pass(h / math.sqrt(30)):.1%}，"
            "h ≤ ε 时达到 50%；v0.2 的理论误放率与样本量无关（每个代理单侧 2.5%，「任一」合并后不超过 5%）。"]

    out += ["", "## 3. 端到端结论分布（v0.2 全流程：L1 → L2 → 联合确认，δ_min=0）", ""]
    concl = ["建议入模", "无显著增量", "联合确认剔除", "有害", "观察", "拒绝", "疑似泄漏"]
    out += _table(["真值类别"] + concl,
                  [[c] + [_pct(_rate(v, lambda r, k=k: r["conclusion"] == k)) for k in concl] for c, v in by.items()])

    out += ["", "## 4. CI 宽度：聚类 vs 样本级 bootstrap（LightGBM ΔAUC，中位数）", ""]
    width = lambda t: t[2] - t[1]
    out += _table(["真值类别", "中位 ΔAUC", "聚类 CI 宽度", "样本级 CI 宽度", "聚类/样本级（中位）", "聚类/样本级（最大）"],
                  [[c, f"{np.median([r['lgb'][0] for r in v]):+.4f}",
                    f"{np.median([width(r['lgb']) for r in v]):.4f}",
                    f"{np.median([width(r['lgb_sample']) for r in v]):.4f}",
                    f"{np.median([width(r['lgb']) / width(r['lgb_sample']) for r in v]):.2f}",
                    f"{np.max([width(r['lgb']) / width(r['lgb_sample']) for r in v]):.2f}"] for c, v in by.items()])

    u = by["增量（非单调）"]
    out += ["", "## 5. U 型特征：v0.1 与 v0.2 的 L1 口径", ""]
    out += _table(["指标", "中位数", "按 v0.1 阈值判拒绝的比例"],
                  [["原值 AUC 偏移（v0.1，< 0.005 拒绝）", f"{np.median([r['auc_raw_offset'] for r in u]):.4f}",
                    _pct(_rate(u, lambda r: r["auc_raw_offset"] < 0.005))],
                   ["OOF 分桶编码 AUC 偏移（v0.2）", f"{np.median([r['auc_offset'] for r in u]):.4f}", "—"],
                   [r"单调性 \|ρ\|（v0.1 非单调即拒；10 桶时 \|ρ\| < 0.6 约等于 p ≥ 0.05）",
                    f"{np.median([abs(r['rho']) for r in u]):.2f}", _pct(_rate(u, lambda r: abs(r["rho"]) < 0.6))]])

    pairs = [[r["conclusion"] == "建议入模" for r in recs if r["seed"] == s and r["feature"] in ("c_strong", "c_dup")]
             for s in range(reps)]
    out += ["", "## 6. 联合确认：c_strong 与 c_dup（互为冗余）最终保留几个", ""]
    out += _table(["保留 0 个", "恰好 1 个", "2 个都保留"],
                  [[f"{np.mean([sum(p) == k for p in pairs]):.0%}" for k in (0, 1, 2)]])
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="评估器校准：mock 数据多种子统计各判据的误放/漏放")
    ap.add_argument("--reps", type=int, default=20)
    ap.add_argument("--B", type=int, default=500)
    ap.add_argument("--rows-per-day", type=int, default=15000)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out", default="reports/calibration.md")
    a = ap.parse_args()
    # 子进程用 spawn 启动，OpenMP 线程数要在它们加载 LightGBM 之前经环境变量定好，避免互相抢核
    os.environ.setdefault("OMP_NUM_THREADS", str(max(1, (os.cpu_count() or 1) // a.workers)))
    t0, recs = time.time(), []
    with ProcessPoolExecutor(a.workers, mp_context=get_context("spawn")) as ex:
        futs = [ex.submit(one_seed, s, a.B, a.rows_per_day) for s in range(a.reps)]
        for i, f in enumerate(as_completed(futs), 1):
            recs += f.result()
            print(f"[{i}/{a.reps}] {time.time() - t0:.0f}s", flush=True)
    text = render(recs, a.reps, a.B, a.rows_per_day, time.time() - t0)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
