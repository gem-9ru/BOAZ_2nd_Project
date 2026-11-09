"""세팅 챗봇 (MVP 7번): 광고 관리자 첫 세팅 질문 → 세팅 카드(data/rag/*.md) 찾기 → 카드와 코치 숫자만 근거로 답하기.

- 카드: `## [id] 제목` 단위. 매체·단계·질문 예시·화면 단서·확인(✅/△/❓)·출처·코치 연결·본문 (data/rag/README.md)
- 찾기: 직접 구현한 BM25 (새 패키지 없음). 한국어는 공백 토큰 + 글자 2-gram. 제목·질문 예시·화면 단서에 가중치
- 점수가 기준(MIN_SCORE) 미만이면 "자료에 없어요" (LLM을 부르지 않음)
- 답하기(키 있을 때): chat_intake와 같은 모델·키 읽기·오류 처리. 고른 카드와 코치 숫자만 근거로 3~6문장, 쓴 카드 id를 돌려받음
- 화면 캡처: 선택, png/jpg 5MB 이하, 이미지로 함께 보내고 저장하지 않음
- 키 없을 때: 고른 카드 상위 3장을 요약해 보여 줌
"""
import base64
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import chat_intake as CI
from . import defaults as D

ROOT = Path(__file__).resolve().parents[2]
RAG_DIR = ROOT / "data" / "rag"
CARD_FILES = ("naver_searchad.md", "meta_ads.md")
TOP_K = 4
MIN_SCORE = 4.0            # 이보다 낮으면 '자료에 없어요' (시험 문항 tests/fixtures/setup_questions.json으로 정함)
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
FIELD_WEIGHTS = {"title": 3, "questions": 2, "screen": 2, "body": 1, "coach": 1, "stage": 1, "media": 1}
CHECK_MARKS = ("✅", "△", "❓", "🧮")
CHECK_WORDS = {"✅": "공식 확인", "△": "다른 자료 기준", "❓": "공식 확인 못 함", "🧮": "앱 계산"}

_CARD_HEAD = re.compile(r"^## \[([\w-]+)\]\s*(.+?)\s*$")


@dataclass
class Card:
    id: str
    title: str
    media: str = ""
    stage: str = ""
    questions: str = ""
    screen: str = ""
    check: str = ""            # ✅ / △ / ❓ (🧮)
    check_text: str = ""
    sources: List[str] = field(default_factory=list)
    coach: str = ""
    body: str = ""
    file: str = ""


def _field(line: str, name: str) -> Optional[str]:
    prefix = f"- {name}:"
    return line[len(prefix):].strip() if line.startswith(prefix) else None


def parse_cards(text: str, file: str = "") -> List[Card]:
    """`## [id] 제목`부터 다음 카드 전까지. 파일 머리말(첫 카드 앞)은 카드가 아님."""
    cards, cur, body = [], None, []

    def close():
        if cur is not None:
            cur.body = " ".join(x.strip() for x in body if x.strip() and x.strip() != "---").strip()
            cards.append(cur)

    for raw in text.splitlines():
        m = _CARD_HEAD.match(raw)
        if m:
            close()
            cur, body = Card(id=m.group(1), title=m.group(2), file=file), []
            continue
        if cur is None:
            continue
        line = raw.strip()
        if (v := _field(line, "매체")) is not None:
            parts = [p.strip() for p in v.split("|")]
            cur.media = parts[0]
            for p in parts[1:]:
                if p.startswith("단계:"):
                    cur.stage = p[len("단계:"):].strip()
        elif (v := _field(line, "질문 예시")) is not None:
            cur.questions = v
        elif (v := _field(line, "화면 단서")) is not None:
            cur.screen = v
        elif (v := _field(line, "확인")) is not None:
            cur.check_text = v
            cur.check = next((mk for mk in CHECK_MARKS if mk in v), "")
        elif (v := _field(line, "출처")) is not None:
            cur.sources = [s.strip() for s in v.split(" ; ") if s.strip()]
        elif (v := _field(line, "코치 연결")) is not None:
            cur.coach = v
        elif line.startswith("본문:"):
            body.append(line[len("본문:"):])
        elif body:
            body.append(line)
    close()
    return cards


_CACHE: Dict[str, List[Card]] = {}


def _cards_key(rag_dir: Path) -> str:
    """카드 파일 수정 시각까지 캐시 키에 (카드만 고쳐 올려도 배포 앱이 새 카드를 읽게, 검수 A8)."""
    stamps = [str((rag_dir / f).stat().st_mtime) for f in CARD_FILES if (rag_dir / f).exists()]
    return str(rag_dir) + "|" + "|".join(stamps)


def load_cards(rag_dir: Path = RAG_DIR) -> List[Card]:
    key = _cards_key(rag_dir)
    if key not in _CACHE:
        cards = []
        for f in CARD_FILES:
            path = rag_dir / f
            if path.exists():
                cards += parse_cards(path.read_text(encoding="utf-8"), f)
        _CACHE[key] = cards
    return _CACHE[key]


# ── 찾기 (BM25) ─────────────────────────────────────────────────
_WORD = re.compile(r"[0-9A-Za-z가-힣]+")
# 말끝·조사 (긴 것부터 뗌). 떼고 남은 말이 2글자 이상일 때만 (예: "나가게"→"나가", "사람한테"→"사람", "넣어?"는 그대로)
_ENDINGS = sorted("""하려면 하는데 해야돼 해야 할까 할래 해줘 써줘 하고 싶어 고싶어 한테 에게 에서 으로 까지 부터 이랑 하면 려면
    는데 은데 인데 이야 이에요 예요 해요 나요 되나요 될까 돼요 했어 됐어 하게 나게 되게 은 는 이 가 을 를 에 도 만 로 와 과 랑 야 요 해 돼 줘 게""".split(),
                  key=len, reverse=True)
# 질문 쪽에서만 버리는 말 (어느 카드에나 맞아 순위를 흐림)
STOPWORDS = {"어떻게", "어디", "어디서", "어디에", "뭐", "뭘", "뭐로", "뭐야", "수", "있어", "있나", "하는", "할", "해",
             "돼", "좀", "잘", "꼭", "많은", "많이", "어때", "괜찮아", "메뉴", "좋아", "그냥", "나", "내", "우리", "광고", "광고를", "광고가", "사람", "사람한테", "싶어", "하고", "하려면", "써도", "되나"}


# 같은 뜻 다른 말 (광고 관리자 화면 말 ↔ 사장님 말). 질문에 앞말이 있으면 뒷말도 찾음
SYNONYMS = {"사진": "이미지", "이미지": "사진", "영상": "동영상", "타깃": "타겟", "타겟": "타깃",
            "문구": "소재", "카피": "소재", "제외어": "제외", "모바일": "기기", "pc": "기기"}


def _stem(w: str) -> str:
    for e in _ENDINGS:
        if w.endswith(e) and len(w) - len(e) >= 2:
            return w[: -len(e)]
    return w


def tokenize(text: str, query: bool = False) -> List[str]:
    """단어(말끝·조사를 뗀 것) + 한글·영문 2글자 조각. query=True면 흔한 말(STOPWORDS)은 뺌."""
    out = []
    for w in _WORD.findall((text or "").lower()):
        if query and w in STOPWORDS:
            continue
        s = _stem(w)
        if query and s in STOPWORDS:
            continue
        out.append(s)
        if len(s) > 2:
            out += [s[i:i + 2] for i in range(len(s) - 1)]
        if query and s in SYNONYMS:
            out.append(SYNONYMS[s])         # 같은 뜻 말은 통째로만 (조각까지 더하면 점수가 부풀음)
    return out


# 매체: 고른 매체 카드에서만 찾되, 질문에 다른 매체 이름이 있으면 그 매체로 (계획 가정 2)
MEDIA = {"naver": "네이버", "meta": "메타"}
MEDIA_WORDS = {"naver": ("네이버", "파워링크", "쇼핑검색", "비즈머니", "검색광고", "키워드도구"),
               "meta": ("메타", "인스타", "페이스북", "페북", "릴스", "스토리", "픽셀", "어드밴티지")}
MEDIA_NAMES = {"naver": ("네이버", "검색광고"), "meta": ("메타", "인스타그램", "인스타", "페이스북", "페북")}   # 찾을 때 빼는 매체 이름만
# 카드보다 코치 배분 숫자로 답할 질문 ("뭐부터 해?", "30만 원 어떻게 나눠?")
_COACH = re.compile(r"뭐부터|어디부터|먼저\s*(해|할|시작)|어떻게\s*나눠|나눠야|나누면|얼마씩|반반|(네이버|메타).*(랑|하고|vs|중).*(네이버|메타).*(중|뭐|어디|먼저|더)")


def media_in(query: str) -> Optional[str]:
    """질문에 한 매체 이름만 있으면 그 매체 ('naver'/'meta'), 없거나 둘 다면 None."""
    q = (query or "").replace(" ", "").lower()
    hits = [m for m, words in MEDIA_WORDS.items() if any(w in q for w in words)]
    return hits[0] if len(hits) == 1 else None


def is_coach_question(query: str) -> bool:
    return bool(_COACH.search(query or ""))


def query_weights(query: str) -> Dict[str, float]:
    """질문 토큰 → 무게. 단어는 1, 단어에서 나온 2글자 조각은 합쳐서 1 (긴 단어 하나가 점수를 독차지하지 않게)."""
    w: Dict[str, float] = {}
    for word in _WORD.findall((query or "").lower()):
        toks = tokenize(word, query=True)
        if not toks:
            continue
        head, rest = toks[0], toks[1:]
        grams = [x for x in rest if x not in SYNONYMS.values() or len(x) <= 2]
        extra = [x for x in rest if x not in grams]
        for x in [head] + extra:
            w[x] = w.get(x, 0) + 1.0
        for x in grams:
            w[x] = w.get(x, 0) + 1.0 / len(grams)
    return w


class Index:
    def __init__(self, cards: List[Card], k1: float = 1.5, b: float = 0.75):
        self.cards, self.k1, self.b = cards, k1, b
        self.tf: List[Counter] = []
        for c in cards:
            tf = Counter()
            for name, w in FIELD_WEIGHTS.items():
                for tok in tokenize(getattr(c, name)):
                    tf[tok] += w
            self.tf.append(tf)
        self.len = [sum(tf.values()) for tf in self.tf]
        self.avg = sum(self.len) / max(len(self.len), 1)
        df = Counter(t for tf in self.tf for t in tf)
        n = len(cards)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(self, query: str, top: int = TOP_K, media: Optional[str] = None) -> List[Tuple[Card, float]]:
        q = query_weights(query)
        scored = []
        for c, tf, dl in zip(self.cards, self.tf, self.len):
            if media and media not in c.media:
                continue
            s = 0.0
            for t, qn in q.items():
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg)) * min(qn, 2.0)
            if s > 0:
                scored.append((c, s))
        scored.sort(key=lambda x: -x[1])
        return scored[:top]


_INDEX: Dict[str, Index] = {}


def index(rag_dir: Path = RAG_DIR) -> Index:
    key = _cards_key(rag_dir)
    if key not in _INDEX:
        _INDEX[key] = Index(load_cards(rag_dir))
    return _INDEX[key]


def find(query: str, top: int = TOP_K, media: Optional[str] = None) -> List[Tuple[Card, float]]:
    """기준 이상인 카드만 (없으면 빈 목록 = '자료에 없어요'). media: 고른 매체('naver'/'meta'), 질문에 다른 매체 이름이 있으면 그쪽."""
    m = media_in(query) or media
    q = query
    if m:   # 매체로 거른 뒤엔 매체 이름(인스타·네이버…)이 모든 카드에 맞아 순위만 흐림 → 빼고 찾음
        for w in MEDIA_NAMES[m]:
            q = re.sub(w + r"[가-힣]{0,2}", " ", q, flags=re.I)
    return [(c, s) for c, s in index().search(q, top, MEDIA.get(m)) if s >= MIN_SCORE]


# ── 매체 고르기 (7d 1단계) ──────────────────────────────────────
MEDIA_CHOICES = {"both": "둘 다 (네이버 먼저)", "naver": "네이버만", "meta": "메타만"}
CHIPS = {"naver": ["하루 예산 어디에 넣어?", "처음 입찰가 얼마로 해?", "파워링크랑 쇼핑검색 중 뭐 해?", "구매가 보고서에 잡히게 하려면?"],
         "meta": ["목표 뭐 골라?", "하루 예산 얼마 넣어?", "머신 러닝 단계가 뭐야?", "픽셀 꼭 달아야 해?"]}


def default_media(naver_spend: float, meta_spend: float) -> str:
    """코치 배분으로 미리 고를 매체 (계획 가정 1): 메타 0원 → 네이버만, 네이버 0원 → 메타만, 둘 다 있으면 둘 다(네이버 먼저)."""
    if meta_spend <= 0 < naver_spend:
        return "naver"
    if naver_spend <= 0 < meta_spend:
        return "meta"
    return "both"


def coach_answer(split, kw: str, no_ad: bool = False) -> str:
    """'뭐부터 해? / 어떻게 나눠?' → 카드 대신 코치 배분 숫자로 답 (마크다운). split: coach.Split."""
    from .coach import split_reason
    from .guide import daily_budget
    from .insights import won
    first = "네이버" if split.naver_spend > 0 else "메타"
    lines = [f"코치가 나눈 시험 예산 {won(split.total)}: **네이버 {won(split.naver_spend)} · 메타 {won(split.meta.spend)}** "
             f"(하루 약 {won(daily_budget(split.naver_spend))} · {won(daily_budget(split.meta.spend))}).",
             split_reason(split, kw),
             "세팅은 **네이버 먼저** 하세요. 네이버는 비즈머니 충전과 검토(보통 영업일 1~2일)가 있어서, "
             "먼저 올려 두면 메타를 세팅하는 동안 검토가 끝나요 (naver-setup-015)."
             if split.naver_spend > 0 and split.meta.spend > 0 else f"이번 배분은 **{first}만** 써요."]
    if no_ad:
        lines.insert(0, "지금은 **광고 안 함**을 추천해요. 시작한다면 아래처럼 나눠요.")
    return "  \n".join(lines)


def find_in(query: str, card_ids: List[str], media: Optional[str] = None) -> List[Tuple[Card, float]]:
    """'여기서 막혔어요': 그 단계 카드에서 먼저 찾고, 기준을 넘는 게 없으면 매체 전체에서."""
    ids = set(card_ids)
    first = [(c, s) for c, s in index().search(query, len(index().cards), MEDIA.get(media_in(query) or media))
             if c.id in ids and s >= MIN_SCORE]
    return first[:TOP_K] if first else find(query, media=media)


# ── 광고 문구 초안 (키 있을 때 AI 3개, 7d 3단계) ──────────────────────
COPY_SYSTEM = """너는 광고를 처음 하는 사장님의 광고 문구 초안을 쓰는 도우미야.
사장님이 준 상품명·강점·혜택만 써. 없는 사실(수상·순위·후기 수·가격·할인)은 지어내지 마.
'최고·최초·1위·유일·100%·완벽·보장' 같은 최상급·순위·보장 표현은 쓰지 마. 특수문자를 반복하지 마.
네이버 제목은 15자 이하, 설명은 20~45자(띄어쓰기 포함), 메타 제목은 27자 이하, 메타 기본 문구는 50~150자.
서로 다른 느낌으로 초안 3개를 만들어."""
COPY_SCHEMA = {
    "type": "object",
    "properties": {"drafts": {"type": "array", "items": {
        "type": "object",
        "properties": {k: {"type": "string"} for k in ("naver_title", "naver_desc", "meta_text", "meta_headline")},
        "required": ["naver_title", "naver_desc", "meta_text", "meta_headline"], "additionalProperties": False}}},
    "required": ["drafts"], "additionalProperties": False,
}


def draft_copy(client, product: str, strength: str = "", benefit: str = "") -> List[Dict[str, str]]:
    """키가 있으면 초안 3개 (실패하면 CI.IntakeUnavailable → 화면은 틀 채우기로)."""
    msg = CI.scrub(f"상품명: {product}\n강점: {strength or '(없음)'}\n혜택: {benefit or '(없음)'}")
    out = CI.call_json(client, COPY_SYSTEM, [{"role": "user", "content": msg}], COPY_SCHEMA, max_tokens=1_200)
    drafts = [{k: str(d.get(k, "")).strip()[:200] for k in ("naver_title", "naver_desc", "meta_text", "meta_headline")}
              for d in (out.get("drafts") or []) if isinstance(d, dict)]
    if not drafts:
        raise CI.IntakeUnavailable("빈 초안")
    return drafts[:3]


def route(query: str, media: Optional[str] = None) -> Tuple[str, List[Tuple[Card, float]]]:
    """질문 → ("coach", []) 코치 배분 숫자로 답 / ("cards", 찾은 카드) / ("none", []) 자료에 없어요."""
    if is_coach_question(query):
        return "coach", []
    found = find(query, media=media)
    return ("cards", found) if found else ("none", [])


# ── 답하기 ──────────────────────────────────────────────────────
SYSTEM = """너는 광고를 처음 하는 사장님이 네이버 검색광고·메타 광고 관리자를 처음 세팅할 때 돕는 도우미야.
아래에 주는 '세팅 카드'와 '코치 숫자'만 근거로 답해. 카드에 없는 내용은 지어내지 말고 "자료에 없어요"라고 해.
- 지금 화면에서 누를 메뉴(화면 단서 글자 그대로)와 넣을 값(코치 숫자)을 3~6문장으로, 쉬운 말로.
- 확인 표시가 ❓인 카드의 내용은 "공식 확인 못 함"이라고 밝히고 단정하지 마. △이면 "공식 문서가 아니라 다른 자료 기준"이라고.
- 사장님이 화면 캡처를 올리면, 캡처에 보이는 메뉴·버튼 글자를 카드의 화면 단서와 맞춰 보고 어디를 누를지 알려 줘.
- 광고를 대신 집행하거나 계정에 접속하지 않는다. 개인정보는 묻지 마.
card_ids에는 실제로 근거로 쓴 카드 id만 넣어."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}, "card_ids": {"type": "array", "items": {"type": "string"}}},
    "required": ["answer", "card_ids"],
    "additionalProperties": False,
}


def md_safe(text) -> str:
    """화면(마크다운)에 그릴 글: '1~2일 … 1~2주'처럼 물결표가 둘이면 취소선이 되므로 '~'를 '\\~'로 (카드 원문은 그대로, D2)."""
    return re.sub(r"(?<!\\)~", r"\\~", str(text or ""))


def card_text(c: Card) -> str:
    return (f"[{c.id}] {c.title}\n매체: {c.media} | 단계: {c.stage}\n화면 단서: {c.screen}\n"
            f"확인: {c.check} {CHECK_WORDS.get(c.check, '')}\n코치 연결: {c.coach}\n본문: {c.body}")


def coach_text(ctx: Dict) -> str:
    """코치 숫자 (네이버·메타 배분, 하루 예산 = 월 ÷ 30.4, 검색어, 판매가, 100번 중 ○번). 개인정보 없음."""
    if not ctx:
        return "코치 숫자: 아직 없음"
    from .guide import daily_budget
    rows = []
    for key, label in (("naver", "네이버 월 예산"), ("meta", "메타 월 예산")):
        if ctx.get(key) is not None:
            rows.append(f"{label} {ctx[key]:,.0f}원 (하루 {daily_budget(ctx[key]):,.0f}원)")
    if ctx.get("keyword"):
        rows.append(f"검색어 '{ctx['keyword']}'")
    if ctx.get("price"):
        rows.append(f"판매가 {ctx['price']:,.0f}원")
    if ctx.get("wins") is not None:
        rows.append(f"100번 해 보면 1년 동안 {ctx['wins']}번 남음")
    if ctx.get("stores"):
        rows.append("판매처 " + ", ".join(ctx["stores"]))
    text = "코치 숫자: " + " · ".join(rows)
    if ctx.get("settings"):
        text += "\n지금 세팅 중인 광고 세팅값 (ad_setup):\n" + "\n".join("- " + s for s in ctx["settings"])
    return text


def check_image(data: bytes, name: str) -> str:
    """캡처 검사 → media type. 크기·형식이 맞지 않으면 ValueError (보내지 않음)."""
    ext = (name or "").rsplit(".", 1)[-1].lower()
    if ext not in IMAGE_TYPES:
        raise ValueError("png나 jpg 캡처만 올릴 수 있어요")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("캡처가 5MB보다 커요. 필요한 부분만 잘라서 올려 주세요")
    return IMAGE_TYPES[ext]


HISTORY_TURNS = 6          # 키가 있을 때 앞 대화 6턴(질문·답 12개)까지 기억 (계획 결정 11/9)


def trim_history(history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    """앞 대화 → 최근 6턴, 질문은 개인정보를 지우고, 사용자 → 도우미 순서로 맞춤."""
    msgs = [{"role": m["role"], "content": CI.scrub(m["content"]) if m["role"] == "user" else str(m["content"])[:1_500]}
            for m in (history or []) if m.get("role") in ("user", "assistant") and m.get("content")]
    msgs = msgs[-HISTORY_TURNS * 2:]
    while msgs and msgs[0]["role"] != "user":
        msgs = msgs[1:]
    return msgs


def answer(client, question: str, found: List[Tuple[Card, float]], ctx: Dict,
           image: Optional[Tuple[bytes, str]] = None, history: Optional[List[Dict[str, str]]] = None) -> Dict:
    """→ {"answer": 글, "cards": [Card...]}. 카드가 없으면 LLM을 부르지 않는다. 실패하면 CI.IntakeUnavailable.
    history: 앞 대화 [{"role", "content"}] (최근 6턴만 보냄)."""
    if not found:
        return {"answer": "자료에 없어요. 네이버 검색광고·메타 광고 관리자 세팅에 관한 질문으로 다시 물어봐 주세요.", "cards": []}
    content: List[Dict] = []
    if image is not None:
        data, name = image
        media_type = check_image(data, name)
        content.append({"type": "image", "source": {"type": "base64", "media_type": media_type,
                                                    "data": base64.standard_b64encode(data).decode("ascii")}})
    cards = [c for c, _ in found]
    content.append({"type": "text", "text": "세팅 카드:\n\n" + "\n\n".join(card_text(c) for c in cards)
                    + "\n\n" + coach_text(ctx) + "\n\n사장님 질문: " + CI.scrub(question)})
    out = CI.call_json(client, SYSTEM, trim_history(history) + [{"role": "user", "content": content}], ANSWER_SCHEMA,
                       max_tokens=1_500)
    by_id = {c.id: c for c in cards}
    used = [by_id[i] for i in out.get("card_ids", []) if isinstance(i, str) and i in by_id]
    text = str(out.get("answer") or "").strip()[:1_500]
    if not text:
        raise CI.IntakeUnavailable("빈 답")
    return {"answer": text, "cards": used or cards[:1]}


def summaries(found: List[Tuple[Card, float]], n: int = 3, chars: int = 160) -> List[Dict]:
    """키가 없을 때 보여 줄 카드 요약 (제목·본문 앞부분·출처·확인 표시)."""
    out = []
    for c, _ in found[:n]:
        body = c.body if len(c.body) <= chars else c.body[:chars].rsplit(" ", 1)[0] + "…"
        out.append({"id": c.id, "title": c.title, "body": body, "check": c.check,
                    "check_word": CHECK_WORDS.get(c.check, ""), "sources": c.sources, "screen": c.screen})
    return out


def by_id(card_id: str) -> Optional[Card]:
    return next((c for c in load_cards() if c.id == card_id), None)


def my_numbers(card: Card, nums: Dict) -> List[str]:
    """카드 '코치 연결'에 맞는 내 숫자 한 줄들 (키가 없을 때 카드 위에). 숫자는 앱이 이미 계산한 값(nums)만 쓴다.
    nums: naver, naver_daily, meta, meta_daily, meta_rec_daily, bid, shopping_min, smartstore, keyword, cpa, be_first, meta_objective."""
    link, naver = card.coach, "네이버" in card.media
    lines: List[str] = []

    def won(v) -> str:
        return f"{v:,.0f}원"

    if naver:
        if "하루 예산" in link and nums.get("naver"):
            lines.append(f"네이버 하루 예산 약 {won(nums['naver_daily'])} (월 {won(nums['naver'])} ÷ 30.4)")
        elif ("네이버 월 배분" in link or "네이버 배분" in link) and "입찰가" not in link and nums.get("naver"):
            lines.append(f"네이버 월 배분 {won(nums['naver'])}")
        if "입찰가" in link and nums.get("naver"):
            if nums.get("smartstore"):
                lines.append(f"쇼핑검색 기본 입찰가는 최소 {won(nums['shopping_min'])}부터"
                             + (f" (참고: '{nums['keyword']}' 키워드 예상 실적 입찰가 약 {won(nums['bid'])})" if nums.get("bid") else ""))
            elif nums.get("bid"):
                lines.append(f"기본 입찰가 약 {won(nums['bid'])} ('{nums['keyword']}' 예상 실적)")
        if ("검색어" in link or "키워드" in link) and nums.get("keyword"):
            lines.append(f"검색어 '{nums['keyword']}'")
    else:
        if "하루 예산" in link and nums.get("meta"):
            lines.append(f"메타 하루 예산 약 {won(nums['meta_daily'])} (월 {won(nums['meta'])} ÷ 30.4)"
                         + (f", 메타 권장(결과 1개 비용 × 10) 약 {won(nums['meta_rec_daily'])}" if nums.get("meta_rec_daily") else ""))
        elif "메타 월 배분" in link and nums.get("meta"):
            lines.append(f"메타 월 배분 {won(nums['meta'])}")
        if ("예상 CPA" in link or "손님 1명 비용" in link or "CPA" in link) and nums.get("cpa"):
            lines.append(f"손님 1명 데려오는 비용(예상) 약 {won(nums['cpa'])}, 한도 {won(nums['be_first'])}")
        if ("pixel_ready" in link or "메타 목적" in link) and nums.get("meta_objective"):
            lines.append(f"코치 추천 목적: {nums['meta_objective']}")
    return list(dict.fromkeys(lines))[:3]
