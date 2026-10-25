from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TargetSpec:
    """口径卡：一个目标模型参与评估所依据的口径（术语见 CONTEXT.md，字段见方案 3.0）。"""

    name: str
    label: str = "label"
    label_type: str = "binary"  # 连续型指标族（方案 3.1.4）尚未实现
    group_key: str = "user_id"  # 聚类 bootstrap 与 GAUC 的分组键
    day_key: str = "day"
    maturity_days: int = 0  # valid 日必须 ≤ 数据末日 − 成熟期
    primary_metric: str = "auc"  # auc | gauc | logloss（logloss 越小越好，Δ 已取反）
    population: str | None = None  # 适用人群：布尔/0-1 列名；None = 全部样本
    online_score: str | None = None  # 线上模型离线回放分列名；None = 不做残差分析

    def __post_init__(self):
        if self.label_type != "binary":
            raise NotImplementedError(f"{self.name}: 只实现了二分类 label，连续型见方案 3.1.4")
        if self.primary_metric not in ("auc", "gauc", "logloss"):
            raise ValueError(f"{self.name}: 未知主指标 {self.primary_metric}")
