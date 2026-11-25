"""챗봇 세팅의 대화 엔진 (순수 파이썬, LLM 없음).

- 상태(state)는 JSON으로 저장되는 dict. 함수는 모두 새 state를 돌려주고, 받은 state는 고치지 않는다.
- 서비스(Services)는 화면이 넣어 준다. 테스트는 가짜를 넣는다. 엔진은 네트워크를 모른다.
- 흐름: 가게 정보 → 확인 카드 → 내 손님(키워드) → 예산 → 칸 질문(칸 사양 순서) → 끝.
- 숫자는 엔진(planner·market)이 준 값만 보여 준다. 답을 못 읽으면 고치는 법과 예시 칩을 보이고 같은 단계에 머문다.
- 질문이 오면 도움말(sv.help)로 답하고 같은 질문을 다시 묻는다.
"""
import copy
import datetime
import json
import re
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from types import SimpleNamespace
from typing import Callable, Dict, Iterator, List, Optional

from . import chat_parse as cp

STAGES = ["가게", "확인", "손님", "예산", "세팅 질문"]
PHASE_STAGE = {"store": 0, "confirm": 1, "market": 2, "budget": 3, "ask": 4, "done": 5}
STORE_STEPS = [("name", "가게 이름"), ("product", "상품"), ("price", "판매가"), ("margin", "1개 팔면 남는 돈"),
               ("budget", "한 달 광고비"), ("channel", "판매처"), ("slug", "영문 이름")]
STORE_LABEL = dict(STORE_STEPS)
CHANNELS = ["스마트스토어", "내 쇼핑몰(자사몰)"]
CHANNEL_KEY = {"스마트스토어": "smartstore", "내 쇼핑몰(자사몰)": "own"}
CHANNEL_ALIAS = (("자사", "own"), ("카페24", "own"), ("아임웹", "own"), ("고도몰", "own"), ("메이크샵", "own"),
                 ("내 쇼핑몰", "own"), ("직접", "own"), ("스마트", "smartstore"), ("스토어", "smartstore"),
                 ("네이버", "smartstore"))
YES_CHIP, FIX_CHIP = "맞아요", "고칠래요"
MARKET_OK, MARKET_AGAIN, MARKET_SKIP, MARKET_RETRY = "이대로 쓸게요", "다른 단어로 찾을래요", "자료 없이 넘어갈래요", "다시 찾아볼게요"
BUDGET_OK, BUDGET_AGAIN = "이대로 할게요", "목표·기간 다시 고를래요"
SKIP_REST_CHIP = "남은 질문은 권장 답으로"
LATER_CHIP = "나중에 입력할게요"
OBJECTIVE_KEY, END_DATE_KEY = "meta.campaign.objective", "meta.adset.end_date"
DEFAULT_OBJECTIVE_OPTIONS = ["스토어 방문 늘리기", "가게 알리기"]
DEFAULT_OBJECTIVE_MAP = {"스토어 방문 늘리기": "트래픽", "가게 알리기": "인지도"}
DEFAULT_DAY_OPTIONS = ["7일", "14일", "30일"]
COPY_KEYS = {"meta": "meta.creative.copy", "naver": "naver.ad.copy"}
MIN_BUDGET, MAX_BUDGET = 10000, 100000000
MARKET_KEY = "naver.keywords.list"

_STREAMS = {}   # type: Dict[str, Iterator[str]]   # 스트리밍 답은 JSON에 못 넣어서 따로 보관 (take_stream으로 꺼냄)


@dataclass
class Turn:
    role: str                         # "user" | "bot"
    text: str
    kind: str = "text"                # text | confirm_card | market_card | budget_card | help | error | done
    data: Dict = field(default_factory=dict)
    chips: List[str] = field(default_factory=list)


@dataclass
class Services:
    market: Callable[[List[str]], object]                        # seeds → MarketReport | None
    plan: Callable[[dict, Optional[object], str, int], object]   # store, market, objective, days → BudgetPlan
    help: Callable[[str, Optional[str], dict], object]           # question, step_id, ctx → HelpAnswer
    questions: Callable[[List[str]], List[dict]]                 # intake.questions
    copies: Callable[[str, str], Dict[str, list]]                # product, strengths → {"meta": [...], "naver": [...]}
    is_question: Optional[Callable[[str], bool]] = None          # 없으면 chat_parse.looks_like_question
    market_error: Optional[Callable[[], Optional[str]]] = None   # 검색 실패 이유(쉬운 문장, 키 값 없음)


class _Bad(Exception):
    """답을 못 읽었을 때. msg는 고치는 법, chips는 예시."""

    def __init__(self, msg: str, chips: Optional[List[str]] = None):
        super().__init__(msg)
        self.msg, self.chips = msg, chips or []


# ── 작은 도구 ─────────────────────────────────────────────

def _won(n: object) -> str:
    try:
        return "{:,}원".format(int(n))
    except (TypeError, ValueError):
        return str(n)


def _jsonable(x: object) -> object:
    """numpy·DataFrame 값 같은 것을 JSON 기본형으로."""
    def default(o):
        if hasattr(o, "item"):
            try:
                return o.item()
            except (ValueError, TypeError):
                pass
        if hasattr(o, "tolist"):
            return o.tolist()
        if is_dataclass(o):
            return asdict(o)
        return str(o)
    return json.loads(json.dumps(x, ensure_ascii=False, default=default))


def _turn(st: dict, role: str, text: str, kind: str = "text", data: Optional[dict] = None,
          chips: Optional[List[str]] = None) -> dict:
    st["seq"] = st.get("seq", 0) + 1
    t = asdict(Turn(role=role, text=text, kind=kind, data=dict(data or {}), chips=list(chips or [])))
    t["data"]["turn_id"] = "%s-%d" % (st["sid"], st["seq"])
    st["turns"].append(t)
    return t


def _say(st: dict, text: str, kind: str = "text", data: Optional[dict] = None, chips: Optional[List[str]] = None) -> dict:
    return _turn(st, "bot", text, kind, data, chips)


def _error(st: dict, msg: str, chips: Optional[List[str]] = None) -> None:
    _say(st, msg, "error", chips=chips)


def turns(state: dict) -> List[Turn]:
    return [Turn(**{k: t[k] for k in ("role", "text", "kind", "data", "chips")}) for t in state["turns"]]


def last_turn(state: dict) -> Optional[Turn]:
    ts = turns(state)
    return ts[-1] if ts else None


def _clone(state: dict) -> dict:
    return copy.deepcopy(state)


def _is_question(text: str, sv: Services) -> bool:
    fn = getattr(sv, "is_question", None) or cp.looks_like_question
    try:
        return bool(fn(text))
    except Exception:  # noqa: BLE001 (판별이 깨져도 대화는 계속)
        return cp.looks_like_question(text)


# ── 상태 ──────────────────────────────────────────────────

def start(media: List[str], month: Optional[str] = None) -> dict:
    """새 대화. 첫 질문(가게 이름)까지 말풍선에 담아 돌려준다."""
    media = [m for m in dict.fromkeys(media or []) if m]
    bad = [m for m in media if m not in ("meta", "naver")]
    if not media or bad:
        raise ValueError("매체는 'meta', 'naver' 중에서 골라 주세요.")
    st = {"version": 1, "sid": uuid.uuid4().hex[:8], "seq": 0, "media": media,
          "month": month or "%d월" % datetime.date.today().month,
          "phase": "store", "step": STORE_STEPS[0][0], "sub": None, "editing": False,
          "store": {}, "market": None, "plan": None, "objective": None, "days": None,
          "answers": {}, "qs": None, "cand": None, "ask_intro": False, "qno": 0, "qtotal": 0, "turns": []}
    _say(st, "안녕하세요! 광고를 처음 하셔도 괜찮아요. 몇 가지만 물어볼게요. 모르는 건 언제든 물어보셔도 돼요.")
    _append_prompt(st)
    return st


def progress(state: dict) -> dict:
    """진행 표시용: 단계 이름들, 지금 단계 번호(0부터, 끝나면 단계 수), 질문 번호."""
    idx = PHASE_STAGE.get(state["phase"], 0)
    return {"stages": list(STAGES), "index": idx, "label": STAGES[idx] if idx < len(STAGES) else "끝",
            "question_no": state.get("qno", 0), "question_total": state.get("qtotal", 0),
            "done": state["phase"] == "done"}


def _store_line(st: dict, key: str) -> str:
    s = st["store"]
    v = s.get(key)
    if key in ("price", "budget"):
        return _won(v)
    if key == "margin":
        p = s.get("price") or 0
        return "%s (판매가의 %d%%)" % (_won(v), int(round(100.0 * v / p))) if p else _won(v)
    if key == "channel":
        return next((c for c in CHANNELS if CHANNEL_KEY[c] == s.get("store_type")), "")
    if key == "slug":
        return str(s.get("slug", ""))
    return str(v or "")


def _store_items(st: dict) -> List[dict]:
    items = [{"key": k, "label": lab, "value": _store_line(st, "channel" if k == "channel" else k)}
             for k, lab in STORE_STEPS]
    items.append({"key": "media", "label": "광고 매체",
                  "value": "·".join({"meta": "메타(인스타·페이스북)", "naver": "네이버 검색광고"}[m] for m in st["media"])})
    return items


def editable(state: dict) -> List[dict]:
    """'지난 답 고치기' 칩용: 지금까지 답한 것들 [{key, label, value}] (가게 7개 → 손님 → 예산 → 칸 답)."""
    out = [i for i in _store_items(state) if i["key"] != "media"] if state["store"].get("slug") else []
    m = state.get("market")
    if m and m.get("picked") is not None:
        out.append({"key": "market", "label": "내 손님(검색 단어)", "value": ", ".join(m["picked"][:5])})
    if state.get("plan"):
        out.append({"key": "budget_plan", "label": "예산 나누기",
                    "value": "%s · %d일" % (state["objective"], state["days"])})
    for q in state.get("qs") or []:
        if q["id"] in state["answers"] and q["id"] not in (OBJECTIVE_KEY, END_DATE_KEY):
            out.append({"key": q["id"], "label": q["label"], "value": _show_answer(state["answers"][q["id"]])})
    return out


def _show_answer(v: object) -> str:
    if isinstance(v, dict):
        return " / ".join(str(v[k]) for k in ("headline", "text") if v.get(k))
    return str(v)


# ── 질문(칸) 찾기 ──────────────────────────────────────────

def _ensure_qs(st: dict, sv: Services) -> None:
    if not st.get("qs"):
        st["qs"] = _jsonable(sv.questions(st["media"]))


def _qspec(st: dict, qid: str) -> Optional[dict]:
    return next((q for q in st.get("qs") or [] if q["id"] == qid), None)


def _pending(st: dict) -> List[dict]:
    return [q for q in st.get("qs") or [] if q["id"] not in st["answers"]]


def _field_for_step(st: dict) -> Optional[str]:
    """지금 단계에 맞는 칸 id (도움말이 칸을 알도록)."""
    ph = st["phase"]
    if ph == "ask":
        return st["step"]
    if ph == "market" and "naver" in st["media"]:
        return MARKET_KEY
    if ph == "budget":
        return {"objective": OBJECTIVE_KEY, "days": END_DATE_KEY}.get(st["step"]) if "meta" in st["media"] else None
    return None


# ── 말풍선 만들기 (지금 단계의 질문) ─────────────────────────

def _prompt(st: dict) -> dict:
    """지금 단계의 질문을 Turn dict로 (붙이지는 않음). 다시 물을 때도 같은 것을 쓴다."""
    ph, step = st["phase"], st["step"]
    s = st["store"]
    if ph == "store":
        return _build_store_prompt(st, step)
    if ph == "confirm":
        if step == "fix":
            items = [i for i in _store_items(st) if i["key"] != "media"]
            return _mk("어느 걸 고칠까요?", chips=[i["label"] for i in items])
        return _confirm_card(st)
    if ph == "market":
        if step == "seeds":
            return _mk("손님이 검색창에 칠 만한 단어를 알려 주세요. 여러 개면 쉼표로 나눠 주세요. 아래에서 골라도 돼요.",
                       chips=_seed_chips(s))
        if step == "pick":
            return _market_card(st)
        why = str((st.get("market") or {}).get("why") or "").strip()
        return _mk("검색 자료를 지금은 불러오지 못했어요." + (" (이유: %s)" % why if why else "")
                   + " 다시 찾아보거나, 자료 없이 넘어갈 수 있어요. "
                   "넘어가면 방금 적은 단어를 그대로 쓰고, 예산은 검색량 없이 나눠요.",
                   kind="error", chips=[MARKET_RETRY, MARKET_SKIP])
    if ph == "budget":
        if step == "objective":
            opts, _m = _objective_opts(st)
            return _mk("광고로 가장 원하는 게 뭐예요?", chips=opts)
        if step == "days":
            return _mk("광고를 며칠 동안 돌릴까요? 처음엔 7~14일을 권해요. 숫자로 적어도 돼요. (예: 10일, 2주)",
                       chips=_day_opts(st))
        return _budget_card(st)
    if ph == "ask":
        q = _qspec(st, step)
        return _question_turn(st, q) if q else _mk("남은 질문이 없어요.")
    return _mk("세팅이 끝났어요. 바꾸고 싶은 칸이 있으면 '지난 답 고치기'를 눌러 주세요.")


def _mk(text: str, kind: str = "text", data: Optional[dict] = None, chips: Optional[List[str]] = None) -> dict:
    return {"text": text, "kind": kind, "data": data or {}, "chips": chips or []}


def _append_prompt(st: dict) -> None:
    p = _prompt(st)
    _say(st, p["text"], p["kind"], p["data"], p["chips"])


def _build_store_prompt(st: dict, step: str) -> dict:
    s = st["store"]
    name = s.get("name", "")
    if step == "name":
        return _mk("가게 이름이 뭐예요? (예: 소연베이크)")
    if step == "product":
        return _mk("어떤 상품을 광고할 거예요? 한 가지만 먼저 정해요. (예: 수제 구움과자)")
    if step == "price":
        return _mk("그 상품의 판매가는 얼마예요? (예: 26,000원 · 2만 6천원)", chips=[])
    if step == "margin":
        return _mk("1개 팔면 재료비·포장비·수수료를 빼고 손에 남는 돈은 얼마예요? 광고가 본전을 하려면 몇 개 팔아야 하는지 계산할 때 써요. "
                   "(예: 8,000원, 또는 판매가의 30%)")
    if step == "budget":
        return _mk("한 달에 광고비로 쓸 수 있는 돈은 얼마예요? 이 안에서만 쓰도록 나눠 드려요. (예: 30만원)",
                   chips=["10만원", "30만원", "50만원"])
    if step == "channel":
        return _mk("상품은 어디에서 파세요?", chips=list(CHANNELS))
    slug = cp.suggest_slug(name) if name else "item"
    if slug == "item":
        slug = cp.suggest_slug(s.get("product", ""))
    return _mk("가게를 영어로 한 단어로 적어 주세요. 광고 이름과 방문 꼬리표에 쓰여서, 나중에 어떤 광고에서 온 손님인지 구분할 수 있어요. "
               "영어 소문자·숫자만 돼요. (예: %s)" % slug, chips=[slug])


def _confirm_card(st: dict) -> dict:
    items = _store_items(st)
    lines = ["%s: %s" % (i["label"], i["value"]) for i in items]
    return _mk("이렇게 이해했어요.\n" + "\n".join("· " + l for l in lines) + "\n\n맞나요?",
               kind="confirm_card", data={"items": items}, chips=[YES_CHIP, FIX_CHIP])


def _seed_chips(s: dict) -> List[str]:
    product = str(s.get("product", "")).strip()
    words = product.split()
    core = words[-1] if words else product
    out = []
    for c in (core, product.replace(" ", ""), core + "선물", core + " 답례품"):
        c = c.strip()
        if c and c not in out:
            out.append(c)
    return out[:4]


def _objective_opts(st: dict):
    q = _qspec(st, OBJECTIVE_KEY)
    if q and q.get("options"):
        return list(q["options"]), dict(q.get("map") or DEFAULT_OBJECTIVE_MAP)
    return list(DEFAULT_OBJECTIVE_OPTIONS), dict(DEFAULT_OBJECTIVE_MAP)


def _day_opts(st: dict) -> List[str]:
    q = _qspec(st, END_DATE_KEY)
    return list(q["options"]) if q and q.get("options") else list(DEFAULT_DAY_OPTIONS)


def _market_card(st: dict) -> dict:
    m = st["market"] or {}
    rec = m.get("recommended") or []
    head = m.get("headline") or ""
    lines = []
    if head:
        lines.append(head)
    if rec:
        lines.append("손님이 많이 찾는 단어로 이런 걸 골랐어요: " + ", ".join(rec[:8]))
    else:
        lines.append("추천할 만한 단어를 못 찾았어요. 단어를 바꿔 다시 찾아볼까요?")
    if m.get("negatives"):
        lines.append("엉뚱한 사람이 들어오지 않게 이 단어는 빼요: " + ", ".join(m["negatives"][:6]))
    lines.append("이 단어로 광고를 낼까요? 다른 단어를 직접 적어도 돼요.")
    chips = [MARKET_OK, MARKET_AGAIN] if rec else [MARKET_AGAIN, MARKET_SKIP]
    return _mk("\n\n".join(lines), kind="market_card",
               data={k: m.get(k) for k in ("seeds", "headline", "recommended", "negatives", "audience_hint", "groups", "fetched")},
               chips=chips)


def _budget_card(st: dict) -> dict:
    p = st["plan"] or {}
    media = st["media"]
    parts = []
    if "naver" in media and p.get("naver_month"):
        parts.append("네이버 검색광고 %s (하루 %s)" % (_won(p["naver_month"]), _won(p["naver_daily"])))
    if "meta" in media and p.get("meta_month"):
        parts.append("메타 %s (하루 %s, %d일)" % (_won(p["meta_month"]), _won(p["meta_daily"]), st["days"]))
    text = "한 달 %s을 이렇게 나눌게요.\n" % _won(p.get("budget", 0)) + "\n".join("· " + x for x in parts)
    notes = p.get("notes") or []
    if notes:
        text += "\n\n" + "\n".join(notes)
    return _mk(text, kind="budget_card",
               data={"plan": p, "objective": st["objective"], "days": st["days"], "notes": notes},
               chips=[BUDGET_OK, BUDGET_AGAIN])


def _question_turn(st: dict, q: dict) -> dict:
    qs = st.get("qs") or []
    ids = [x["id"] for x in qs]
    n = ids.index(q["id"]) + 1 if q["id"] in ids else 0
    st["qno"], st["qtotal"] = n, len(qs)
    data = {"qid": q["id"], "label": q["label"], "stage": q["stage"], "n": n, "total": len(qs), "why": q.get("why", "")}
    text = q["ask"]
    if q["kind"] == "llm":
        if st.get("cand") and st.get("sub") == "pick":
            return _copy_turn(st, data)
        return _mk(text, data=data, chips=[])
    chips = list(q.get("options") or [])
    if q["input"] == "choice":
        if q.get("default"):
            text += " (잘 모르겠으면 '%s'가 무난해요)" % q["default"]
        return _mk(text, data=data, chips=chips)
    chips = _free_chips(st, q)
    if q["input"] == "url":
        text += " 붙여 넣기만 하면 돼요."
    return _mk(text, data=data, chips=chips)


def _free_chips(st: dict, q: dict) -> List[str]:
    chips = []
    if q.get("default"):
        chips.append(str(q["default"]))
    hint = (st.get("market") or {}).get("audience_hint")
    if q.get("suggest_from") == "market_age_gender" and hint:
        chips.append(hint)
    if not q.get("default"):
        chips.append(LATER_CHIP)
    return chips


def _copy_turn(st: dict, data: dict) -> dict:
    c = st["cand"]
    lines = ["이런 문구를 만들어 봤어요. 마음에 드는 걸 골라 주세요.", ""]
    for i, cp_ in enumerate(c["show"]):
        lines.append("%d번  %s\n    %s" % (i + 1, cp_["headline"], cp_["text"]))
    lines.append("\n장점을 다시 적어 주시면 새로 만들어 드려요.")
    return _mk("\n".join(lines), data=dict(data, copies=c["show"]), chips=list(c["labels"]))


# ── 진입점 ────────────────────────────────────────────────

def handle(state: dict, text: str, sv: Services) -> dict:
    """사장님이 글을 쓴 경우. 새 state를 돌려준다."""
    st = _clone(state)
    text = (text or "").strip()
    if text:
        _turn(st, "user", text)
    _run(st, text, sv, chip=False)
    return st


def choose(state: dict, chip: str, sv: Services) -> dict:
    """사장님이 칩을 누른 경우 (칩 글자는 질문으로 보지 않는다)."""
    if chip == SKIP_REST_CHIP:
        return skip_rest(state, sv)
    st = _clone(state)
    _turn(st, "user", chip)
    _run(st, chip, sv, chip=True)
    return st


def _run(st: dict, text: str, sv: Services, chip: bool) -> None:
    _ensure_qs(st, sv)
    if not text:
        _error(st, "아직 아무것도 적지 않으셨어요. 아래 칸에 답을 적어 주세요.")
        _append_prompt(st)
        return
    free_text = (st["phase"] == "store" and st["step"] in ("name", "product", "slug")) or \
                (st["phase"] == "market" and st["step"] == "seeds")
    if not chip and free_text:
        # 이름·검색 단어 칸: 물음표·끝말이 분명하고, 도움말 판별도 질문이라 할 때만 질문
        if cp.looks_like_question(text, strict=True) and _is_question(text, sv):
            _help(st, text, sv)
            return
    elif not chip and _is_question(text, sv):
        _help(st, text, sv)
        return
    handler = {"store": _h_store, "confirm": _h_confirm, "market": _h_market, "budget": _h_budget,
               "ask": _h_ask, "done": _h_done}[st["phase"]]
    try:
        handler(st, text, sv)
    except _Bad as e:
        _error(st, e.msg, e.chips)


# ── 도움말 ────────────────────────────────────────────────

def _ctx(st: dict) -> dict:
    store = to_store(st)
    return {"store": store, "plan": st.get("plan"), "budget_plan": st.get("plan"), "media": list(st["media"]),
            "answers": dict(st["answers"]), "objective": st.get("objective"), "days": st.get("days")}


def _help(st: dict, question: str, sv: Services) -> None:
    sid = _field_for_step(st)
    try:
        ans = sv.help(question, sid, _ctx(st))
    except Exception:  # noqa: BLE001 (도움말이 깨져도 대화는 계속)
        ans = None
    if ans is None:
        _say(st, "지금은 답을 찾지 못했어요. 이 질문은 잠시 접어 두고, 아래 질문에 먼저 답해 주세요.", "help",
             {"kind": "none", "field_id": sid, "sources": [], "stream": False})
    else:
        sources = [{"title": str(x.get("title", "")), "url": str(x.get("url", "")), "check": str(x.get("check", ""))}
                   for x in (getattr(ans, "sources", None) or []) if isinstance(x, dict)]
        stream = getattr(ans, "stream", None)
        t = _say(st, "" if stream is not None else str(getattr(ans, "text", "") or ""), "help",
                 {"kind": str(getattr(ans, "kind", "help")), "field_id": getattr(ans, "field_id", None),
                  "sources": sources, "stream": stream is not None})
        if stream is not None:
            _STREAMS[t["data"]["turn_id"]] = stream
    _append_prompt(st)


def take_stream(state: dict) -> Optional[Iterator[str]]:
    """가장 최근 도움말 말풍선의 스트리밍 답을 꺼낸다 (한 번만). 없으면 None. 다 흘린 뒤 set_help_text로 글을 저장."""
    for t in reversed(state["turns"]):
        if t["kind"] == "help" and t["data"].get("stream"):
            return _STREAMS.pop(t["data"]["turn_id"], None)
    return None


def set_help_text(state: dict, text: str) -> dict:
    """스트리밍이 끝난 글을 가장 최근 스트리밍 말풍선에 적어 넣는다 (대화 기록이 완전해짐)."""
    st = _clone(state)
    for t in reversed(st["turns"]):
        if t["kind"] == "help" and t["data"].get("stream"):
            t["text"] = text
            t["data"]["stream"] = False
            break
    return st


# ── 가게 정보 ─────────────────────────────────────────────

def _money_error(label: str, example: str, lo: int, hi: int) -> _Bad:
    return _Bad("%s을(를) 금액으로 읽지 못했어요. 숫자와 원·만·천으로 적어 주세요. 예: %s (%s ~ %s 사이)"
                % (label, example, _won(lo), _won(hi)), [example])


def _store_value(st: dict, key: str, text: str):
    """(값, 되말하기). 못 읽으면 _Bad."""
    s = st["store"]
    if key in ("name", "product"):
        v = re.sub(r"\s+", " ", text).strip()
        if len(v) > 40:
            raise _Bad("너무 길어요. 40자 안으로 짧게 적어 주세요.")
        return v, "'%s'(으)로 적어 둘게요." % v
    if key == "price":
        v = cp.parse_money(text)
        if v is None or not 100 <= v <= 10000000:
            raise _money_error("판매가", "26,000원", 100, 10000000)
        return v, "%s으로 이해했어요." % _won(v)
    if key == "margin":
        price = s.get("price") or 0
        pct = cp.parse_percent(text)
        if pct is not None and price:
            v = int(round(price * pct / 100.0, -1)) or 10
            return v, "판매가의 %s%%인 %s으로 이해했어요." % (("%g" % pct), _won(v))
        v = cp.parse_money(text)
        if v is None or v <= 0:
            raise _Bad("1개 팔 때 남는 돈을 금액으로 읽지 못했어요. 예: 8,000원 (판매가의 30%%처럼 퍼센트로 적어도 돼요)", ["8,000원"])
        if price and v > price:
            raise _Bad("남는 돈(%s)이 판매가(%s)보다 클 수는 없어요. 재료비·포장비·수수료를 뺀 뒤 손에 남는 돈으로 다시 적어 주세요."
                       % (_won(v), _won(price)), ["%s" % _won(int(price * 0.3 // 100 * 100) or 100)])
        return v, "%s으로 이해했어요. 판매가의 %d%%예요." % (_won(v), int(round(100.0 * v / price))) if price else "%s으로 이해했어요." % _won(v)
    if key == "budget":
        v = cp.parse_money(text)
        if v is None or not MIN_BUDGET <= v <= MAX_BUDGET:
            hint = " 혹시 %d만 원이라면 '%d만원'이라고 적어 주세요." % (v, v) if v and 0 < v < 1000 else ""
            raise _Bad("한 달 광고비를 %s 이상으로 적어 주세요. 1만 원보다 적으면 광고가 거의 나가지 않아요. 예: 30만원%s"
                       % (_won(MIN_BUDGET), hint), ["30만원"])
        return v, "한 달 %s으로 이해했어요." % _won(v)
    if key == "channel":
        t = text.replace(" ", "")
        kind = next((k for w, k in CHANNEL_ALIAS if w.replace(" ", "") in t), None)
        pick = cp.parse_choice(text, CHANNELS)
        if pick is None and kind:
            pick = next(c for c in CHANNELS if CHANNEL_KEY[c] == kind)
        if pick is None:
            raise _Bad("판매처를 못 알아봤어요. 둘 중에서 골라 주세요. 스마트스토어가 아니면 '내 쇼핑몰'을 골라 주세요.", list(CHANNELS))
        return CHANNEL_KEY[pick], "%s에서 파신다고 이해했어요." % pick
    if key == "slug":
        v = cp.suggest_slug(text) if re.search(r"[가-힣]", text) else re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        if not v or v == "item":
            raise _Bad("영어 소문자와 숫자로 적어 주세요. 한글만 있으면 만들 수 없어요. 예: soyeonbake",
                       [cp.suggest_slug(s.get("name", "")) if s.get("name") else "myshop"])
        echo = "'%s'(으)로 쓸게요." % v
        if v != text.strip():
            echo = "'%s'(으)로 바꿔서 쓸게요. (영어 소문자·숫자·밑줄만 쓸 수 있어요)" % v
        return v, echo
    raise _Bad("알 수 없는 단계예요.")


def _h_store(st: dict, text: str, sv: Services) -> None:
    key = st["step"]
    val, echo = _store_value(st, key, text)
    if key == "channel":
        st["store"]["store_type"] = val
    else:
        st["store"][key] = val
    _say(st, echo)
    keys = [k for k, _ in STORE_STEPS]
    if st["editing"] or key == keys[-1]:
        st["editing"] = False
        _show_confirm(st)
        return
    st["step"] = keys[keys.index(key) + 1]
    _append_prompt(st)


def _show_confirm(st: dict) -> None:
    st["phase"], st["step"] = "confirm", "ok"
    _append_prompt(st)


def _h_confirm(st: dict, text: str, sv: Services) -> None:
    if st["step"] == "fix":
        items = [i for i in _store_items(st) if i["key"] != "media"]
        label = cp.parse_choice(text, [i["label"] for i in items])
        if label is None:
            if cp.parse_yes_no(text) is True:
                return _after_confirm(st, sv)
            raise _Bad("어느 칸인지 못 알아봤어요. 아래에서 눌러 주세요.", [i["label"] for i in items])
        _begin_edit(st, next(i["key"] for i in items if i["label"] == label))
        return
    yn = cp.parse_yes_no(text)
    if yn is True:
        return _after_confirm(st, sv)
    if yn is False:
        st["step"] = "fix"
        _append_prompt(st)
        return
    raise _Bad("'맞아요'인지 '고칠래요'인지 눌러 주세요. 고치고 싶은 칸이 있으면 '고칠래요'를 누르세요.", [YES_CHIP, FIX_CHIP])


def _after_confirm(st: dict, sv: Services) -> None:
    st["confirmed"] = True
    if st["market"] is None:
        _start_market(st)
    elif st["plan"] is not None:
        _replan_and_continue(st, sv)
    else:
        _start_budget(st, sv)


def _begin_edit(st: dict, key: str) -> None:
    """고칠 칸으로 돌아가 다시 묻는다. 고친 뒤에는 확인 카드(가게) 또는 다음 안 한 질문으로 이어진다."""
    if key in STORE_LABEL:
        st["phase"], st["step"], st["editing"] = "store", key, True
        _say(st, "'%s'을(를) 다시 알려 주세요." % STORE_LABEL[key])
    elif key == "market":
        st["phase"], st["step"], st["editing"] = "market", "seeds", True
        _say(st, "검색 단어를 다시 정해 볼게요.")
    elif key == "budget_plan":
        st["phase"], st["editing"] = "budget", True
        st["step"] = "objective" if "meta" in st["media"] else "ok"
        _say(st, "예산 나누기를 다시 해 볼게요.")
    else:
        q = _qspec(st, key)
        if q is None:
            _error(st, "그 칸은 아직 물어보기 전이라 고칠 게 없어요.")
            return
        st["phase"], st["step"], st["editing"], st["sub"], st["cand"] = "ask", key, True, None, None
        _say(st, "'%s'을(를) 다시 정해요." % q["label"])
    _append_prompt(st)


def edit(state: dict, key: str) -> dict:
    """'지난 답 고치기': key는 가게 칸(name·product·price·margin·budget=한 달 광고비·channel·slug), 'market', 'budget' 또는 칸 id."""
    st = _clone(state)
    label = next((i["label"] for i in editable(st) if i["key"] == key), key)
    _turn(st, "user", "'%s' 고칠래요" % label)
    _begin_edit(st, key)
    return st


# ── 내 손님 ───────────────────────────────────────────────

def _start_market(st: dict) -> None:
    st["phase"], st["step"] = "market", "seeds"
    _say(st, "이제 내 손님을 찾아볼게요. 네이버에서 사람들이 실제로 검색하는 단어를 보고, 광고에 쓸 단어를 골라 드려요.")
    _append_prompt(st)


def _h_market(st: dict, text: str, sv: Services) -> None:
    step = st["step"]
    if step in ("pick", "fail"):
        opts = [MARKET_OK, MARKET_AGAIN] if step == "pick" else [MARKET_RETRY, MARKET_SKIP]
        pick = cp.parse_choice(text, opts)
        yn = cp.parse_yes_no(text)
        if pick is None and yn is True and step == "pick":
            pick = MARKET_OK
        if pick == MARKET_OK:
            return _accept_market(st, sv)
        if pick == MARKET_SKIP or (step == "pick" and text == MARKET_SKIP):
            return _skip_market(st, sv)
        if pick == MARKET_RETRY:
            return _run_market(st, st["market"]["seeds"], sv)
        if pick == MARKET_AGAIN:
            st["step"] = "seeds"
            _append_prompt(st)
            return
    seeds = cp.parse_words(text)
    if not seeds:
        raise _Bad("검색 단어를 못 읽었어요. 쉼표로 나눠 적어 주세요. 예: 휘낭시에, 쿠키선물세트", _seed_chips(st["store"]))
    _run_market(st, seeds, sv)


def _rows(report: object, words: List[str]) -> List[dict]:
    try:
        df = report.keywords
        sub = df[df["keyword"].isin(words)]
        return _jsonable(sub[[c for c in ("keyword", "total_qc", "intent") if c in sub.columns]].to_dict("records"))
    except Exception:  # noqa: BLE001
        return []


def _audience_hint(report: object) -> Optional[str]:
    """시장 카드 한 줄 요약(headline)과 같은 연령·성별로 만든 제안. 요약에 연령이 없으면 None."""
    head = str(getattr(report, "headline", "") or "")
    m = re.search(r"(\d{2})대\s*(여성|남성)?", head)
    if not m:
        return None
    return "%s대 %s 중심" % (m.group(1), m.group(2)) if m.group(2) else "%s대 중심" % m.group(1)


def _run_market(st: dict, seeds: List[str], sv: Services) -> None:
    try:
        rep = sv.market(list(seeds))
    except Exception:  # noqa: BLE001
        rep = None
    if rep is None:
        why = None
        if sv.market_error is not None:
            try:
                why = sv.market_error()
            except Exception:  # noqa: BLE001
                why = None
        st["market"] = {"seeds": list(seeds), "fail": True, "why": why}
        st["step"] = "fail"
        _append_prompt(st)
        return
    rec = [str(x) for x in (getattr(rep, "recommended", None) or [])]
    try:
        groups = _jsonable(rep.groups.to_dict("records"))
    except Exception:  # noqa: BLE001
        groups = []
    st["market"] = {"seeds": list(seeds), "recommended": rec, "negatives": [str(x) for x in (getattr(rep, "negatives", None) or [])],
                    "headline": str(getattr(rep, "headline", "") or ""), "audience_hint": _audience_hint(rep),
                    "groups": groups, "rows": _rows(rep, rec), "picked": None,
                    "fetched": str(getattr(rep, "fetched", "") or "")}
    st["step"] = "pick"
    _append_prompt(st)


def _accept_market(st: dict, sv: Services) -> None:
    m = st["market"]
    m["picked"] = list(m.get("recommended") or m["seeds"])
    _say(st, "좋아요. 검색 단어 %d개로 광고를 낼게요." % len(m["picked"]))
    _after_market(st, sv)


def _skip_market(st: dict, sv: Services) -> None:
    m = st["market"] or {"seeds": []}
    m.update({"fail": True, "picked": list(m.get("seeds") or []), "recommended": list(m.get("seeds") or []),
              "negatives": [], "rows": [], "headline": "", "audience_hint": None})
    st["market"] = m
    _say(st, "검색 자료 없이 적어 주신 단어(%s)로 갈게요. 예산은 검색량을 모른 채 나눠서 덜 정확해요." % ", ".join(m["picked"]))
    _after_market(st, sv)


def _after_market(st: dict, sv: Services) -> None:
    st["editing"] = False
    if st["objective"] and st["days"]:
        _replan_and_continue(st, sv)
    else:
        _start_budget(st, sv)


# ── 예산 ──────────────────────────────────────────────────

def _start_budget(st: dict, sv: Services) -> None:
    st["phase"] = "budget"
    if "meta" not in st["media"]:
        st["objective"], st["days"] = "트래픽", 14
        if _make_plan(st, sv):
            st["step"] = "ok"
            _append_prompt(st)
        return
    st["step"] = "objective"
    _say(st, "한 달 광고비를 나눠 볼게요. 먼저 목표부터 정해요.")
    _append_prompt(st)


def _parse_days(text: str) -> Optional[int]:
    t = text.replace(" ", "")
    if re.search(r"한달|1달|1개월|한 달", t):
        return 30
    if t in ("일주일", "1주", "1주일"):
        return 7
    m = re.fullmatch(r"(\d+)(일|주|주일|주간|일간)?", t)
    if not m:
        return None
    n = int(m.group(1))
    return n * 7 if (m.group(2) or "").startswith("주") else n


def _h_budget(st: dict, text: str, sv: Services) -> None:
    step = st["step"]
    if step == "objective":
        opts, mp = _objective_opts(st)
        pick = cp.parse_choice(text, opts)
        if pick is None:
            raise _Bad("목표를 못 알아봤어요. 둘 중에서 골라 주세요. 잘 모르겠으면 '%s'가 무난해요." % opts[0], opts)
        st["answers"][OBJECTIVE_KEY] = pick
        st["objective"] = mp.get(pick, pick)
        _say(st, "'%s'(으)로 이해했어요." % pick)
        st["step"] = "days"
        _append_prompt(st)
    elif step == "days":
        d = _parse_days(text)
        if d is None or not 1 <= d <= 90:
            raise _Bad("기간을 못 읽었어요. 1~90일 사이로 적어 주세요. 예: 14일, 2주", _day_opts(st))
        st["days"] = d
        opts = _day_opts(st)
        st["answers"][END_DATE_KEY] = "%d일" % d if "%d일" % d in opts else "%d일" % d
        _say(st, "%d일로 이해했어요." % d)
        if _make_plan(st, sv):
            st["step"] = "ok"
            _append_prompt(st)
    else:
        pick = cp.parse_choice(text, [BUDGET_OK, BUDGET_AGAIN])
        if pick is None:
            pick = BUDGET_OK if cp.parse_yes_no(text) is True else None
        if pick == BUDGET_OK:
            st["editing"] = False
            _advance(st, sv)
        elif pick == BUDGET_AGAIN:
            st["step"] = "objective" if "meta" in st["media"] else "ok"
            if st["step"] == "objective":
                _append_prompt(st)
            else:
                raise _Bad("메타 광고를 안 쓰면 바꿀 목표·기간이 없어요. 한 달 광고비를 바꾸려면 '지난 답 고치기'를 눌러 주세요.", [BUDGET_OK])
        else:
            raise _Bad("'이대로 할게요'인지 '다시 고를래요'인지 눌러 주세요.", [BUDGET_OK, BUDGET_AGAIN])


def _make_plan(st: dict, sv: Services) -> bool:
    market = st["market"] if st["market"] and st["market"].get("picked") is not None else None
    try:
        plan = sv.plan(to_store(st), market, st["objective"], st["days"])
    except Exception as e:  # noqa: BLE001
        _error(st, "예산을 나누지 못했어요. %s" % (str(e) if isinstance(e, ValueError) else "잠시 뒤에 다시 해 주세요."),
               [BUDGET_AGAIN] if "meta" in st["media"] else [])
        return False
    st["plan"] = _jsonable(asdict(plan) if is_dataclass(plan) else (plan if isinstance(plan, dict) else vars(plan)))
    return True


def _replan_and_continue(st: dict, sv: Services) -> None:
    """가게·단어가 바뀐 뒤 예산을 같은 목표·기간으로 다시 계산해 카드를 보이고 이어 간다."""
    st["phase"], st["step"] = "budget", "ok"
    _say(st, "바뀐 내용으로 예산을 다시 계산했어요.")
    if _make_plan(st, sv):
        p = _budget_card(st)
        _say(st, p["text"], p["kind"], p["data"], [])
        _advance(st, sv)


# ── 칸 질문 ───────────────────────────────────────────────

def _advance(st: dict, sv: Services) -> None:
    """다음 안 한 질문으로. 없으면 끝."""
    _ensure_qs(st, sv)
    pend = _pending(st)
    if pend:
        st["phase"], st["step"], st["sub"], st["cand"] = "ask", pend[0]["id"], None, None
        if not st["ask_intro"]:
            st["ask_intro"] = True
            _say(st, "이제 광고 관리자 화면의 칸을 하나씩 같이 채워요. 모르는 칸은 물어보셔도 돼요. "
                     "귀찮으면 '남은 질문은 권장 답으로'를 눌러도 돼요.")
        _append_prompt(st)
        return
    st["phase"], st["step"] = "done", "done"
    _say(st, "세팅 질문이 모두 끝났어요! 아래 '세팅값 시트'에서 광고 관리자에 넣을 값을 확인하세요.",
         "done", {"answered": len(st["answers"])})


def _h_done(st: dict, text: str, sv: Services) -> None:
    _say(st, "세팅은 끝났어요. 바꾸고 싶은 칸이 있으면 '지난 답 고치기'를 눌러 주세요. 모르는 게 있으면 물어보셔도 돼요.", chips=[])


def _answer_text(q: dict, text: str, st: dict):
    """(값, 되말하기). 못 읽으면 _Bad."""
    kind = q["input"]
    if kind == "choice":
        opts = q["options"]
        pick = cp.parse_choice(text, opts)
        if pick is None:
            raise _Bad("보기 중에서 골라 주세요. 번호(예: 1)로 답해도 돼요.", opts)
        return pick, "'%s'(으)로 이해했어요." % pick
    if text == LATER_CHIP:
        return "", "나중에 직접 넣을게요. 시트에는 '아직 입력 전이에요'로 보여요."
    if kind == "url":
        if not cp.is_url(text):
            raise _Bad("주소를 못 알아봤어요. 상품 페이지 주소를 통째로 붙여 넣어 주세요. 예: https://smartstore.naver.com/soyeonbake/products/123",
                       [LATER_CHIP])
        url = cp.normalize_url(text)
        return url, "주소를 확인했어요."
    v = text.strip().lstrip("@") if q["id"].endswith("ig_account") else text.strip()
    if not v:
        raise _Bad("내용을 적어 주세요.", _free_chips(st, q))
    return v, "'%s'(으)로 적어 둘게요." % v


def _h_ask(st: dict, text: str, sv: Services) -> None:
    q = _qspec(st, st["step"])
    if q is None:
        return _advance(st, sv)
    if q["kind"] == "llm":
        return _h_copy(st, q, text, sv)
    val, echo = _answer_text(q, text, st)
    st["answers"][q["id"]] = val
    _say(st, echo)
    if q["kind"] == "precheck" and q.get("options") and val == next((o for o in q["options"] if _norm_neg(o)), None):
        _say(st, "참고: %s" % q["why"])
    st["editing"] = False
    _advance(st, sv)


def _norm_neg(opt: str) -> bool:
    return opt.startswith(("아직", "없", "아니"))


def _gen_copies(st: dict, strengths: str, sv: Services) -> bool:
    try:
        res = sv.copies(st["store"].get("product", ""), strengths) or {}
    except Exception:  # noqa: BLE001
        res = {}
    primary = "meta" if "meta" in st["media"] else "naver"
    lst = [c for c in (res.get(primary) or []) if isinstance(c, dict)]
    if not lst:
        return False
    st["cand"] = {"strengths": strengths, "meta": _jsonable(res.get("meta") or []), "naver": _jsonable(res.get("naver") or []),
                  "show": _jsonable(lst), "labels": ["%d번 %s" % (i + 1, c.get("headline", "")[:16]) for i, c in enumerate(lst)]}
    return True


def _set_copy(st: dict, idx: int) -> dict:
    c = st["cand"]
    chosen = None
    for media in st["media"]:
        pool = c.get(media) or []
        if pool:
            pick = pool[idx] if idx < len(pool) else pool[0]
            st["answers"][COPY_KEYS[media]] = pick
            chosen = chosen or pick
    return chosen or c["show"][idx]


def _h_copy(st: dict, q: dict, text: str, sv: Services) -> None:
    if st.get("cand") and st.get("sub") == "pick":
        pick = cp.parse_choice(text, st["cand"]["labels"])
        if pick is not None:
            idx = st["cand"]["labels"].index(pick)
            chosen = _set_copy(st, idx)
            _say(st, "'%s' 문구로 정했어요." % chosen.get("headline", ""))
            st["sub"], st["cand"], st["editing"] = None, None, False
            return _advance(st, sv)
    if len(text.strip()) < 2:
        raise _Bad("장점을 한두 마디로 적어 주세요. 예: 버터 향이 진하고 선물 포장이 예뻐요")
    if not _gen_copies(st, text.strip(), sv):
        raise _Bad("지금은 문구를 만들지 못했어요. 장점을 조금 더 자세히 적어 주시거나, 잠시 뒤에 다시 시도해 주세요.", [LATER_CHIP])
    st["sub"] = "pick"
    _append_prompt(st)


def skip_rest(state: dict, sv: Services) -> dict:
    """남은 질문을 권장 답(칸 사양의 기본값)으로 채우고 끝낸다."""
    st = _clone(state)
    _ensure_qs(st, sv)
    if st["phase"] not in ("ask", "done"):
        _error(st, "가게 정보와 예산을 먼저 정해야 남은 질문을 권장 답으로 채울 수 있어요. 지금 질문에 먼저 답해 주세요.")
        _append_prompt(st)
        return st
    _turn(st, "user", SKIP_REST_CHIP)
    pend = _pending(st)
    for q in pend:
        if q["kind"] == "llm":
            if _gen_copies(st, "", sv):
                _set_copy(st, 0)
            else:
                st["answers"][q["id"]] = q.get("default") or ""
            st["cand"] = None
            continue
        st["answers"][q["id"]] = q.get("default") if q.get("default") is not None else ""
    st["sub"], st["cand"], st["editing"] = None, None, False
    if pend:
        _say(st, "남은 질문 %d개는 권장 답으로 채웠어요. 시트에서 '기본값으로 채움' 칸은 나중에 바꿀 수 있어요." % len(pend))
    _advance(st, sv)
    return st


# ── 결과 꺼내기 ────────────────────────────────────────────

def to_answers(state: dict) -> Dict[str, object]:
    """intake.build_sheet에 넣을 answers (칸 id → 답). 예산 단계에서 고른 목표·기간도 들어 있다."""
    return _jsonable(state["answers"])


def to_store(state: dict) -> dict:
    """plan_io.Plan.store에 넣을 가게 정보 (+ 고른 검색 단어·제안 연령). 아직 모르는 값은 비어 있다."""
    s = state["store"]
    m = state.get("market") or {}
    return {"name": s.get("name", ""), "product": s.get("product", ""), "product_slug": s.get("slug", ""),
            "store_type": s.get("store_type", "smartstore"), "price": s.get("price", 0),
            "margin_per_order": s.get("margin", 0), "budget": s.get("budget", 0),
            "seeds": list(m.get("picked") or m.get("seeds") or []), "search_words": list(m.get("seeds") or []),
            "negatives": list(m.get("negatives") or []), "audience_hint": m.get("audience_hint"),
            "month": state.get("month", ""), "media": list(state["media"]),
            "objective": state.get("objective"), "days": state.get("days")}


def demo_state(sv: Services) -> dict:
    """예시(소연베이크)를 채워 '이렇게 이해했어요' 확인 카드까지 온 대화."""
    st = start(["meta", "naver"])
    for text in ("소연베이크", "수제 구움과자", "26,000원", "8,000원", "30만원", "스마트스토어", "soyeonbake"):
        st = handle(st, text, sv)
    return st


# ── 실제 서비스 연결 (화면이 쓴다) ──────────────────────────────

_CLIENT = []   # 게으른 캐시 (키가 있으면 Claude 클라이언트)


def _client():
    if not _CLIENT:
        try:
            from . import copywriter
            _CLIENT.append(copywriter.make_client())
        except Exception:  # noqa: BLE001
            _CLIENT.append(None)
    return _CLIENT[0]


def _none_answer(text: str):
    return SimpleNamespace(kind="none", text=text, field_id=None, sources=[], stream=None)


def make_services(online: bool = True) -> Services:
    """진짜 모듈을 게으르게 연결한다. helpdesk는 나중에 만들어지므로 없거나 깨져도 대화는 계속된다."""

    def market(seeds: List[str]):
        from . import market as mk
        rep = mk.build(seeds, online=False)       # 저장된 자료 먼저
        if rep is None and online:
            rep = mk.build(seeds, online=True)
        return rep

    def market_error() -> Optional[str]:
        from . import naver_api as api
        if not api.ad_available():
            return "이 앱에 네이버 검색광고 API 키(NAVER_AD_API_KEY·NAVER_AD_SECRET_KEY·NAVER_AD_CUSTOMER_ID)가 없어요"
        return api.last_error()

    def plan(store: dict, mkt, objective: str, days: int):
        import pandas as pd
        from . import planner
        kw = None
        if isinstance(mkt, dict):
            rows = mkt.get("rows") or []
            kw = pd.DataFrame(rows) if rows else None
        elif mkt is not None and hasattr(mkt, "keywords"):
            df = mkt.keywords
            kw = df[df["keyword"].isin(list(getattr(mkt, "recommended", [])))] if len(getattr(mkt, "recommended", [])) else None
        media = store.get("media") or ["meta", "naver"]
        share = 0.5 if len(media) == 2 else (0.0 if media == ["meta"] else 1.0)
        return planner.plan_budget(int(store["budget"]), kw, objective=objective, days=days, naver_share_max=share)

    def help_(question: str, step_id: Optional[str], ctx: dict):
        try:
            from . import helpdesk
        except Exception:  # noqa: BLE001
            return _none_answer("도움말 기능을 아직 불러오지 못했어요.")
        return helpdesk.answer(question, step_id, ctx, client=_client())

    def is_question(text: str) -> bool:
        try:
            from . import helpdesk
            return bool(helpdesk.is_question(text))
        except Exception:  # noqa: BLE001
            return cp.looks_like_question(text)

    def questions(media: List[str]) -> List[dict]:
        from . import intake
        return intake.questions(media)

    def copies(product: str, strengths: str) -> Dict[str, list]:
        from . import copywriter
        return {"meta": copywriter.meta_copies(product, strengths), "naver": copywriter.naver_copies(product, strengths)}

    return Services(market=market, plan=plan, help=help_, questions=questions, copies=copies, is_question=is_question,
                    market_error=market_error)
