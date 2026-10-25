"""前置评估流水线（方案 2.3 数据流①）：L1 → L2 → 通过者联合确认 → 矩阵报告。

    python -m feval.pipeline        # mock 数据跑一遍，报告写到 reports/mock-matrix.md
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from . import l2
from .l1 import screen
from .spec import TargetSpec


def evaluate(df: pl.DataFrame, spec: TargetSpec, base: list[str], candidates: list[str], B: int = 1000,
             delta_min: float = l2.DELTA_MIN, domains: dict[str, str] | None = None, l2_for_all: bool = False,
             compare_sample_bootstrap: bool = False, seed: int = 0) -> dict[str, dict]:
    """单个目标列的前置评估，返回 {候选: 结果}。domains：{特征: 定义域列}，未声明的特征定义域为全部样本。

    候选若本在基线里（正对照），先从基线移出再评估。l2_for_all=True 是校准模式：L1 没通过的也跑 L2，
    以便单独度量 L2 判据。"""
    if spec.population:
        df = df.filter(pl.col(spec.population) == 1)
    rows = {c: {"l1": screen(df, c, spec, (domains or {}).get(c))} for c in candidates}
    train, valid = l2.time_split(df, spec)
    y, groups = valid[spec.label].to_numpy(), valid[spec.group_key].to_numpy()
    base_scores = l2.proxy_scores(train, valid, base, spec.label)
    ref = l2.online_reference(train, valid, spec) if spec.online_score else None
    for c, r in rows.items():
        if r["l1"]["grade"] != "通过" and not l2_for_all:
            continue
        b = [f for f in base if f != c]
        bs = base_scores if b == base else l2.proxy_scores(train, valid, b, spec.label)
        es = l2.proxy_scores(train, valid, b + [c], spec.label)
        r["l2"] = {k: l2.paired_bootstrap(y, bs[k], es[k], groups, B, seed=seed) for k in es}
        if compare_sample_bootstrap:
            r["l2_sample"] = l2.paired_bootstrap(y, bs["lgb"], es["lgb"], groups, B, scheme="sample", seed=seed)
        if ref is not None:
            p_res = l2.lgb_scores(train, valid, [c], spec.label, init=ref[:2], n_estimators=100)
            r["residual"] = l2.paired_bootstrap(y, ref[2], p_res, groups, B, seed=seed)
        r["l2_decision"] = l2.decide([v[spec.primary_metric][1:] for v in r["l2"].values()], delta_min)
    passed = sorted((c for c, r in rows.items()
                     if c not in base and r["l1"]["grade"] == "通过" and r.get("l2_decision") == "建议入模"),
                    key=lambda c: -max(v[spec.primary_metric][1] for v in rows[c]["l2"].values()))
    kept = set(l2.confirm_jointly(train, valid, spec, base, passed, B, delta_min, seed))
    for c, r in rows.items():
        r["conclusion"] = _conclusion(r, joint_ok=c in kept or c in base)
    return rows


def _conclusion(r: dict, joint_ok: bool) -> str:
    if r["l1"]["grade"] != "通过":
        return r["l1"]["grade"]
    if r["l2_decision"] == "建议入模" and not joint_ok:
        return "联合确认剔除"
    return r["l2_decision"]


ICON = {"建议入模": "✅", "无显著增量": "⚠️", "观察": "⚠️", "联合确认剔除": "⚠️", "样本不足": "⊘", "疑似泄漏": "🔍"}


def _ci(t: tuple) -> str:
    return f"{t[0]:+.4f} [{t[1]:+.4f}, {t[2]:+.4f}]"


def matrix_markdown(results: dict[str, dict], primary: dict[str, str] | None = None) -> str:
    """矩阵报告：行 = 候选，列 = 目标；gate 只看该特征的主目标列（方案 3.5），未声明时取第一列。"""
    targets, primary = list(results), primary or {}
    lines = ["| 候选 | " + " | ".join(targets) + " | 主目标 | gate |", "|---" * (len(targets) + 3) + "|"]
    for c in results[targets[0]]:
        cells = []
        for t in targets:
            r = results[t][c]
            delta = f" {r['l2']['lgb']['auc'][0]:+.4f}" if "l2" in r else ""
            cells.append(f"{ICON.get(r['conclusion'], '❌')} {r['conclusion']}{delta}")
        p = primary.get(c, targets[0])
        lines.append(f"| {c} | " + " | ".join(cells) + f" | {p} | {results[p][c]['conclusion']} |")
    return "\n".join(lines)


def detail_markdown(rows: dict[str, dict]) -> str:
    lines = ["| 候选 | L1 | IV | AUC 偏移 | PSI | 缺失率 | ΔAUC·LGB [95% CI] | ΔAUC·LR | 残差 ΔAUC | 结论 |",
             "|---" * 10 + "|"]
    for c, r in rows.items():
        m = r["l1"]
        l2r = r.get("l2")
        lines.append(f"| {c} | {m['grade']} | {m['iv']:.4f} | {m['auc_offset']:+.4f} | {m['psi']:.3f} | "
                     f"{m['missing_rate']:.0%} | {_ci(l2r['lgb']['auc']) if l2r else '—'} | "
                     f"{_ci(l2r['lr']['auc']) if l2r else '—'} | "
                     f"{_ci(r['residual']['auc']) if 'residual' in r else '—'} | {r['conclusion']} |")
    return "\n".join(lines)


def control_summary(rows: dict[str, dict], negatives: list[str], positives: list[str]) -> str:
    """每批自带的对照检查：负对照不该入模，正对照应该入模。"""
    fp = [c for c in negatives if rows[c]["conclusion"] == "建议入模"]
    fn = [c for c in positives if rows[c]["conclusion"] != "建议入模"]
    return (f"对照检查：负对照误放 {len(fp)}/{len(negatives)}{' ' + str(fp) if fp else ''}；"
            f"正对照漏放 {len(fn)}/{len(positives)}{' ' + str(fn) if fn else ''}")


def main(out: str = "reports/mock-matrix.md") -> None:
    from .mock import BASE, CANDIDATES, FEATURE_DOMAIN, POSITIVE_CONTROL, make_ctr_mock, probe_names

    df = make_ctr_mock(seed=0)
    probes = probe_names()
    # 用户级常量探针会被代理当作用户 ID，不算干净负对照（方案 7.1）
    negatives = [c for c, t in probes.items() if t != "噪声探针（用户级常量）"]
    specs = [TargetSpec("CTR", online_score="p_online"),
             TargetSpec("游戏", population="is_game", online_score="p_online")]
    results = {s.name: evaluate(df, s, BASE, CANDIDATES + list(probes) + [POSITIVE_CONTROL], domains=FEATURE_DOMAIN)
               for s in specs}
    parts = ["# 矩阵报告（mock 数据，seed=0）", "", matrix_markdown(results, primary={"c_game": "游戏"})]
    for name, rows in results.items():
        parts += ["", f"## {name}", "", control_summary(rows, negatives, [POSITIVE_CONTROL]), "", detail_markdown(rows)]
    text = "\n".join(parts) + "\n"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
