"""좋은 점 칩에서 다른 가게·브랜드 이름 거르기 (② 문구).

- 네이버 검색어에서 뽑은 꾸밈말 낱말만 Claude에게 보내 "브랜드·가게 이름인가"를 묻는다. 네이버 숫자는 보내지 않는다.
- 한 번 물어본 낱말은 서버가 켜져 있는 동안 기억한다 (같은 상품을 다시 찾을 때 기다리지 않게).
- 키가 없거나 실패하면 아무것도 거르지 않는다 (화면은 예전처럼 '그 밖'에 접고 경고).
"""
import json
import logging
import os
from typing import Dict, Iterable, List, Set

from . import copywriter

log = logging.getLogger("coach.brands")
MODEL = os.environ.get("COACH_BRAND_MODEL", "claude-sonnet-5-5")

_known: Dict[str, bool] = {}   # 낱말 → 브랜드인가 (서버 메모리)

SCHEMA = {
    "type": "object",
    "properties": {"brands": {"type": "array", "items": {"type": "string"}}},
    "required": ["brands"], "additionalProperties": False,
}

SYSTEM = ("너는 한국 온라인 쇼핑 검색어를 분류하는 도우미야. 사장님이 파는 상품과, 손님이 그 상품과 함께 검색한 낱말 목록을 받는다.\n"
          "이 중 브랜드·회사·가게·카페·캐릭터 이름(오타나 줄임말 포함, 예: 스탠리·스텐리·스벅·투썸·락앤락)인 낱말만 골라 돌려준다.\n"
          "재질·크기·기능·맛·모양·용도처럼 상품의 특징을 말하는 낱말(예: 스텐·유리·대용량·보온·아이스·개별포장)은 고르지 않는다.\n"
          "애매하면 고르지 않는다. 받은 낱말을 그대로 써서 돌려준다.")


def _ask(client, product: str, words: List[str]) -> Set[str]:
    resp = client.messages.create(
        model=MODEL, max_tokens=4000, system=SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": json.dumps({"상품": product, "낱말": words}, ensure_ascii=False)}])
    text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
    picked = json.loads(text).get("brands", [])
    return {w for w in picked if w in words}


def brand_words(product: str, words: Iterable[str], client=None) -> Set[str]:
    """words 중 브랜드·가게 이름. client가 None이면 키로 만들고, False면 묻지 않는다 (기억한 것만)."""
    words = [w for w in dict.fromkeys(words) if w]
    unknown = [w for w in words if w not in _known]
    if unknown and client is not False:
        client = client or copywriter.make_client()
        if client:
            try:
                found = _ask(client, product, unknown)
                for w in unknown:
                    _known[w] = w in found
                log.info("brand check asked=%d brands=%d", len(unknown), len(found))
            except Exception as e:  # noqa: BLE001 (요청 내용이 섞일 수 있어 메시지는 남기지 않음)
                log.warning("claude degraded part=brands err=%s", type(e).__name__)
    return {w for w in words if _known.get(w)}
