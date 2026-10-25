import numpy as np
import polars as pl
import pytest

from feval import l1, l2
from feval.mock import BASE, FEATURE_DOMAIN, make_ctr_mock
from feval.pipeline import evaluate
from feval.spec import TargetSpec


# —— 口径基准：Spark 后端必须复现这些数（ADR-0002）——

def test_auc_grouped_matches_pairwise_definition_with_ties():
    rng = np.random.default_rng(0)
    s = rng.integers(0, 5, 300).astype(float)  # 大量并列
    y = (rng.random(300) < 0.3).astype(float)
    pos, neg = s[y == 1], s[y == 0]
    expected = ((pos[:, None] > neg[None, :]) + 0.5 * (pos[:, None] == neg[None, :])).mean()
    assert l1.auc_grouped(s, y, 1 - y)[0] == pytest.approx(expected)


def test_iv_golden():
    assert l1.iv_terms(np.array([10.0, 30.0]), np.array([90.0, 70.0]), smooth=0).sum() == pytest.approx(0.421853, abs=1e-6)


def test_psi_golden():
    e = np.array([50.0, 50.0])
    assert l1.psi(e, e) == pytest.approx(0)
    assert l1.psi(e, np.array([60.0, 40.0])) == pytest.approx(0.040546, abs=1e-6)


# —— L1 ——

def test_bins_keep_min_positives_and_separate_missing():
    rng = np.random.default_rng(1)
    x = rng.normal(size=20000)
    y = (rng.random(20000) < 0.02).astype(np.int64)  # 约 400 个正样本 → k = 4
    x[:1000] = np.nan
    codes, categorical = l1.bin_codes(pl.Series(x), y)
    ct = l1.count_table(codes, y).filter(pl.col("bin") != l1.MISSING)
    assert not categorical and (codes[:1000] == l1.MISSING).all()
    assert ct.height <= 4 and (ct["pos"] >= l1.MIN_POS_PER_BIN).all()


OK = dict(n_pos=1000, iv=0.05, auc_offset=0.03, psi=0.01, missing_rate=0.0, missing_iv=0.0)


@pytest.mark.parametrize("override, expected", [
    ({}, "通过"),
    ({"n_pos": 200}, "样本不足"),
    ({"iv": 0.8}, "疑似泄漏"),
    ({"iv": 0.01, "auc_offset": 0.001}, "拒绝"),
    ({"iv": 0.01, "auc_offset": 0.01}, "观察"),
    ({"psi": 0.3}, "拒绝"),
    ({"psi": 0.15}, "观察"),
    ({"missing_rate": 0.3}, "拒绝"),
    ({"missing_rate": 0.3, "missing_iv": 0.03}, "通过"),
    ({"missing_rate": 0.1}, "观察"),
])
def test_grade_table(override, expected):
    assert l1.grade({**OK, **override}) == expected


def test_missing_rate_counts_only_feature_domain():
    df = make_ctr_mock(seed=0, rows_per_day=3000)
    spec = TargetSpec("CTR")
    assert l1.screen(df, "c_game", spec)["missing_rate"] > 0.6
    assert l1.screen(df, "c_game", spec, domain="is_game")["missing_rate"] == 0.0


def test_target_spec_rejects_unimplemented_label_type():
    with pytest.raises(NotImplementedError):
        TargetSpec("PLTV", label_type="continuous")


# —— L2 ——

def test_bootstrap_of_identical_predictions_is_zero():
    rng = np.random.default_rng(2)
    y = (rng.random(2000) < 0.2).astype(float)
    p, g = rng.random(2000), rng.integers(0, 100, 2000)
    for scheme in ("cluster", "sample"):
        for v in l2.paired_bootstrap(y, p, p, g, B=50, scheme=scheme).values():
            assert v == pytest.approx((0, 0, 0))


def test_superiority_rule_rejects_what_v01_admits():
    # 冗余特征的典型形态：点估计略正、CI 跨 0
    assert l2.decide_v01(point=0.0003, lo=-0.0003) == "建议入模"
    assert l2.decide([(-0.0003, 0.0009)]) == "无显著增量"
    assert l2.decide([(-0.0003, 0.0009), (0.0002, 0.002)]) == "建议入模"  # 任一代理优效即可
    assert l2.decide([(-0.003, -0.001), (-0.002, -0.0005)]) == "有害"
    assert l2.decide([(-0.003, -0.001), (-0.002, 0.0005)]) == "无显著增量"


def test_pipeline_on_mock_matches_truth():
    df = make_ctr_mock(seed=3, rows_per_day=8000)
    rows = evaluate(df, TargetSpec("CTR", online_score="p_online"), BASE,
                    ["c_strong", "c_ushape", "b1", "c_noise", "c_leak", "c_drift"], B=100, domains=FEATURE_DOMAIN)
    got = {c: r["conclusion"] for c, r in rows.items()}
    assert got == {"c_strong": "建议入模", "c_ushape": "建议入模", "b1": "建议入模",  # b1 为正对照
                   "c_noise": "拒绝", "c_leak": "疑似泄漏", "c_drift": "拒绝"}
