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
    assert all(not copywriter.check_copy(c) for c in cs)


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


def test_claude_gets_strengths_and_search_words_apart_with_room_to_answer():
    """검색어(노트북대여)를 장점으로 보내면 '대여 가능'처럼 없는 사실을 쓴다: 따로 보낸다.
    생각이 토큰을 먼저 쓰므로 max_tokens는 넉넉히, 답은 JSON 틀로 받는다."""
    seen = {}

    class Msgs:
        def create(self, **kw):
            seen.update(kw)
            body = {"copies": [{"headline": "가볍게 들고 다니는 노트북",
                                "text": "카페에서도 도서관에서도 가볍게 꺼내 쓰세요. 무게 부담 없는 노트북, 프로필 링크에서 만나 보세요."}]}
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(body, ensure_ascii=False))],
                                   stop_reason="end_turn")

    client = SimpleNamespace(messages=Msgs())
    cs, used = copywriter.meta_copies_with_source("노트북", ["가벼움"], n=3, client=client,
                                                 keywords=["노트북대여", "가성비노트북"])
    sent = json.loads(seen["messages"][0]["content"])
    assert sent["장점"] == ["가벼움"] and sent["검색어"] == ["노트북대여", "가성비노트북"]
    assert seen["max_tokens"] >= 8000 and seen["output_config"]["format"]["type"] == "json_schema"
    assert used and cs[0]["headline"] == "가볍게 들고 다니는 노트북" and len(cs) == 3


def test_basis_catches_changed_word_endings_and_claude_paraphrase():
    c = {"headline": "가볍게 들고 다니는 노트북", "text": "가벼운 노트북이라 하나씩 따로 포장해 드려요."}
    assert copywriter.basis(c, ["가벼움", "개별포장", "버터 듬뿍"], None) == ["가벼움"]
    c2 = {**c, "basis": ["개별포장", "버터 듬뿍"]}   # Claude가 '썼다'고만 하고 문구에 없는 말은 넣지 않는다
    assert copywriter.basis(c2, ["가벼움", "개별포장", "버터 듬뿍"], {"label": "선물로 찾는 손님"}) == ["가벼움", "선물로 찾는 손님"]
    c3 = {"headline": "천연 비누", "text": "천연 재료로 만든 수제 비누예요.", "basis": ["천연비누"]}
    assert copywriter.basis(c3, ["천연비누", "수제비누"], None) == ["천연비누", "수제비누"]   # 띄어쓰기만 다르면 같은 말


def test_claude_copies_keep_their_basis_list():
    body = {"copies": [{"headline": "가볍게 들고 다니는 노트북", "text": "가벼운 노트북, 프로필 링크에서 만나 보세요.", "basis": ["가벼움"]}]}
    out = copywriter._parse(json.dumps(body, ensure_ascii=False))
    assert out[0]["basis"] == ["가벼움"]


def test_tone_goes_to_claude_only_when_known():
    seen = []

    class Msgs:
        def create(self, **kw):
            seen.append(json.loads(kw["messages"][0]["content"]))
            return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"copies": []}')], stop_reason="end_turn")

    client = SimpleNamespace(messages=Msgs())
    copywriter.meta_copies_with_source("쿠키", ["버터"], n=3, client=client, tone="감성적으로")
    copywriter.meta_copies_with_source("쿠키", ["버터"], n=3, client=client, tone="이상한값")
    assert seen[0]["말투"].startswith("장면이 떠오르게") and "말투" not in seen[1]


def test_prompt_and_templates_do_not_invent_facts_or_post_wording():
    """광고는 누르면 바로 가는 곳이 있다: '프로필 링크' 말투 대신 버튼 권유. 틀 문장은 없는 후기를 말하지 않는다. 제목 27자 권장(메타)."""
    p = copywriter._system_prompt(3)
    assert "프로필 링크에서' 같은 게시물 말투는 쓰지 않는다" in p and "27자 이내 권장" in p
    cs = copywriter.meta_copies("수제 쿠키", ["버터 듬뿍", "개별포장", "당일 구움"], n=9, client=False)
    assert cs and not any("후기" in c["text"] for c in cs)



def test_prompt_asks_for_the_product_name():
    assert "'상품' 이름은 제목이나 본문에 한 번은 그대로 넣는다" in copywriter._system_prompt(3)


def test_basis_does_not_count_a_cut_compound_word():
    c = {"headline": "아로마 향이 머무는 향초", "text": "은은한 아로마 향을 좋아하시나요? 향초에 불을 붙여 보세요."}
    assert copywriter.basis(c, ["아로마향초", "아로마", "향초"], None) == ["아로마", "향초"]
