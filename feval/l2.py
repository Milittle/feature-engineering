"""L2 增量评估（方案 3.2）：双代理消融、按分组键的 paired Poisson bootstrap、残差分析、通过者联合确认。"""

from __future__ import annotations

import lightgbm as lgb
import numpy as np
import polars as pl
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .l1 import auc_grouped, is_categorical
from .spec import TargetSpec

DELTA_MIN = 0.0  # 入模优效门槛：CI 下界须 > DELTA_MIN（ADR-0004），实际取值靠评估器校准
EPS = 0.0005  # 非劣效容差：下线判据用；v0.1 的入模判据也用它（仅供校准对照）
CHUNK = 250


def time_split(df: pl.DataFrame, spec: TargetSpec) -> tuple[pl.DataFrame, pl.DataFrame]:
    """时间外推：valid = 数据末日 − 成熟期，train = 更早的天（label 未成熟的天不用）。"""
    valid_day = df[spec.day_key].max() - spec.maturity_days
    return df.filter(pl.col(spec.day_key) < valid_day), df.filter(pl.col(spec.day_key) == valid_day)


def lgb_scores(train, valid, features, label, init=None, n_estimators=200) -> np.ndarray:
    """LightGBM 代理；init=(train_logit, valid_logit) 时在线上分之上继续拟合（残差分析）。"""
    model = lgb.LGBMClassifier(n_estimators=n_estimators, learning_rate=0.05, num_leaves=31,
                               min_child_samples=100, reg_lambda=1.0, random_state=0,
                               deterministic=True, force_col_wise=True, verbose=-1)
    model.fit(train.select(features).to_numpy(), train[label].to_numpy(),
              init_score=None if init is None else init[0])
    raw = model.predict(valid.select(features).to_numpy(), raw_score=True)
    return _sigmoid(raw if init is None else raw + init[1])


def lr_scores(train, valid, features, label) -> np.ndarray:
    """LR 代理：低基数整数 one-hot，数值列补缺失指示后标准化。"""
    cat = [i for i, f in enumerate(features) if is_categorical(train[f])]
    num = [i for i in range(len(features)) if i not in cat]
    parts = [("cat", OneHotEncoder(handle_unknown="ignore"), cat)] if cat else []
    if num:
        parts.append(("num", make_pipeline(SimpleImputer(add_indicator=True), StandardScaler()), num))
    model = make_pipeline(ColumnTransformer(parts), LogisticRegression(max_iter=500))
    model.fit(train.select(features).to_numpy(), train[label].to_numpy())
    return model.predict_proba(valid.select(features).to_numpy())[:, 1]


def proxy_scores(train, valid, features, label) -> dict[str, np.ndarray]:
    return {"lgb": lgb_scores(train, valid, features, label), "lr": lr_scores(train, valid, features, label)}


def online_reference(train, valid, spec: TargetSpec):
    """线上分先在 train 上做 Platt 校准，返回 (train_logit, valid_logit, valid_prob)。"""
    zt, zv = _logit(train[spec.online_score].to_numpy()), _logit(valid[spec.online_score].to_numpy())
    cal = LogisticRegression().fit(zt[:, None], train[spec.label].to_numpy())
    it, iv = cal.decision_function(zt[:, None]), cal.decision_function(zv[:, None])
    return it, iv, _sigmoid(iv)


def paired_bootstrap(y, p_base, p_exp, groups, B=1000, scheme="cluster", seed=0) -> dict:
    """配对 Poisson bootstrap：每个分组（scheme="sample" 时每个样本）独立抽 Poisson(1) 权重，
    在 Spark 上可逐行生成。返回 {metric: (点估计, CI 下界, CI 上界)}，Δ 一律"正 = 实验组更好"。"""
    rng = np.random.default_rng(seed)
    y = np.asarray(y, dtype=float)
    uniq, g = np.unique(groups, return_inverse=True)
    ll_gain = _logloss(y, p_base) - _logloss(y, p_exp)
    gid, n_u, d_u = _group_auc_delta(y, p_base, p_exp, g)
    point = {
        "auc": float(auc_grouped(p_exp, y, 1 - y)[0] - auc_grouped(p_base, y, 1 - y)[0]),
        "logloss": float(ll_gain.mean()),
        "gauc": float((n_u * d_u).sum() / n_u.sum()),
    }
    draws = {k: [] for k in point}
    for start in range(0, B, CHUNK):
        b = min(CHUNK, B - start)
        if scheme == "cluster":
            C = rng.poisson(1.0, (b, len(uniq))).astype(float)
            W = C[:, g]
            draws["gauc"].append(C[:, gid] @ (n_u * d_u) / (C[:, gid] @ n_u))
        else:
            W = rng.poisson(1.0, (b, len(y))).astype(float)
        draws["auc"].append(auc_grouped(p_exp, W * y, W * (1 - y)) - auc_grouped(p_base, W * y, W * (1 - y)))
        draws["logloss"].append(W @ ll_gain / W.sum(axis=1))
    out = {}
    for k, v in draws.items():
        if v:  # 样本级重采样不算 GAUC：GAUC 天然按用户分组
            lo, hi = np.percentile(np.concatenate(v), [2.5, 97.5])
            out[k] = (point[k], float(lo), float(hi))
    return out


def decide(cis: list[tuple[float, float]], delta_min: float = DELTA_MIN) -> str:
    """v0.2 入模判据（优效）：cis 为各代理主指标 Δ 的 (CI 下界, CI 上界)。

    任一代理 CI 下界 > δ_min 即建议入模（LR 补线性弱信号、LightGBM 补非线性，方案 7.1）；全部 CI 上界 < 0 为有害。"""
    if any(lo > delta_min for lo, _ in cis):
        return "建议入模"
    return "有害" if all(hi < 0 for _, hi in cis) else "无显著增量"


def decide_v01(point: float, lo: float, eps: float = EPS) -> str:
    """v0.1 入模判据（非劣效），仅用于校准对照，勿用于判定。"""
    return "建议入模" if point >= 0 and lo > -eps else "不建议"


def confirm_jointly(train, valid, spec: TargetSpec, base, ranked, B=1000, delta_min=DELTA_MIN, seed=0) -> list:
    """通过者联合确认：按单独增量从大到小逐个加入，在已接收集合之上仍优效才保留，剔除彼此冗余者。"""
    y = valid[spec.label].to_numpy()
    groups = valid[spec.group_key].to_numpy()
    kept, cur = [], proxy_scores(train, valid, base, spec.label)
    for c in ranked:
        exp = proxy_scores(train, valid, base + kept + [c], spec.label)
        cis = [paired_bootstrap(y, cur[k], exp[k], groups, B, seed=seed)[spec.primary_metric][1:] for k in exp]
        if decide(cis, delta_min) == "建议入模":
            kept.append(c)
            cur = exp
    return kept


def _group_auc_delta(y, p_base, p_exp, g):
    """每组（用户）的 AUC 差；只保留正负样本都有的组。返回 (组号, 组样本数, ΔAUC)。"""
    def per_group(p):
        out = (pl.DataFrame({"g": g, "y": y, "p": p})
               .with_columns(r=pl.col("p").rank("average").over("g"))
               .group_by("g").agg(n=pl.len().cast(pl.Float64), npos=pl.col("y").sum(),
                                  rs=(pl.col("r") * pl.col("y")).sum())
               .sort("g"))
        n, npos = out["n"].to_numpy(), out["npos"].to_numpy()
        with np.errstate(invalid="ignore", divide="ignore"):
            auc = (out["rs"].to_numpy() - npos * (npos + 1) / 2) / (npos * (n - npos))
        return out["g"].to_numpy(), n, auc

    gid, n, auc_b = per_group(p_base)
    _, _, auc_e = per_group(p_exp)
    ok = np.isfinite(auc_b)
    return gid[ok], n[ok], (auc_e - auc_b)[ok]


def _logloss(y, p):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def _logit(p):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return np.log(p / (1 - p))


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))
