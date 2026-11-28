"""좋은 점 칩 다듬기 (② 문구): 다른 가게·브랜드 이름과 다른 상품을 찾는 말 거르기 + 상품에 맞는 묶음 이름 붙이기.

- 네이버 검색어에서 뽑은 꾸밈말 낱말만 Claude에게 보낸다. 네이버 숫자는 보내지 않는다.
- 한 번에 묻는다: 이 중 브랜드·가게 이름은? 이 상품이 아닌 다른 상품(쿠키의 '커터'·'믹스')을 찾는 말은? 나머지는 어떤 묶음(재질·기능·크기…)인가?
- 거를지와 묶음은 (상품, 낱말)마다 서버가 켜져 있는 동안 기억한다 (다른 상품인지는 상품마다 달라서).
- 키가 없거나 실패하면 아무것도 거르지 않고 묶음도 바꾸지 않는다 (화면은 원래 묶음 + '그 밖').
"""
import json
import logging
import os
from typing import Dict, Iterable, List, Optional, Set, Tuple

from . import copywriter

log = logging.getLogger("coach.brands")
MODEL = os.environ.get("COACH_BRAND_MODEL", "claude-sonnet-5-5")
OTHER = "그 밖"
MAX_KNOWN = 20000   # 기억할 (상품, 낱말) 수. 넘으면 비우고 다시 묻는다 (메모리가 끝없이 늘지 않게)

_known: Dict[Tuple[str, str], bool] = {}   # (상품, 낱말) → 거를 말인가 (브랜드이거나 다른 상품)
_groups: Dict[Tuple[str, str], str] = {}   # (상품, 낱말) → 묶음 이름

SCHEMA = {
    "type": "object",
    "properties": {
        "brands": {"type": "array", "items": {"type": "string"}},
        "others": {"type": "array", "items": {"type": "string"}},
        "groups": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "words": {"type": "array", "items": {"type": "string"}}},
            "required": ["name", "words"], "additionalProperties": False}},
    },
    "required": ["brands", "others", "groups"], "additionalProperties": False,
}

SYSTEM = ("너는 한국 온라인 쇼핑 검색어를 분류하는 도우미야. 사장님이 파는 상품과, 손님이 그 상품과 함께 검색한 낱말 목록을 받는다.\n"
          "1) brands: 브랜드·회사·가게·카페·캐릭터 이름(오타나 줄임말 포함, 예: 스탠리·스텐리·스벅·투썸·락앤락)인 낱말. "
          "재질·크기·기능·맛·모양·용도처럼 상품의 특징을 말하는 낱말(예: 스텐·유리·대용량·보온·개별포장)은 넣지 않는다. 애매하면 넣지 않는다.\n"
          "2) others: 이 상품이 아니라 다른 상품을 찾을 때 쓰는 낱말(예: 상품이 수제 쿠키면 커터·틀·믹스처럼 만드는 도구나 재료). "
          "맛·모양·포장·용도처럼 이 상품을 꾸미는 낱말은 넣지 않는다. 애매하면 넣지 않는다.\n"
          "3) groups: brands·others가 아닌 낱말을 이 상품을 사려는 손님이 보는 기준으로 2~5개 묶음에 나눈다. "
          "묶음 이름은 2~4글자 쉬운 말(예: 재질·기능·크기·용도·맛·색·디자인·포장·배송). 낱말 하나는 한 묶음에만. "
          "어디에도 안 맞는 낱말만 '그 밖'에 넣는다.\n"
          "받은 낱말을 글자 그대로 써서 돌려준다.")


def _norm(product: str) -> str:
    return product.replace(" ", "")


def _ask(client, product: str, words: List[str]) -> Tuple[Set[str], Dict[str, str]]:
    resp = client.messages.create(
        model=MODEL, max_tokens=4000, system=SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": json.dumps({"상품": product, "낱말": words}, ensure_ascii=False)}])
    data = json.loads(copywriter.reply_text(resp))
    brand = {w for w in [*data.get("brands", []), *data.get("others", [])] if w in words}   # 둘 다 칩·추천 검색어에서 뺀다
    groups: Dict[str, str] = {}
    for g in data.get("groups", []):
        name = str(g.get("name", "")).strip()[:6] or OTHER
        for w in g.get("words", []):
            if w in words and w not in brand and w not in groups:
                groups[w] = name
    return brand, groups


def classify(product: str, words: Iterable[str], client=None) -> Tuple[Set[str], Dict[str, str]]:
    """→ (브랜드 낱말, {낱말: 묶음 이름}). client가 None이면 키로 만들고, False면 묻지 않는다 (기억한 것만)."""
    words = [w for w in dict.fromkeys(words) if w]
    p = _norm(product)
    unknown = [w for w in words if not _known.get((p, w)) and (p, w) not in _groups]   # 모르는 말 + 거르지 않는데 묶음이 없는 말
    if unknown and client is not False:
        client = client or copywriter.make_client()
        if client:
            if len(_known) + len(unknown) > MAX_KNOWN:   # 묻기 전에 비우고 이번 낱말을 모두 묻는다 (물은 뒤 비우면 이미 알던 말이 이번 답에서 빠짐)
                _known.clear()
                _groups.clear()
                unknown = words
            try:
                found, groups = _ask(client, product, unknown)
                for w in unknown:
                    _known[(p, w)] = w in found
                    if w in groups:
                        _groups[(p, w)] = groups[w]
                log.info("good points check asked=%d brands=%d groups=%d", len(unknown), len(found), len(set(groups.values())))
            except Exception as e:  # noqa: BLE001 (요청 내용이 섞일 수 있어 메시지는 남기지 않음)
                log.warning("claude degraded part=brands err=%s", type(e).__name__)
    brand = {w for w in words if _known.get((p, w))}
    return brand, {w: g for w in words if (g := _groups.get((p, w))) and w not in brand}   # get: 다른 요청이 그사이 비워도 안 깨지게


def brand_words(product: str, words: Iterable[str], client=None) -> Set[str]:
    """words 중 거를 말: 브랜드·가게 이름과 다른 상품을 찾는 말 (classify의 앞 절반)."""
    return classify(product, words, client)[0]
