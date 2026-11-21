import pathlib

from fastapi.testclient import TestClient

from server.app import app


def test_health():
    assert TestClient(app).get("/health").json() == {"ok": True}


def test_engine_has_no_streamlit():
    src = "".join(p.read_text(encoding="utf-8") for p in pathlib.Path(__file__).resolve().parents[1].joinpath("engine").glob("*.py"))
    assert "streamlit" not in src


CACHED_SEEDS = ["답례품쿠키", "디저트선물", "수제쿠키", "쿠키선물세트", "휘낭시에"]


def test_research_offline_uses_cache(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")          # 온라인 호출 금지 → 저장본만
    r = TestClient(app).post("/research", json={"product": "수제 쿠키", "seeds": CACHED_SEEDS})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "cache" and body["fetched"] == "2026-11-15"
    assert 1 <= len(body["keywords"]) <= 10
    assert body["keywords"][0] == {"keyword": "수제쿠키", "total_qc": body["keywords"][0]["total_qc"]}
    aud = body["audience"]
    assert aud["keyword"] == "쿠키선물세트" and set(aud["ages"]) >= {"20", "30", "40", "50"}
    assert aud["top_age"] == "30"                      # 한 줄 요약(분야 평균 대비)과 같은 연령대
    assert "30대 여성" in body["headline"]


def test_research_unknown_product_is_friendly(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    r = TestClient(app).post("/research", json={"product": "zzqq없는상품"})
    assert r.status_code == 200
    assert r.json()["keywords"] == [] and r.json()["notice"]
