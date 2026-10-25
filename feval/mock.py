"""带真值的 mock 数据：本地验证与评估器校准用（方案 7.1）。真值写死在生成过程里，判据对不对一查便知。"""

from __future__ import annotations

import numpy as np
import polars as pl

BASE = ["b1", "b2", "b3", "slot", "is_game"]
POSITIVE_CONTROL = "b1"  # 正对照：从基线移出后当候选，应被建议入模

TRUTH = {
    "c_strong": "增量",
    "c_user": "增量（用户级）",
    "c_weak": "弱增量",
    "c_ushape": "增量（非单调）",
    "c_dup": "与 c_strong 互为冗余",
    "c_redundant": "冗余（基线已含）",
    "c_redundant2": "冗余（基线已含）",
    "c_noise": "噪声",
    "c_leak": "泄漏",
    "c_drift": "漂移",
    "c_game": "行业专属",
}
CANDIDATES = list(TRUTH)
FEATURE_DOMAIN = {"c_game": "is_game"}  # 特征定义域：c_game 只对游戏广告有定义


def probe_names(n_probes: int = 3) -> dict[str, str]:
    """负对照（噪声探针）：样本级、用户×天级、用户级常量各 n_probes 个。

    用户级常量随机数能区分用户，代理模型（没有 ID embedding）可能借它记住持久的用户效应，未必是干净的负对照。"""
    names = {f"probe_row_{i}": "噪声探针（样本级）" for i in range(n_probes)}
    names.update({f"probe_userday_{i}": "噪声探针（用户×天级）" for i in range(n_probes)})
    names.update({f"probe_user_{i}": "噪声探针（用户级常量）" for i in range(n_probes)})
    return names


def make_ctr_mock(seed=0, n_users=1500, days=8, rows_per_day=15000, n_probes=3) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    n = days * rows_per_day
    day = np.repeat(np.arange(days), rows_per_day)
    activity = rng.lognormal(0, 1.2, n_users)  # 人均曝光重尾：少数重度用户贡献大量样本，组内相关才像真实流量
    user = rng.choice(n_users, n, p=activity / activity.sum())
    # 用户×天随机效应：制造组内相关；不跨天持续，所以用户级噪声探针学不到它
    u_eff = rng.normal(0, 0.5, (n_users, days))[user, day]
    user_feat = rng.normal(size=n_users)[user]  # 用户级特征：同一用户取值不变，效应跨天持续
    b1, b2, b3, strong, weak, ushape, z_drift, game_raw = rng.normal(size=(8, n))
    slot = rng.integers(0, 5, n)
    is_game = (rng.random(n) < 0.3).astype(np.int8)
    base_logit = -3.0 + 0.6 * b1 + 0.4 * b2 - 0.3 * b3 + np.array([0.0, 0.3, -0.2, 0.5, -0.4])[slot]
    logit = (base_logit + 0.5 * strong + 0.3 * user_feat + 0.15 * weak + 0.35 * (ushape**2 - 1)
             + 0.4 * z_drift + 0.6 * game_raw * is_game + u_eff)
    label = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(np.int8)
    cols = {
        "user_id": user, "day": day, "label": label,
        "p_online": 1 / (1 + np.exp(-base_logit)),  # 线上模型只掌握基线特征
        "b1": b1, "b2": b2, "b3": b3, "slot": slot, "is_game": is_game,
        "c_strong": strong,
        "c_user": user_feat,
        "c_weak": weak,
        "c_ushape": ushape,
        "c_dup": strong + rng.normal(0, 0.3, n),
        "c_redundant": b1 + rng.normal(0, 0.3, n),
        "c_redundant2": b2 + rng.normal(0, 0.3, n),
        "c_noise": rng.normal(size=n),
        "c_leak": 1.5 * label + rng.normal(size=n),
        "c_drift": z_drift + 0.08 * day,
        "c_game": np.where(is_game == 1, game_raw, np.nan),  # 只在游戏广告上有值
    }
    for i in range(n_probes):
        cols[f"probe_row_{i}"] = rng.normal(size=n)
        cols[f"probe_userday_{i}"] = rng.normal(size=(n_users, days))[user, day]
        cols[f"probe_user_{i}"] = rng.normal(size=n_users)[user]
    return pl.DataFrame(cols).with_columns(pl.col("c_game").fill_nan(None))
