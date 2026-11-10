"""PROTOTYPE (버림용) — 챗봇 형태 UI 시안 3가지. 실제 앱(app/main.py)과 상관없음. 고른 뒤 이 파일은 지움.

질문: "① 세팅 흐름(가게 정보 → 결과 → 매체별 세팅 단계)을 챗봇 화면으로 바꾸면 어떤 모양이 좋은가?"
시안 3개를 같은 페이지에서 ?variant=A|B|C 로 바꿔 봄 (아래 가운데 막대의 ← → 버튼).
  A 대화창 하나: 결과·세팅값 카드가 모두 대화 안에 차례로 쌓임
  B 대화 + 오른쪽 결과판: 대화는 짧게, 숫자·격자·세팅 체크리스트는 오른쪽 판에서 계속 갱신
  C 한 번에 한 질문: 맨 위 진행 표시 + 지금 질문 하나만 크게, 지난 답은 칩으로 접힘
숫자는 실제 엔진(CO.solve, 네이버 저장본, ad_setup 세팅값, 세팅 카드)에서. LLM 키 없이 버튼 답변으로 동작.

실행: .venv/bin/streamlit run app/prototype_chat.py
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.engine import NaverCurve  # noqa: E402
from src.engine import ad_setup as AS  # noqa: E402
from src.engine import coach as CO  # noqa: E402
from src.engine import defaults as D  # noqa: E402
from src.engine import montecarlo as MC  # noqa: E402
from src.engine import naver_source as ns  # noqa: E402
from src.engine import setup_rag as SR  # noqa: E402
from src.engine.insights import won  # noqa: E402

st.set_page_config(page_title="PROTOTYPE 챗봇 시안", page_icon="🧪", layout="wide")
ss = st.session_state
VARIANTS = {"A": "대화창 하나", "B": "대화 + 오른쪽 결과판", "C": "한 번에 한 질문"}
BLUE, MUTED = "#4C78A8", "rgba(127,127,127,.35)"
EXAMPLES = {"원두 로스터리": dict(product="원두", price=20_000, profit=7_000, rep="매달(정기)", budget=300_000, kw="원두커피"),
            "단백질 쉐이크": dict(product="단백질 쉐이크", price=79_000, profit=39_500, rep="매달(정기)", budget=500_000, kw="프로틴쉐이크")}
REPS = list(CO.REPURCHASE_PRESETS)
BADGE = {"go": ("해 볼 만해요", "green", ":material/check_circle:"), "small": ("작게 시험", "orange", ":material/error:"),
         "prep": ("지금은 미뤄요", "red", ":material/pause_circle:")}

# ── 공통: 대화 상태 (기록 + 지금 단계). 세 시안이 같은 상태를 다르게 그림 ──────────────
# stage: product → numbers → rep → budget → confirm → result → setup → done
ss.setdefault("p_stage", "product")
ss.setdefault("p_shop", {})
ss.setdefault("p_log", [])        # [(role, text)]  role = bot / me
ss.setdefault("p_pos", 0)         # 세팅 단계 위치
ss.setdefault("p_stuck", None)


def say(role, text):
    ss.p_log.append((role, text))


def go(stage):
    ss.p_stage = stage


def reset():
    for k in ("p_stage", "p_shop", "p_log", "p_pos", "p_stuck"):
        ss.pop(k, None)


QUESTIONS = {"product": "무엇을 파세요? 예시로 먼저 봐도 돼요.",
             "numbers": "1개 팔면 받는 돈과 남는 돈을 알려 주세요. (원가·배송비·수수료를 뺀 금액이 남는 돈)",
             "rep": "한 번 산 손님이 다시 사나요?",
             "budget": "한 달에 광고에 쓸 수 있는 최대 금액은요?",
             "confirm": "이렇게 이해했어요. 맞으면 계산할게요."}


@st.cache_data(show_spinner=False)
def _estimate(kw):
    try:
        return ns.bid_estimate(kw, device=D.NAVER_DEVICE, online=False)
    except Exception:  # noqa: BLE001
        return None


def solve(shop):
    est = _estimate(shop["kw"]) if shop.get("kw") else None
    curve = NaverCurve({shop["kw"]: est}) if est is not None and (est["clicks"] > 0).any() else None
    ans = CO.solve(CO.CoachInputs(shop["price"], shop["profit"], shop["budget"], shop.get("kw", ""), None), curve,
                   CO.repurchase_source(shop["rep"], None))
    plan = AS.build_settings(answer=ans, stores=["스마트스토어"], keyword=shop.get("kw", ""), product=shop["product"],
                             month=CO.today_kst().strftime("%y%m"))
    return ans, plan.for_media("naver") + plan.for_media("meta")


# ── 공통: 답하기 위젯 (지금 단계의 버튼·입력). 시안마다 놓는 자리만 다름 ──────────────
def answer_widgets(key):
    stg, shop = ss.p_stage, ss.p_shop
    if stg == "product":
        cols = st.columns(3)
        for c, name in zip(cols, EXAMPLES):
            if c.button(f"예시: {name}", key=f"{key}_ex_{name}", use_container_width=True):
                ss.p_shop = dict(EXAMPLES[name])
                say("me", f"{name} 예시로 볼게요")
                go("confirm"); st.rerun()
        with st.form(f"{key}_prod", border=False):
            p = st.text_input("상품", placeholder="예: 수제 마카롱", label_visibility="collapsed")
            if st.form_submit_button("보내기") and p:
                shop["product"], shop["kw"] = p, p.replace(" ", "")
                say("me", p); go("numbers"); st.rerun()
    elif stg == "numbers":
        with st.form(f"{key}_num", border=False):
            c1, c2 = st.columns(2)
            price = c1.number_input("받는 돈 (원)", 0, 10_000_000, 20_000, 1_000)
            profit = c2.number_input("남는 돈 (원)", 0, 10_000_000, 7_000, 1_000)
            if profit > price:
                st.caption(":red[남는 돈은 받는 돈보다 작아야 해요. 원가·배송비·수수료를 뺀 금액을 넣어 주세요.]")
            if st.form_submit_button("보내기") and profit <= price and price:
                shop["price"], shop["profit"] = price, profit
                say("me", f"{won(price)}에 팔고 {won(profit)} 남아요"); go("rep"); st.rerun()
    elif stg == "rep":
        cols = st.columns(len(REPS))
        for c, r in zip(cols, REPS):
            if c.button(r, key=f"{key}_rep_{r}", use_container_width=True):
                shop["rep"] = r; say("me", r); go("budget"); st.rerun()
    elif stg == "budget":
        cols = st.columns(4)
        for c, b in zip(cols, (100_000, 300_000, 500_000, 1_000_000)):
            if c.button(won(b), key=f"{key}_b_{b}", use_container_width=True):
                shop["budget"] = b; say("me", f"한 달 {won(b)}까지"); go("confirm"); st.rerun()
    elif stg == "confirm":
        c1, c2 = st.columns(2)
        if c1.button("맞아요, 계산해 주세요", type="primary", key=f"{key}_ok", use_container_width=True):
            say("me", "맞아요"); go("result"); st.rerun()
        if c2.button("처음부터 다시", key=f"{key}_re", use_container_width=True):
            reset(); st.rerun()
    elif stg == "result":
        c1, c2 = st.columns(2)
        if c1.button("세팅 시작", type="primary", key=f"{key}_set", use_container_width=True):
            say("me", "세팅 시작할게요"); go("setup"); st.rerun()
        if c2.button("이번 달은 광고 안 할래요", key=f"{key}_no", use_container_width=True):
            say("me", "이번 달은 광고 안 할래요"); go("done"); st.rerun()
    elif stg == "setup":
        _, steps = solve(shop)
        step = steps[ss.p_pos]
        c1, c2 = st.columns(2)
        if c1.button("했어요 →", type="primary", key=f"{key}_done_{ss.p_pos}", use_container_width=True):
            say("me", f"{step.title} 했어요")
            ss.p_stuck = None
            if ss.p_pos + 1 >= len(steps):
                go("done")
            else:
                ss.p_pos += 1
            st.rerun()
        if c2.button("여기서 막혔어요", key=f"{key}_stuck_{ss.p_pos}", use_container_width=True):
            ss.p_stuck = ss.p_pos; st.rerun()
    elif stg == "done":
        if st.button("처음부터 다시", key=f"{key}_again"):
            reset(); st.rerun()


# ── 공통: 카드 (확인 · 결과 · 세팅 단계). 시안마다 대화 안 / 옆 판 / 가운데에 놓음 ──────────
def confirm_card():
    s = ss.p_shop
    with st.container(border=True):
        st.markdown(f"**{s['product']}** · 받는 돈 {won(s['price'])} · 남는 돈 {won(s['profit'])}  \n"
                    f"재구매 **{s['rep']}** · 한 달 최대 **{won(s['budget'])}** · 검색어 '{s.get('kw', '')}'")


def grid(wins, size=12):
    cells = "".join(f"<div style='width:{size}px;height:{size}px;border-radius:3px;background:{BLUE if i < wins else MUTED}'></div>"
                    for i in range(100))
    return f"<div style='display:grid;grid-template-columns:repeat(10,{size}px);gap:3px;margin:6px 0'>{cells}</div>"


def result_card(compact=False):
    ans, _ = solve(ss.p_shop)
    mc, act = ans.mc, MC.action(ans.mc["wins"])
    with st.container(border=True):
        t, c, i = BADGE[act]
        st.badge(t, color=c, icon=i)
        st.markdown(f"**100번 해 보면 1년 동안 {mc['wins']}번 남아요** · 시험 예산 {won(ans.budget)}")
        st.markdown(grid(mc["wins"], 10 if compact else 12), unsafe_allow_html=True)
        st.caption(f"1년 동안 남는 돈 가운데값 {won(mc['p50'])} · 범위 {won(mc['p10'])} ~ {won(mc['p90'])}")
        st.markdown(f"**네이버 {won(ans.split.naver_spend)} · 메타 {won(ans.split.meta.spend)}**  \n{ans.split_reason(ss.p_shop.get('kw', ''))}")


def step_card(pos=None):
    _, steps = solve(ss.p_shop)
    pos = ss.p_pos if pos is None else pos
    step = steps[pos]
    with st.container(border=True):
        st.caption(f"{'네이버' if step.media == 'naver' else '메타'} {pos + 1}/{len(steps)} · 광고 관리자에서: {step.where}")
        st.markdown(f"**{step.title}**")
        for it in step.items:
            if it.value in ("", None, []):
                continue
            st.markdown(f"{it.source} {it.label}")
            st.code(AS.show(it.value).replace(",", "") if isinstance(it.value, (int, float)) else AS.show(it.value), language=None)
        if ss.p_stuck == pos:
            card = next((SR.by_id(c) for c in step.cards if SR.by_id(c)), None)
            if card:
                body = card.body if len(card.body) <= 260 else card.body[:260].rsplit(" ", 1)[0] + "…"
                st.info(f"**{card.title}** {card.check}\n\n{body}", icon=":material/menu_book:")
            else:
                st.info("이 단계는 자료에 없어요. 광고 관리자 도움말을 열어 보세요.", icon=":material/help:")


def bot_text():
    """지금 단계에서 봇이 하는 말 (질문 또는 안내)."""
    stg = ss.p_stage
    if stg in QUESTIONS:
        return QUESTIONS[stg]
    if stg == "result":
        return "계산했어요. 이대로 세팅을 시작할까요?"
    if stg == "setup":
        return "광고 관리자를 열고, 아래 값을 칸에 그대로 붙여 넣으세요. 다 하면 '했어요'."
    return "세팅값을 다 모았어요. 광고를 켜고 14일 뒤에 리포트를 올려 주세요."


# ── 시안 A: 대화창 하나 ─────────────────────────────────────────
def variant_a():
    st.markdown("### 광고 코치와 대화하기")
    with st.chat_message("assistant"):
        st.markdown(QUESTIONS["product"])
    for role, text in ss.p_log:
        with st.chat_message("user" if role == "me" else "assistant"):
            st.markdown(text)
    stg = ss.p_stage
    with st.chat_message("assistant"):
        if stg != "product":
            st.markdown(bot_text())
        if stg in ("confirm",):
            confirm_card()
        if stg in ("result", "setup", "done") and ss.p_shop:
            if stg == "result":
                result_card()
            if stg == "setup":
                step_card()
        answer_widgets("A")


# ── 시안 B: 대화 + 오른쪽 결과판 ────────────────────────────────────
def variant_b():
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown("### 대화")
        with st.container(height=560, border=True):
            with st.chat_message("assistant"):
                st.markdown(QUESTIONS["product"])
            for role, text in ss.p_log:
                with st.chat_message("user" if role == "me" else "assistant"):
                    st.markdown(text)
            if ss.p_stage != "product":
                with st.chat_message("assistant"):
                    st.markdown(bot_text())
        answer_widgets("B")
    with right:
        st.markdown("### 내 광고 계획")
        s = ss.p_shop
        if not s:
            st.caption("대화가 진행되면 여기에 숫자와 세팅값이 채워져요.")
            return
        st.markdown(" · ".join(f"**{v}**" for v in (s.get("product"), s.get("price") and won(s["price"]), s.get("rep"),
                                                    s.get("budget") and won(s["budget"])) if v))
        if ss.p_stage in ("result", "setup", "done"):
            result_card(compact=True)
            _, steps = solve(s)
            st.markdown("**세팅 체크리스트**")
            for i, stp in enumerate(steps):
                mark = "✓" if (ss.p_stage == "done" or i < ss.p_pos) and ss.p_stage != "result" else ("●" if i == ss.p_pos and ss.p_stage == "setup" else "○")
                st.markdown(f"{mark} {'네이버' if stp.media == 'naver' else '메타'} · {stp.title}")
            if ss.p_stage == "setup":
                step_card()


# ── 시안 C: 한 번에 한 질문 ────────────────────────────────────────
def variant_c():
    order = ["product", "numbers", "rep", "budget", "confirm", "result", "setup", "done"]
    i = order.index(ss.p_stage)
    st.progress((i + 1) / len(order), text=f"① 세팅 · {i + 1}/{len(order)}")
    s = ss.p_shop
    chips = [v for v in (s.get("product"), s.get("price") and f"{won(s['price'])}/{won(s.get('profit', 0))}", s.get("rep"),
                         s.get("budget") and f"월 {won(s['budget'])}") if v]
    if chips:
        st.pills("지금까지 답", chips, key=f"chips_{len(chips)}", disabled=True)
    _, mid, _ = st.columns([1, 3, 1])
    with mid:
        st.markdown(f"## {bot_text()}")
        if ss.p_stage == "confirm":
            confirm_card()
        if ss.p_stage == "result":
            result_card()
        if ss.p_stage == "setup":
            step_card()
        answer_widgets("C")
        if ss.p_log:
            with st.expander(f"지난 대화 {len(ss.p_log)}개"):
                for role, text in ss.p_log:
                    st.markdown(("👤 " if role == "me" else "🤖 ") + text)


# ── 시안 바꾸기 막대 (아래 가운데, 시안의 일부 아님) ─────────────────────────
v = st.query_params.get("variant", "A")
v = v if v in VARIANTS else "A"
st.markdown("""<style>
[data-testid="stBaseButton-primary"] {background-color: #4C78A8 !important; border-color: #4C78A8 !important; color: #fff !important;}
.st-key-proto_bar {position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%); z-index: 1000; width: auto;
  background: #111; color: #fff; border-radius: 999px; padding: 4px 10px; box-shadow: 0 4px 14px rgba(0,0,0,.35);}
.st-key-proto_bar p {color: #fff !important; margin: 0; white-space: nowrap;}
.st-key-proto_bar button {background: transparent !important; color: #fff !important; border: none !important;}
</style>""", unsafe_allow_html=True)
keys = list(VARIANTS)
with st.container(key="proto_bar", horizontal=True, vertical_alignment="center"):
    if st.button("←", key="pv_prev"):
        st.query_params["variant"] = keys[(keys.index(v) - 1) % len(keys)]; st.rerun()
    st.markdown(f"**PROTOTYPE {v}** ({VARIANTS[v]})")
    if st.button("→", key="pv_next"):
        st.query_params["variant"] = keys[(keys.index(v) + 1) % len(keys)]; st.rerun()

st.caption("🧪 PROTOTYPE · 버림용 시안 · 숫자는 실제 엔진 · 대화 상태는 시안끼리 같이 씀 (같은 대화를 다른 모양으로 비교)")
{"A": variant_a, "B": variant_b, "C": variant_c}[v]()
