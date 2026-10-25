"""L1 快筛（方案 3.1）：所有指标都从分桶计数表 (bin, pos, neg) 算。

计数表是本地与 Spark 两个后端的交接面：Spark 侧只需 group by 产出同一张表，下面的指标函数原样复用（ADR-0002）。
"""

from __future__ import annotations

import numpy as np
import polars as pl

from .spec import TargetSpec

MISSING = -1  # 缺失箱编号：缺失单独成箱参与计算
MIN_POS_PER_BIN = 50
MIN_POS_TOTAL = 300
MAX_CATS = 100


def is_categorical(s: pl.Series) -> bool:
    """离散特征：字符串/布尔，或取值 ≤ 50 的整数（方案 4.2 低基枚举）。"""
    if s.dtype in (pl.String, pl.Categorical, pl.Boolean):
        return True
    return s.dtype.is_integer() and s.n_unique() <= 50


def bin_codes(s: pl.Series, y: np.ndarray) -> tuple[np.ndarray, bool]:
    """3.1.2 自适应分桶：返回每行桶号（缺失为 MISSING）和是否离散特征。"""
    if s.dtype.is_float():
        s = s.fill_nan(None)
    present = ~s.is_null().to_numpy()
    codes = np.full(len(s), MISSING, dtype=np.int64)
    categorical = is_categorical(s)
    if categorical:
        codes[present] = _categorical_codes(s.drop_nulls(), y[present])
    else:
        yp = y[present]
        k = int(np.clip(yp.sum() // 100, 3, 10))
        codes[present] = _continuous_codes(s.drop_nulls().to_numpy().astype(float), yp, k)
    return codes, categorical


def _continuous_codes(x: np.ndarray, y: np.ndarray, k: int) -> np.ndarray:
    edges = np.unique(np.quantile(x, np.linspace(0, 1, k + 1)[1:-1]))
    pos = np.bincount(np.searchsorted(edges, x, side="right"), weights=y, minlength=len(edges) + 1)
    kept, acc = [], 0.0
    for i, p in enumerate(pos[:-1]):  # 第 i 条边分开桶 i 与 i+1；攒够正样本才保留这条边
        acc += p
        if acc >= MIN_POS_PER_BIN:
            kept.append(i)
            acc = 0.0
    if kept and pos[kept[-1] + 1:].sum() < MIN_POS_PER_BIN:  # 末桶不足则并入前一桶
        kept.pop()
    return np.searchsorted(edges[kept], x, side="right")


def _categorical_codes(s: pl.Series, y: np.ndarray) -> np.ndarray:
    """按频次取 top-N（累计覆盖 ≥ 95% 或 N ≤ 100），正样本 < 50 的类别并入 other。"""
    stats = (pl.DataFrame({"v": s, "y": y}).group_by("v")
             .agg(n=pl.len(), pos=pl.col("y").sum())
             .sort(["n", "v"], descending=[True, False]))
    n_top = min(int((stats["n"].cum_sum() / len(s) < 0.95).sum()) + 1, MAX_CATS)
    top = stats.head(n_top).filter(pl.col("pos") >= MIN_POS_PER_BIN)["v"]
    return s.replace_strict(top, list(range(len(top))), default=len(top), return_dtype=pl.Int64).to_numpy()


def count_table(codes: np.ndarray, y: np.ndarray) -> pl.DataFrame:
    """(bin, pos, neg) 计数表，按 bin 升序。"""
    return (pl.DataFrame({"bin": codes, "y": y}).group_by("bin")
            .agg(pos=pl.col("y").sum().cast(pl.Float64), n=pl.len().cast(pl.Float64))
            .with_columns(neg=pl.col("n") - pl.col("pos"))
            .select("bin", "pos", "neg").sort("bin"))


def iv_terms(pos: np.ndarray, neg: np.ndarray, smooth: float = 0.5) -> np.ndarray:
    """每桶的 IV 贡献；smooth 防止空桶取对数。"""
    p = (pos + smooth) / (pos + smooth).sum()
    q = (neg + smooth) / (neg + smooth).sum()
    return (p - q) * np.log(p / q)


def mutual_info(pos: np.ndarray, neg: np.ndarray) -> float:
    joint = np.stack([pos, neg]) / (pos.sum() + neg.sum())
    outer = joint.sum(axis=1, keepdims=True) * joint.sum(axis=0, keepdims=True)
    nz = joint > 0
    return float((joint[nz] * np.log(joint[nz] / outer[nz])).sum())


def ks(pos: np.ndarray, neg: np.ndarray) -> float:
    order = np.argsort(pos / (pos + neg), kind="mergesort")
    return float(np.abs(np.cumsum(pos[order]) / pos.sum() - np.cumsum(neg[order]) / neg.sum()).max())


def auc_grouped(key: np.ndarray, pos: np.ndarray, neg: np.ndarray) -> np.ndarray:
    """按 key 升序的 AUC，key 相同算并列（记 0.5）。pos/neg 是每个单元的正/负权重，形状 (n,) 或 (B, n)，返回 (B,)。

    L1 拿桶编码当 key、桶计数当权重；L2 拿模型分当 key、bootstrap 权重当权重，同一个函数。
    """
    pos, neg = np.atleast_2d(pos), np.atleast_2d(neg)
    order = np.argsort(key, kind="mergesort")
    k = np.asarray(key)[order]
    starts = np.flatnonzero(np.r_[True, k[1:] != k[:-1]])
    p = np.add.reduceat(pos[:, order], starts, axis=1)
    q = np.add.reduceat(neg[:, order], starts, axis=1)
    below = np.cumsum(q, axis=1) - q
    return (p * (below + 0.5 * q)).sum(axis=1) / (p.sum(axis=1) * q.sum(axis=1))


def psi(expected: np.ndarray, actual: np.ndarray, eps: float = 1e-6) -> float:
    e = np.maximum(expected / expected.sum(), eps)
    a = np.maximum(actual / actual.sum(), eps)
    return float(((a - e) * np.log(a / e)).sum())


def _oof_auc(codes: np.ndarray, y: np.ndarray, groups: np.ndarray) -> float:
    """两折 OOF：一折的桶转化率定桶序，另一折算 AUC（按分组键分折，防同用户跨折泄漏）。"""
    fold = (pl.Series(groups).hash(seed=0) % 2).to_numpy()
    aucs = []
    for f in (0, 1):
        fit, ev = count_table(codes[fold != f], y[fold != f]), count_table(codes[fold == f], y[fold == f])
        prior = fit["pos"].sum() / (fit["pos"].sum() + fit["neg"].sum())
        rate = dict(zip(fit["bin"].to_list(), (fit["pos"] / (fit["pos"] + fit["neg"])).to_list()))
        key = np.array([rate.get(b, prior) for b in ev["bin"].to_list()])
        aucs.append(auc_grouped(key, ev["pos"].to_numpy(), ev["neg"].to_numpy())[0])
    return float(np.mean(aucs))


def _max_psi(codes: np.ndarray, days: np.ndarray, window: int = 7) -> float:
    """首日为基期，取最近 window 天里最大的 PSI。"""
    _, inv = np.unique(codes, return_inverse=True)
    width = inv.max() + 1
    counts = np.stack([np.bincount(inv[days == d], minlength=width) for d in np.unique(days)]).astype(float)
    return max((psi(counts[0], c) for c in counts[1:][-window:]), default=0.0)


def _monotonic_rho(ct: pl.DataFrame) -> float | None:
    """桶序与桶转化率的 Spearman ρ；只做描述，不参与判定（v0.2）。"""
    ct = ct.filter(pl.col("bin") != MISSING)
    if ct.height < 3:
        return None
    r = (ct["pos"] / (ct["pos"] + ct["neg"])).to_numpy()
    return float(np.corrcoef(np.arange(len(r)), np.argsort(np.argsort(r)))[0, 1])


def _raw_auc_offset(s: pl.Series, y: np.ndarray, present: np.ndarray) -> float:
    x = s.cast(pl.Float64).fill_nan(None).to_numpy()[present]
    return abs(float(auc_grouped(x, y[present], 1 - y[present])[0]) - 0.5)


def screen(df: pl.DataFrame, feature: str, spec: TargetSpec, domain: str | None = None) -> dict:
    """单个特征在一个目标上的 L1 指标与等级。df 应已按口径卡的适用人群过滤。

    domain：特征定义域（0/1 列名）。缺失率只在定义域内算，域外是结构性缺失；缺失箱照常参与 IV。"""
    y = df[spec.label].cast(pl.Int64).to_numpy()
    codes, categorical = bin_codes(df[feature], y)
    ct = count_table(codes, y)
    pos, neg = ct["pos"].to_numpy(), ct["neg"].to_numpy()
    terms = iv_terms(pos, neg)
    present = codes != MISSING
    in_domain = np.ones(len(codes), bool) if domain is None else df[domain].to_numpy() == 1
    m = {
        "n_pos": int(y.sum()),
        "iv": float(terms.sum()),
        "ks": ks(pos, neg),
        "mi": mutual_info(pos, neg),
        "auc_offset": _oof_auc(codes, y, df[spec.group_key].to_numpy()) - 0.5,
        # v0.1 口径（连续特征直接用原值算 AUC），保留作对照
        "auc_raw_offset": None if categorical else _raw_auc_offset(df[feature], y, present),
        "psi": _max_psi(codes, df[spec.day_key].to_numpy()),
        "missing_rate": float((~present[in_domain]).mean()),
        "missing_iv": float(terms[ct["bin"].to_numpy() == MISSING].sum()),
        "monotonic_rho": None if categorical else _monotonic_rho(ct),
    }
    m["grade"] = grade(m)
    return m


def grade(m: dict) -> str:
    """方案 3.1.3 判定合成规则（v0.2）。优先级：样本不足 > 疑似泄漏 > 拒绝 > 观察 > 通过。"""
    if m["n_pos"] < MIN_POS_TOTAL:
        return "样本不足"
    if m["iv"] > 0.5:
        return "疑似泄漏"
    disc_pass = m["iv"] >= 0.02 or m["auc_offset"] >= 0.02
    disc_observe = not disc_pass and m["auc_offset"] >= 0.005
    missing_ok = m["missing_rate"] < 0.05 or m["missing_iv"] >= 0.02
    if (not disc_pass and not disc_observe) or m["psi"] >= 0.25 or (not missing_ok and m["missing_rate"] >= 0.20):
        return "拒绝"
    if disc_observe or m["psi"] >= 0.1 or not missing_ok:
        return "观察"
    return "通过"
