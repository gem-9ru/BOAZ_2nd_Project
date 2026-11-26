from fastapi.testclient import TestClient

from server.app import app
from server.engine import analyze as A
from server.engine.loop.words import placement_label
from server.engine.meta_export import read_export

DEMO = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def _post(path):
    with open(path, "rb") as f:
        return TestClient(app).post("/analysis", files={"file": ("x.csv", f, "text/csv")})


def test_ovenlog_demo_case_is_hold_with_end_date_change():
    out = A.analyze(read_export(DEMO))
    assert out["status"] == "hold"
    assert out["finding"]["id"] == "rule.hold_small_sample"
    assert "30" in out["finding"]["message"]                       # "아직 클릭이 30번이라…"
    assert out["changes"][0]["field_id"] == "meta.adset.end_date"


def test_placement_label_keeps_unknown_names():
    assert placement_label("Audience Network an_classic") == "Audience Network 네이티브·배너·전면"
    assert placement_label("Instagram brand_new_spot") == "인스타그램 brand_new_spot"
    assert placement_label("Threads feed") == "Threads 피드"


def test_fired_rule_wins_over_hold():
    b = read_export(DEMO)
    out = A.analyze(b, metrics_override={"an_click_share": 0.5, "link_clicks": 30.0, "link_ctr": 0.0165})
    assert out["status"] == "fired" and out["finding"]["id"] == "rule.placement_quality"


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


def test_straddling_rule_uses_hold_changes():
    out = A.analyze(read_export(DEMO), metrics_override={"link_ctr": 0.0075, "link_clicks": 30.0, "an_click_share": 0.0})
    assert out["status"] == "hold"
    assert [c["field_id"] for c in out["changes"]] == ["meta.adset.end_date"]


def test_placement_label_for_real_export_names():
    assert placement_label("Audience Network 네이티브, 배너 및 전면 광고") == "Audience Network 네이티브·배너·전면"
    assert placement_label("Instagram 릴스") == "인스타그램 릴스"
    assert placement_label("Facebook 피드") == "페이스북 피드"
    assert placement_label("Instagram 둘러보기/탐색 탭") == "인스타그램 둘러보기/탐색 탭"
