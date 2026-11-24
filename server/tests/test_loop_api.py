"""분석 페이지가 쓰는 서버 주소: /analysis (올리기·예시), /simulate, /plan/{코드}."""
from fastapi.testclient import TestClient

from server.app import app

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"
c = TestClient(app)


def _upload():
    with open(OVEN, "rb") as f:
        return c.post("/analysis", files={"file": ("oven.csv", f, "text/csv")})


def test_upload_returns_all_blocks_and_a_4_letter_code():
    r = _upload()
    assert r.status_code == 200
    body = r.json()
    assert {"check", "summary", "verdict", "replay", "next", "placements", "code"} <= set(body)
    assert len(body["code"]) == 4 and body["code"].isalnum()


def test_example_is_the_ovenlog_file():
    body = c.get("/analysis/example").json()
    assert body["verdict"]["badge"]["level"] == "유력"


def test_simulate_uses_the_uploaded_arms():
    code = _upload().json()["code"]
    r = c.post("/simulate", json={"code": code, "arm": "B_피드만노출(AN제외)", "budget": 30000}).json()
    assert r["link_clicks"]["lo"] < r["link_clicks"]["median"] < r["link_clicks"]["hi"]


def test_plan_code_gives_the_chatbot_its_one_change():
    code = _upload().json()["code"]
    p = c.get(f"/plan/{code}").json()
    assert p["change"]["field_id"] == "meta.ad.media" and len(p["summary"]) == 3
    assert c.get("/plan/ZZZZ").status_code == 404


def test_bad_file_is_friendly():
    r = c.post("/analysis", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")})
    assert r.status_code == 400 and r.json()["error"]


def test_the_analysis_page_is_served_with_its_assets():
    import pathlib
    if not pathlib.Path("web/dist/index.html").exists():
        import pytest
        pytest.skip("web/dist가 없음 (cd web && npm run build)")
    page = c.get("/analysis")
    assert page.status_code == 200 and "Ad assistant" in page.text
    asset = next(pathlib.Path("web/dist/assets").glob("*.js")).name
    assert c.get(f"/analysis/assets/{asset}").status_code == 200


def test_stored_results_are_capped_oldest_first(monkeypatch):
    from server import app as appmod
    monkeypatch.setattr(appmod, "MAX_PLANS", 3)
    appmod._PLANS.clear()
    codes = [appmod._store({"next": {}, "verdict": None})["code"] for _ in range(5)]
    assert len(appmod._PLANS) == 3
    assert codes[0] not in appmod._PLANS and codes[-1] in appmod._PLANS


def test_too_big_upload_is_refused_with_a_fix(monkeypatch):
    from server import app as appmod
    monkeypatch.setattr(appmod, "MAX_UPLOAD_BYTES", 1000)
    r = c.post("/analysis", files={"file": ("big.csv", b"a," * 2000, "text/csv")})
    assert r.status_code == 400 and "MB" in r.json()["error"]


def test_analysis_has_v4_blocks_alerts_matrix_backtest():
    r = c.get("/analysis/example").json()
    assert r["blocked"] is False
    assert [a["mark"] for a in r["alerts"]][0] in ("▲", "●")
    assert r["matrix"]["change"]["path"] == "광고 › 형식·미디어"
    assert r["backtest"]["ok"] is True


def test_analysis_takes_setting_values_as_json():
    import json
    with open(OVEN, "rb") as f:
        r = c.post("/analysis", files={"file": ("o.csv", f, "text/csv")},
                   data={"settings": json.dumps({"meta.adset.daily_budget": "10000", "meta.ad.media": "정사각 이미지 1장"})}).json()
    assert any(a["kind"] == "underspent" for a in r["alerts"])
    # 예산을 반도 못 썼으면 0 게재가 먼저 막힌 단계 → 바꿀 칸은 예산, 지금 값은 세팅값에서
    assert r["matrix"]["change"]["field_id"] == "meta.adset.daily_budget"
    assert r["matrix"]["change"]["now"] == "10000"
    with open(OVEN, "rb") as f:
        r2 = c.post("/analysis", files={"file": ("o.csv", f, "text/csv")},
                    data={"settings": json.dumps({"meta.ad.media": "정사각 이미지 1장"})}).json()
    assert r2["matrix"]["change"]["now"] == "정사각 이미지 1장"


def test_simulate_marks_untried_budget_as_hypothesis_and_gives_test_and_roll():
    code = _upload().json()["code"]
    small = c.post("/simulate", json={"code": code, "arm": "A_자동노출위치", "budget": 5000}).json()
    big = c.post("/simulate", json={"code": code, "arm": "A_자동노출위치", "budget": 20000}).json()
    assert small["tried"] is True and big["tried"] is False
    # Test & Roll은 슬라이더(테스트 금액)가 아니라 전체 예산 기준 (기본 ₩100,000 → 세트당 ₩4,000~10,000)
    assert (small["next_test"]["per_set_lo"], small["next_test"]["per_set_hi"]) == (4000, 10000)
    t = c.post("/simulate", json={"code": code, "arm": "A_자동노출위치", "budget": 5000, "total": 300000}).json()
    assert t["next_test"]["total"] == 300000


def test_plan_gives_path_certainty_checklist_keep_dont():
    code = _upload().json()["code"]
    p = c.get(f"/plan/{code}").json()
    assert p["change"]["path"] == "광고 › 형식·미디어"
    assert p["change"]["certainty"]["label"] == "유력" and p["change"]["checklist"]
    assert p["keep"][0]["field_id"] == "meta.adset.placements" and p["dont"]


# ── v4 8장: 세팅값은 URL에 값을 넣지 않고 세션 키로 넘긴다 ──
def test_settings_are_kept_under_a_session_key_not_in_the_url():
    k = c.post("/settings", json={"settings": {"meta.adset.daily_budget": "10000", "meta.ad.media": "정사각 이미지 1장"}}).json()["key"]
    assert len(k) >= 16 and "10000" not in k
    with open(OVEN, "rb") as f:
        r = c.post("/analysis", files={"file": ("o.csv", f, "text/csv")}, data={"settings_key": k}).json()
    assert any(a["kind"] == "underspent" for a in r["alerts"])
    assert r["settings"]["meta.ad.media"] == "정사각 이미지 1장"


def test_unknown_settings_key_is_ignored_not_an_error():
    with open(OVEN, "rb") as f:
        r = c.post("/analysis", files={"file": ("o.csv", f, "text/csv")}, data={"settings_key": "nope"})
    assert r.status_code == 200 and r.json()["settings"] == {}


def test_setting_rows_cover_every_given_field_in_ads_manager_order():
    import json
    s = {"meta.campaign.objective": "트래픽", "meta.adset.placements": "수동", "meta.ad.media": "정사각 이미지", "meta.adset.end_date": "2026-11-20"}
    with open(OVEN, "rb") as f:
        r = c.post("/analysis", files={"file": ("o.csv", f, "text/csv")}, data={"settings": json.dumps(s)}).json()
    rows = r["matrix"]["settings"]
    assert [x["field_id"] for x in rows][:1] == ["meta.campaign.objective"]
    by = {x["field_id"]: x for x in rows}
    assert by["meta.ad.media"]["kind"] == "변경" and by["meta.ad.media"]["value"] == "정사각 이미지"
    assert by["meta.adset.placements"]["kind"] == "유지"
    assert by["meta.campaign.objective"]["kind"] == "그대로" and by["meta.campaign.objective"]["path"].startswith("캠페인")


def test_example_also_uses_the_received_settings():
    k = c.post("/settings", json={"settings": {"meta.ad.media": "정사각 이미지 1장"}}).json()["key"]
    r = c.get(f"/analysis/example?settings_key={k}").json()
    assert r["matrix"]["change"]["now"] == "정사각 이미지 1장"


def test_fields_on_the_same_ads_manager_spot_share_the_change():
    import json
    s = {"meta.ad.format": "단일 이미지", "meta.ad.media": "정사각 이미지 1장"}
    with open(OVEN, "rb") as f:
        r = c.post("/analysis", files={"file": ("o.csv", f, "text/csv")}, data={"settings": json.dumps(s)}).json()
    kinds = {x["field_id"]: x["kind"] for x in r["matrix"]["settings"]}
    assert kinds == {"meta.ad.format": "변경", "meta.ad.media": "변경"}
