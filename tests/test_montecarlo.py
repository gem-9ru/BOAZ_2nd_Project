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
    s = simulate(sp["channels"], sp["spends"], params).summary
    assert det["new"] == pytest.approx(s["paid_new"] / params.months)
    assert det["profit"] == pytest.approx(s["paid_new"] / params.months * s["ltv_12m"] - s["spend_total"] / params.months, rel=1e-6)
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
