"""MVP 7e 2단계: 코치 '풀기'를 엔진 하나로 (CO.solve → Answer, Split).

화면(app/main.py)은 입력을 모아 solve를 한 번 부르고, Answer만 읽는다. 네이버 곡선은 화면이 불러와 넘김(바깥 일).
"""
import pandas as pd
import pytest

from src.engine import NaverCurve
from src.engine import coach as C


def _naver_curve(cap_cost=200_000.0, cap_clicks=400.0):
    df = pd.DataFrame({"bid": [100, 300, 600, 1000], "cost": [20_000, 60_000, 120_000, cap_cost],
                       "clicks": [80, 180, 290, cap_clicks], "impressions": [0, 0, 0, 0]})
    return NaverCurve({"원두커피": df})


# ── Split: 배분 결과 (dict → 데이터클래스) ──
def test_split_has_naver_and_meta_legs():
    params = C.coach_params(20_000, 7_000, 0.5)
    sp = C.split_budget(1_000_000, _naver_curve(), 1_300.0, params)
    assert sp.has_naver and sp.naver.spend + sp.meta.spend == pytest.approx(1_000_000)
    assert sp.naver.spend <= sp.naver_capacity + 1 and sp.meta.cpc == 1_300.0
    # 네이버 클릭 비용 = 네이버에 쓴 돈 ÷ 그 돈으로 받는 클릭 (등급표에 보이는 값)
    assert sp.naver.cpc == pytest.approx(sp.naver.spend / sp.naver.curve.clicks(sp.naver.spend))
    assert sp.spends == [sp.naver.spend, sp.meta.spend] and [c.key for c in sp.channels] == ["naver", "meta"]
    assert sp.total == pytest.approx(1_000_000)


def test_split_without_naver_has_no_naver_leg():
    params = C.coach_params(20_000, 7_000, 0.5)
    sp = C.split_budget(210_000, None, 1_300.0, params)
    assert sp.naver is None and not sp.has_naver and sp.spends == [210_000] and sp.meta.cpc == 1_300.0
    assert sp.cpc > 1_300.0          # 평균 클릭 비용은 메타 포화 곡선 때문에 입력값보다 조금 높음


def test_split_still_reads_like_the_old_dict():
    """이전 단계 동안 화면 코드가 그대로 돌도록 예전 키도 읽힘 (main.py 호출부를 옮긴 뒤 지움)."""
    params = C.coach_params(20_000, 7_000, 0.5)
    sp = C.split_budget(1_000_000, _naver_curve(), 1_300.0, params)
    assert sp["naver"] == sp.naver.spend and sp["meta"] == sp.meta.spend and sp["meta_cpc"] == 1_300.0
    assert sp["has_naver"] and sp["spends"] == sp.spends and sp["channels"] == sp.channels
    assert sp["table"] is sp.table and sp["cpc"] == sp.cpc and sp["clicks"] == sp.clicks
    assert sp["naver_capacity"] == sp.naver_capacity and sp["naver_marginal_cpc"] == sp.naver_marginal_cpc
    none = C.split_budget(210_000, None, 1_300.0, params)
    assert none["naver"] == 0.0 and none["naver_marginal_cpc"] is None


# ── solve: 입력 → Answer (main.py 맨 위 계산과 한 달 뒤 다시 계산을 엔진 한 곳으로) ──
from tests.test_coach_examples import EXAMPLES, EXPECTED, _coach  # noqa: E402


def _inputs(name="coffee", meta_cpc=None):
    price, profit, max_budget, kw = EXAMPLES[name]
    return C.CoachInputs(price=price, profit=profit, max_budget=max_budget, keyword=kw, meta_cpc=meta_cpc)


def _example_curve(name="coffee"):
    from src.engine import defaults as D
    from src.engine import naver_source as ns
    kw = EXAMPLES[name][3]
    return NaverCurve({kw: ns.bid_estimate(kw, device=D.NAVER_DEVICE, online=False)})


MONTHLY = C.repurchase_source("매달(정기)")


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_solve_default_matches_example_numbers(name):
    a = C.solve(_inputs(name), _example_curve(name), MONTHLY)
    be, budget, split, mc = _coach(name)
    pick = EXPECTED[name][-1]
    assert a.pick == a.default_pick == pick
    assert a.budget == budget and a.be == be
    assert a.split.spends == pytest.approx(split.spends) and a.mc["wins"] == mc["wins"] and a.mc["p50"] == pytest.approx(mc["p50"])
    assert a.cpc == pytest.approx(split.cpc) and a.need == pytest.approx(C.required_rate(split.cpc, be.first))
    assert a.prediction["budget"] == budget and a.prediction["wins"] == mc["wins"]
    assert a.ch_name == "메타 광고" and a.grades["retention"] == "D"


def test_solve_chosen_budget_resplits_and_rates_follow():
    """B1: 고른 예산으로 다시 나누면 클릭 비용·필요 구매율도 그 배분 값."""
    rec = C.solve(_inputs("protein"), _example_curve("protein"), MONTHLY)
    small = C.solve(_inputs("protein"), _example_curve("protein"), MONTHLY, pick="small")
    amount = next(o["amount"] for o in small.options if o["key"] == "small")
    assert small.pick == "small" and small.budget == amount and small.split.total == pytest.approx(amount)
    assert small.default_pick == rec.default_pick == "recommended"     # 기본 선택은 권장 예산 결과로 정함
    assert small.cpc == pytest.approx(small.split.cpc) and small.cpc != pytest.approx(rec.cpc)
    assert small.need == pytest.approx(C.required_rate(small.split.cpc, small.be.first))
    assert small.prediction["budget"] == amount and small.prediction["cpc"] == pytest.approx(small.split.cpc)


def test_solve_no_ads_keeps_recommended_budget_for_simulation():
    a = C.solve(_inputs("protein"), _example_curve("protein"), MONTHLY, pick="none")
    rec = next(o["amount"] for o in a.options if o["key"] == "recommended")
    assert a.pick == "none" and a.budget == rec
    assert C.solve(_inputs("protein"), _example_curve("protein"), MONTHLY, pick="없는 값").pick == "recommended"


def test_solve_without_keyword_goes_all_meta():
    a = C.solve(C.CoachInputs(20_000, 7_000, 300_000), None, MONTHLY)
    assert not a.split.has_naver and a.ch_name == "메타 광고" and a.cpc_src.startswith("메타 대략값")
    typed = C.solve(C.CoachInputs(20_000, 7_000, 300_000, meta_cpc=900.0), None, MONTHLY)
    assert typed.split.meta.cpc == 900.0 and typed.grades["cpc_meta"] == "A" and typed.cpc_src.endswith("메타 클릭 비용 직접 입력")


def test_repurchase_source_preset_measured_and_fallback():
    assert MONTHLY.per_year == 6.0 and MONTHLY.grade == "D" and MONTHLY.word == "다 쓰면 매달 다시 사요(정기)"
    m = C.repurchase_source(C.MEASURED, {"repeats_year": 1.84})
    assert (m.name, m.per_year, m.grade, m.word) == (C.MEASURED, 1.84, "C", "내 가게 실측 (1.8번)")
    # 실측을 골랐는데 주문 내역이 없으면 '가끔' (계획 파일을 불러온 경우 등)
    assert C.repurchase_source(C.MEASURED, None).name == "가끔" and C.repurchase_source("모름").per_year == 0.5
    a = C.solve(_inputs("coffee"), _example_curve("coffee"), m)
    assert a.grades["retention"] == "C" and a.be.year == pytest.approx(7_000 * 2.84)


def test_solve_with_actuals_recalculates_with_measured_numbers():
    """한 달 뒤: 실측 클릭 비용·구매 비율로 다시 계산 (등급 A). B2: 재구매 등급은 처음 계산과 같음 (실측이면 C)."""
    m = C.repurchase_source(C.MEASURED, {"repeats_year": 1.84})
    base = C.solve(_inputs("protein"), _example_curve("protein"), m)
    act = C.Actuals(naver_clicks=100, naver_cost=150_000, meta_clicks=200, meta_cost=300_000, orders=9)
    a = C.solve(_inputs("protein"), _example_curve("protein"), m, pick=base.pick, actuals=act)
    assert a.budget == base.budget and a.split.meta.cpc == pytest.approx(1_500)
    assert a.params.cvr == pytest.approx(9 / 300)
    assert a.grades == {"aov": "A", "margin": "A", "cpc_naver": "A", "cpc_meta": "A", "cvr": "A", "retention": "C"}
    # 네이버 곡선은 같은 돈에 실제 클릭 ÷ 예상 클릭 배수로 보정
    expected_clicks = base.split.naver.curve.clicks(150_000)
    assert a.split.naver.curve.clicks(150_000) == pytest.approx(100) and expected_clicks != pytest.approx(100)
    none = C.solve(_inputs("protein"), _example_curve("protein"), MONTHLY, actuals=C.Actuals(orders=3))
    assert none.grades["cpc_naver"] == "B" and none.grades["cvr"] == "C" and none.grades["retention"] == "D"
    assert none.params.cvr == pytest.approx(base.params.cvr)
