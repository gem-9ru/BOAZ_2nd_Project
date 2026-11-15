"""앱 공용 상태와 계산 (화면 부품은 ui.py, 화면은 home·setup·run·diagnose.py).

- 화면 사이에 나눠 쓰는 값은 모두 st.session_state에 둔다.
  store(가게 정보) · media · answers · budget_plan이 곧 '계획'이고, 세팅 단계가 끝나면 Plan으로 묶인다.
- 이 파일의 함수 대부분은 Streamlit 없이도 돌아가는 순수 함수라 테스트하기 쉽다.
"""
import datetime as dt
from dataclasses import asdict
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from v2.engine import conversation, copywriter, intake, plan_io, planner, specs, tracking

# ── 예시 (소연베이크) ───────────────────────────────────────
DEMO_SEEDS = ["휘낭시에", "쿠키선물세트", "답례품쿠키", "디저트선물", "수제쿠키"]
DEMO_STORE = {
    "name": "소연베이크", "product": "수제 구움과자", "product_slug": "soyeon", "store_type": "smartstore",
    "price": 26000, "margin_per_order": 8000, "budget": 300000, "month": "11월", "seeds": DEMO_SEEDS,
}
DEMO_STRENGTHS = "국내산 버터로 매일 굽는 수제 구움과자, 답례·선물용 소포장"
DEMO_ANSWERS = {
    "meta.pre.ig_account": "soyeonbake",
    "meta.ad.website_url": "https://smartstore.naver.com/soyeonbake/products/1000000001",
}
DEMO_START = dt.date(2026, 11, 16)    # 가상 데이터의 광고 기간
DEMO_END = dt.date(2026, 12, 15)

CASE_NAMES = {"C1": "추천 경로", "C2": "플랫폼 기본값", "C3": "좁게·길게 인지도", "C4": "네이버 몰빵",
              "C0": "광고 안 함", "C1b": "개선 사이클"}
MODE_NAMES = {"sim": "가상 실제", "forecast": "추천 예측", "real": "실제"}

# 대화 단계(가게 → 확인 → 손님 → 예산 → 세팅 질문) 다음이 세팅값 시트. setup_step은 지금 대화 단계 번호.
STEPS = list(conversation.STAGES) + ["세팅값 시트"]
LAST_STEP = len(STEPS) - 1
# 예산·예측 단계에서 정하므로 질문 목록에서는 뺀다 (같은 걸 두 번 묻지 않음)
ASKED_IN_BUDGET = ("meta.campaign.objective", "meta.adset.end_date")
STORE_TYPES = {"스마트스토어": "smartstore", "자사몰": "own"}
GRADES = "A 실측 · B 매체 추산 · C 공개 자료 · D 우리 가정"


# ── 세션 ───────────────────────────────────────────────────

def _defaults() -> Dict[str, object]:
    return {
        "store": {"name": "", "product": "", "product_slug": "", "store_type": "smartstore", "price": 20000,
                  "margin_per_order": 7000, "budget": 300000, "month": "{}월".format(dt.date.today().month),
                  "seeds": []},
        "media": ["meta", "naver"], "answers": {}, "budget_plan": None, "market": None,
        "setup_step": 0, "month_index": 1, "history": [], "created": "",
        "chat": None, "chat_pending": None, "is_demo": False, "ad_start": None, "run_checks": {},
        "sheet_checked": [], "diag_done": False,
    }


def init() -> None:
    """처음 한 번만 기본값을 채운다 (이미 있는 값은 건드리지 않음)."""
    for k, v in _defaults().items():
        if k not in st.session_state:
            st.session_state[k] = v


_WIDGET_PREFIXES = ("w_", "chat_text", "chip_", "chk_", "sheet_media", "sheet_editor",
                    "diag_case", "diag_mode", "diag_period")


def clear_widgets() -> None:
    """입력칸이 기억하던 값을 지운다. 계획을 통째로 바꿀 때(예시·처음부터·다음 달) 칸이 옛 값을 붙들지 않게."""
    for k in [k for k in st.session_state if isinstance(k, str) and k.startswith(_WIDGET_PREFIXES)]:
        del st.session_state[k]


def reset() -> None:
    """모든 입력을 지우고 처음 상태로."""
    clear_widgets()
    for k, v in _defaults().items():
        st.session_state[k] = v


def setup_done() -> bool:
    return st.session_state.get("setup_step", 0) >= LAST_STEP and st.session_state.get("budget_plan") is not None


def go_step(step: int) -> None:
    st.session_state["setup_step"] = max(0, min(LAST_STEP, step))


# ── 챗봇 세팅 (대화 상태는 st.session_state["chat"], 엔진은 v2/engine/conversation.py) ──

_SERVICES: List[object] = []   # 테스트는 set_services로 가짜를 넣는다


def set_services(sv: Optional[conversation.Services]) -> None:
    """대화에 쓸 서비스를 바꿔 끼운다 (None이면 진짜로 되돌림)."""
    _SERVICES.clear()
    if sv is not None:
        _SERVICES.append(sv)


def services() -> conversation.Services:
    """대화 엔진이 쓰는 서비스. 내 손님 찾기 결과 원본(연령·월별 그래프용)은 session_state["market"]에 따로 둔다."""
    if _SERVICES:
        return _SERVICES[0]
    real = conversation.make_services(online=True)
    inner = real.market

    def market(seeds):
        report = inner(seeds)
        st.session_state["market"] = report
        return report

    inner_plan = real.plan

    def plan(store, mkt, objective, days):
        kept = _kept_plan((st.session_state.get("chat") or {}).get("loaded"), store, objective, days)
        if kept is not None:
            return kept
        p = inner_plan(store, mkt, objective, days)
        return _fix_notes(p, store)

    real.market = market
    real.plan = plan
    _SERVICES.append(real)
    return real


def _kept_plan(loaded: Optional[dict], store: dict, objective: str, days: int) -> Optional[dict]:
    """불러온 계획의 예산은 광고비·목표·기간·검색 단어를 바꾸지 않았으면 그대로 둔다 (진단이 바꾼 하루 예산을 지키려고)."""
    if not loaded:
        return None
    same = (int(store.get("budget") or 0) == loaded["budget"] and objective == loaded["objective"]
            and int(days) == loaded["days"] and [str(w) for w in (store.get("seeds") or [])] == loaded["picked"])
    return dict(loaded["plan"]) if same else None


def _fix_notes(plan, store: dict):
    """검색 단어는 골랐는데 검색량 표가 없어 다시 계산한 경우, '키워드를 아직 고르지 않아서'라는 틀린 문장을 바로잡는다."""
    notes = getattr(plan, "notes", None)
    if notes is None or not store.get("seeds") or getattr(plan, "naver_cap_month", 0) is not None:
        return plan
    plan.notes = ["검색어는 골랐지만 검색량 자료가 없어서, 네이버에는 예산의 절반까지만 잡았어요." if "아직 고르지 않아서" in n else n
                  for n in notes]
    return plan


def start_chat() -> None:
    """새 대화를 시작한다 (첫 질문까지)."""
    s = st.session_state
    s["chat"] = conversation.start(list(s["media"]), s["store"].get("month"))
    s["chat_pending"] = None
    s["market"] = None


def sync_from_chat() -> None:
    """대화 상태 → 계획(store·answers·budget_plan). 대화가 끝나면 세팅값 시트로, 아니면 지금 대화 단계로."""
    s = st.session_state
    cs = s.get("chat")
    if cs is None:
        return
    if cs["phase"] == "done" and cs.get("plan"):
        store = conversation.to_store(cs)
        store["keywords"] = list(store.get("seeds") or [])
        s["store"] = store
        s["media"] = list(cs["media"])
        s["answers"] = conversation.to_answers(cs)
        s["budget_plan"] = dict(cs["plan"])
        s["sheet_checked"] = []
        go_step(LAST_STEP)
    else:
        go_step(min(conversation.PHASE_STAGE.get(cs["phase"], 0), LAST_STEP - 1))


def _saved_rows(seeds: List[str]) -> List[dict]:
    """저장해 둔 검색량 표(캐시)가 있으면 고른 단어의 행을 되살린다. 없으면 빈 목록."""
    if not seeds:
        return []
    try:
        from v2.engine import market
        report = market.build(list(seeds), online=False)
        return conversation._rows(report, list(seeds)) if report is not None else []
    except Exception:  # noqa: BLE001  저장본이 없어도 대화는 열려야 함
        return []


def restore_chat() -> None:
    """불러온 계획(파일·다음 달)으로 '끝난 대화'를 만든다. 지난 답 고치기를 쓰려고. 가게 숫자·답·예산은 계획 그대로."""
    s = st.session_state
    store, media = s["store"], list(s["media"])
    cs = conversation.start(media, store.get("month"))
    seeds = [str(x) for x in (store.get("seeds") or [])]
    cs["store"] = {"name": store.get("name", ""), "product": store.get("product", ""), "price": store.get("price", 0),
                   "margin": store.get("margin_per_order", 0), "budget": store.get("budget", 0),
                   "store_type": store.get("store_type", "smartstore"), "slug": store.get("product_slug", "")}
    cs["market"] = {"seeds": list(store.get("search_words") or seeds), "recommended": seeds, "picked": seeds,
                    "negatives": list(store.get("negatives") or []), "headline": "",
                    "audience_hint": store.get("audience_hint"), "groups": [], "rows": []}
    cs["plan"] = dict(s["budget_plan"] or {})
    cs["objective"] = store.get("objective") or cs["plan"].get("objective") or "트래픽"
    cs["days"] = int(store.get("days") or cs["plan"].get("days") or 14)
    cs["market"]["rows"] = _saved_rows(seeds)
    cs["loaded"] = {"plan": dict(cs["plan"]), "budget": int(store.get("budget") or 0), "objective": cs["objective"],
                    "days": cs["days"], "picked": list(seeds)}
    cs["answers"] = dict(s["answers"])
    cs["phase"], cs["step"], cs["confirmed"], cs["ask_intro"] = "done", "done", True, True
    cs["turns"] = []
    conversation._say(cs, "지난 계획을 불러왔어요. 고치고 싶은 답이 있으면 '지난 답 고치기'를 눌러 골라 주세요. 모르는 게 있으면 물어보셔도 돼요.")
    s["chat"], s["chat_pending"] = cs, None


# ── 계산 (순수 함수) ───────────────────────────────────────

def audience_hint(report) -> Optional[str]:
    """시장 조사에서 나온 첫 손님 정보 → 메타 '연령·성별' 칸 제안 (예: '30대 여성 중심 (넓게 노출)')."""
    if report is None or not report.audiences:
        return None
    aud = next(iter(report.audiences.values()))
    ages = {a: s for a, s in aud["ages"].items() if s >= 0.15}
    if not ages:
        return None
    idx = aud.get("index", {})
    best = max(ages, key=lambda a: (idx.get(a, 0), ages[a]))
    sex = "여성 " if aud["female"] >= 0.6 else "남성 " if aud["female"] <= 0.4 else ""
    return "{}대 {}중심 (넓게 노출)".format(best, sex)


def kw_frame(report, chosen: List[str]) -> Optional[pd.DataFrame]:
    """고른 키워드만 남긴 표 (네이버 상한 계산용). 고른 게 없으면 None."""
    if report is None or not chosen:
        return None
    df = report.keywords
    df = df[df["keyword"].isin(chosen)]
    return df if len(df) else None


def objective_options() -> Tuple[List[str], Dict[str, str]]:
    f = specs.all_fields()["meta.campaign.objective"]
    return list(f["options"]), dict(f["map"])


def days_options() -> List[str]:
    return list(specs.all_fields()["meta.adset.end_date"]["options"])


def compute_budget(store: dict, media: List[str], report, objective: str, days: int,
                   naver_share_max: float = 0.5) -> planner.BudgetPlan:
    """고른 매체에 맞춰 예산을 나눈다. 네이버만 고르면 메타 몫은 0, 메타만 고르면 네이버 몫은 0."""
    chosen = store.get("keywords") or []
    share = naver_share_max
    if "naver" not in media:
        share = 0.0
    elif "meta" not in media:
        share = 1.0
    return planner.plan_budget(int(store["budget"]), kw_frame(report, chosen), objective=objective,
                               days=days, naver_share_max=share)


def expected_orders(bp: dict) -> Tuple[float, float]:
    """예상 클릭 × 구매율 가정(근거 D) = 예상 주문 (낮게, 높게). 인지도 목표는 메타 클릭이 없다."""
    cvr = specs.assumptions()["store"]["cvr"]
    meta_clicks = float(bp.get("meta_forecast", {}).get("link_clicks", 0) or 0)
    naver_clicks = float(bp.get("naver_forecast", {}).get("clicks", 0) or 0)
    naver = naver_clicks * cvr["naver_ad"]["value"]
    return (meta_clicks * cvr["meta_feed"]["low"] + naver, meta_clicks * cvr["meta_feed"]["high"] + naver)


def make_ctx(store: dict, media: List[str], bp: Optional[dict], report=None) -> intake.SetupContext:
    bp = bp or {}
    slug = store.get("product_slug") or tracking.slugify(store.get("name"), fallback=tracking.slugify(store.get("product"), "shop"))
    return intake.SetupContext(
        product=str(store.get("product") or store.get("name") or "상품"), product_slug=slug,
        store_type=str(store.get("store_type") or "smartstore"), month=str(store.get("month") or ""),
        media=list(media), meta_daily=int(bp.get("meta_daily") or 0), naver_daily=int(bp.get("naver_daily") or 0),
        naver_bid=int(bp.get("naver_bid") or 0), keywords=list(store.get("keywords") or []),
        negatives=list(store.get("negatives") or []),
        audience_hint=store.get("audience_hint") or audience_hint(report))


def asked_questions(media: List[str]) -> List[dict]:
    """사장님께 한 번에 하나씩 물을 질문 (목표·기간은 예산 단계에서 이미 정함)."""
    return [q for q in intake.questions(media) if q["id"] not in ASKED_IN_BUDGET]


def make_copies(product: str, strengths: str, live: bool) -> Dict[str, list]:
    """메타·네이버 문구 3개씩. live=False면 항상 문장 틀 (키 없이도 같은 결과)."""
    client = None if live else False
    return {"meta": copywriter.meta_copies(product, strengths, 3, client=client),
            "naver": copywriter.naver_copies(product, strengths, 3, client=client)}


def default_answers(qs: List[dict], product: str, demo: bool) -> Dict[str, object]:
    """질문마다 권장 답(기본값). 예시에서는 비어 있는 칸(계정·주소·문구)도 예시 값으로 채운다."""
    out: Dict[str, object] = {}
    for q in qs:
        if q["kind"] == "llm":
            if demo:
                c = make_copies(product, DEMO_STRENGTHS, False)
                out[q["id"]] = c["meta"][0]
                out["naver.ad.copy"] = c["naver"][0]
            continue
        v = DEMO_ANSWERS.get(q["id"]) if demo else None
        out[q["id"]] = v if v is not None else q["default"]
    return out


def build_plan() -> Optional[plan_io.Plan]:
    """세션 값을 Plan으로 묶는다 (세팅이 아직 안 끝났으면 None)."""
    if not setup_done():
        return None
    s = st.session_state
    return plan_io.Plan(
        month_index=int(s["month_index"]), created=s["created"] or dt.date.today().isoformat(),
        store=dict(s["store"]), media=list(s["media"]), answers=dict(s["answers"]),
        budget_plan=dict(s["budget_plan"]), history=list(s["history"]))


def load_plan(plan: plan_io.Plan, demo: bool = False) -> None:
    """계획(파일에서 읽었거나 다음 달로 넘긴 것)을 화면 상태로 옮긴다. 세팅값 시트 단계로 이동."""
    s = st.session_state
    clear_widgets()
    s["store"] = dict(plan.store)
    s["media"] = list(plan.media)
    s["answers"] = dict(plan.answers)
    s["budget_plan"] = dict(plan.budget_plan)
    s["month_index"] = plan.month_index
    s["history"] = list(plan.history)
    s["created"] = plan.created
    s["is_demo"] = demo
    s["sheet_checked"] = []
    s["run_checks"] = {}
    s["diag_done"] = False
    s["chat"], s["chat_pending"] = None, None
    go_step(LAST_STEP)


def load_demo() -> None:
    """예시(소연베이크)로 시작: 가게 정보를 채워 '이렇게 이해했어요' 확인 카드까지 온 대화."""
    reset()
    s = st.session_state
    s["store"] = dict(DEMO_STORE, seeds=list(DEMO_SEEDS))
    s["is_demo"] = True
    s["chat"] = conversation.demo_state(services())
    sync_from_chat()


def _load_demo_store() -> None:
    """예시 가게 정보와 저장된 손님 조사로 채운 계획 상태 (대화 없이)."""
    from v2.engine import market
    reset()
    s = st.session_state
    s["store"] = dict(DEMO_STORE, seeds=list(DEMO_SEEDS))
    s["is_demo"] = True
    try:
        report = market.build(list(DEMO_SEEDS), online=False)
    except Exception:  # noqa: BLE001  저장본이 없어도 화면은 열려야 함 (단어만 채워짐)
        report = None
    s["market"] = report
    if report is not None:
        s["store"]["keywords"], s["store"]["negatives"] = list(report.recommended), list(report.negatives)
        s["store"]["audience_hint"] = audience_hint(report)
    go_step(LAST_STEP)


def load_demo_plan() -> None:
    """예시 계획을 끝까지 채워서 불러온다 (③ 진단을 바로 해 볼 때). 키 없이도 같은 결과."""
    from v2.engine import market
    _load_demo_store()
    s = st.session_state
    store, media = s["store"], s["media"]
    report = market.build(store["seeds"], online=False)
    s["market"] = report
    if report is not None:
        store["keywords"], store["negatives"] = list(report.recommended), list(report.negatives)
    objective_label = objective_options()[0][0]
    store["objective"], store["days"] = "트래픽", 14
    bp = compute_budget(store, media, report, "트래픽", 14)
    s["budget_plan"] = asdict(bp)
    qs = asked_questions(media)
    answers = default_answers(qs, store["product"], True)
    answers["meta.campaign.objective"] = objective_label
    answers["meta.adset.end_date"] = "14일"
    s["answers"] = answers
    store["audience_hint"] = audience_hint(report)


def start_next_month(new_plan: plan_io.Plan) -> None:
    load_plan(new_plan, demo=st.session_state.get("is_demo", False))


# ── 내려받기 파일 ──────────────────────────────────────────

def sheet_csv(df: pd.DataFrame) -> bytes:
    """엑셀에서 한글이 안 깨지도록 BOM을 붙인 CSV."""
    return df.to_csv(index=False).encode("utf-8-sig")


def sheet_excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="세팅값")
        ws = w.sheets["세팅값"]
        for col, width in zip("ABCDEFGH", (8, 14, 26, 28, 40, 12, 60, 8)):
            ws.column_dimensions[col].width = width
    return buf.getvalue()


def plan_file_name(plan: plan_io.Plan) -> str:
    slug = tracking.slugify(plan.store.get("product_slug") or plan.store.get("name"), "plan")
    return "{}_{}월차_계획.json".format(slug, plan.month_index)
