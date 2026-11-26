"""광고 문구 쓰기 (T07): 사장님이 알려 준 장점으로 메타·네이버 문구를 만든다.

- ANTHROPIC_API_KEY가 있으면 Claude(claude-sonnet-5-5)가 쓰고, 없거나 실패하면 문장 틀을 쓴다.
- 사장님이 고른 장점과 손님이 찾는 검색어는 따로 보낸다: 검색어는 손님 말투로만 쓰고 상품의 사실로 쓰지 않는다.
- 어느 쪽이든 같은 검사를 거친다: 글자 수(네이버 제목 15자·설명 20~45자), 근거 없는 말 금지, 특수문자 정리.
- 키 값은 출력·로그·예외 문구 어디에도 넣지 않는다.
"""
import json
import logging
import os
import re
from typing import Dict, List, Optional, Sequence, Union

log = logging.getLogger("coach.copy")
MODEL = os.environ.get("COACH_COPY_MODEL", "claude-sonnet-5-5")
MAX_TOKENS = 16000   # 생각(thinking)이 먼저 토큰을 쓰므로 넉넉히: 1024에서는 답이 중간에 잘려 문장 틀로 떨어졌다
KEY_NAME = "ANTHROPIC_API_KEY"

META_HEADLINE_MAX = 40
META_TEXT_MIN, META_TEXT_MAX = 10, 125

# 근거를 댈 수 없는 최상급·보장 표현 (광고 심의·신뢰 문제)
BANNED = ["최저가", "최저", "1위", "1등", "최고", "최상", "최초", "국내 유일", "세계 유일", "유일", "넘버원",
          "no.1", "no 1", "100%", "무조건", "보장", "완치", "특효"]
GENERIC_STRENGTH = "정성껏 만들었어요"
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


def check_copy(copy: Copy) -> List[str]:
    """메타 문구 하나의 문제 목록 (비어 있으면 통과)."""
    h, t = copy.get("headline", ""), copy.get("text", "")
    lim = (META_HEADLINE_MAX, META_TEXT_MIN, META_TEXT_MAX)
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


def _used(word: str, flat: str) -> bool:
    """낱말이 문구에 들어갔나 (띄어쓰기 무시). 3글자 이상이면 끝 글자가 바뀐 꼴도 본다 (가벼움 → 가벼운, 따뜻함 → 따뜻한)."""
    w = re.sub(r"\s+", "", word)
    return bool(w) and (w in flat or (len(w) >= 3 and w[:-1] in flat))


def _partly(word: str, flat: str) -> bool:
    """두 글자 조각 하나라도 문구에 있나 (Claude가 쓴다고 한 낱말을 풀어 쓴 경우: 개별포장 → '하나씩 따로 포장')."""
    w = re.sub(r"\s+", "", word)
    return any(w[i:i + 2] in flat for i in range(len(w) - 1))


def basis(copy: Copy, words: Sequence[str], segment: Optional[dict]) -> List[str]:
    """문구에 쓴 낱말(중복 없음) + 고른 손님 무리 이름.
    Claude가 basis를 주면 그중 받은 낱말이고 문구에도 보이는 것만 믿고, 그다음 글자로 맞춰 본 낱말을 더한다."""
    flat = re.sub(r"\s+", "", copy.get("headline", "") + copy.get("text", ""))
    given = [(w or "").strip() for w in words]
    claimed = {b.strip() for b in copy.get("basis", []) or []}   # type: ignore[union-attr]
    out: List[str] = []
    for w in given:   # 받은 순서대로
        if w and w not in out and (_used(w, flat) or (w in claimed and _partly(w, flat))):
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
    """키와 SDK가 있으면 클라이언트, 없거나 COACH_NO_LLM=1이면 None (문장 틀·정해진 설명으로)."""
    if os.environ.get("COACH_NO_LLM") == "1":
        return None
    key = _read_key()
    if not key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key, max_retries=1, timeout=60.0)
    except Exception:  # noqa: BLE001
        return None


def reply_text(resp) -> str:
    """Claude 답에서 글(text) 부분만."""
    return next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")


def _system_prompt(n: int) -> str:
    spec = (f"제목(headline)은 {META_HEADLINE_MAX}자 이하, 본문(text)은 60~{META_TEXT_MAX}자. "
            "인스타그램·페이스북 피드에서 스크롤하다 멈추게 하는 광고다. 본문은 "
            "① 손님이 공감할 상황이나 질문 한 문장 → ② 이 상품의 장점을 구체적으로 → ③ 부담 없는 행동 권유(예: 프로필 링크에서 보기) 순서로 쓴다. "
            "제목은 본문을 반복하지 말고 장점 하나를 짧고 또렷하게.")
    return ("너는 광고를 처음 하는 1인 가게 사장님을 돕는 한국어 광고 카피라이터야. 쉬운 말, 존댓말(해요체)로 쓴다.\n"
            f"{spec}\n"
            "'장점'은 사장님이 직접 고르거나 적은 사실이다. 문구의 내용은 이 장점에서만 가져온다.\n"
            "'검색어'는 손님이 네이버에서 찾는 말이다. 손님 말투를 맞추는 데만 쓰고, 상품의 사실로 쓰지 않는다 "
            "(예: 검색어에 '대여'·'할인'·'리퍼'가 있어도 장점에 없으면 '대여 가능'·'할인 중'이라고 쓰지 않는다). "
            "검색어는 자연스러울 때만 한두 개 넣고, 붙여 쓴 말은 띄어 쓴다(가성비노트북 → 가성비 노트북).\n"
            "'손님'·'시기'가 있으면 그 손님의 상황에 맞춘다. '말투'가 있으면 그 말투로 쓴다.\n"
            "가게·브랜드 이름, 가격, 숫자, 후기, 수상처럼 주어지지 않은 사실은 지어내지 마. "
            "'최저가·1위·최고·국내 유일·100%·무조건' 같은 근거 없는 표현, 이모지, 해시태그, 특수문자 남발은 금지.\n"
            f"서로 다른 각도의 문구 {n}개를 쓴다 (예: 상황 공감 / 장점 강조 / 선물·시기).\n"
            "각 문구의 basis에는 그 문구에 실제로 쓴 '장점'·'검색어'를 받은 그대로(글자 그대로) 적는다. "
            "말을 바꿔 썼어도(가벼움 → 가벼운) 받은 낱말로 적는다.")


COPY_SCHEMA = {
    "type": "object",
    "properties": {"copies": {"type": "array", "items": {
        "type": "object",
        "properties": {"headline": {"type": "string"}, "text": {"type": "string"},
                       "basis": {"type": "array", "items": {"type": "string"}}},
        "required": ["headline", "text", "basis"], "additionalProperties": False}}},
    "required": ["copies"], "additionalProperties": False,
}


def _parse(text: str) -> List[Copy]:
    """응답 글 → [{headline, text}] (앞뒤 군더더기·코드 블록 허용)."""
    try:
        data = json.loads(text or "")
        data = data.get("copies", []) if isinstance(data, dict) else data
    except ValueError:
        m = re.search(r"\[.*\]", text or "", flags=re.S)
        try:
            data = json.loads(m.group(0)) if m else []
        except ValueError:
            return []
    out = []
    for d in data if isinstance(data, list) else []:
        if isinstance(d, dict) and isinstance(d.get("headline"), str) and isinstance(d.get("text"), str):
            c = {"headline": tidy(d["headline"], 0), "text": tidy(d["text"])}
            if isinstance(d.get("basis"), list):
                c["basis"] = [str(b) for b in d["basis"] if isinstance(b, str)]
            out.append(c)
    return out


TONES = {"친근하게": "동네 단골에게 말하듯 친근하고 다정하게", "깔끔하게": "군더더기 없이 짧고 또렷하게",
         "감성적으로": "장면이 떠오르게 감성적이고 따뜻하게"}


def _ask_claude(client, product: str, strengths: List[str], n: int,
                segment: Optional[dict] = None, keywords: Optional[List[str]] = None, tone: Optional[str] = None) -> List[Copy]:
    """Claude에게 문구를 받음. 어떤 실패든 빈 목록 (오류 문구에 키가 섞이지 않게 내용은 버림)."""
    try:
        payload: Dict[str, object] = {"상품": product, "장점": strengths, "개수": n}
        if keywords:
            payload["검색어"] = keywords
        if tone in TONES:   # 사장님이 고른 말투
            payload["말투"] = TONES[tone]
        if segment and segment.get("label"):   # 낱말만: 손님 무리 이름과 시기. 네이버 숫자는 넣지 않는다
            payload["손님"] = segment["label"]
            if segment.get("peak_month"):
                payload["시기"] = f"{segment['peak_month']}월"
        resp = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, system=_system_prompt(n),
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": COPY_SCHEMA}},
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}])
        out = _parse(reply_text(resp))
        if not out:
            log.warning("claude degraded err=empty stop=%s", getattr(resp, "stop_reason", None))
        return out
    except Exception as e:  # noqa: BLE001
        log.warning("claude degraded err=%s", type(e).__name__)   # 메시지는 요청 내용이 섞일 수 있어 남기지 않음
        return []


# ── 공개 함수 ─────────────────────────────────────────────

def _copies_with_source(product: str, strengths: Strengths, n: int, client,
                        segment: Optional[dict] = None, keywords: Optional[Sequence[str]] = None, tone: Optional[str] = None):
    """→ (문구 목록, Claude가 쓴 문구가 하나라도 들어갔는지)."""
    n = max(int(n), 0)
    if n == 0:
        return [], False
    product = _clean_product(product)
    raw = [strengths] if isinstance(strengths, str) else list(strengths or [])
    own = _strength_list(raw) if any(str(r or "").strip() for r in raw) else []   # Claude에게: 사장님 장점만
    kws = [k for k in dict.fromkeys(tidy(k, 0) for k in keywords or []) if k and not has_banned(k)]
    pieces = _strength_list(raw + kws)                          # 문장 틀: 예전처럼 장점+검색어 (비면 기본 한 마디)
    if client is None:
        client = make_client()
    elif client is False:
        client = None
    candidates: List[Copy] = _ask_claude(client, product, own, n, segment, kws, tone) if client else []
    templates = _meta_templates(product, pieces)
    seg_tpl = _segment_template(product, pieces[0], segment)
    if seg_tpl:
        templates.insert(0, seg_tpl)
    out: List[Copy] = []
    used_claude = False
    for i, c in enumerate(candidates + templates):
        key = (c["headline"], c["text"])
        if not check_copy(c) and key not in {(o["headline"], o["text"]) for o in out}:
            out.append(c)
            used_claude = used_claude or i < len(candidates)
        if len(out) >= n:
            break
    return out, used_claude


def meta_copies(product: str, strengths: Strengths, n: int = 3, client=None,
                segment: Optional[dict] = None) -> List[Copy]:
    """메타 문구 n개 [{headline, text}]. client: None이면 키로 자동, False면 항상 문장 틀 (테스트·미리보기)."""
    return _copies_with_source(product, strengths, n, client, segment)[0]


def meta_copies_with_source(product: str, strengths: Strengths, n: int = 3, client=None,
                            segment: Optional[dict] = None, keywords: Optional[Sequence[str]] = None,
                            tone: Optional[str] = None):
    """meta_copies와 같고, Claude 문구가 쓰였는지도 돌려준다 (화면의 출처 표시용).
    keywords: 손님 검색어 (Claude에게는 장점과 따로 보냄). tone: 친근하게 | 깔끔하게 | 감성적으로."""
    return _copies_with_source(product, strengths, n, client, segment, keywords, tone)
