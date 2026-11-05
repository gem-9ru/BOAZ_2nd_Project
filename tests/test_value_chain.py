"""밸류체인 v2 (밸류체인_정의.md): 판매 수수료 채널 rev_share, 증분 계수 incr_mult, 체인 단계 이름."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import Channel, FunnelParams, MetaCurve, simulate  # noqa: E402
from src.engine import defaults as D  # noqa: E402
from src.engine.acquisition import RevShareCurve  # noqa: E402
from src.engine.optimize import compare_options, lever_table, optimize_allocation  # noqa: E402

P = FunnelParams()


def meta(cpc=300.0):
    return Channel("meta", "메타", MetaCurve(cpc, 0.0))


def gonggu(rate=0.2, sales=100, n=1, upfront=0.0):
    return Channel("gonggu", "공동구매", RevShareCurve(rate, sales, n, upfront))


def test_rev_share_cost_per_purchase_rule():
    # 구매당 비용 = 수수료율 × 객단가 + 착수금 ÷ 판매 수 (밸류체인 4-1 D)
    c = RevShareCurve(0.2, 100, 1, upfront=300_000)
    assert c.cost_per_purchase(60_000) == pytest.approx(0.2 * 60_000 + 300_000 / 100)
    assert c.sales() == 100   # 상한 = 1회 판매량 × 횟수


def test_rev_share_channel_in_simulation():
    r = simulate([gonggu(sales=100, n=2)], [5_000_000], P)
    row = r.by_channel.iloc[0]
    assert row["new_customers"] == pytest.approx(200)            # 예산과 무관
    assert row["spend"] == pytest.approx(0.2 * 200 * P.aov)      # 매출 비례 비용
    assert row["unspent"] == 0 and row["clicks"] == 0
    assert r.summary["paid_new"] == pytest.approx(200 * 12)
    assert r.funnel.iloc[len(P.steps)]["count"] == pytest.approx(200 * 12)   # ④ 구매로 바로 들어옴


def test_optimizer_ignores_rev_share_budget():
    chs = [meta(), gonggu()]
    opt = optimize_allocation(chs, 1_000_000, P, "new_customers")
    assert opt["spends"][1] == 0 and opt["spends"][0] == pytest.approx(1_000_000)


def test_incr_mult_scales_only_counted_customers():
    a = simulate([meta()], [1_000_000], P).summary
    b = simulate([Channel("meta", "메타", MetaCurve(300.0, 0.0), incr_mult=0.6)], [1_000_000], P).summary
    assert b["paid_new"] == pytest.approx(a["paid_new"] * 0.6)
    assert b["spend_total"] == pytest.approx(a["spend_total"])   # 비용은 그대로 → CAC가 커짐
    assert b["paid_cac"] == pytest.approx(a["paid_cac"] / 0.6)


def test_compare_options_has_gonggu_row():
    chs = [meta(), gonggu(rate=0.2, sales=50)]
    sp = [1_000_000, 0.0]
    df = compare_options(chs, sp, P, lever_table(chs, sp, P), 1_000_000).set_index("option")
    row = df.loc["공동구매 (판매 수수료)"]
    with_ = simulate(chs, sp, P).summary["profit_12m"]
    without = simulate(chs[:1], sp[:1], P).summary["profit_12m"]
    assert row["gain"] == pytest.approx(with_ - without)
    assert row["cost"] == pytest.approx(0.2 * 50 * P.aov * 12)


def test_chain_step_names():
    names = [n for n, _ in D.FUNNEL_STEPS]
    assert names[0].startswith("③") and names[-1] == "④ 구매"
    assert [c[1] for c in D.CHAIN] == ["접촉", "반응", "행동", "구매", "재구매", "추천"]
    assert [c[2] for c in D.CHAIN] == ["획득", "획득", "활성화", "활성화", "유지", "추천"]
