"""챗봇 답 해석 (순수 파이썬, LLM 없음): 금액·선택·단어·주소·영문 이름.

사장님이 쓰는 말("2만 6천원", "네", "1번", "휘낭시에, 쿠키")을 값으로 바꾼다. 못 읽으면 None —
고치는 법을 말하는 건 대화 엔진(conversation.py)의 몫이다.
"""
import re
from typing import List, Optional, Sequence

# ── 금액 ──────────────────────────────────────────────────

_KDIG = {"영": 0, "공": 0, "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "륙": 6, "칠": 7, "팔": 8, "구": 9}
_SMALL = {"십": 10, "백": 100, "천": 1000}
_BIG = {"만": 10 ** 4, "억": 10 ** 8}
_FILLER = ("약", "대략", "정도", "쯤", "가량", "이상", "이하", "한", "월", "원", "₩", "krw", "won")
_MONEY_SEG = re.compile(r"\d[\d,]*(?:\.\d+)?(?:\s*[억만천백십]\s*(?:\d[\d,]*(?:\.\d+)?)?)*")


def _money_core(s: str) -> Optional[int]:
    """공백·쉼표·'원'을 뺀 글 하나를 읽는다. 숫자·한글 숫자·단위(십백천만억)만 허용."""
    total = 0.0
    section = 0.0
    num = None  # type: Optional[float]
    seen = False
    i = 0
    while i < len(s):
        c = s[i]
        if c.isascii() and (c.isdigit() or c == "."):
            j = i
            while j < len(s) and s[j].isascii() and (s[j].isdigit() or s[j] == "."):
                j += 1
            try:
                num = float(s[i:j])
            except ValueError:
                return None
            seen = True
            i = j
            continue
        if c in _KDIG:
            d = _KDIG[c]
            num = d if num is None else num * 10 + d
            seen = True
        elif c in _SMALL:
            section += (1 if num is None else num) * _SMALL[c]
            num = None
            seen = True
        elif c in _BIG:
            part = section + (num or 0)
            total += (part if part else 1) * _BIG[c]
            section = 0.0
            num = None
            seen = True
        else:
            return None
        i += 1
    if not seen:
        return None
    total += section + (num or 0)
    return int(round(total))


def parse_money(text: object) -> Optional[int]:
    """"2만 6천원"·"26,000"·"3만"·"30만원"·"1.5만"·"삼만" → 정수. 못 읽거나 음수면 None."""
    if text is None or isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        return int(text) if text >= 0 else None
    raw = str(text).strip().lower()
    if not raw or "%" in raw or "-" in raw[:1]:
        return None
    s = re.sub(r"[\s,]", "", raw)
    for w in sorted(_FILLER, key=len, reverse=True):
        s = s.replace(w, "")
    v = _money_core(s) if s else None
    if v is not None:
        return v
    m = _MONEY_SEG.search(raw)          # "한 달에 30만원 정도 쓸래요" 같은 문장 속 금액
    if m:
        return _money_core(re.sub(r"[\s,]", "", m.group(0)))
    return None


def parse_percent(text: object) -> Optional[float]:
    """"30%"·"30 퍼센트" → 30.0 (0 초과 100 이하만)."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(%|퍼센트|프로)", str(text or ""))
    if not m:
        return None
    v = float(m.group(1))
    return v if 0 < v <= 100 else None


# ── 예/아니요·선택 ────────────────────────────────────────

_YES = ("맞아요", "맞아", "맞습니다", "맞네요", "그래요", "좋아요", "좋아", "좋습니다", "좋네요", "그렇습니다", "그렇죠",
        "그렇게", "이대로", "확인", "오케이", "당연", "물론", "그럼요", "ㅇㅇ", "ㅇㅋ")
_YES_EXACT = ("네", "예", "넵", "넹", "응", "어", "그래", "ok", "yes", "y", "yep", "yeah")
_NO_ANY = ("아니", "아뇨", "아직", "틀렸", "틀려", "고칠", "수정", "싫", "안돼", "안되", "다시", "no")
_NO_TOKEN = ("없", "못", "안")          # 낱말 앞머리일 때만 (예: '문제없어요'는 부정이 아님)


def _norm(s: object) -> str:
    return re.sub(r"[\s.,!?~·()\[\]'\"]+", "", str(s or "")).lower()


def _tokens(text: object) -> List[str]:
    return [t for t in re.split(r"[\s.,!?~·()\[\]'\"“”‘’]+", str(text or "").lower()) if t]


def parse_yes_no(text: object) -> Optional[bool]:
    """True(긍정) / False(부정) / None(모르겠음). 부정어를 먼저 보고, 그다음 긍정어를 낱말 단위로 찾는다."""
    toks = _tokens(text)
    if not toks:
        return None
    whole = _norm(text)
    if re.search(r"(고칠|수정할?)\s*(건|게|거|것|곳|데|곳이)?\s*(없|안)", str(text).lower()):
        return True                                  # "고칠 거 없어요" = 맞다는 뜻
    if any(w in whole for w in _NO_ANY if w != "no") or whole in ("n", "no") or "no" in toks:
        return False
    if any(t.startswith(_NO_TOKEN) for t in toks):
        return False
    for t in toks:
        if t in _YES_EXACT or re.fullmatch(r"(네|예|응|넵|넹)+(요)?", t) or any(t.startswith(w) for w in _YES):
            return True
    return None


_ORDINAL = {"첫": 1, "첫째": 1, "첫번째": 1, "처음": 1, "두": 2, "둘째": 2, "두번째": 2, "세": 3, "셋째": 3, "세번째": 3}
_NEG_START = ("아니", "아직", "없", "안")


def _lead_number(s: str) -> Optional[int]:
    m = re.match(r"\d+", s)
    return int(m.group(0)) if m else None


def parse_choice(text: object, options: Sequence[str]) -> Optional[str]:
    """번호("2", "2번")·글자 그대로·부분 일치·예/아니요 → options 안의 글 하나. 못 고르면 None.

    부분 일치는 하나로 좁혀질 때만 (애매하면 None). 예/아니요는 '아니·없·아직'으로 시작하는 선택지가 하나 있을 때만.
    """
    opts = [str(o) for o in options]
    t = _norm(text)
    if not t or not opts:
        return None
    nopts = [_norm(o) for o in opts]
    m = re.fullmatch(r"(\d+)(번째|번)?", t)
    if m:
        n = int(m.group(1))
        if not m.group(2):                         # "14" → "14일" (번호보다 선택지 속 숫자가 먼저)
            hit = [o for o, no in zip(opts, nopts) if _lead_number(no) == n]
            if len(hit) == 1:
                return hit[0]
        return opts[n - 1] if 1 <= n <= len(opts) else None
    if t in _ORDINAL:
        k = _ORDINAL[t]
        return opts[k - 1] if k <= len(opts) else None
    for o, no in zip(opts, nopts):
        if t == no:
            return o
    inside = [o for o, no in zip(opts, nopts) if len(t) >= 2 and t in no]
    if len(inside) == 1:
        return inside[0]
    contains = [o for o, no in zip(opts, nopts) if len(no) >= 2 and no in t]
    if contains:
        contains.sort(key=lambda o: -len(_norm(o)))
        if len(contains) == 1 or len(_norm(contains[0])) > len(_norm(contains[1])):
            return contains[0]
        return None
    negs = [o for o, no in zip(opts, nopts) if no.startswith(_NEG_START)]
    if len(negs) == 1 and len(opts) == 2:
        yn = parse_yes_no(text)
        if yn is False:
            return negs[0]
        if yn is True:
            return next(o for o in opts if o != negs[0])
    return None


# ── 단어·주소 ─────────────────────────────────────────────

def parse_words(text: object, limit: int = 10) -> List[str]:
    """"휘낭시에, 쿠키" → ["휘낭시에", "쿠키"]. 쉼표·줄바꿈·슬래시로 나누고, 구분이 없으면 띄어쓰기로 나눔."""
    s = str(text or "").strip()
    if not s:
        return []
    parts = re.split(r"[,，、/\n;·]+", s)
    if len(parts) == 1:
        parts = s.split()
    out = []  # type: List[str]
    for p in parts:
        w = p.strip().strip("'\"“”‘’")
        if w and w not in out:
            out.append(w)
    return out[:limit]


_URL = re.compile(r"^(?:https?://)?(?:[a-z0-9가-힣-]+\.)+[a-z]{2,}(?::\d+)?(?:[/?#]\S*)?$", re.I)


def is_url(text: object) -> bool:
    s = str(text or "").strip()
    if not s or re.search(r"\s", s):
        return False
    return bool(_URL.match(s))


def normalize_url(text: object) -> str:
    s = str(text or "").strip()
    return s if re.match(r"https?://", s, re.I) else "https://" + s


# ── 영문 이름 (NT 꼬리표용) ────────────────────────────────

_WORDS = {"구움과자": "bakery", "휘낭시에": "financier", "마들렌": "madeleine", "마카롱": "macaron", "케이크": "cake",
          "쿠키": "cookie", "베이크": "bake", "베이커리": "bakery", "디저트": "dessert", "수제": "handmade",
          "공방": "studio", "스튜디오": "studio", "카페": "cafe", "스토어": "store", "마켓": "market", "샵": "shop",
          "빵": "bread", "과자": "snack", "선물": "gift", "하우스": "house", "네일": "nail", "꽃": "flower"}
_INIT = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"]
_VOW = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu",
        "eu", "ui", "i"]
_FIN = ["", "k", "kk", "k", "n", "n", "n", "t", "l", "k", "m", "p", "l", "l", "p", "l", "m", "p", "p", "t", "t",
        "ng", "t", "t", "k", "t", "p", "t"]


def _romanize(ch: str) -> str:
    code = ord(ch) - 0xAC00
    if not 0 <= code < 11172:
        return ""
    return _INIT[code // 588] + _VOW[(code % 588) // 28] + _FIN[code % 28]


def suggest_slug(product: object) -> str:
    """영문 소문자·숫자 후보 (예: "소연베이크" → "soyeonbake"). 만들 수 없으면 "item"."""
    s = str(product or "")
    keys = sorted(_WORDS, key=len, reverse=True)
    out = ""
    i = 0
    while i < len(s):
        hit = next((k for k in keys if s.startswith(k, i)), None)
        if hit:
            out += _WORDS[hit]
            i += len(hit)
            continue
        c = s[i]
        if c.isascii() and c.isalnum():
            out += c.lower()
        else:
            out += _romanize(c)
        i += 1
    return out[:24] or "item"


# ── 질문인지 (도움말 엔진이 없을 때 쓰는 가벼운 판별) ─────────────

_Q_START = ("어떻게", "어떤", "무슨", "뭐", "뭘", "왜", "언제", "어디", "누가", "얼마", "몇", "어느", "혹시", "이게", "그게")
_Q_END = ("나요", "가요", "까요", "뭐예요", "뭔가요", "인가요", "되나요", "할까요", "건가요", "있나요",
          "없나요", "어때요", "알려줘", "알려 줘", "알려주세요", "알려 주세요", "모르겠어요", "뭐야", "뭐죠", "인지요", "어떨까요")
_Q_START_RE = re.compile(r"^(?:%s)(?:\s|$)" % "|".join(_Q_START))
_Q_ANY_RE = re.compile(r"(어떻게|무슨\s|뭐예요|뭔가요|뭐죠|왜\s|얼마(?:\s|$|예요|에요|죠|나\s|인가요))")


def looks_like_question(text: object, strict: bool = False) -> bool:
    """물음표가 있거나, 물어보는 말투로 시작·끝나면 True. '2만 6천원'·'네'·'1' 같은 답은 False.

    strict=True는 가게 이름·상품명처럼 아무 글이나 올 수 있는 칸에서 쓴다: 물음표나 물어보는 끝말만 본다
    ('언제나베이커리'는 이름이지 질문이 아니다).
    """
    s = str(text or "").strip()
    if not s:
        return False
    if "?" in s or "？" in s:
        return True
    n = s.rstrip(".! ")
    if n.endswith(_Q_END):
        return not n.endswith(("좋아요",))
    if strict:
        return False
    return bool(_Q_START_RE.match(n) or _Q_ANY_RE.search(n))
