"""광고 문구 쓰기 (T07): 사장님이 알려 준 장점으로 메타·네이버 문구를 만든다.

- ANTHROPIC_API_KEY가 있으면 Claude(claude-haiku-5-5)가 쓰고, 없거나 실패하면 문장 틀을 쓴다.
- 어느 쪽이든 같은 검사를 거친다: 글자 수(네이버 제목 15자·설명 20~45자), 근거 없는 말 금지, 특수문자 정리.
- 키 값은 출력·로그·예외 문구 어디에도 넣지 않는다.
"""
import json
import logging
import os
import re
from typing import Dict, List, Optional, Sequence, Union

log = logging.getLogger("coach.copy")
MODEL = "claude-haiku-5-5"
KEY_NAME = "ANTHROPIC_API_KEY"

NAVER_HEADLINE_MAX = 15
NAVER_TEXT_MIN, NAVER_TEXT_MAX = 20, 45
META_HEADLINE_MAX = 40
META_TEXT_MIN, META_TEXT_MAX = 10, 125

# 근거를 댈 수 없는 최상급·보장 표현 (광고 심의·신뢰 문제)
BANNED = ["최저가", "최저", "1위", "1등", "최고", "최상", "최초", "국내 유일", "세계 유일", "유일", "넘버원",
          "no.1", "no 1", "100%", "무조건", "보장", "완치", "특효"]
GENERIC_STRENGTH = "정성껏 만들었어요"
NAVER_FILLERS = ["스토어에서 확인해 보세요", "지금 만나 보세요", "후기도 확인해 보세요"]
_SAFE_CHARS = re.compile(r"[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ\s.,!?~%&()·\-+'\"]")

Copy = Dict[str, str]
Strengths = Union[str, Sequence[str], None]


# ── 글 정리·검사 ─────────────────────────────────────────

def has_banned(text: str) -> bool:
    low = (text or "").lower()
    return any(b in low for b in BANNED)


def tidy(text: object, max_bang: int = 1) -> str:
    """허용하지 않는 특수문자를 지우고, 공백·느낌표를 정리."""
    t = _SAFE_CHARS.sub(" ", str(text or ""))
    t = re.sub(r"[!]{2,}", "!", t)
    if t.count("!") > max_bang:
        first = t.index("!")
        t = t[:first + 1] + t[first + 1:].replace("!", "")
    return re.sub(r"\s+", " ", t).strip()


def _strength_list(strengths: Strengths) -> List[str]:
    """장점 입력 → 근거 없는 말이 든 조각을 뺀 짧은 조각들. 남는 게 없으면 기본 한 마디."""
    raw = [strengths] if isinstance(strengths, str) else list(strengths or [])
    pieces: List[str] = []
    for r in raw:
        for p in re.split(r"[,;/\n·]|\s및\s", str(r or "")):
            p = tidy(p).rstrip(".!?~ ")
            if p and not has_banned(p) and p not in pieces:
                pieces.append(p)
    return pieces or [GENERIC_STRENGTH]


def _clean_product(product: str) -> str:
    """상품 이름에 근거 없는 말이 있으면 그 단어를 뺌."""
    p = tidy(product, max_bang=0)
    for b in sorted(BANNED, key=len, reverse=True):
        p = re.sub(re.escape(b), "", p, flags=re.I)
    return re.sub(r"\s+", " ", p).strip() or "우리 가게"


def _clip(text: str, limit: int) -> str:
    """limit자 안으로. 되도록 단어 끝에서 자름."""
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if " " in cut and text[limit] != " ":
        cut = cut[:cut.rindex(" ")]
    return cut.rstrip(" ,.·-")


def check_copy(media: str, copy: Copy) -> List[str]:
    """문구 하나의 문제 목록 (비어 있으면 통과). media: 'meta' | 'naver'."""
    h, t = copy.get("headline", ""), copy.get("text", "")
    lim = ((NAVER_HEADLINE_MAX, NAVER_TEXT_MIN, NAVER_TEXT_MAX) if media == "naver"
           else (META_HEADLINE_MAX, META_TEXT_MIN, META_TEXT_MAX))
    problems = []
    if not h or len(h) > lim[0]:
        problems.append(f"제목은 1~{lim[0]}자여야 해요 (지금 {len(h)}자)")
    if not lim[1] <= len(t) <= lim[2]:
        problems.append(f"설명은 {lim[1]}~{lim[2]}자여야 해요 (지금 {len(t)}자)")
    if has_banned(h) or has_banned(t):
        problems.append("근거를 댈 수 없는 표현(최저가·1위·최고·국내 유일 등)이 있어요")
    if _SAFE_CHARS.search(h + t):
        problems.append("쓸 수 없는 특수문자가 있어요")
    return problems


# ── 문장 틀 (키 없을 때·보충용) ─────────────────────────────────

def _fit_text(text: str, lo: int, hi: int, fillers: Sequence[str]) -> str:
    """text를 lo~hi자로 맞춤: 길면 자르고, 짧으면 덧붙임."""
    text = tidy(text)
    for filler in fillers:
        if len(text) >= lo:
            break
        text = f"{text.rstrip('.!? ')}. {filler}"
    return _clip(text, hi)


def _naver_templates(product: str, strengths: List[str]) -> List[Copy]:
    out: List[Copy] = []
    for i in range(max(len(strengths), 3) * 2):
        s = strengths[i % len(strengths)]
        shape = i % 3
        if shape == 0:
            head = product if len(product) <= NAVER_HEADLINE_MAX else s
            body = f"{s}. {product} 지금 만나 보세요"
        elif shape == 1:
            head = f"{product} 보러 가기"
            body = f"{product}, {s}"
        else:
            head = s
            body = f"{product} 찾으세요? {s}"
        head = _clip(tidy(head, 0), NAVER_HEADLINE_MAX) or _clip(product, NAVER_HEADLINE_MAX)
        out.append({"headline": head,
                    "text": _fit_text(body, NAVER_TEXT_MIN, NAVER_TEXT_MAX, NAVER_FILLERS)})
    return out


def _meta_templates(product: str, strengths: List[str]) -> List[Copy]:
    out: List[Copy] = []
    for i in range(max(len(strengths), 3) * 2):
        s = strengths[i % len(strengths)]
        shape = i % 3
        if shape == 0:
            head, body = f"{product}, {s}", f"{product}, {s}. 스토어에서 자세히 확인해 보세요."
        elif shape == 1:
            head, body = f"{s}", f"{s}. {product} 지금 만나 보세요."
        else:
            head, body = f"{product} 소개", f"{product} 어떠세요? {s}. 후기도 함께 확인해 보세요."
        out.append({"headline": _clip(tidy(head, 0), META_HEADLINE_MAX),
                    "text": _clip(tidy(body), META_TEXT_MAX)})
    return out


def _segment_template(product: str, strength: str, segment: Optional[dict]) -> Optional[Copy]:
    """고른 손님 무리에 맞는 틀 하나 (선물·답례 / 달이 있는 시즌). 없으면 None."""
    if not segment:
        return None
    intent, m = segment.get("intent"), segment.get("peak_month")
    if intent == "선물·답례":
        head, body = f"{strength} {product}", f"고마운 분께 {product} 어떠세요? {strength}."
    elif intent == "시즌" and m:
        head, body = f"{m}월 {product}", f"{m}월, {product} 준비하세요. {strength}."
    else:
        return None
    return {"headline": _clip(tidy(head, 0), META_HEADLINE_MAX), "text": _clip(tidy(body), META_TEXT_MAX)}


def basis(copy: Copy, words: Sequence[str], segment: Optional[dict]) -> List[str]:
    """문구 글자에 실제로 들어간 낱말(띄어쓰기 무시, 중복 없음) + 고른 손님 무리 이름."""
    flat = re.sub(r"\s+", "", copy.get("headline", "") + copy.get("text", ""))
    out: List[str] = []
    for w in words:
        w = (w or "").strip()
        if w and re.sub(r"\s+", "", w) in flat and w not in out:
            out.append(w)
    if segment and segment.get("label"):
        out.append(segment["label"])
    return out


# ── Claude 호출 ─────────────────────────────────────────

def _read_key() -> Optional[str]:
    """환경 변수 → 루트 .env 순서 (naver_api.read_keys와 같은 방식)."""
    try:
        from .naver_api import read_keys
        found = read_keys([KEY_NAME])
        return found[KEY_NAME] if found else None
    except Exception:  # noqa: BLE001 (.env 읽기 오류 → 환경 변수만)
        return os.environ.get(KEY_NAME) or None


def make_client():
    """키와 SDK가 있으면 클라이언트, 없으면 None (문장 틀로)."""
    key = _read_key()
    if not key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key, max_retries=1, timeout=30.0)
    except Exception:  # noqa: BLE001
        return None


def _system_prompt(media: str, n: int) -> str:
    if media == "naver":
        spec = (f"제목은 {NAVER_HEADLINE_MAX}자 이하, 설명은 {NAVER_TEXT_MIN}~{NAVER_TEXT_MAX}자. "
                "네이버 검색 결과에 보이는 광고라 검색한 사람의 질문에 답하는 말투로.")
    else:
        spec = (f"제목은 {META_HEADLINE_MAX}자 이하, 본문은 {META_TEXT_MAX}자 이하. "
                "인스타그램·페이스북에서 스치는 사람의 눈길을 끄는 짧은 말투로.")
    return ("너는 광고를 처음 하는 1인 가게 사장님을 돕는 카피라이터야. 쉬운 한국어로 쓴다.\n"
            f"{spec}\n"
            "사장님이 알려 준 장점만 쓰고, 사실이 아닌 말은 지어내지 마. "
            "'최저가·1위·최고·국내 유일·100%·무조건' 같은 근거 없는 표현, 이모지, 특수문자 남발은 금지.\n"
            f"서로 다른 문구 {n}개를 JSON 배열로만 답해: "
            '[{"headline": "...", "text": "..."}]. 다른 설명은 붙이지 마.')


def _parse(text: str) -> List[Copy]:
    """응답 글 → [{headline, text}] (앞뒤 군더더기·코드 블록 허용)."""
    m = re.search(r"\[.*\]", text or "", flags=re.S)
    try:
        data = json.loads(m.group(0)) if m else []
    except ValueError:
        return []
    out = []
    for d in data if isinstance(data, list) else []:
        if isinstance(d, dict) and isinstance(d.get("headline"), str) and isinstance(d.get("text"), str):
            out.append({"headline": tidy(d["headline"], 0), "text": tidy(d["text"])})
    return out


def _ask_claude(client, media: str, product: str, strengths: List[str], n: int,
                segment: Optional[dict] = None) -> List[Copy]:
    """Claude에게 문구를 받음. 어떤 실패든 빈 목록 (오류 문구에 키가 섞이지 않게 내용은 버림)."""
    try:
        payload: Dict[str, object] = {"상품": product, "장점": strengths, "개수": n}
        if segment and segment.get("label"):   # 낱말만: 손님 무리 이름과 시기. 네이버 숫자는 넣지 않는다
            payload["손님"] = segment["label"]
            if segment.get("peak_month"):
                payload["시기"] = f"{segment['peak_month']}월"
        resp = client.messages.create(
            model=MODEL, max_tokens=1024, system=_system_prompt(media, n),
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
        return _parse(text)
    except Exception as e:  # noqa: BLE001
        log.warning("claude degraded err=%s", type(e).__name__)   # 메시지는 요청 내용이 섞일 수 있어 남기지 않음
        return []


# ── 공개 함수 ─────────────────────────────────────────────

def _copies(media: str, product: str, strengths: Strengths, n: int, client) -> List[Copy]:
    return _copies_with_source(media, product, strengths, n, client)[0]


def _copies_with_source(media: str, product: str, strengths: Strengths, n: int, client,
                        segment: Optional[dict] = None):
    """→ (문구 목록, Claude가 쓴 문구가 하나라도 들어갔는지)."""
    n = max(int(n), 0)
    if n == 0:
        return [], False
    product = _clean_product(product)
    pieces = _strength_list(strengths)
    if client is None:
        client = make_client()
    elif client is False:
        client = None
    candidates: List[Copy] = _ask_claude(client, media, product, pieces, n, segment) if client else []
    templates = _naver_templates(product, pieces) if media == "naver" else _meta_templates(product, pieces)
    seg_tpl = _segment_template(product, pieces[0], segment) if media == "meta" else None
    if seg_tpl:
        templates.insert(0, seg_tpl)
    out: List[Copy] = []
    used_claude = False
    for i, c in enumerate(candidates + templates):
        key = (c["headline"], c["text"])
        if not check_copy(media, c) and key not in {(o["headline"], o["text"]) for o in out}:
            out.append(c)
            used_claude = used_claude or i < len(candidates)
        if len(out) >= n:
            break
    return out, used_claude


def meta_copies(product: str, strengths: Strengths, n: int = 3, client=None,
                segment: Optional[dict] = None) -> List[Copy]:
    """메타 문구 n개 [{headline, text}]. client: None이면 키로 자동, False면 항상 문장 틀 (테스트·미리보기)."""
    return _copies_with_source("meta", product, strengths, n, client, segment)[0]


def meta_copies_with_source(product: str, strengths: Strengths, n: int = 3, client=None,
                            segment: Optional[dict] = None):
    """meta_copies와 같고, Claude 문구가 쓰였는지도 돌려준다 (화면의 출처 표시용)."""
    return _copies_with_source("meta", product, strengths, n, client, segment)


def naver_copies(product: str, strengths: Strengths, n: int = 3, client=None) -> List[Copy]:
    """네이버 문구 n개 [{headline(≤15자), text(20~45자)}]."""
    return _copies("naver", product, strengths, n, client)

