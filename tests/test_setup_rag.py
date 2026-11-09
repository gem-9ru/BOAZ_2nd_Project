"""MVP 7번 세팅 챗봇: 세팅 카드 파싱·찾기(BM25)·답하기 (실제 API 호출 없이)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import chat_intake as CI  # noqa: E402
from src.engine import setup_rag as SR  # noqa: E402


class FakeClient:
    def __init__(self, payload):
        self.payload, self.sent, self.calls = payload, None, 0
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        self.sent = kw
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps(self.payload, ensure_ascii=False))])


def test_59_cards_with_required_fields():
    cards = SR.load_cards()
    assert len(cards) == 59 and len({c.id for c in cards}) == 59
    assert sum(c.id.startswith("naver") for c in cards) == 28 and sum(c.id.startswith("meta") for c in cards) == 31
    for c in cards:
        assert c.title and c.media and c.stage and c.questions and c.screen and c.coach and c.body, c.id
        assert c.check in ("✅", "△", "❓", "🧮") and c.sources, c.id
    assert SR.parse_cards("# 머리말\n- 이건 카드 아님\n") == []      # 파일 머리말은 카드가 아님


@pytest.mark.parametrize("query,expect", [
    ("하루 예산", "naver-setup-009"),
    ("네이버 하루 예산 어디에 넣어?", "naver-setup-009"),
    ("머신 러닝", "meta-lrn-"),
    ("월간검색수", "naver-kw-002"),
    ("스마트스토어에 픽셀 달 수 있어?", "meta-obj-003"),
    ("광고 순위는 어떻게 정해져?", "naver-setup-012"),
    ("전환 추적 어떻게 해", "naver-setup-016"),
    ("메타 목표 뭐 골라?", "meta-obj-"),
])
def test_search_finds_right_card(query, expect):
    found = SR.find(query)
    assert found and found[0][0].id.startswith(expect), [(c.id, round(s, 1)) for c, s in found]


def test_below_threshold_does_not_call_llm():
    for q in ("오늘 날씨 어때", "점심 메뉴 추천", "주식 뭐 사"):
        assert SR.find(q) == []
    client = FakeClient({"answer": "x", "card_ids": []})
    out = SR.answer(client, "오늘 날씨 어때", SR.find("오늘 날씨 어때"), {})
    assert client.calls == 0 and "자료에 없어요" in out["answer"]


def test_no_key_shows_card_summaries():
    with pytest.raises(CI.IntakeUnavailable):
        SR.answer(None, "하루 예산", SR.find("하루 예산"), {})
    s = SR.summaries(SR.find("하루 예산"))
    assert 1 <= len(s) <= 3 and s[0]["title"] and s[0]["sources"] and s[0]["check"] in ("✅", "△", "❓", "🧮")


def test_answer_cites_used_cards_and_keeps_secrets_out(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-should-not-be-sent")
    found = SR.find("네이버 하루 예산 어디에 넣어?")
    client = FakeClient({"answer": "캠페인 하루 예산에 2,237원을 넣으세요.", "card_ids": ["naver-setup-009", "nope-999"]})
    ctx = {"naver": 68_000, "meta": 142_000, "keyword": "원두커피", "price": 20_000, "wins": 3}
    out = SR.answer(client, "네이버 하루 예산 어디에 넣어? 제 번호 010-1234-5678", found, ctx)
    assert [c.id for c in out["cards"]] == ["naver-setup-009"]           # 없는 id는 버림
    body = json.dumps(client.sent, ensure_ascii=False)
    assert "sk-ant" not in body and "010-1234-5678" not in body
    assert "하루 2,237원" in body and "100번 해 보면 1년 동안 3번" in body   # 코치 숫자(하루 예산 = 월 ÷ 30.4)
    assert "공식 확인 못 함" in client.sent["system"] and client.sent["model"] == "claude-haiku-5-5"


def test_screenshot_limits():
    found = SR.find("메타 목표 뭐 골라?")
    client = FakeClient({"answer": "판매를 고르세요", "card_ids": [found[0][0].id]})
    SR.answer(client, "이 화면에서 뭐 눌러?", found, {}, image=(b"\x89PNG" + b"0" * 100, "cap.png"))
    blocks = client.sent["messages"][0]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["media_type"] == "image/png"
    with pytest.raises(ValueError):
        SR.answer(client, "x", found, {}, image=(b"0" * (SR.MAX_IMAGE_BYTES + 1), "big.png"))
    with pytest.raises(ValueError):
        SR.answer(client, "x", found, {}, image=(b"GIF89a", "anim.gif"))


def test_helpbot_falls_back_to_setup_card():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
    import helpbot
    won = lambda v: f"{v:,.0f}원"  # noqa: E731
    out = helpbot.answer("스마트스토어에 메타 픽셀 달 수 있어?", {}, "광고 관리자", won)
    assert "세팅 자료에서 찾았어요" in out and "❓" in out
    assert "포화" in helpbot.answer("포화가 뭐야?", {}, "광고 관리자", won)      # 규칙 기반 답은 그대로


NUMS = {"naver": 68_000, "naver_daily": 68_000 / 30.4, "meta": 142_000, "meta_daily": 142_000 / 30.4, "meta_rec_daily": 13_000,
        "meta_objective": "트래픽", "bid": 2_400, "shopping_min": 50, "smartstore": True, "keyword": "원두커피",
        "cpa": 150_000, "be_first": 7_000, "no_ad": True}


def test_my_numbers_follow_card_coach_link():
    line = SR.my_numbers(SR.by_id("naver-setup-009"), NUMS)
    assert line == ["네이버 하루 예산 약 2,237원 (월 68,000원 ÷ 30.4)"]
    bid = SR.my_numbers(SR.by_id("naver-setup-011"), NUMS)
    assert "최소 50원" in bid[0] and "2,400원" in bid[0]                 # 스마트스토어: 쇼핑검색 최소 입찰가 + 키워드 참고
    meta = " ".join(SR.my_numbers(SR.by_id("meta-bud-004"), NUMS))
    assert "메타 하루 예산 약 4,671원" in meta and "13,000원" in meta
    obj = " ".join(SR.my_numbers(SR.by_id("meta-obj-004"), NUMS))
    assert "트래픽" in obj and "150,000원" in obj
    assert SR.my_numbers(SR.by_id("naver-setup-013"), NUMS) == []         # 코치 연결 '없음'
    assert SR.my_numbers(SR.by_id("naver-setup-009"), {**NUMS, "naver": 0}) == []   # 네이버 배분이 없으면 숫자 없음
