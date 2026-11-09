"""Phase 2: 데이터 신뢰 등급과 몬테카를로 (100번 중 ○번)."""
import sys
import time
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import NaverCurve, simulate  # noqa: E402
from src.engine import coach as C  # noqa: E402
from src.engine import defaults as D  # noqa: E402
from src.engine import montecarlo as MC  # noqa: E402


def _setup(price=20_000, profit=7_000, rep=0.5, budget=210_000):
    df = pd.DataFrame({"bid": [100, 300, 600, 1000], "cost": [20_000, 60_000, 120_000, 200_000],
                       "clicks": [80, 180, 290, 400], "impressions": [0] * 4})
    params = C.coach_params(price, profit, rep)
    sp = C.split_budget(budget, NaverCurve({"원두커피": df}), 1_300.0, params)
    return sp, params


def test_every_engine_input_has_grade():
    for name, (grade, why) in D.INPUT_GRADES.items():
        assert hasattr(D, name), name
        assert grade in D.GRADE_LABELS and why
    assert set(D.GRADE_WIDTH) == set(D.GRADE_LABELS)
    assert D.GRADE_WIDTH == {"A": 0.10, "B": 0.25, "C": 0.40, "D": 0.60}


def test_zero_width_matches_engine():
    sp, params = _setup()
    det = MC.one_month(sp["channels"], sp["spends"], params)
    # 엔진 12개월 시뮬레이션: 매달 같은 코호트 → 한 코호트 = 신규 ÷ 12, 손님 1명 12개월 이익 = ltv_12m
    # 단, 코치는 첫 달을 딱 1번 구매로 셈 (Q1) → 엔진(첫 달도 월 구매 횟수 1.1번)보다 손님 1명당 (1.1 − 1)번 × 판매가 × 마진 적음
    s = simulate(sp["channels"], sp["spends"], params).summary
    assert det["new"] == pytest.approx(s["paid_new"] / params.months)
    ltv_coach = s["ltv_12m"] - (params.purchase_freq - 1) * params.aov * params.margin
    assert det["profit"] == pytest.approx(s["paid_new"] / params.months * ltv_coach - s["spend_total"] / params.months, rel=1e-6)
    zero = MC.run(sp["channels"], sp["spends"], params, C.mc_grades(False), n=50, widths=0.0)
    assert zero["p10"] == pytest.approx(det["profit"]) and zero["p90"] == pytest.approx(det["profit"])


def test_same_seed_same_result_and_fast():
    sp, params = _setup(price=50_000, profit=30_000, rep=2.0)
    g = C.mc_grades(False)
    t = time.time()
    a = MC.run(sp["channels"], sp["spends"], params, g)
    assert time.time() - t < 1.0
    b = MC.run(sp["channels"], sp["spends"], params, g)
    assert a["wins"] == b["wins"] and a["p10"] == b["p10"] and a["n"] == 10_000
    assert a["p10"] < a["p50"] < a["p90"]
    assert a["wins_first"] <= a["wins"]          # 첫 구매만 보면 남는 경우가 더 적거나 같음


def test_action_thresholds():
    assert MC.action(80) == "go" and MC.action(79) == "small" and MC.action(50) == "small" and MC.action(49) == "prep"
    assert C.default_budget_pick(MC.action(49)) == "none" and C.default_budget_pick(MC.action(50)) == "recommended"


@pytest.mark.parametrize("preset", ["거의 안 삼", "가끔", "자주", "매달(정기)"])
def test_one_month_customer_value_matches_breakeven(preset):
    """Q1 (11/10): 손님 1명 가치 = 첫 달 딱 1번 구매 + 그 뒤 재구매. 손익분기 식(남는 돈 × (1 + 재구매))과 시뮬레이션이 같은 값.
    네이버만 봄 (재구매 배수 1.0). 메타는 재구매 배수 0.9 가정이라 손님 1명 가치가 조금 낮은 게 맞음."""
    rep = C.REPURCHASE_PRESETS[preset]
    sp, params = _setup(price=20_000, profit=7_000, rep=rep)
    naver = sp["channels"][0]
    assert naver.key == "naver" and naver.retention_mult == 1.0
    be = C.breakeven(7_000, rep)
    det = MC.one_month([naver], [sp["spends"][0]], params)
    spend = naver.curve.spendable(sp["spends"][0])
    assert det["profit"] == pytest.approx(det["new"] * be.year - spend, rel=1e-6)
    assert det["first_only"] == pytest.approx(det["new"] * be.first - spend, rel=1e-6)
