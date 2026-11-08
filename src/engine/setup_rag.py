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

ROOT = Path(__file__).resolve().parents[2]
RAG_DIR = ROOT / "data" / "rag"
CARD_FILES = ("naver_searchad.md", "meta_ads.md")
TOP_K = 4
MIN_SCORE = 6.0            # 이보다 낮으면 '자료에 없어요' (찾기 테스트로 정함)
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


def load_cards(rag_dir: Path = RAG_DIR) -> List[Card]:
    key = str(rag_dir)
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


def tokenize(text: str) -> List[str]:
    """공백·기호로 나눈 단어 + 한글·영문 2글자 조각 (조사가 붙어도 맞게)."""
    out = []
    for w in _WORD.findall((text or "").lower()):
        out.append(w)
        if len(w) > 2:
            out += [w[i:i + 2] for i in range(len(w) - 1)]
    return out


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
        q = Counter(tokenize(query))
        scored = []
        for c, tf, dl in zip(self.cards, self.tf, self.len):
            if media and media not in c.media:
                continue
            s = 0.0
            for t, qn in q.items():
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg)) * min(qn, 2)
            if s > 0:
                scored.append((c, s))
        scored.sort(key=lambda x: -x[1])
        return scored[:top]


_INDEX: Dict[str, Index] = {}


def index(rag_dir: Path = RAG_DIR) -> Index:
    key = str(rag_dir)
    if key not in _INDEX:
        _INDEX[key] = Index(load_cards(rag_dir))
    return _INDEX[key]


def find(query: str, top: int = TOP_K) -> List[Tuple[Card, float]]:
    """기준 이상인 카드만 (없으면 빈 목록 = '자료에 없어요')."""
    return [(c, s) for c, s in index().search(query, top) if s >= MIN_SCORE]


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


def card_text(c: Card) -> str:
    return (f"[{c.id}] {c.title}\n매체: {c.media} | 단계: {c.stage}\n화면 단서: {c.screen}\n"
            f"확인: {c.check} {CHECK_WORDS.get(c.check, '')}\n코치 연결: {c.coach}\n본문: {c.body}")


def coach_text(ctx: Dict) -> str:
    """코치 숫자 (네이버·메타 배분, 하루 예산 = 월 ÷ 30.4, 검색어, 판매가, 100번 중 ○번). 개인정보 없음."""
    if not ctx:
        return "코치 숫자: 아직 없음"
    rows = []
    for key, label in (("naver", "네이버 월 예산"), ("meta", "메타 월 예산")):
        if ctx.get(key) is not None:
            rows.append(f"{label} {ctx[key]:,.0f}원 (하루 {ctx[key] / 30.4:,.0f}원)")
    if ctx.get("keyword"):
        rows.append(f"검색어 '{ctx['keyword']}'")
    if ctx.get("price"):
        rows.append(f"판매가 {ctx['price']:,.0f}원")
    if ctx.get("wins") is not None:
        rows.append(f"100번 해 보면 1년 동안 {ctx['wins']}번 남음")
    if ctx.get("stores"):
        rows.append("판매처 " + ", ".join(ctx["stores"]))
    return "코치 숫자: " + " · ".join(rows)


def check_image(data: bytes, name: str) -> str:
    """캡처 검사 → media type. 크기·형식이 맞지 않으면 ValueError (보내지 않음)."""
    ext = (name or "").rsplit(".", 1)[-1].lower()
    if ext not in IMAGE_TYPES:
        raise ValueError("png나 jpg 캡처만 올릴 수 있어요")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("캡처가 5MB보다 커요. 필요한 부분만 잘라서 올려 주세요")
    return IMAGE_TYPES[ext]


def answer(client, question: str, found: List[Tuple[Card, float]], ctx: Dict,
           image: Optional[Tuple[bytes, str]] = None) -> Dict:
    """→ {"answer": 글, "cards": [Card...]}. 카드가 없으면 LLM을 부르지 않는다. 실패하면 CI.IntakeUnavailable."""
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
    out = CI.call_json(client, SYSTEM, [{"role": "user", "content": content}], ANSWER_SCHEMA, max_tokens=1_500)
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
