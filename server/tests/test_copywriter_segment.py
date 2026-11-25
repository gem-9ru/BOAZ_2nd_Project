"""문구 쓰기: 고른 손님 무리 반영과 근거 낱말 (찾기-문구-되묻기 Task 6)."""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from server.app import app
from server.engine import copywriter

GIFT = {"intent": "선물·답례", "label": "선물로 찾는 손님"}
SEASON = {"intent": "시즌", "label": "시즌에 찾는 손님", "peak_month": 12}


def test_basis_lists_words_in_copy_and_segment():
    c = {"headline": "답례품 쿠키", "text": "개별포장으로 드려요"}
    assert copywriter.basis(c, ["개별포장", "버터", "답례품쿠키"], {"label": "선물로 찾는 손님"}) == [
        "개별포장", "답례품쿠키", "선물로 찾는 손님"]


def test_basis_without_segment_and_no_duplicates():
    c = {"headline": "쿠키", "text": "쿠키 선물"}
    assert copywriter.basis(c, ["쿠키", "쿠키", "버터"], None) == ["쿠키"]


def test_gift_segment_template_first():
    cs, _ = copywriter.meta_copies_with_source("수제 쿠키", ["개별포장"], n=3, client=False, segment=GIFT)
    assert cs[0]["text"].startswith("고마운 분께")
    assert all(not copywriter.check_copy("meta", c) for c in cs)


def test_season_segment_template_first():
    cs, _ = copywriter.meta_copies_with_source("수제 쿠키", ["개별포장"], n=3, client=False, segment=SEASON)
    assert cs[0]["headline"] == "12월 수제 쿠키" and "12월, 수제 쿠키 준비하세요" in cs[0]["text"]


def test_season_without_month_has_no_segment_template():
    seg = {"intent": "시즌", "label": "시즌에 찾는 손님"}
    a, _ = copywriter.meta_copies_with_source("수제 쿠키", ["개별포장"], n=3, client=False, segment=seg)
    b, _ = copywriter.meta_copies_with_source("수제 쿠키", ["개별포장"], n=3, client=False)
    assert a == b


def test_claude_gets_segment_words_not_numbers():
    seen = []

    class Msgs:
        def create(self, **kw):
            seen.append(kw["messages"][0]["content"])
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="[]")])

    client = SimpleNamespace(messages=Msgs())
    copywriter.meta_copies_with_source("수제 쿠키", ["개별포장"], n=3, client=client, segment=SEASON)
    sent = json.loads(seen[0])
    assert sent["손님"] == "시즌에 찾는 손님" and sent["시기"] == "12월"
    assert "total_qc" not in seen[0] and "%" not in seen[0]


def test_copies_api_returns_basis(monkeypatch):
    monkeypatch.setenv("COACH_NO_LLM", "1")
    b = TestClient(app).post("/copies", json={"product": "수제 쿠키", "strengths": ["개별포장"], "keywords": [], "avoid": [],
                                              "segment": GIFT}).json()
    assert all("basis" in c for c in b["copies"]) and "선물로 찾는 손님" in b["copies"][0]["basis"]


def test_copies_api_backfill_has_basis(monkeypatch):
    monkeypatch.setenv("COACH_NO_LLM", "1")
    b = TestClient(app).post("/copies", json={"product": "수제 쿠키", "strengths": ["개별포장"], "keywords": [],
                                              "avoid": ["고마운"], "segment": GIFT}).json()
    assert len(b["copies"]) == 3 and all(isinstance(c["basis"], list) for c in b["copies"])
