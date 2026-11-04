"""M4 자동화 (명세 5장)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import Channel, FunnelParams, MetaCurve, simulate  # noqa: E402
from src.engine import automation as AU  # noqa: E402

CH = [Channel("meta", "메타", MetaCurve(300.0, 0.0))]
SP = [1_000_000]


def test_breakeven_rate_formula():
    # 명세 예: 객단가 6만 원, 마진 35% → 반응 1건 이익 2.1만 원
    assert AU.breakeven_rate(21, 60_000, 0.35) == pytest.approx(0.001)
    assert AU.breakeven_rate(21, 60_000, 0.35, discount=0.5) == pytest.approx(0.002)


def test_extra_cost_reduces_profit():
    a = simulate(CH, SP, FunnelParams()).summary
    b = simulate(CH, SP, FunnelParams(), extra_cost_m=10_000).summary
    assert a["profit_12m"] - b["profit_12m"] == pytest.approx(120_000)
    assert b["extra_cost"] == pytest.approx(120_000)


@pytest.mark.parametrize("key", list(AU.SCENARIOS))
def test_scenario_without_response_gives_breakeven_only(key):
    r = AU.run_scenario(CH, SP, FunnelParams(), AU.ScenarioInput(key, reach=0.5, cost_per_send=20))
    assert r["profit_delta"] is None and r["breakeven"] > 0 and r["sends_month"] > 0
    assert r["cost_12m"] == pytest.approx(r["sends_month"] * 12 * 20)


@pytest.mark.parametrize("key", list(AU.SCENARIOS))
def test_response_above_breakeven_raises_profit(key):
    p = FunnelParams()
    be = AU.breakeven_rate(20, p.aov, p.margin)
    hi = AU.run_scenario(CH, SP, p, AU.ScenarioInput(key, 0.5, 20, response=be * 5))
    zero = AU.run_scenario(CH, SP, p, AU.ScenarioInput(key, 0.5, 20, response=0.0))
    assert hi["profit_delta"] > 0
    assert zero["profit_delta"] == pytest.approx(-zero["cost_12m"])   # 반응 0이면 발송비만큼 손해


def test_repeat_targets_previous_cohorts():
    p = FunnelParams()
    base = simulate(CH, SP, p)
    r = AU.run_scenario(CH, SP, p, AU.ScenarioInput("repeat", 1.0, 10))
    new = base.monthly["paid_new"].values
    assert r["extra_cost_m"][0] == 0
    assert r["extra_cost_m"][2] == pytest.approx((new[1] + new[0]) * 10)
