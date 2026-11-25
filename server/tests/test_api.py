import pathlib
import re

import pytest

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
    assert set(aud["ages"]) >= {"20", "30", "40", "50"}
    assert body["headline"].startswith(aud["keyword"])            # 대표 키워드 = 한 줄 요약의 키워드
    assert f"{aud['top_age']}대 여성" in body["headline"]          # 한 줄 요약(분야 평균 대비)과 같은 연령대


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
    assert all(set(c) == {"primary_text", "headline", "basis"} for c in body["copies"])


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
    monkeypatch.setattr(market, "category_guess", lambda product, online=True: (None, []))   # 네트워크 금지
    monkeypatch.setattr(market, "build", lambda seeds, online=True, **kw: None)
    monkeypatch.setattr(naver_api, "last_error", lambda: "네이버 키가 없어요.")
    body = TestClient(app).post("/research", json={"product": "아무거나"}).json()
    assert body["notice"].startswith("네이버 키가 없어요.")


def test_research_calls_do_not_overlap(monkeypatch):
    """네이버 조회일·오류는 모듈 전역이라, 동시에 온 요청이 섞이지 않게 한 번에 하나씩."""
    import threading
    import time

    from server.engine import market
    active, overlaps = [0], [0]

    def slow_build(seeds, online=True, **kw):
        active[0] += 1
        overlaps[0] = max(overlaps[0], active[0])
        time.sleep(0.05)
        active[0] -= 1
        return None

    monkeypatch.setattr(market, "category_guess", lambda product, online=True: (None, []))   # 네트워크 금지
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


def test_research_reports_each_part_with_its_own_date(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    body = TestClient(app).post("/research", json={"product": "수제 쿠키", "seeds": CACHED_SEEDS}).json()
    parts = {s["part"]: s for s in body["sources"]}
    assert parts["product"] == {"part": "product", "label": "검색어·연령", "fetched": "2026-11-15", "today": False}
    assert parts["baseline"]["label"] == "분야 평균"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts["baseline"]["fetched"])   # 고정 저장본을 새로 받으면 날짜가 바뀐다


def test_research_is_live_when_product_data_is_from_today_even_if_baseline_is_old(monkeypatch):
    import datetime
    from server.engine import market, naver_api
    real_build = market.build
    today = datetime.date.today().isoformat()

    def build(seeds, online=True, **kw):
        report = real_build(seeds, online=False)
        naver_api.reset_fetched()
        naver_api._note_fetched(f"{today} 12:00:00", "product")
        naver_api._note_fetched("2026-11-15 14:35:09", "baseline")
        report.fetched_parts = naver_api.fetched_parts()
        return report

    monkeypatch.setattr(market, "build", build)
    body = TestClient(app).post("/research", json={"product": "수제 쿠키", "seeds": CACHED_SEEDS}).json()
    assert body["source"] == "live"
    parts = {s["part"]: s for s in body["sources"]}
    assert parts["product"]["today"] is True and parts["baseline"]["today"] is False


def test_research_returns_up_to_20_words_to_leave_out(monkeypatch):
    """장표 6·12장: 추천 10개 + 뺄 키워드 20개 (만들기·매장·관련 낮음)."""
    monkeypatch.setenv("COACH_OFFLINE", "1")
    body = TestClient(app).post("/research", json={"product": "수제 쿠키"}).json()
    neg = body["negatives"]
    assert 1 <= len(neg) <= 20
    assert not set(neg) & {k["keyword"] for k in body["keywords"]}


def test_copies_never_use_a_left_out_word(monkeypatch):
    from server.engine import copywriter
    bad = [{"text": "쿠키만들기 재료처럼 정성껏 구웠어요. 오늘 만나 보세요.", "headline": "쿠키만들기"},
           {"text": "버터 듬뿍 넣고 당일 구운 수제 쿠키예요.", "headline": "당일 구운 수제 쿠키"},
           {"text": "광주맛집에서 만든 쿠키를 집에서 받아 보세요.", "headline": "집에서 받는 쿠키"}]
    monkeypatch.setattr(copywriter, "meta_copies_with_source", lambda *a, **k: (bad, True))
    monkeypatch.setenv("COACH_NO_LLM", "1")
    body = TestClient(app).post("/copies", json={"product": "수제 쿠키", "strengths": ["버터 듬뿍"],
                                                  "keywords": ["수제쿠키"], "avoid": ["쿠키만들기", "광주맛집"]}).json()
    assert len(body["copies"]) == 3
    for c in body["copies"]:
        assert "쿠키만들기" not in c["primary_text"] + c["headline"]
        assert "광주맛집" not in c["primary_text"] + c["headline"]


def test_avoid_words_inside_the_product_name_do_not_empty_the_copies(monkeypatch):
    monkeypatch.setenv("COACH_NO_LLM", "1")
    body = TestClient(app).post("/copies", json={"product": "쿠키만들기 키트", "strengths": ["재료 다 들어 있음"],
                                                  "keywords": [], "avoid": ["쿠키만들기", "광주맛집"]}).json()
    assert len(body["copies"]) == 3


def test_research_offline_has_segments_trend_and_modifiers(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    b = TestClient(app).post("/research", json={"product": "수제 쿠키", "seeds": CACHED_SEEDS}).json()
    assert b["category"] == {"code": "50000006", "name": "식품", "guessed": True}
    assert len(b["categories"]) == 12
    assert 1 <= len(b["segments"]) <= 3 and b["segments"][0]["label"].endswith("손님")
    assert b["modifiers"] and b["headline"] and b["audience"]          # 하위 호환


def _fake_report():
    import pandas as pd
    from server.engine import market
    kw = pd.DataFrame([{"keyword": "립밤", "total_qc": 900, "intent": "상품"}])
    return market.MarketReport(seeds=["립밤"], groups=pd.DataFrame(), keywords=kw, recommended=["립밤"],
                               headline="h", fetched="2026-11-15")


def test_research_unknown_category_returns_no_segments(monkeypatch):
    from server.engine import market
    monkeypatch.setattr(market, "category_guess", lambda product, online=True: (None, []))
    monkeypatch.setattr(market, "build", lambda seeds, online=True, **kw: _fake_report())
    b = TestClient(app).post("/research", json={"product": "zz상품"}).json()
    assert b["category"] is None and b["segments"] == [] and len(b["categories"]) == 12
    assert b["keywords"] == [{"keyword": "립밤", "total_qc": 900}] and b["audience"] is None


def test_research_passes_category_and_keywords(monkeypatch):
    from server.engine import market
    seen = {}

    def guess(*a, **k):
        raise AssertionError("분야를 줬으면 추정하지 않는다")

    def build(seeds, online=True, category=None, keep=None, **kw):
        seen.update(seeds=seeds, category=category, keep=keep, product=kw.get("product"))
        return _fake_report()

    monkeypatch.setattr(market, "category_guess", guess)
    monkeypatch.setattr(market, "build", build)
    b = TestClient(app).post("/research", json={"product": "수제 립밤", "seeds": ["립밤"],
                                                "category": "50000002", "keywords": ["립밤"]}).json()
    assert seen["category"] == "50000002" and seen["keep"] == ["립밤"] and seen["product"] == "수제 립밤"
    assert seen["seeds"] == ["립밤"]      # 검색 요청 seeds는 그대로, 사장님 낱말은 product로 만든다
    assert b["category"]["code"] == "50000002" and b["category"]["guessed"] is False


def test_research_returns_category_candidates_when_unknown(monkeypatch):
    from server.engine import market
    monkeypatch.setattr(market, "category_guess", lambda product, online=True: (None, ["50000006", "50000008"]))
    monkeypatch.setattr(market, "build", lambda *a, **k: _fake_report())
    b = TestClient(app).post("/research", json={"product": "캠핑의자"}).json()
    assert [c["code"] for c in b["category_candidates"]] == ["50000006", "50000008"] and all(c["name"] for c in b["category_candidates"])
    monkeypatch.setattr(market, "category_guess", lambda product, online=True: ("50000006", ["50000006"]))
    assert TestClient(app).post("/research", json={"product": "캠핑의자"}).json()["category_candidates"] == []


def test_research_counts_category_points_calls_once_even_when_all_fail(monkeypatch):
    from server.engine import market, naver_api
    calls = []
    monkeypatch.setattr(naver_api, "category_keyword_points", lambda c, k, online=True: calls.append(c))   # 전부 실패(None)
    monkeypatch.setattr(market, "build", lambda *a, **k: None)
    TestClient(app).post("/research", json={"product": "캠핑의자"})
    assert 0 < len(calls) <= 12
