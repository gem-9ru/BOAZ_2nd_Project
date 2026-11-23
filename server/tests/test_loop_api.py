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
    assert p["change"]["field_id"] == "meta.adset.end_date" and len(p["summary"]) == 3
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
