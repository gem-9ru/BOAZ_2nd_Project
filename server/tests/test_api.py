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


def test_copies_without_key_uses_template(monkeypatch):
    monkeypatch.setenv("COACH_NO_LLM", "1")
    body = TestClient(app).post("/copies", json={"product": "수제 쿠키", "strengths": ["버터 듬뿍"],
                                                 "keywords": ["쿠키 선물"]}).json()
    assert body["source"] == "template" and len(body["copies"]) == 3
    assert all(c["primary_text"] and c["headline"] for c in body["copies"])
    assert all(set(c) == {"primary_text", "headline"} for c in body["copies"])


def test_copies_without_strengths_still_three(monkeypatch):
    monkeypatch.setenv("COACH_NO_LLM", "1")
    body = TestClient(app).post("/copies", json={"product": "수제 쿠키", "strengths": [], "keywords": []}).json()
    assert len(body["copies"]) == 3


def test_fields_are_the_eleven_questions():
    fields = TestClient(app).get("/fields").json()["fields"]
    assert [f["id"] for f in fields] == [
        "meta.pre.fb_page", "meta.pre.ig_account", "meta.campaign.objective", "meta.campaign.special_category",
        "meta.adset.conversion_location", "meta.adset.end_date", "meta.adset.location", "meta.adset.age_gender",
        "meta.ad.format", "meta.ad.website_url", "meta.ad.media"]
    end = next(f for f in fields if f["id"] == "meta.adset.end_date")
    assert end["kind"] == "question" and end["options"] == ["7일", "14일", "30일"] and end["ask"]
    assert set(end) == {"id", "kind", "label", "ask", "options", "default", "why"}


def test_defaults_lists_fields_not_asked():
    defaults = TestClient(app).get("/fields").json()["defaults"]
    ids = [d["id"] for d in defaults]
    assert "meta.campaign.buying_type" in ids and "meta.adset.age_gender" not in ids
    assert all(d["default"] is not None and d["why"] for d in defaults)


def test_research_failure_explains_naver_error(monkeypatch):
    from server.engine import market, naver_api
    monkeypatch.setattr(market, "build", lambda seeds, online=True: None)
    monkeypatch.setattr(naver_api, "last_error", lambda: "네이버 키가 없어요.")
    body = TestClient(app).post("/research", json={"product": "아무거나"}).json()
    assert body["notice"].startswith("네이버 키가 없어요.")


def test_research_calls_do_not_overlap(monkeypatch):
    """네이버 조회일·오류는 모듈 전역이라, 동시에 온 요청이 섞이지 않게 한 번에 하나씩."""
    import threading
    import time

    from server.engine import market
    active, overlaps = [0], [0]

    def slow_build(seeds, online=True):
        active[0] += 1
        overlaps[0] = max(overlaps[0], active[0])
        time.sleep(0.05)
        active[0] -= 1
        return None

    monkeypatch.setattr(market, "build", slow_build)
    client = TestClient(app)
    threads = [threading.Thread(target=lambda: client.post("/research", json={"product": "x"})) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert overlaps[0] == 1


def test_copies_source_is_template_when_claude_gives_nothing(monkeypatch):
    from server.engine import copywriter
    monkeypatch.delenv("COACH_NO_LLM", raising=False)
    monkeypatch.setattr(copywriter, "make_client", lambda: object())          # 키는 있는 척
    monkeypatch.setattr(copywriter, "_ask_claude", lambda *a, **k: [])        # Claude가 아무것도 못 줌
    body = TestClient(app).post("/copies", json={"product": "수제 쿠키", "strengths": ["버터"], "keywords": []}).json()
    assert body["source"] == "template" and len(body["copies"]) == 3
