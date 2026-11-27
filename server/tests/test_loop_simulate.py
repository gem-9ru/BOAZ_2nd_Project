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


def test_period_changes_daily_amount_and_hypothesis_not_the_range():
    """AN-05 기간 토글 (v4.2): 범위는 총액 기준 그대로, 하루 금액이 써 본 적 없거나 메타 하루 최소보다 적으면 표시."""
    from server.engine.loop import simulate as sim
    arm = {"spend": 5308.0, "daily_max": 2643.0}
    four, seven = sim.tried(arm, 5000, 4), sim.tried(arm, 5000, 7)
    assert four["tried"] and four["daily"] == 1250 and seven["daily"] < 1000
    assert seven["below_daily_min"] and not sim.tried(arm, 6000, 4)["below_daily_min"]
    assert not sim.tried(arm, 5000, 1)["daily_tried"]          # 하루에 5,000원은 써 본 적 없음 → 가설
    assert sim.tried(arm, 5000)["tried"] and sim.tried(arm, 5000)["daily"] is None


def test_judge_chance_matches_v5_wire():
    """축소안 v5 ③: 오븐로그 B 실측으로 5,000원 약 70% · 6,000원 약 90% · 10,000원 거의 확실."""
    import json, pathlib
    oven = json.loads((pathlib.Path(__file__).parents[2] / "web/tests/fixtures/oven.json").read_text())
    b = next(a for a in oven["summary"]["arms"] if a["name"].startswith("B"))
    got = [simulate.judge_chance(b, x, runs=50000) for x in (5000, 6000, 10000)]
    assert 0.64 < got[0] < 0.74 and 0.85 < got[1] < 0.93 and got[2] > 0.99


def test_grid_for_the_budget_slider():
    """최종안 ③ 슬라이더: 3,000~30,000원 1,000원 단위, 판단 어려운 금액 표시, run과 같은 방문자 범위."""
    import json, pathlib
    oven = json.loads((pathlib.Path(__file__).parents[2] / "web/tests/fixtures/oven.json").read_text())
    b = next(a for a in oven["summary"]["arms"] if a["name"].startswith("B"))
    g = simulate.grid(b, days=4, runs=50000)
    rows = {r["budget"]: r for r in g["rows"]}
    assert min(rows) == 3000 and max(rows) == 30000 and len(rows) == 28
    assert rows[5000]["hard"] and not rows[6000]["hard"]          # 69% · 89% (기준 80%)
    assert rows[5000]["below_daily_min"] and not rows[6000]["below_daily_min"]
    one = simulate.run(b, 6000, runs=50000)
    assert abs(rows[6000]["visits"]["median"] - one["visits"]["median"]) < 0.5
