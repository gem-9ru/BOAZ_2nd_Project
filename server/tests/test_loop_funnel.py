"""퍼널: 본 사람 → 누른 사람 → 들어온 사람. 단계 사이 비율과 95% 범위, 건수가 적으면 '아직 몰라요'."""
from server.engine.loop import funnel, summary
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def test_stages_rates_and_ranges_per_arm():
    f = funnel.run(summary.run(read_export(OVEN))["arms"])
    a = f["arms"][0]
    assert [s["key"] for s in a["stages"]] == ["impressions", "link_clicks", "landing_page_views"]
    click, visit = a["stages"][1], a["stages"][2]
    assert click["count"] == 13 and abs(click["rate"] - 13 / 837) < 1e-9
    assert click["per100"] == "1,000번 보여지면 약 16번 눌렸어요"   # 노출은 사람 수가 아니라 횟수 (점검 A) · 1,000 기준
    assert visit["range"][0] < visit["rate"] < visit["range"][1]
    assert 0.45 < visit["range"][0] < 0.55 and visit["range"][1] > 0.9      # 팀 계산 A 74%(49~92%)


def test_few_counts_are_marked_unknown_and_a_hint_is_given():
    rows = [summary.arm("A", 1000, 900, 6, 2)]
    f = funnel.run(rows)
    assert f["arms"][0]["stages"][2]["unknown"] is True                    # 클릭 10건 미만에서 나온 비율
    assert "페이지" in f["hint"]                                          # 클릭→도착 33% → 페이지 점검
