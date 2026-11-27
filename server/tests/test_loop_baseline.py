"""세트 1개 (축소안 v5 ①b): 기준값과 비교한 신호, 클릭 30번 미만이면 무조건 '아직 몰라요'."""
from server.engine.loop import baseline


def arm(**k):
    return {"name": "A", "spend": 5000.0, "impressions": 1000.0, "link_clicks": 17.0, "landing_page_views": 14.0, **k}


def test_two_sets_have_no_baseline():
    assert baseline.run([arm(), arm()]) == []


def test_wire_example_visit_rate_82_with_range_and_unknown_under_30_clicks():
    rows = {r["key"]: r for r in baseline.run([arm(frequency_min=1.6)])}
    v = rows["visit_rate"]
    assert round(v["value"], 2) == 0.82 and v["standard"] == "60%"
    assert 0.58 < v["range"][0] < 0.66 and 0.9 < v["range"][1] < 0.95   # 와이어: 범위 62~92%
    assert v["signal"] == "unknown" and "17번이라 30번이 안 돼요" in v["why"]
    assert rows["frequency"]["signal"] == "unknown"   # 클릭이 모자라면 모두 –


def test_enough_clicks_gives_ok_or_low():
    rows = {r["key"]: r for r in baseline.run([arm(link_clicks=40.0, landing_page_views=12.0, frequency_min=1.6)])}
    assert rows["visit_rate"]["signal"] == "low"   # 30% < 60%
    assert rows["ctr"]["signal"] == "ok"           # 1,000번에 40번 ≥ 10번
    assert rows["frequency"]["signal"] == "unknown" and rows["frequency"]["text"] == "적어도 1.6번"   # 아래쪽 값이라 단정하지 않음
    assert {r["key"]: r for r in baseline.run([arm(link_clicks=40.0, frequency_min=3.0)])}["frequency"]["signal"] == "low"
