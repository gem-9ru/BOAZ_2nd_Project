"""희수 실험 예시 (scripts/heesu_example.py 가 정리 엑셀에서 만든 파일): 설계 문서의 숫자와 같게 읽히는지."""
from fastapi.testclient import TestClient

from server.app import app


def test_heesu_example_matches_the_team_notes():
    r = TestClient(app).get("/analysis/example", params={"name": "heesu"})
    assert r.status_code == 200
    body = r.json()
    a, b = body["summary"]["arms"]
    assert (a["spend"], a["impressions"], a["link_clicks"], a["landing_page_views"]) == (1524, 203, 6, 5)
    assert (b["spend"], b["impressions"], b["link_clicks"], b["landing_page_views"]) == (5368, 1122, 41, 26)
    assert round(b["click_to_visit"], 2) == 0.63                       # 'B 도착 63%'
    row1 = next(x for x in body["matrix"]["rows"] if x["row"] == "1")
    assert row1["signal"] == "B(수동)가 36% 싸요 · 확실해요"            # '수동이 CPM 36% 저렴'
    kinds = {x["kind"] for x in body["alerts"]}
    assert {"spend_gap", "no_delivery", "many_fields", "meta_vs_measured"} <= kinds   # 돈 쏠림 · A 안 나간 날 · 타깃+노출 위치 묶음
    assert body["verdict"]["badge"]["word"] == "아직 몰라요"            # 돈이 몰려 한 단계 낮춤
    assert not body["blocked"]


def test_unknown_example_is_404_and_default_is_ovenlog():
    c = TestClient(app)
    assert c.get("/analysis/example", params={"name": "x"}).status_code == 404
    assert c.get("/analysis/example").json()["summary"]["arms"][0]["spend"] == 5308
