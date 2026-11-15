"""① 세팅: 가게 정보 → 내 손님 찾기 → 예산·예측 → 질문(한 번에 하나) → 세팅값 시트."""
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import datetime as dt  # noqa: E402

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from v2.app import data, state, ui  # noqa: E402
from v2.engine import intake, plan_io, tracking  # noqa: E402

MEDIA_NAMES = {"meta": "메타 (인스타그램·페이스북)", "naver": "네이버 검색광고"}
MONTHS = ["{}월".format(m) for m in range(1, 13)]


def _s() -> dict:
    return st.session_state


# ───────────────────────── 맨 위: 단계 이동 ─────────────────────────

def _jump() -> None:
    """단계 이동 막대에서 고른 단계로 (이미 지나온 단계까지만)."""
    label = _s().get("setup_nav")
    if label in state.STEPS:
        state.go_step(state.STEPS.index(label))


def sub_stepper(step: int) -> None:
    reached = max(_s()["setup_max"], step)
    _s()["setup_nav"] = state.STEPS[step]
    st.progress((step + 1) / len(state.STEPS), text="{}/{} · {}".format(step + 1, len(state.STEPS), state.STEPS[step]))
    st.radio("단계 이동", state.STEPS[:reached + 1], key="setup_nav", on_change=_jump, horizontal=True,
             label_visibility="collapsed")
    if reached < state.LAST_STEP:
        st.caption("다음 단계는 지금 단계를 마치면 열려요.")


# ───────────────────────── 1. 가게 정보 ─────────────────────────

def _store_values() -> dict:
    g = _s().get
    return {"name": (g("w_name") or "").strip(), "product": (g("w_product") or "").strip(),
            "price": g("w_price"), "margin_per_order": g("w_margin"), "budget": g("w_budget"),
            "month": g("w_month"), "store_type": state.STORE_TYPES.get(g("w_type"), "smartstore"),
            "slug": g("w_slug") or ""}


def store_errors(v: dict) -> dict:
    """칸 이름 → 어떻게 고치면 되는지."""
    e = {}
    if not v["name"]:
        e["name"] = "가게 이름을 적어 주세요. 예: 소연베이크"
    if not v["product"]:
        e["product"] = "무엇을 파는지 한 마디로 적어 주세요. 예: 수제 구움과자"
    if not v["budget"] or v["budget"] < 10000:
        e["budget"] = "한 달 광고비는 1만 원 이상으로 적어 주세요. 처음이라면 10만~30만 원이 무난해요."
    if v["margin_per_order"] is not None and v["price"] and v["margin_per_order"] >= v["price"]:
        e["margin"] = "남는 돈이 판매가보다 클 수 없어요. 판매가에서 재료비·포장비·수수료·배송비를 뺀 금액을 적어 주세요."
    return e


def _store_next() -> None:
    v = _store_values()
    if store_errors(v):
        _s()["store_tried"] = True
        return
    s = _s()["store"]
    slug = tracking.slugify(v["slug"] or s.get("product_slug"),
                            fallback=tracking.slugify(v["name"], fallback=tracking.slugify(v["product"], "shop")))
    s.update(name=v["name"], product=v["product"], price=v["price"], margin_per_order=v["margin_per_order"],
             budget=int(v["budget"]), month=v["month"], store_type=v["store_type"], product_slug=slug)
    _s()["store_tried"] = False
    state.go_step(1)


def step_store() -> None:
    s = _s()["store"]
    st.markdown("#### 가게 정보")
    st.caption("딱 필요한 것만 물어봐요. 모두 나중에 바꿀 수 있어요.")
    tried = _s().get("store_tried", False)
    types = list(state.STORE_TYPES)
    ui.init_widget("w_name", s.get("name", ""))
    ui.init_widget("w_product", s.get("product", ""))
    ui.init_widget("w_type", next((k for k in types if state.STORE_TYPES[k] == s.get("store_type", "smartstore")), types[0]))
    ui.init_widget("w_price", int(s.get("price") or 0))
    ui.init_widget("w_margin", int(s.get("margin_per_order") or 0))
    ui.init_widget("w_budget", int(s.get("budget") or 0))
    ui.init_widget("w_month", s["month"] if s.get("month") in MONTHS else MONTHS[0])
    ui.init_widget("w_slug", s.get("product_slug", ""))
    errs = store_errors(_store_values()) if "w_name" in _s() else {}

    def show(key: str) -> None:
        if tried and key in errs:
            st.error(errs[key])

    st.text_input("가게 이름", key="w_name", placeholder="예: 소연베이크")
    show("name")
    st.text_input("무엇을 파세요?", key="w_product", placeholder="예: 수제 구움과자")
    show("product")
    st.radio("판매하는 곳", types, key="w_type", horizontal=True)
    c1, c2, c3 = st.columns(3)
    c1.number_input("대표 상품 판매가 (원)", min_value=0, step=1000, key="w_price")
    c2.number_input("한 개 팔면 남는 돈 (원)", min_value=0, step=500, key="w_margin",
                    help="판매가에서 재료비·포장비·수수료·배송비를 뺀 금액이에요. 이 숫자가 '손님 1명에게 쓸 수 있는 광고비 한도'가 돼요.")
    c3.number_input("한 달 광고비 (원)", min_value=0, step=10000, key="w_budget")
    with c2:
        show("margin")
    with c3:
        show("budget")
    st.caption("모르겠다면 남는 돈은 판매가의 30~40%, 광고비는 10만~30만 원으로 시작해도 돼요.")
    st.selectbox("광고를 시작하는 달", MONTHS, key="w_month")
    with st.expander("고급: 링크 꼬리표에 쓸 영문 이름"):
        st.text_input("영문 소문자·숫자·밑줄만", key="w_slug",
                      help="비워 두면 자동으로 만들어요. 광고 결과를 스토어 통계에서 구분하는 이름이에요.")
    st.button("다음: 내 손님 찾기", type="primary", on_click=_store_next, key="store_next", icon=":material/arrow_forward:")


# ───────────────────────── 2. 내 손님 찾기 ─────────────────────────

def parse_seeds(text: str) -> list:
    return [x.strip() for x in (text or "").replace("\n", ",").split(",") if x.strip()][:10]


def _fill_demo_seeds() -> None:
    _s()["w_seeds"] = ", ".join(state.DEMO_SEEDS)


def age_chart(aud: dict) -> go.Figure:
    ages = aud["ages"]
    idx = aud.get("index", {})
    labels = ["{}대".format(a) for a in ages]
    fig = go.Figure(go.Bar(x=labels, y=[v * 100 for v in ages.values()],
                           text=["{:.0f}%\n(분야 평균의 {:g}배)".format(v * 100, idx.get(a, 0)) if idx.get(a) else "{:.0f}%".format(v * 100)
                                 for a, v in ages.items()], textposition="outside", marker_color="#4C78A8"))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="비중 (%)", showlegend=False)
    return fig


def month_chart(aud: dict) -> go.Figure:
    m = aud.get("monthly") or {}
    fig = go.Figure(go.Scatter(x=list(m), y=list(m.values()), mode="lines+markers", line=dict(color="#4C78A8")))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="검색 관심도(상대값)", showlegend=False)
    return fig


def _clear_picks() -> None:
    """검색어 고르기 칸의 기억을 지운다 (새로 찾으면 추천 검색어부터 다시 보이게)."""
    for k in [k for k in _s() if str(k).startswith(("kw_use_", "kw_neg_"))]:
        del _s()[k]


def _use_saved_example() -> None:
    """실시간 조회가 안 될 때: 토글을 끄고 예시 단어의 저장본으로 바로 채운다."""
    _s()["use_live"] = False
    _s()["market_error"] = None
    _s()["w_seeds"] = ", ".join(state.DEMO_SEEDS)
    seeds = list(state.DEMO_SEEDS)
    report, _ = data.market_report(tuple(seeds), False)
    st_ = _s()["store"]
    st_["seeds"] = seeds
    _clear_picks()
    _s()["market"] = report
    if report is not None:
        st_["keywords"], st_["negatives"] = list(report.recommended), list(report.negatives)
        st_["audience_hint"] = state.audience_hint(report)


def _skip_market() -> None:
    _s()["store"].update(keywords=[], negatives=[])
    _s()["market"] = None
    state.go_step(2)


def _market_next() -> None:
    state.go_step(2)


@st.fragment
def keyword_picker(report) -> None:
    """검색어 고르기 (이 부분만 다시 그려서 화면이 깜빡이지 않게)."""
    s = _s()["store"]
    uid = "_".join(report.seeds)
    allk = report.keywords["keyword"].tolist()
    use = [k for k in allk if k not in set(report.negatives)]
    chosen = [k for k in (s.get("keywords") or report.recommended) if k in allk]
    neg = [k for k in (s.get("negatives") or report.negatives) if k in allk]
    ui.init_widget("kw_use_" + uid, chosen)
    ui.init_widget("kw_neg_" + uid, neg)
    s["keywords"] = st.multiselect("광고에 쓸 검색어", use + [k for k in allk if k not in use],
                                   key="kw_use_" + uid, help="사러 온 사람이 찾는 단어만 골랐어요. 빼고 싶은 건 지워 주세요.")
    s["negatives"] = st.multiselect("제외할 검색어 (이 말로 들어오면 광고를 보여 주지 않아요)", allk,
                                    key="kw_neg_" + uid, help="'만들기'처럼 사려는 게 아니라 배우려는 사람, 다른 지역 매장을 찾는 사람이에요.")


def step_market() -> None:
    s = _s()["store"]
    st.markdown("#### 내 손님 찾기")
    st.caption("상품을 나타내는 단어를 적으면, 사람들이 어떤 말로 찾는지와 누가 찾는지 알려 드려요.")
    ui.init_widget("w_seeds", ", ".join(s.get("seeds") or []))
    ui.init_widget("use_live", False)
    st.text_input("상품 단어 (쉼표로 구분)", key="w_seeds",
                  placeholder="예: 휘낭시에, 쿠키선물세트, 답례품쿠키")
    c1, c2 = st.columns([1, 3])
    go_find = c1.button("내 손님 찾기", type="primary", key="market_find", icon=":material/search:")
    c2.toggle("실시간으로 네이버에 물어보기 (키가 있을 때)", key="use_live",
              help="끄면 저장된 예시 데이터만 써요. 시연이나 키가 없을 때는 꺼 두세요.")
    if go_find:
        seeds = parse_seeds(_s().get("w_seeds"))
        if not seeds:
            st.error("상품 단어를 한 개 이상 적어 주세요. 예: 휘낭시에")
        else:
            with st.spinner("검색어와 손님 정보를 모으는 중이에요…"):
                report, api_error = data.market_report(tuple(seeds), bool(_s()["use_live"]))
            _s()["market_error"] = api_error
            s["seeds"] = seeds
            _clear_picks()
            _s()["market"] = report
            if report is not None:
                s["keywords"], s["negatives"] = list(report.recommended), list(report.negatives)
                s["audience_hint"] = state.audience_hint(report)
    report = _s().get("market")
    if not _s().get("use_live"):
        _s()["market_error"] = None                      # 실시간을 끄면 지난 오류 안내도 지운다
    api_error = _s().get("market_error") if _s().get("use_live") else None
    if report is None:
        with st.container(border=True):
            if api_error:
                st.warning(api_error)
                st.caption("잠시 뒤 '내 손님 찾기'를 다시 누르거나, 아래 '저장된 예시로 계속하기'로 먼저 진행해 보세요.")
            elif go_find:
                st.warning("이 단어로는 검색 예상치를 찾지 못했어요. 더 넓은 단어(예: 디저트선물)로 다시 찾아 보세요.")
            else:
                st.write("아직 찾지 않았어요. 위 칸에 단어를 적고 '내 손님 찾기'를 눌러 주세요.")
            b1, b2 = st.columns(2)
            if api_error:
                b1.button("저장된 예시로 계속하기", on_click=_use_saved_example, key="market_use_saved")
            else:
                b1.button("예시 단어로 채우기", on_click=_fill_demo_seeds, key="market_demo_seeds")
            b2.button("검색어 없이 다음으로", on_click=_skip_market, key="market_skip",
                      help="네이버 검색 수요를 몰라서, 네이버 예산은 보수적으로 잡혀요.")
        return
    if api_error:
        st.warning(api_error)
        st.caption("지금 보이는 값은 저장해 둔 값이에요. 잠시 뒤 '내 손님 찾기'를 다시 누르면 최신 값으로 바꿔 봐요.")
    st.success(report.headline or "검색어를 찾았어요.")
    st.caption("{} · 검색량은 네이버 추산이라 실제와 다를 수 있어요.".format(ui.grade("B")))
    t1, t2, t3 = st.tabs(["검색어 묶음", "손님은 누구?", "언제 많이 찾나?"])
    with t1:
        st.dataframe(report.groups, hide_index=True, width="stretch", column_config={
            "intent": st.column_config.TextColumn("어떤 말인가요"), "count": st.column_config.NumberColumn("검색어 수"),
            "total_qc": st.column_config.NumberColumn("한 달 검색 수", format="%d"),
            "mobile_ctr": st.column_config.NumberColumn("모바일 클릭률", format="%.1f%%"),
            "top_keyword": st.column_config.TextColumn("대표 검색어")})
        st.caption("'제외' 묶음은 사러 온 사람이 아니라서 제외 검색어로 넣어요.")
    names = list(report.audiences)
    with t2:
        if names:
            who = st.selectbox("검색어", names, key="aud_pick")
            st.plotly_chart(age_chart(report.audiences[who]), use_container_width=True)
            a = report.audiences[who]
            st.caption("여성 {:.0f}% · 모바일 {} · {}".format(a["female"] * 100,
                       "{:.0f}%".format(a["mobile"] * 100) if a.get("mobile") else "-", ui.grade(a.get("grade", "B"))))
        else:
            st.info("손님 정보를 가져오지 못했어요. 그대로 다음 단계로 가도 괜찮아요.")
    with t3:
        if names:
            who = st.selectbox("검색어", names, key="aud_pick_month")
            st.plotly_chart(month_chart(report.audiences[who]), use_container_width=True)
        else:
            st.info("월별 흐름을 가져오지 못했어요.")
    keyword_picker(report)
    st.button("다음: 예산·예측", type="primary", on_click=_market_next, key="market_next", icon=":material/arrow_forward:")


# ───────────────────────── 3. 예산·예측 ─────────────────────────

def _budget_next() -> None:
    d = _s().get("_draft")
    if not d:
        return
    s = _s()["store"]
    s.update(objective=d["objective"], days=d["days"])
    _s()["media"] = d["media"]
    _s()["budget_plan"] = d["bp"]
    a = _s()["answers"]
    a["meta.campaign.objective"] = d["objective_label"]
    a["meta.adset.end_date"] = "{}일".format(d["days"])
    _s()["q_index"] = 0
    state.go_step(3)


def budget_chart(bp: dict) -> go.Figure:
    fig = go.Figure(go.Pie(labels=["네이버", "메타"], values=[bp["naver_month"], bp["meta_month"]], hole=0.55,
                           marker=dict(colors=["#2CA02C", "#4C78A8"]), textinfo="label+percent"))
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    return fig


def step_budget() -> None:
    s = _s()["store"]
    report = _s().get("market")
    st.markdown("#### 예산·예측")
    margin = int(s.get("margin_per_order") or 0)
    k1, k2 = st.columns(2)
    k1.metric("손님 1명에게 쓸 수 있는 광고비 한도", ui.won(margin) if margin else "미입력",
              help="한 개 팔면 남는 돈이에요. 이보다 많이 쓰면 팔수록 손해예요.")
    k2.metric("한 달 광고비", ui.won(s["budget"]))
    labels, mapping = state.objective_options()
    cur_label = _s()["answers"].get("meta.campaign.objective") or labels[0]
    ui.init_widget("w_obj", cur_label if cur_label in labels else labels[0])
    obj_label = st.radio("광고로 가장 원하는 게 뭐예요?", labels, horizontal=True, key="w_obj")
    st.caption("첫 달은 '스토어 방문 늘리기'를 권해요. 판매 목표는 구매 데이터가 쌓여야 잘 돌아가요. {}".format(
        "" if mapping.get(obj_label) == "트래픽" else "(가게 알리기는 클릭이 아니라 '얼마나 많은 사람에게 보였나'로 봐요.)"))
    objective = mapping.get(obj_label, "트래픽")
    days_opts = state.days_options()
    cur_days = "{}일".format(s.get("days", 14))
    ui.init_widget("w_days", cur_days if cur_days in days_opts else days_opts[min(1, len(days_opts) - 1)])
    days_label = st.radio("메타 광고 기간", days_opts, horizontal=True, key="w_days")
    st.caption("7일보다 짧으면 광고가 자리를 잡기 어려워요. 기본은 14일이에요.")
    days = int(days_label.replace("일", ""))
    ui.init_widget("w_media", list(_s()["media"]))
    media = st.pills("쓸 광고", list(MEDIA_NAMES), selection_mode="multi",
                     format_func=lambda m: MEDIA_NAMES[m], key="w_media")
    if not media:
        st.error("광고를 하나 이상 골라 주세요. 처음이라면 둘 다 켜 두는 걸 권해요.")
        return
    with st.expander("고급: 네이버에 쓸 최대 비중"):
        ui.init_widget("w_share", 50)
        share = st.slider("예산 중 네이버 최대 비중", 0, 100, step=5, key="w_share", format="%d%%")
    bp = state.compute_budget(s, media, report, objective, days, share / 100.0)
    bpd = asdict(bp)
    _s()["_draft"] = {"bp": bpd, "media": list(media), "objective": objective, "objective_label": obj_label, "days": days}

    st.markdown("##### 이렇게 나눠 쓰길 권해요")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("네이버 하루 예산", ui.won(bp.naver_daily), help="한 달 ÷ 30일")
    c2.metric("메타 하루 예산", ui.won(bp.meta_daily), help="한 달 ÷ 광고 기간")
    c3.metric("예상 클릭 (네이버)", "{:,}번".format(int(bp.naver_forecast["clicks"])))
    c4.metric("예상 도달 (메타)", "{:,}명".format(int(bp.meta_forecast["reach"])))
    left, right = st.columns([2, 1])
    with left:
        for n in bp.notes:
            st.write("• " + n)
        lo, hi = state.expected_orders(bpd)
        if hi > 0:
            line = "예상 주문은 한 달에 약 {:.0f}~{:.0f}건이에요. ({}: 클릭 뒤 구매율은 우리 가정이라 틀릴 수 있어요)".format(lo, hi, ui.grade("D"))
            st.write("• " + line)
            if margin and bp.budget / max(hi, 0.5) > margin:
                gap = bp.budget / max(hi, 0.5) - margin
                st.warning("이 예상대로면 손님 1명에 최소 약 {} 들고, 한 개 팔아 남는 {}보다 {} 많아요. "
                           "(계산: 한 달 광고비 {} ÷ 예상 주문 {:.0f}건). 첫 달은 '배우는 비용'으로 보고, 결과를 보고 줄이거나 바꾸세요."
                           .format(ui.won(bp.budget / hi), ui.won(margin), ui.won(gap), ui.won(bp.budget), hi))
    with right:
        st.plotly_chart(budget_chart(bpd), use_container_width=True)
    ui.grade_legend()
    st.button("다음: 질문 시작", type="primary", on_click=_budget_next, key="budget_next", icon=":material/arrow_forward:")


# ───────────────────────── 4. 질문 (한 번에 하나) ─────────────────────────

def _finish_questions() -> None:
    _s()["created"] = _s().get("created") or dt.date.today().isoformat()
    _s()["q_index"] = len(state.asked_questions(_s()["media"]))
    state.go_step(state.LAST_STEP)


def _save_and_next(qid: str, value: object, extra: dict = None) -> None:
    a = _s()["answers"]
    a[qid] = value
    a.update(extra or {})
    qs = state.asked_questions(_s()["media"])
    if _s()["q_index"] + 1 >= len(qs):
        _finish_questions()
    else:
        _s()["q_index"] += 1


def _use_choice(qid: str, key: str, default: object) -> None:
    _save_and_next(qid, _s().get(key) or default)


def _use_default(qid: str, default: object) -> None:
    _save_and_next(qid, default)


def _prev_question() -> None:
    if _s()["q_index"] > 0:
        _s()["q_index"] -= 1
    else:
        state.go_step(2)


def _skip_rest() -> None:
    """남은 질문은 권장 답(예시에서는 예시 값)으로 채우고 시트로."""
    s = _s()
    qs = state.asked_questions(s["media"])
    rest = qs[s["q_index"]:]
    filled = state.default_answers(rest, s["store"].get("product", ""), s.get("is_demo", False))
    hint = s["store"].get("audience_hint") or state.audience_hint(s.get("market"))
    for q in rest:
        if q.get("suggest_from") == "market_age_gender" and hint:
            filled[q["id"]] = hint
    for k, v in filled.items():
        s["answers"].setdefault(k, v)
    for q in rest:
        if q["kind"] == "llm" and q["id"] not in s["answers"]:
            try:
                c = state.make_copies(s["store"].get("product", ""), "", False)
                s["answers"][q["id"]] = c[q["media"]][0]
                s["answers"].setdefault("naver.ad.copy", c["naver"][0])
            except Exception:  # noqa: BLE001  문구는 나중에 시트에서 다시 만들 수 있음
                pass
    _finish_questions()


def _validate_url(text: str) -> str:
    t = text.strip()
    if t and not (t.startswith("http://") or t.startswith("https://")):
        return "주소는 http:// 또는 https:// 로 시작해야 해요. 상품 페이지 주소를 그대로 복사해 붙여 넣어 주세요."
    if t and "." not in t:
        return "주소가 끝까지 복사되지 않은 것 같아요. 브라우저 주소창의 전체 주소를 붙여 넣어 주세요."
    return ""


def _copy_choice(q: dict) -> None:
    s = _s()
    opts = s["copy_options"]
    st.caption("알려 주신 장점: {}".format(opts.get("strengths", "")))
    base = opts[q["media"]]
    ui.init_widget("copy_pick", 0)
    pick = st.radio("마음에 드는 문구를 고르세요", range(len(base)), key="copy_pick",
                    format_func=lambda i: "{} — {}".format(base[i]["headline"], base[i]["text"]))
    st.caption("사실이 아닌 말(최저가·1위 등)은 넣지 않았어요. 네이버는 제목 15자·설명 20~45자에 맞췄어요.")
    c1, c2 = st.columns(2)
    extra = {}
    if "naver" in s["media"] and "meta" in s["media"]:
        extra["naver.ad.copy"] = opts["naver"][min(pick, len(opts["naver"]) - 1)]
    c1.button("이 문구로 다음", type="primary", key="copy_ok", on_click=_save_and_next,
              args=(q["id"], base[pick], extra), icon=":material/check:")
    c2.button("다시 만들기", key="copy_redo", on_click=lambda: s["copy_options"].clear())


def step_questions() -> None:
    s = _s()
    media = s["media"]
    qs = state.asked_questions(media)
    i = min(s["q_index"], len(qs) - 1)
    q = qs[i]
    st.markdown("#### 질문 {}/{}".format(i + 1, len(qs)))
    st.progress(i / len(qs), text="남은 질문 {}개".format(len(qs) - i))
    answers = s["answers"]
    cur = answers.get(q["id"], q["default"])
    hint = s["store"].get("audience_hint") or state.audience_hint(s.get("market"))
    if q.get("suggest_from") == "market_age_gender" and hint and q["id"] not in answers:
        cur = hint
    for prev in qs[max(0, i - 2):i]:   # 방금 한 대화만 위에 남겨 둠
        with st.chat_message("assistant"):
            st.write(prev["ask"])
        with st.chat_message("user"):
            st.write(intake.show({"id": prev["id"], "kind": prev["kind"]}, answers.get(prev["id"], prev["default"])))
    with st.chat_message("assistant"):
        st.markdown("**[{}] {}**".format(q["media"].replace("meta", "메타").replace("naver", "네이버"), q["ask"]))
        st.caption("왜 묻나요? " + q["why"])
    prev_col, skip_col = st.columns(2)
    prev_col.button("이전", on_click=_prev_question, key="q_prev", icon=":material/arrow_back:")
    skip_col.button("남은 질문은 권장 답으로 넘기기", on_click=_skip_rest, key="q_skip_rest",
                    help="예시나 기본값으로 채워요. 시트에서 언제든 다시 고칠 수 있어요.")

    if q["kind"] == "llm":
        if s["copy_options"].get("for") == q["id"]:
            _copy_choice(q)
            return
        st.button("예시 장점으로 채우기", key="copy_demo",
                  on_click=lambda: _make_copy_options(q, state.DEMO_STRENGTHS))
        txt = st.chat_input("예: 국내산 버터로 매일 구워요", key="chat_copy")
        if txt:
            _make_copy_options(q, txt)
            st.rerun()
        return
    if q["input"] == "choice":
        default_opt = q["default"]
        ui.init_widget("q_" + q["id"], cur if cur in q["options"] else default_opt)
        st.radio(q["label"], q["options"],
                 key="q_" + q["id"], label_visibility="collapsed",
                 format_func=lambda o: o + ("  · 권장" if o == default_opt else ""))
        st.button("이 답으로 다음", type="primary", key="q_ok", on_click=_use_choice,
                  args=(q["id"], "q_" + q["id"], default_opt), icon=":material/arrow_forward:")
        return
    # 글로 쓰는 답 (계정 이름, 주소, 연령·성별)
    if cur:
        st.button("{} → 이대로 다음".format(("권장: " if cur == q["default"] or cur == hint else "") + str(cur)[:40]),
                  key="q_use_default", type="primary", on_click=_use_default, args=(q["id"], cur))
    else:
        st.button("나중에 입력하고 다음", key="q_later", on_click=_use_default, args=(q["id"], ""),
                  help="비워 두면 세팅값 시트에 '아직 입력 전이에요'로 보여요.")
    txt = st.chat_input("직접 입력하려면 여기에 쓰고 Enter", key="chat_text")
    if txt:
        err = _validate_url(txt) if q["input"] == "url" else ""
        if err:
            st.error(err)
        else:
            _save_and_next(q["id"], txt.strip())
            st.rerun()


def _make_copy_options(q: dict, strengths: str) -> None:
    s = _s()
    try:
        c = state.make_copies(s["store"].get("product", "상품"), strengths, bool(s.get("use_live")))
    except Exception:  # noqa: BLE001  외부 서비스 오류는 문장 틀로 대신함
        c = state.make_copies(s["store"].get("product", "상품"), strengths, False)
    s["copy_options"] = {"for": q["id"], "strengths": strengths, **c}


# ───────────────────────── 5. 세팅값 시트 ─────────────────────────

def _back_to_questions() -> None:
    _s()["q_index"] = 0
    state.go_step(3)


def sheet_frame(plan_df, media_pick: str):
    df = plan_df
    if media_pick != "전체":
        df = df[df["media"] == {"메타": "meta", "네이버": "naver"}[media_pick]]
    return df.reset_index(drop=True)


@st.fragment
def sheet_table(df) -> None:
    """세팅값 시트 (체크하면 이 표만 다시 그림). 바뀐 칸은 '바뀜' 열에 체크로 표시."""
    done = set(_s().get("sheet_checked") or [])
    view = df[["stage", "label", "value", "kind_label", "why", "changed", "field_id"]].copy()
    view.insert(0, "done", view["field_id"].isin(done))
    styled = view.style.apply(lambda r: ["background-color: rgba(255, 214, 0, 0.35)" if r["changed"] else "" for _ in r], axis=1)
    edited = st.data_editor(
        styled, hide_index=True, width="stretch", height=560, key="sheet_editor",
        disabled=["stage", "label", "value", "kind_label", "why", "changed", "field_id"],
        column_order=["done", "stage", "label", "value", "kind_label", "why", "changed"],
        column_config={
            "done": st.column_config.CheckboxColumn("옮겨 적음", help="광고 관리자에 입력했으면 체크하세요."),
            "stage": st.column_config.TextColumn("단계", width="small"),
            "label": st.column_config.TextColumn("칸 이름", width="medium"),
            "value": st.column_config.TextColumn("넣을 값", width="large"),
            "kind_label": st.column_config.TextColumn("어떻게 정해졌나요", width="small"),
            "why": st.column_config.TextColumn("이유", width="large"),
            "changed": st.column_config.CheckboxColumn("바뀜", width="small")})
    now = set(edited.loc[edited["done"], "field_id"]) | (done - set(view["field_id"]))
    _s()["sheet_checked"] = sorted(now)
    st.progress(len(now & set(df["field_id"])) / max(len(df), 1),
                text="광고 관리자에 옮겨 적은 칸 {}/{}".format(len(now & set(df["field_id"])), len(df)))


def changed_rows(plan, sheet):
    """'이번 달에 바뀐 칸' 표: 칸 이름 · 지금까지 → 바뀐 값 · 왜. 지난 진단 기록이 있으면 그걸, 없으면 시트의 '바뀜' 칸을 쓴다."""
    import pandas as pd
    last = (plan.history[-1].get("changes") if plan.history else None) or []
    rows = [{"칸 이름": r.get("label", ""), "지난달": str(r.get("before", "")), "이번 달": str(r.get("after", "")),
             "왜 바꾸나요": r.get("note", "")} for r in last]
    if not rows and not plan.history:
        ch = sheet[sheet["changed"]]
        rows = [{"칸 이름": r["label"], "지난달": "-", "이번 달": str(r["value"]), "왜 바꾸나요": r["why"]}
                for _, r in ch.iterrows()]
    return pd.DataFrame(rows, columns=["칸 이름", "지난달", "이번 달", "왜 바꾸나요"])


def changed_panel(plan, sheet) -> None:
    """바뀐 칸만 따로 모아 보여 준다 (표 편집기는 칸 색을 칠하지 못해서, 색이 되는 보기 전용 표를 쓴다)."""
    df = changed_rows(plan, sheet)
    if not len(df):
        return
    with st.container(border=True):
        st.markdown("##### 이번 달에 바뀐 칸")
        st.dataframe(df.style.apply(lambda r: ["background-color: rgba(255, 214, 0, 0.35)"] * len(r), axis=1),
                     hide_index=True, width="stretch")


def step_sheet() -> None:
    s = _s()
    plan = state.build_plan()
    if plan is None:
        st.warning("세팅이 아직 끝나지 않았어요. 질문 단계로 돌아가 주세요.")
        st.button("질문으로", on_click=_back_to_questions, key="sheet_to_q")
        return
    ctx = state.make_ctx(s["store"], s["media"], s["budget_plan"], s.get("market"))
    sheet = intake.build_sheet(s["answers"], ctx)
    if plan.history:   # '바뀜'은 가장 최근 진단이 바꾼 칸만 (옛 계획 파일의 누적 표시도 여기서 걸러진다)
        last_ids = {r.get("field_id") for r in (plan.history[-1].get("changes") or [])}
        sheet["changed"] = sheet["field_id"].isin(last_ids)
    n_changed = int(sheet["changed"].sum())
    st.markdown("#### 세팅값 시트")
    if plan.month_index > 1 and not n_changed:
        st.info("{}개월 차예요. 이번 진단에서는 새로 바꿀 칸이 없어요 — 지난달에 바꾼 세팅을 그대로 유지해요."
                .format(plan.month_index))
    elif plan.month_index > 1:
        st.info("{}개월 차예요. 지난 진단으로 바뀐 칸이 {}개 있어요. 아래 '이번 달에 바뀐 칸'을 먼저 보고, 시트에서는 '바뀜'에 체크된 칸만 확인해서 고치면 돼요."
                .format(plan.month_index, n_changed))
        changed_panel(plan, sheet)
    else:
        st.success("준비가 끝났어요. 아래 값을 광고 관리자에 순서대로 옮겨 적으세요.")
    pick = "전체"
    if len(s["media"]) > 1:
        pick = st.radio("보기", ["전체", "메타", "네이버"], horizontal=True, key="sheet_media")
    sheet_table(sheet_frame(sheet, pick))
    with st.expander("추적 링크 (스토어 통계에서 어느 광고에서 왔는지 보려고 붙이는 꼬리표)", expanded=False):
        if "meta" in s["media"]:
            link = intake.meta_final_link(s["answers"], ctx)
            tag = intake.meta_tracking(s["answers"], ctx)
            st.markdown("**메타 광고 'URL 매개변수' 칸에 넣을 값**")
            st.code(tag, language="text")
            if link:
                st.markdown("**꼬리표가 붙은 최종 주소**")
                st.code(link, language="text")
            else:
                st.caption("상품 페이지 주소를 아직 입력하지 않아서 최종 주소는 만들지 못했어요. 질문 단계에서 주소를 넣어 주세요.")
        else:
            st.caption("네이버 검색광고는 스토어 통계에 '네이버 광고'로 따로 잡혀서 꼬리표가 필요 없어요.")
    with st.expander("광고 문구 확인"):
        for k, label in (("meta.creative.copy", "메타"), ("naver.ad.copy", "네이버")):
            v = s["answers"].get(k)
            if isinstance(v, dict):
                st.write("**{}** · {} — {}".format(label, v.get("headline", ""), v.get("text", "")))
    st.markdown("##### 내려받기")
    d1, d2, d3 = st.columns(3)
    d1.download_button("계획 파일 (.json)", plan_io.to_json(plan), file_name=state.plan_file_name(plan),
                       mime="application/json", icon=":material/download:", key="dl_plan",
                       help="다음 달에 이 파일을 올리면 이어서 할 수 있어요.")
    d2.download_button("세팅값 시트 (CSV)", state.sheet_csv(sheet), file_name="세팅값_{}월차.csv".format(plan.month_index),
                       mime="text/csv", icon=":material/download:", key="dl_csv")
    d3.download_button("세팅값 시트 (엑셀)", state.sheet_excel(sheet), file_name="세팅값_{}월차.xlsx".format(plan.month_index),
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       icon=":material/download:", key="dl_xlsx")
    st.divider()
    if plan.month_index > 1 and not n_changed:
        st.markdown("**다음 할 일: 지난달 세팅 그대로 광고 실행을 이어가요.**")
    else:
        st.markdown("**다음 할 일: 광고를 켜기 전 준비를 확인해요.**")
    ui.next_link("run", "② 실행으로 가기", ":material/arrow_forward:")
    st.button("질문 답 다시 고치기", on_click=_back_to_questions, key="sheet_redo")


# ───────────────────────── 화면 ─────────────────────────

def render() -> None:
    state.init()
    st.title("① 세팅")
    ui.stepper(0)
    step = _s()["setup_step"]
    sub_stepper(step)
    if step == 0:
        step_store()
    elif step == 1:
        step_market()
    elif step == 2:
        step_budget()
    elif step == 3:
        step_questions()
    else:
        step_sheet()


if __name__ == "__main__":
    render()
