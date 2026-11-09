"""예시 1(원두)·2(단백질 쉐이크) 숫자 고정 (MVP 7e: 리팩토링 전후 같은 숫자인지).

app/main.py의 코치 계산(권장 예산 → 배분 → 100번 돌리기)과 같은 순서로 계산한다. 네이버 예상 실적은 저장된 캐시(오프라인).
기대값은 리팩토링 시작 전(61f6921) 앱 계산에서 잰 값. 결정된 변경(Q1 손님 가치)으로 바뀌는 값은 그 커밋에서 함께 고치고 이유를 적는다.
"""
import numpy as np
import pytest

from src.engine import coach as CO
from src.engine import defaults as D
from src.engine import montecarlo as MC
from src.engine import naver_source as ns
from src.engine.acquisition import NaverCurve

EXAMPLES = {"coffee": (20_000, 7_000, 300_000, "원두커피"), "protein": (79_000, 39_500, 500_000, "프로틴쉐이크")}


def _coach(name: str, with_naver: bool = True):
    price, profit, max_budget, kw = EXAMPLES[name]
    rep = CO.REPURCHASE_PRESETS["매달(정기)"]
    be = CO.breakeven(profit, rep)
    est = ns.bid_estimate(kw, device=D.NAVER_DEVICE, online=False)
    curve = NaverCurve({kw: est}) if (with_naver and est is not None) else None
    params = CO.coach_params(price, profit, rep)
    options = CO.budget_options(be.first, max_budget)
    budget = next(o["amount"] for o in options if o["key"] == "recommended")
    split = CO.split_budget(budget, curve, float(D.NAVER_FALLBACK_CPC), params)
    mc = MC.run(split["channels"], split["spends"], params, CO.mc_grades(False))
    return be, budget, split, mc


# (권장 예산, 네이버, 메타, 평균 클릭 비용, 100번 중, p10, p50, p90, 기본 선택)
EXPECTED = {
    "coffee": (210_000, 67_664, 142_336, 1_503.0, 3, -177_603, -142_905, -66_744, "none"),
    "protein": (500_000, 120_635, 379_365, 1_469.8, 85, -62_980, 412_543, 1_459_959, "recommended"),
}
EXPECTED_META_ONLY = {"coffee": (4, -183_503, -147_248, -60_692), "protein": (75, -170_929, 279_310, 1_354_249)}


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_example_split_and_odds_stay_the_same(name):
    be, budget, split, mc = _coach(name)
    budget_x, naver, meta, cpc, wins, p10, p50, p90, pick = EXPECTED[name]
    assert budget == budget_x
    assert split["naver"] == pytest.approx(naver, abs=1)
    assert split["meta"] == pytest.approx(meta, abs=1)
    assert split["cpc"] == pytest.approx(cpc, abs=0.1)
    assert mc["wins"] == wins
    assert (mc["p10"], mc["p50"], mc["p90"]) == pytest.approx((p10, p50, p90), abs=1)
    assert CO.default_budget_pick(MC.action(mc["wins"])) == pick


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_example_meta_only_odds_stay_the_same(name):
    _, _, split, mc = _coach(name, with_naver=False)
    wins, p10, p50, p90 = EXPECTED_META_ONLY[name]
    assert split["naver"] == 0 and not split["has_naver"]
    assert mc["wins"] == wins
    assert (mc["p10"], mc["p50"], mc["p90"]) == pytest.approx((p10, p50, p90), abs=1)


def test_example_new_customers_stay_the_same():
    assert float(np.mean(_coach("coffee")[3]["new"])) == pytest.approx(1.58, abs=0.005)
    assert float(np.mean(_coach("protein")[3]["new"])) == pytest.approx(3.82, abs=0.005)
