"""광고 어시스턴트 (v4 5장 공통 레이아웃·8장): 단계마다 첫 말풍선 + 추천 질문 2개, 질문엔 그 단계 결과 JSON만 주고 LLM이 설명."""
from fastapi.testclient import TestClient

from server.app import app
from server.engine.loop import assistant
from server.engine.loop import run as loop_run
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"
STEPS = ["AN-01", "AN-02", "AN-03", "AN-04", "AN-05", "AN-06"]


def oven():
    return loop_run.run(read_export(OVEN))


def test_every_step_has_an_opening_and_two_suggestions_without_llm():
    r = oven()
    for s in STEPS:
        o = assistant.opening(r, s)
        assert o["message"] and len(o["suggestions"]) == 2


def test_opening_of_an01_names_the_field_and_first_alert():
    o = assistant.opening(oven(), "AN-01")
    assert "형식·미디어" in o["message"]
    assert o["alerts"] and o["alerts"][0]["mark"] == "▲"


def test_alert_bubble_only_on_the_screen_it_belongs_to():
    r = oven()
    assert all(a["screen"] == "AN-02" for a in assistant.opening(r, "AN-02")["alerts"])


def test_context_for_a_step_is_only_that_steps_numbers():
    ctx = assistant.context(oven(), "AN-05")
    assert "backtest" in ctx and "matrix" not in ctx


class FakeClient:
    def __init__(self):
        self.sent = None
        self.messages = self

    def create(self, **kw):
        self.sent = kw
        return type("R", (), {"content": [type("B", (), {"type": "text", "text": "릴스에 세로 소재가 맞아요."})()]})()


def test_answer_sends_step_json_and_rules_to_llm():
    fake = FakeClient()
    a = assistant.answer(oven(), "AN-01", "왜 세로예요?", client=fake)
    assert a["source"] == "llm" and "세로" in a["message"]
    assert "JSON에 있는 숫자만" in fake.sent["system"]
    assert "형식·미디어" in fake.sent["messages"][0]["content"]
    # 모델이 먼저 생각(thinking)을 하므로 한도가 작으면 글 없이 끝난다 (400 → 글 없음 실측)
    assert fake.sent["max_tokens"] >= 1500


def test_answer_without_llm_falls_back_to_rules():
    a = assistant.answer(oven(), "AN-01", "왜 세로예요?", client=None)
    assert a["source"] == "rules" and a["message"]


def test_api_assistant_opening_and_bad_code():
    c = TestClient(app)
    code = c.get("/analysis/example").json()["code"]
    r = c.post("/assistant", json={"code": code, "step": "AN-04"}).json()
    assert len(r["suggestions"]) == 2
    assert c.post("/assistant", json={"code": "ZZZZ", "step": "AN-01"}).status_code == 404


def test_ex03_extension_chatbot_takes_over_the_change():
    o = assistant.opening(oven(), "EX-03")
    assert "형식·미디어" in o["message"] and "그대로" in o["message"]
    assert len(o["suggestions"]) == 2
    assert "matrix" in assistant.context(oven(), "EX-03")


def test_v42_speech_rules_are_in_the_system_prompt():
    # 분석 페이지와 확장 프로그램 챗봇(EX-03)이 같은 SYSTEM을 쓴다
    for rule in ("확실해요 / ○ 쪽이에요 / 아직 몰라요", "범위나 확률", "광고 덕분에 늘었어요", "5,000원씩 두 세트", "사장님 말을 먼저"):
        assert rule in assistant.SYSTEM
    fake = FakeClient()
    assistant.answer(oven(), "EX-03", "세로 소재는 어떻게 만들어요?", client=fake)
    assert fake.sent["system"] == assistant.SYSTEM


def test_v42_openings_use_owner_words_only():
    r = oven()
    for s in STEPS + ["EX-03"]:
        o = assistant.opening(r, s)
        for bad in ("유력", "보류", "₩", "코치"):
            assert bad not in o["message"], (s, bad)
    assert "보통" in assistant.opening(r, "AN-05")["message"] and "적게" in assistant.opening(r, "AN-05")["message"]
