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
