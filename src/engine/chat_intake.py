"""챗봇 입구 (노션 Track 2, 계획 Phase 7): 대화로 상품·판매가·남는 돈·예산·목적·검색어를 받아 코치 단계 1을 채운다.

가정 A3 (사용자 결정 11/9)
- 모델: 비용이 낮은 Claude Haiku 계열 (claude-haiku-5-5), 키는 사용자가 .env·Streamlit Secrets의 ANTHROPIC_API_KEY에 넣음
- LLM 출력은 정해진 필드만 받는다: 구조화 출력(JSON 스키마)으로 받고, 값은 여기서 다시 검사한다
- 숫자는 사용자가 확인 카드에서 고친 뒤에만 코치에 반영 (LLM이 직접 바꾸지 않음)
- 키·개인정보는 LLM에 보내지 않는다: 대화에서 전화번호·이메일처럼 보이는 것은 보내기 전에 지운다
- 키가 없거나 호출이 실패하면 IntakeUnavailable → 화면은 지금 질문 폼으로 돌아간다
"""
import json
import os
import re
from typing import Dict, List, Optional, Tuple

MODEL = "claude-haiku-5-5"
MAX_TURNS = 12               # 대화가 길어지면 폼으로 넘기기 (비용 상한 보조)
GOALS = ["판매", "인지도", "방문", "재구매"]

SYSTEM = """너는 광고를 처음 하는 사장님의 첫 광고 예산을 돕는 코치의 접수 담당이야.
사장님과 짧게 대화하며 아래 값을 알아내. 한 번에 한두 개만, 쉬운 말로 물어봐.
- product: 무엇을 파는지 (짧게)
- price: 1개 팔면 손님이 내는 돈 (원, 정수)
- profit: 1개 팔면 남는 돈 (원, 정수). 사장님이 마진 %로 말하면 price × % 로 계산해서 넣어
- budget: 한 달에 광고에 쓸 수 있는 최대 금액 (원, 정수)
- goal: 광고로 바라는 것. 판매·인지도·방문·재구매 중 하나
- keyword: 손님이 이 상품을 찾을 때 네이버에서 검색할 만한 단어 하나 (없으면 null)
모르는 값은 null로 두고 reply에서 물어봐. 추측해서 채우지 마. "2만" = 20000, "30만" = 300000.
다 모이면 done을 true로 하고 reply에 "이렇게 이해했어요"라고 요약해.
이름·전화번호·주소 같은 개인정보는 묻지 마. 광고 집행·계정 접속은 하지 않는다고 안내해."""

SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "product": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "price": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "profit": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "budget": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "goal": {"anyOf": [{"type": "string", "enum": GOALS}, {"type": "null"}]},
        "keyword": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "done": {"type": "boolean"},
    },
    "required": ["reply", "product", "price", "profit", "budget", "goal", "keyword", "done"],
    "additionalProperties": False,
}
FIELD_KEYS = ("product", "price", "profit", "budget", "goal", "keyword")


class IntakeUnavailable(Exception):
    """대화 입구를 쓸 수 없음 (키 없음·SDK 없음·호출 실패·거절). 화면은 질문 폼으로."""


_PHONE = re.compile(r"(\+?82[-\s]?)?0\d{1,2}[-\s.]?\d{3,4}[-\s.]?\d{4}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def scrub(text: str) -> str:
    """보내기 전에 전화번호·이메일처럼 보이는 것을 지운다."""
    return _EMAIL.sub("[이메일 지움]", _PHONE.sub("[전화번호 지움]", text or ""))


def api_key() -> Optional[str]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # noqa: BLE001  (secrets 파일 없음)
        return None


def make_client():
    """키와 SDK가 있으면 클라이언트, 없으면 None (화면은 폼으로)."""
    key = api_key()
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic(api_key=key, max_retries=1, timeout=30.0)


def validate(raw: Dict) -> Dict:
    """LLM 출력에서 정해진 필드만, 범위 안의 값만 남긴다. 이상한 값은 None (사용자에게 다시 물음)."""
    out: Dict = {"reply": str(raw.get("reply") or "")[:800], "done": bool(raw.get("done"))}
    for k in ("price", "profit", "budget"):
        v = raw.get(k)
        out[k] = int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 < v <= 1_000_000_000 else None
    if out["price"] and out["profit"] and out["profit"] > out["price"]:
        out["profit"] = None                         # 남는 돈이 판매가보다 클 수 없음 → 다시 묻기
    for k in ("product", "keyword"):
        v = raw.get(k)
        out[k] = v.strip()[:40] if isinstance(v, str) and v.strip() else None
    out["goal"] = raw.get("goal") if raw.get("goal") in GOALS else None
    if out["done"] and not all(out[k] for k in ("price", "profit", "budget")):
        out["done"] = False
    return out


def ask(client, history: List[Dict[str, str]]) -> Dict:
    """history: [{"role": "user"|"assistant", "content": 글}] → 검증된 필드 dict. 실패하면 IntakeUnavailable."""
    if client is None:
        raise IntakeUnavailable("키 없음")
    if len(history) > MAX_TURNS * 2:
        raise IntakeUnavailable("대화가 길어짐")
    messages = [{"role": m["role"], "content": scrub(m["content"]) if m["role"] == "user" else m["content"]}
                for m in history]
    return validate(call_json(client, SYSTEM, messages, SCHEMA))


def call_json(client, system: str, messages: List[Dict], schema: Dict, max_tokens: int = 2_048) -> Dict:
    """구조화 출력(JSON 스키마)으로 한 번 부르고 dict로. 어떤 실패든 IntakeUnavailable (화면은 대안으로)."""
    if client is None:
        raise IntakeUnavailable("키 없음")
    try:
        import anthropic
        response = client.messages.create(
            model=MODEL, max_tokens=max_tokens, system=system, messages=messages,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        )
    except ImportError as e:
        raise IntakeUnavailable("SDK 없음") from e
    except anthropic.APIConnectionError as e:
        raise IntakeUnavailable("연결 실패") from e
    except anthropic.RateLimitError as e:
        raise IntakeUnavailable("요청이 많음") from e
    except anthropic.APIStatusError as e:
        raise IntakeUnavailable(f"API 오류 {e.status_code}") from e
    except anthropic.APIError as e:             # 그 밖의 SDK 오류도 화면을 멈추지 않게 (검수 A16)
        raise IntakeUnavailable(f"API 오류 {type(e).__name__}") from e
    if response.stop_reason == "refusal":
        raise IntakeUnavailable("응답 거절")
    text = next((b.text for b in response.content if b.type == "text"), None)
    try:
        out = json.loads(text or "")
    except (TypeError, ValueError) as e:
        raise IntakeUnavailable("응답 형식 오류") from e
    if not isinstance(out, dict):
        raise IntakeUnavailable("응답 형식 오류")
    return out


def to_coach_inputs(fields: Dict) -> Tuple[Dict, List[str]]:
    """확인 카드에서 고친 값 → 코치 입력 키. 비어 있는 필수 값 목록도 돌려준다."""
    out = {}
    if fields.get("price"):
        out["q_price"] = int(fields["price"])
    if fields.get("profit"):
        out["q_profit"] = int(fields["profit"])
    if fields.get("budget"):
        out["q_budget"] = int(fields["budget"])
    if fields.get("keyword"):
        out["q_keyword"] = str(fields["keyword"]).replace(" ", "")
    missing = [name for k, name in (("price", "판매가"), ("profit", "남는 돈"), ("budget", "월 최대 광고비")) if not fields.get(k)]
    return out, missing
