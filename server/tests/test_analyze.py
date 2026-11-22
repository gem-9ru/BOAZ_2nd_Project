from fastapi.testclient import TestClient

from server.app import app
from server.engine import analyze as A
from server.engine.meta_export import read_export

DEMO = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def _post(path):
    with open(path, "rb") as f:
        return TestClient(app).post("/analyze", files={"file": ("x.csv", f, "text/csv")})


def test_ovenlog_demo_case_is_hold_with_end_date_change():
    body = _post(DEMO).json()
    assert body["status"] == "hold"
    assert body["finding"]["id"] == "rule.hold_small_sample"
    assert "30" in body["finding"]["message"]                       # "아직 클릭이 30번이라…"
    assert body["changes"][0]["field_id"] == "meta.adset.end_date"
    assert abs(body["ab"]["prob_b_better"] - 0.60) < 0.02
    assert body["ab"]["a"] == "A_자동노출위치" and body["ab"]["b"] == "B_피드만노출(AN제외)"


def test_ovenlog_charts():
    c = _post(DEMO).json()["charts"]
    assert c["funnel"] == {"impressions": 1822, "link_clicks": 30, "landing_page_views": 24}
    assert [d["date"] for d in c["daily"]] == ["2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]
    assert c["daily"][0]["ctr"] is None and c["daily"][1]["spend"] == 3340
    top = max(c["placement"], key=lambda p: p["spend"])
    assert top["placement"] == "인스타그램 릴스"
    names = {p["placement"] for p in c["placement"]}
    assert {"인스타그램 피드", "페이스북 피드", "페이스북 인스트림 동영상"} <= names


def test_placement_label_keeps_unknown_names():
    assert A.placement_label("Audience Network an_classic") == "Audience Network 네이티브·배너·전면"
    assert A.placement_label("Instagram brand_new_spot") == "인스타그램 brand_new_spot"
    assert A.placement_label("Threads feed") == "Threads 피드"


def test_hold_expectation_shows_range_narrowing_with_more_days():
    e = _post(DEMO).json()["expect"]
    assert e["metric"] == "link_ctr" and e["grade"] == "hypothesis"
    assert e["current"][0] < 30 / 1822 < e["current"][1]
    assert (e["expected"][1] - e["expected"][0]) < (e["current"][1] - e["current"][0])


def test_fired_rule_wins_over_hold_and_uses_rule_expectation():
    b = read_export(DEMO)
    out = A.analyze(b, metrics_override={"an_click_share": 0.5, "link_clicks": 30.0, "link_ctr": 0.0165})
    assert out["status"] == "fired" and out["finding"]["id"] == "rule.placement_quality"
    assert out["expect"]["grade"] == "hypothesis"
    assert out["expect"]["expected"][0] >= out["expect"]["current"][0]


def test_ratio_rule_straddling_threshold_becomes_hold():
    b = read_export(DEMO)
    out = A.analyze(b, metrics_override={"link_ctr": 0.0075, "link_clicks": 30.0, "an_click_share": 0.0})
    assert out["status"] == "hold" and out["finding"]["id"] == "rule.creative_weak"


def test_wrong_file_is_friendly(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("이름,나이\n철수,3\n", encoding="utf-8")
    r = _post(p)
    assert r.status_code == 400 and "열이 없어요" in r.json()["error"]


def test_empty_file_is_friendly(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_bytes(b"")
    r = _post(p)
    assert r.status_code == 400 and r.json()["error"]


def test_two_adsets_without_link_clicks_is_400_not_500(tmp_path):
    p = tmp_path / "noclicks.csv"
    p.write_text("보고 시작,광고 세트 이름,지출 금액 (KRW),노출\n2026-11-18,A,100,50\n2026-11-18,B,100,60\n", encoding="utf-8")
    r = _post(p)
    assert r.status_code == 400 and "링크 클릭" in r.json()["error"]


def test_straddling_rule_uses_hold_changes_and_hypothesis_grade():
    out = A.analyze(read_export(DEMO), metrics_override={"link_ctr": 0.0075, "link_clicks": 30.0, "an_click_share": 0.0})
    assert out["status"] == "hold"
    assert [c["field_id"] for c in out["changes"]] == ["meta.adset.end_date"]
    assert out["expect"]["metric"] == "link_ctr" and out["expect"]["grade"] == "hypothesis"


def test_small_sample_hold_range_is_graded_hypothesis():
    assert _post(DEMO).json()["expect"]["grade"] == "hypothesis"
