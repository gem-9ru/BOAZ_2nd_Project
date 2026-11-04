"""기획안 13장 결정 사항 반영 테스트."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import Channel, FunnelParams, MetaCurve, NaverCurve, simulate  # noqa: E402
from src.engine import data_loader as dl  # noqa: E402
from src.engine import defaults as D  # noqa: E402
from src.engine.insights import insights, warnings  # noqa: E402
from src.engine.optimize import lever_table  # noqa: E402


def meta(cpc=1000.0):
    return Channel("meta", "메타", MetaCurve(cpc, 0.0))


def test_keyword_tiers_by_monthly_search():  # 결정 6
    assert dl.keyword_tier(30_000) == "대표"
    assert dl.keyword_tier(29_999) == "세부"
    assert dl.keyword_tier(1_000) == "세부"
    assert dl.keyword_tier(999) == "롱테일"


def test_pmf_warning_uses_ltv_cac():  # 결정 5
    cheap = simulate([meta(cpc=10)], [1_000_000], FunnelParams())
    pricey = simulate([meta(cpc=100_000)], [1_000_000], FunnelParams())
    assert cheap.summary["ltv_cac"] > 1 and not any("PMF" in t for _, t in warnings(cheap))
    assert pricey.summary["ltv_cac"] < 1 and any("PMF" in t for _, t in warnings(pricey))


def test_ga4_funnel_defaults_match_plan():  # 기획안 3-2 GA4 표
    steps, _ = dl.funnel_steps()
    rates = dict(steps)
    assert rates["관심 행동"] == pytest.approx(0.229, abs=1e-3)
    assert rates["과업 시작"] == pytest.approx(0.205, abs=1e-3)
    assert rates["과업 진행"] == pytest.approx(0.774, abs=1e-3)
    assert rates["과업 완료"] == pytest.approx(0.455, abs=1e-3)


def test_meta_target_multiplier():  # 결정 3: 상대 배수만 사용
    assert dl.target_multiplier([]) == 1.0
    assert dl.target_multiplier(["30-34 남"]) == pytest.approx(D.META_TARGETS["30-34 남"][0])
    t = dl.meta_targets()
    assert (t["low"] < t["rel_cpa"]).all() and (t["rel_cpa"] < t["high"]).all()


def test_keyword_saturation_flag():
    df = pd.DataFrame({"bid": [2000, 5000, 8000], "impressions": [1, 1, 1], "clicks": [961, 1869, 1900],
                       "cost": [1_638_349, 7_373_537, 12_000_000]})
    nv = NaverCurve({"kw": df})
    assert not nv.allocation(1_000_000)["saturated"].iloc[0]  # 한계 = 평균 1,705원
    assert not nv.allocation(7_000_000)["saturated"].iloc[0]  # 한계 6,317원 < 평균 3,867원 × 2
    assert nv.allocation(10_000_000)["saturated"].iloc[0]     # 한계 약 149,000원 ≫ 평균 × 2


def test_insight_cards_have_evidence_and_action():
    res = simulate([meta()], [1_000_000], FunnelParams())
    lv = lever_table([meta()], [1_000_000], FunnelParams())
    cards = insights(res, lv, {}, "12개월 누적 이익")
    assert cards and all(c["title"] and c["evidence"] and c["action"] for c in cards)


def test_cvr_mult_single_owner():  # MECE #4: CSV > GA4 매체별 > 기본값, 하나만 채택
    up = pd.DataFrame({"CVR": [0.02]}, index=["naver"])
    m, src = dl.resolve_cvr_mult("naver", 1.0, 0.01, upload=up)
    assert m == pytest.approx(2.0) and "CSV" in src
    m, src = dl.resolve_cvr_mult("naver", 1.0, 0.01)
    assert m == pytest.approx(dl.ga4_medium_cvr("cpc") / dl.ga4_medium_cvr()) and "GA4" in src
    assert dl.ga4_medium_cvr("cpc") == pytest.approx(0.0119, abs=5e-4)
    assert dl.resolve_cvr_mult("naver", 1.0, 0.01, funnel_medium="cpc")[0] == 1.0  # 퍼널이 이미 cpc면 다시 곱하지 않음
    m, src = dl.resolve_cvr_mult("meta", D.META_CVR_MULT, 0.01)
    assert m == D.META_CVR_MULT and "가정값" in src


def test_meta_learning_and_cpm():
    from src.engine.acquisition import cpc_from_cpm, learning_check
    assert cpc_from_cpm(10_000, 0.01) == pytest.approx(1_000)
    small = learning_check(1_000_000, ad_sets=2, cpa=20_000)   # 주 23만 원 < 2×50×2만 원
    assert not small["ok"] and small["weekly_needed"] == pytest.approx(2_000_000)
    assert learning_check(100_000_000, 1, 20_000)["ok"]


def test_segment_table_and_ztest():
    t = dl.segment_table("medium")
    assert "(data deleted)" not in t.index
    assert t.loc["cpc", "방문→완료"] == pytest.approx(0.0119, abs=5e-4)
    z, p = dl.two_prop_z(t.loc["referral", "purchases"], t.loc["referral", "visitors"], t.loc["cpc", "purchases"], t.loc["cpc", "visitors"])
    assert z > 0 and p < 0.05
    assert dl.two_prop_z(10, 1000, 10, 1000)[1] == pytest.approx(1.0)


def test_compare_options_same_basis():
    from src.engine.optimize import compare_options
    ch = [Channel("meta", "메타", MetaCurve(100.0, 0.0))]
    lv = lever_table(ch, [1_000_000], FunnelParams())
    df = compare_options(ch, [1_000_000], FunnelParams(), lv, 1_000_000, pmf_warning=True).set_index("option")
    assert set(df.index) == {"광고비 증액", "채널 재배분", "퍼널 개선", "자동 메시지"}
    assert df.loc["광고비 증액", "disabled"] and df.loc["채널 재배분", "gain"] >= 0
    assert df.loc["퍼널 개선", "cost_kind"] == "ceiling"
    assert sum(df.loc["채널 재배분", "spends"]) == pytest.approx(1_000_000)   # 같은 예산 (덜 쓰기 아님)
