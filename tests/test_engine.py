import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import (Channel, FunnelParams, MetaCurve, NaverCurve,  # noqa: E402
                        lever_table, optimize_allocation, simulate)


def meta(cpc=1000.0, sat=0.0, cvr_mult=1.0, ret_mult=1.0):
    return Channel("meta", "메타", MetaCurve(cpc, sat), cvr_mult, ret_mult)


def naver_curve():
    # 계단 모양 예상 실적 (필라테스 실제 응답과 같은 형태)
    df = pd.DataFrame({
        "bid": [500, 1000, 2000, 5000, 8000],
        "impressions": [4188, 28438, 76938, 99178, 99178],
        "clicks": [0, 0, 961, 1869, 1869],
        "cost": [0, 0, 1_638_349, 7_373_537, 9_000_000],
    })
    return NaverCurve({"kw": df})


def test_zero_budget_zero_paid_customers():
    chs = [Channel("naver", "네이버", naver_curve()), meta()]
    res = simulate(chs, [0, 0], FunnelParams())
    assert res.summary["paid_new"] == 0
    assert res.summary["new_customers"] == 0
    assert res.summary["revenue"] == 0
    assert res.summary["profit_12m"] == 0
    assert res.summary["paid_cac"] is None


def test_zero_retention_no_repeat_revenue():
    p = FunnelParams(retention_floor=0.0, retention_decay=1e6)
    res = simulate([meta()], [500_000], p)
    assert res.summary["new_customers"] > 0
    assert res.summary["repeat_revenue"] == pytest.approx(0.0, abs=1e-6)
    assert res.summary["revenue"] == pytest.approx(res.summary["new_revenue"])


def test_hand_computed_small_case():
    # 메타 CPC 1,000원 고정 → 월 10만 원 = 100클릭, 전환율 10% → 월 10명
    # r(1) = 0.5, 구매 빈도 1, 객단가 1만 원, 마진 50%, 2개월
    p = FunnelParams(steps=[("완료", 0.1)], retention_floor=0.5, retention_decay=1e6,
                     purchase_freq=1.0, aov=10_000, margin=0.5, invite_rate=0.0, months=2)
    res = simulate([meta()], [100_000], p)
    m = res.monthly
    assert m["active"].tolist() == pytest.approx([10, 15])
    assert m["revenue"].tolist() == pytest.approx([100_000, 150_000])
    assert m["profit"].tolist() == pytest.approx([-50_000, -25_000])
    s = res.summary
    assert s["paid_new"] == pytest.approx(20)
    assert s["paid_cac"] == pytest.approx(10_000)
    assert s["ltv_12m"] == pytest.approx(7_500)        # (1 + 0.5) × 1만 원 × 50%
    assert s["roas"] == pytest.approx(1.0)              # 첫 구매 매출 20만 / 광고비 20만
    assert s["repeat_revenue"] == pytest.approx(50_000)
    assert s["profit_12m"] == pytest.approx(-75_000)
    assert s["payback_month"] == 3                      # 5,000 + 2,500 + 2,500 ≥ 10,000 → 3개월째


def test_referral_feeds_next_month():
    p = FunnelParams(steps=[("완료", 0.1)], retention_floor=0.0, retention_decay=1e6,
                     invite_rate=0.5, invite_conv=0.2, months=3)
    res = simulate([meta()], [100_000], p)
    # 1달 활성 10명 × 0.1 = 2달째 추천 신규 1명
    assert res.monthly["referral_new"].tolist() == pytest.approx([0, 1.0, 1.1])
    assert res.summary["blended_cac"] < res.summary["paid_cac"]


def test_naver_curve_monotone_and_capacity():
    nv = naver_curve()
    xs = np.linspace(0, 10_000_000, 50)
    ys = [nv.clicks(x) for x in xs]
    assert all(b >= a - 1e-9 for a, b in zip(ys, ys[1:]))
    assert nv.clicks(1_638_349) == pytest.approx(961)
    assert nv.capacity == pytest.approx(7_373_537)      # 클릭이 더 늘지 않는 8,000원 입찰은 제외
    res = simulate([Channel("naver", "네이버", nv)], [9_000_000], FunnelParams())
    assert res.by_channel.loc[0, "unspent"] == pytest.approx(9_000_000 - 7_373_537)


def test_meta_saturation_raises_cpc():
    c = MetaCurve(700, 0.5)
    assert c.clicks(2_000_000) / 2_000_000 < c.clicks(500_000) / 500_000


def test_optimizer_prefers_cheaper_channel():
    chs = [meta(cpc=500, sat=0.2), meta(cpc=2000, sat=0.2)]
    out = optimize_allocation(chs, 1_000_000, FunnelParams(), "new_customers")
    assert out["spends"][0] > out["spends"][1]
    assert sum(out["spends"]) == pytest.approx(1_000_000, rel=1e-3)


def test_profit_optimizer_can_leave_budget_unspent():
    # 마진이 아주 낮으면 광고비를 쓸수록 손해 → 쓰지 않는 것이 최적
    p = FunnelParams(margin=0.01)
    out = optimize_allocation([meta()], 1_000_000, p, "profit")
    assert sum(out["spends"]) < 1_000_000 * 0.05


def test_lever_table_has_core_levers():
    df = lever_table([meta()], [1_000_000], FunnelParams())
    assert {"spend", "cvr", "retention", "aov"} <= set(df["key"])
    assert (df.set_index("key").loc[["cvr", "retention", "aov"], "up"] > 0).all()


def test_naver_estimate_converted_to_month():
    # 네이버 예상 실적은 과거 28일 기준 → 30.4/28로 월 환산 (캐시 원본은 그대로)
    import json
    from src.engine import defaults as D, naver_source as ns
    raw = json.loads(ns._cache_path("estimate", f"{ns.SAMPLE_KEYWORD}|{D.NAVER_DEVICE}").read_text(encoding="utf-8"))
    raw = pd.DataFrame(raw["response"]["estimate"]).astype({"clicks": float, "cost": float}).sort_values("bid").reset_index(drop=True)
    est = ns.bid_estimate(ns.SAMPLE_KEYWORD, device=D.NAVER_DEVICE, online=False)
    factor = D.DAYS_PER_MONTH / D.NAVER_ESTIMATE_DAYS
    assert factor == pytest.approx(30.4 / 28)
    assert est["bid"].tolist() == raw["bid"].astype(float).tolist()
    assert np.allclose(est["clicks"], raw["clicks"] * factor)
    assert np.allclose(est["cost"], raw["cost"] * factor)
    pos = raw["clicks"] > 0
    assert np.allclose(est.loc[pos, "cost"] / est.loc[pos, "clicks"], raw.loc[pos, "cost"] / raw.loc[pos, "clicks"])
