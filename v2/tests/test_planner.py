"""planner·datacheck 테스트 (네트워크 없음)."""
import math

import pandas as pd

from v2.engine import datacheck, ingest, planner, specs


def _kw(volumes, intents=None):
    df = pd.DataFrame({"keyword": ["k%d" % i for i in range(len(volumes))], "total_qc": volumes})
    if intents:
        df["intent"] = intents
    return df


def test_demand_cap_sends_rest_to_meta():
    # 검색수 합 1,000 × 클릭률 2.1% × 700원 = 14,700원 → 예산 몫(15만)보다 훨씬 작다
    p = planner.plan_budget(300000, _kw([500, 300, 200]))
    assert p.demand_capped is True
    assert p.naver_cap_month == 14700
    assert p.naver_month == 14700
    assert p.meta_month == 300000 - 14700
    assert p.naver_month + p.meta_month == p.budget
    assert any("메타" in n and "C" in n for n in p.notes)


def test_large_demand_not_capped_uses_share():
    p = planner.plan_budget(300000, _kw([100000, 80000]))
    assert p.demand_capped is False
    assert p.naver_month == 150000 and p.meta_month == 150000


def test_no_keywords_uses_share_without_cap():
    for kw in (None, pd.DataFrame()):
        p = planner.plan_budget(300000, kw)
        assert p.naver_cap_month is None and p.demand_capped is False
        assert p.naver_month == 150000
    p = planner.plan_budget(300000, None, naver_share_max=0.3)
    assert p.naver_month == 90000


def test_excluded_intents_and_text_volumes_ignored():
    df = _kw([1000, 5000, "< 10"], ["상품", "제외: 만들기", "상품"])
    p = planner.plan_budget(300000, df)
    assert p.naver_cap_month == 14700


def test_money_rounded_to_10_won():
    p = planner.plan_budget(299995, _kw([333, 777]), days=11)
    for v in (p.budget, p.naver_month, p.meta_month, p.naver_daily, p.meta_daily, p.naver_bid):
        assert v % 10 == 0
    assert p.naver_daily == planner.round10(p.naver_month / 30.0)
    assert p.meta_daily == planner.round10(p.meta_month / 11.0)
    assert planner.round10(15) == 20 and planner.round10(14) == 10


def test_traffic_vs_awareness_forecast():
    t = planner.plan_budget(300000, None, objective="트래픽", target_key="넓게")
    a = planner.plan_budget(300000, None, objective="인지도", target_key="넓게")
    assert t.meta_forecast["link_clicks"] > 0
    assert a.meta_forecast["link_clicks"] == 0
    # 인지도 CPM이 훨씬 싸서 같은 돈으로 더 많이 보여 줌
    assert a.meta_forecast["impressions"] > t.meta_forecast["impressions"]
    assert a.meta_forecast["cpm_high"] < t.meta_forecast["cpm_low"]
    m = specs.assumptions()["meta"]
    expect = t.meta_forecast["impressions"] * m["link_ctr"]["value"]
    assert abs(t.meta_forecast["link_clicks"] - expect) < 1e-6
    assert any("근거" in n for n in t.notes)
    assert any("클릭 수는 예측하지 않아요" in n for n in a.notes)


def test_narrow_awareness_uses_narrow_cpm():
    narrow = planner.plan_budget(300000, None, objective="인지도", target_key="20~39 여성")
    assert narrow.meta_forecast["cpm_low"] == 1900 and narrow.meta_forecast["cpm_high"] == 2400


def test_reach_never_exceeds_target():
    targets = specs.assumptions()["meta"]["effective_target"]
    for key, spec in targets.items():
        for budget in (10000, 300000, 50000000):
            p = planner.plan_budget(budget, None, objective="인지도", target_key=key, naver_share_max=0)
            f = p.meta_forecast
            assert f["reach"] <= spec["value"]
            assert f["reach"] <= f["impressions"] + 1e-9
            if f["reach"] > 0:
                assert f["frequency"] >= 1.0 - 1e-9
    # 아주 큰 예산이면 거의 다 닿고, 작은 예산이면 노출≈도달
    big = planner.reach_from_impressions(1e12, 60000)
    assert big <= 60000 and math.isclose(big, 60000, rel_tol=1e-6)
    assert planner.reach_from_impressions(1000, 850000) > 999


def test_weekly_frequency_and_naver_forecast():
    p = planner.plan_budget(300000, None, days=14)
    f = p.meta_forecast
    assert math.isclose(f["weekly_frequency"], f["frequency"] / 2.0)
    assert math.isclose(p.naver_forecast["clicks"], p.naver_month / 700.0)
    q = planner.plan_budget(300000, None, cpc=500)
    assert q.naver_bid == 500 and q.naver_forecast["clicks"] > p.naver_forecast["clicks"]


def test_bad_inputs_are_plain_errors():
    import pytest
    with pytest.raises(ValueError):
        planner.plan_budget(300000, None, objective="전환")
    with pytest.raises(ValueError):
        planner.plan_budget(300000, None, target_key="없는타겟")
    with pytest.raises(ValueError):
        planner.plan_budget(300000, None, days=0)


def test_zero_budget_is_safe():
    p = planner.plan_budget(0, _kw([100]))
    assert p.naver_month == 0 and p.meta_month == 0 and p.meta_forecast["reach"] == 0


def test_datacheck_demo_table():
    t = datacheck.check(ingest.demo())
    assert list(t.columns) == ["가정", "기대 범위", "관측값", "케이스", "통과"]
    assert len(t) >= 10
    assert t["통과"].dtype == bool
    assert {"C1", "C2", "C3", "C4"} <= set(t["케이스"])
    assert t["통과"].sum() >= len(t) // 2
    by = {(r["가정"].split(" [")[0], r["케이스"]): r for _, r in t.iterrows()}
    assert by[("메타 CPM (트래픽)", "C2")]["통과"]
    assert not by[("메타 CPM (인지도·좁은 타겟)", "C3")]["통과"]     # 가상 실제가 가정보다 비쌈
    assert "예측 대비 실제 지출 차이" in set(x[0] for x in by)


def test_datacheck_excludes_brand_keyword():
    b = ingest.demo()
    with_brand = datacheck.check(b, brand_keywords=())
    without = datacheck.check(b)
    pick = lambda t: t[(t["가정"].str.startswith("네이버 클릭당")) & (t["케이스"] == "C1")]["관측값"].iloc[0]
    assert pick(with_brand) != pick(without)


def test_datacheck_empty_bundle():
    t = datacheck.check(ingest.Bundle())
    assert len(t) == 0 and list(t.columns) == datacheck.COLUMNS
