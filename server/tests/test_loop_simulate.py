"""3 시뮬레이션: 실측 범위로 20만 번 가상 집행 (희수 8장 ③)."""
from server.engine.loop import simulate, summary
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def test_budget_to_clicks_and_visits_with_80pct_band():
    _, b = summary.run(read_export(OVEN))["arms"]
    r = simulate.run(b, budget=30000)
    for k in ("impressions", "link_clicks", "visits"):
        assert r[k]["lo"] < r[k]["median"] < r[k]["hi"]
    expected_clicks = 30000 / b["cpm"] * 1000 * b["link_clicks"] / b["impressions"]
    assert abs(r["link_clicks"]["median"] - expected_clicks) / expected_clicks < 0.1
    assert len(r["histogram"]) == 20 and sum(h["count"] for h in r["histogram"]) == r["runs"] == 200_000


def test_more_money_more_clicks():
    _, b = summary.run(read_export(OVEN))["arms"]
    assert simulate.run(b, 60000)["link_clicks"]["median"] > simulate.run(b, 30000)["link_clicks"]["median"]
