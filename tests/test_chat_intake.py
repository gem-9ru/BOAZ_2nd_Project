"""Phase 7: 챗봇 입구 (실제 API 호출 없이 가짜 클라이언트로)."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import chat_intake as CI  # noqa: E402


class FakeClient:
    def __init__(self, payload, stop_reason="end_turn"):
        self.payload, self.stop_reason, self.sent = payload, stop_reason, None
        self.messages = self

    def create(self, **kw):
        self.sent = kw
        text = self.payload if isinstance(self.payload, str) else json.dumps(self.payload, ensure_ascii=False)
        return SimpleNamespace(stop_reason=self.stop_reason, content=[SimpleNamespace(type="text", text=text)])


GOOD = {"reply": "이렇게 이해했어요", "product": "원두", "price": 20000, "profit": 7000, "budget": 300000,
        "goal": "판매", "keyword": "원두커피", "done": True}


def test_ask_returns_only_schema_fields_and_scrubs_personal_data():
    c = FakeClient({**GOOD, "extra": "무시"})
    out = CI.ask(c, [{"role": "user", "content": "원두 팔아요. 연락처 010-1234-5678, a@b.com"}])
    assert set(out) == {"reply", "done", *CI.FIELD_KEYS} and out["price"] == 20000 and out["done"]
    sent = c.sent["messages"][0]["content"]
    assert "010-1234-5678" not in sent and "a@b.com" not in sent
    assert c.sent["model"] == "claude-haiku-5-5" and c.sent["output_config"]["format"]["type"] == "json_schema"
    assert "ANTHROPIC" not in json.dumps(c.sent, ensure_ascii=False)


def test_validate_rejects_bad_values():
    out = CI.validate({**GOOD, "price": -5, "profit": 99_999, "goal": "해킹", "budget": True})
    assert out["price"] is None and out["goal"] is None and out["budget"] is None and not out["done"]
    out = CI.validate({**GOOD, "profit": 30_000})             # 남는 돈 > 판매가 → 다시 묻기
    assert out["profit"] is None and not out["done"]


def test_unavailable_paths_fall_back_to_form():
    with pytest.raises(CI.IntakeUnavailable):
        CI.ask(None, [{"role": "user", "content": "안녕"}])                     # 키 없음
    with pytest.raises(CI.IntakeUnavailable):
        CI.ask(FakeClient(GOOD, stop_reason="refusal"), [{"role": "user", "content": "x"}])
    with pytest.raises(CI.IntakeUnavailable):
        CI.ask(FakeClient("not json"), [{"role": "user", "content": "x"}])


def test_no_key_means_no_client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(CI, "api_key", lambda: None)
    assert CI.make_client() is None


def test_to_coach_inputs():
    got, missing = CI.to_coach_inputs({"price": 20000, "profit": 7000, "budget": None, "keyword": "원두 커피"})
    assert got == {"q_price": 20000, "q_profit": 7000, "q_keyword": "원두커피"} and missing == ["월 최대 광고비"]
