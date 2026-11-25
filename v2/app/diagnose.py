"""③ 진단: 결과 올리기(또는 예시 케이스) → 지표 → 진단 카드 → 효과 확인 → 다음 달 바뀐 칸 → 다음 달 시작."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import List, Optional, Tuple  # noqa: E402

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from v2.app import board, data, guide, state, ui, viz  # noqa: E402
from v2.engine import datacheck, diagnose, effect, plan_io  # noqa: E402
from v2.engine.metrics import fmt  # noqa: E402

CHAT_KEY = "rd_diag"
CASE_ORDER = ["C1", "C2", "C3", "C4", "C0", "C1b"]
VIRTUAL_MODES = {"sim", "forecast"}
METRIC_NAMES = {
    "meta_spend": "메타 지출", "naver_spend": "네이버 지출", "total_spend": "총 지출", "budget_use": "예산 사용률",
    "naver_daily_spend": "네이버 하루 실제 지출", "meta_daily_with_leftover": "남은 돈을 메타에 쓸 때 하루 예산",
    "weekly_freq_max": "주간 노출 빈도(최대)", "awareness_weekly_freq_min": "알리기 광고 주간 빈도(최소)",
    "ctr_drop_max": "링크 클릭률 하락(최대)", "saturation_max": "타겟 소진율", "link_clicks": "메타 링크 클릭",
    "link_ctr": "메타 링크 클릭률", "meta_cpc_avg": "메타 클릭당 비용", "cpc_rise": "클릭 비용 상승",
    "an_click_share": "다른 앱(Audience Network) 클릭 비중", "ig_spend_share": "인스타그램 지출 비중",
    "naver_ctr": "네이버 클릭률", "naver_dead_keywords": "주문 없는 키워드 수", "naver_dead_keyword_names": "주문 없는 키워드",
    "naive_lift": "광고 전후 변화(시즌 포함)", "corrected_lift": "시즌을 뺀 변화", "lastclick_orders": "광고 클릭 주문(마지막 클릭)",
    "est_orders": "광고 덕분 주문(추정)", "meta_sessions": "메타 유입 방문", "cvr_meta": "메타 방문 구매율",
    "visit_per_click": "클릭 대비 실제 방문", "lastclick_cac": "손님 1명 비용(마지막 클릭)", "est_cac": "손님 1명 비용(추정)",
    "hidden_ratio": "숨은 주문 배수", "margin_per_order": "한 개 팔면 남는 돈", "margin_gap": "한도 대비 초과 금액",
}
# 숫자의 근거 등급: 광고·스토어 보고서에서 그대로 센 값은 A, 시즌·검색 경유를 추정한 값은 효과 추정 등급, 타겟 크기는 B
METRIC_GRADE = {"saturation_max": "B"}
ESTIMATED = {"naive_lift", "corrected_lift", "est_orders", "est_cac", "hidden_ratio", "margin_gap"}
RULE_GRADE = {"hypothesis": "가설: 기준값을 실제 데이터로 아직 확인하지 못했어요", "checked": "확인됨: 실제 데이터로 기준을 확인했어요",
              "calc": "계산: 사장님 숫자로 바로 계산한 결과예요"}


def rule_grade_text(grade: Optional[str]) -> str:
    """진단 규칙 근거 등급 → 쉬운 설명. 모르는 등급이어도 화면이 깨지지 않게 한다."""
    return RULE_GRADE.get(grade or "", "") or ("근거: {}".format(grade) if grade else "근거 등급 없음")


def metric_grade(name: str, eff_grade: str = "D") -> str:
    return eff_grade if name in ESTIMATED else METRIC_GRADE.get(name, "A")


def pct(v: Optional[float]) -> str:
    return "-" if v is None else "{:+.0f}%".format(v * 100)


# ───────────────────────── 자료 고르기 ─────────────────────────

def pick_bundle() -> Tuple[Optional[object], bool]:
    """(결과 묶음, 가상 데이터 여부). 올린 파일이 없으면 (None, False)와 함께 안내를 보여 준다."""
    src = st.radio("어떤 결과로 볼까요?", ["예시 케이스", "내 파일 올리기"], horizontal=True, key="diag_src")
    if src == "예시 케이스":
        bundle = data.demo_bundle()
    else:
        files = st.file_uploader("결과 파일 올리기 (엑셀 1개 또는 CSV 여러 개)", type=["xlsx", "csv"],
                                 accept_multiple_files=True, key="diag_files",
                                 help="메타 보고서, 네이버 키워드별 일별 보고서, 스마트스토어 일별 통계")
        if not files:
            with st.container(border=True):
                st.write("아직 올린 파일이 없어요. 파일을 올리거나, 위에서 '예시 케이스'를 골라 먼저 연습해 보세요.")
            return None, False
        bundle = data.read_upload(tuple((f.name, f.getvalue()) for f in files))
        for p in bundle.problems:
            st.warning(p)
        if not bundle.tables:
            st.error("파일에서 읽을 표를 찾지 못했어요. 광고 관리자에서 '일별' 보고서를 다시 내보내거나, '예시 케이스'로 연습해 보세요.")
            return None, False
    modes = bundle.modes()
    return bundle, bool(modes) and set(modes) <= VIRTUAL_MODES


def select_case(bundle) -> Tuple[object, Optional[str], Optional[str]]:
    """(케이스·구분을 고른 묶음, 케이스, 구분). 케이스 열이 없는 실제 데이터는 그대로."""
    cases = [c for c in CASE_ORDER if c in bundle.cases()] + [c for c in bundle.cases() if c not in CASE_ORDER]
    if not cases:
        return bundle, None, None
    c1, c2 = st.columns([2, 1])
    ui.init_widget("diag_case", "C2" if "C2" in cases else cases[0])
    if st.session_state["diag_case"] not in cases:
        st.session_state["diag_case"] = cases[0]
    case = c1.selectbox("케이스", cases, key="diag_case",
                        format_func=lambda c: "{} · {}".format(c, state.CASE_NAMES.get(c, "")).strip(" ·"))
    modes = bundle.modes()
    mode = None
    if modes:
        ui.init_widget("diag_mode", "sim" if "sim" in modes else modes[0])
        if st.session_state["diag_mode"] not in modes:
            st.session_state["diag_mode"] = modes[0]
        mode = c2.radio("구분", modes, horizontal=True,
                        key="diag_mode", format_func=lambda m: state.MODE_NAMES.get(m, m))
    return bundle.select(case, mode), case, mode


def pick_period(sel, virtual: bool) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    detected = (pd.Timestamp(state.DEMO_START), pd.Timestamp(state.DEMO_END)) if virtual else effect.ad_period(sel)
    if not detected:
        return None, None
    with st.expander("광고 기간 ({} ~ {}) · 다르면 고치세요".format(detected[0].date(), detected[1].date())):
        ui.init_widget("diag_period", (detected[0].date(), detected[1].date()))
        got = st.date_input("광고 기간", key="diag_period")
    if isinstance(got, (tuple, list)) and len(got) == 2:
        return pd.Timestamp(got[0]), pd.Timestamp(got[1])
    return detected


# ───────────────────────── 결과 그리기 ─────────────────────────

def kpis(m: dict, virtual: bool, eff_grade: str) -> None:
    """맨 앞 숫자는 '손님 1명 한도'. 실제 비용은 그 한도에 이어서 보여 준다. (2×2: 좁은 화면에서도 숫자가 잘리지 않게)"""
    margin = m.get("margin_per_order")
    est, last = m.get("est_cac"), m.get("lastclick_cac")
    top = st.columns(2, border=True)
    top[0].metric("손님 1명에게 쓸 수 있는 한도", ui.won(margin) if margin else "미입력",
                  help="한 개 팔면 남는 돈 (내가 입력한 값)")
    delta = None
    if est and margin:
        if ui.won(est) == ui.won(margin):
            delta = "한도와 같아요"
        else:
            delta = "{}{} · 한도보다 {}".format("+" if est > margin else "-", ui.won(abs(est - margin)), "많음" if est > margin else "적음")
    top[1].metric("실제 손님 1명 비용", ui.won(est) if est else "-", delta=delta,
                  delta_color="inverse" if delta else "off", help="총 지출 ÷ 광고 덕분 주문(추정)")
    bottom = st.columns(2, border=True)
    bottom[0].metric("총 지출", ui.won(m.get("total_spend")),
                     delta="예산의 {}".format(fmt("budget_use", m.get("budget_use"))) if m.get("budget_use") else None,
                     delta_color="off")
    bottom[1].metric("광고 덕분 주문", "{:.0f}건".format(m["est_orders"]) if m.get("est_orders") is not None else "-")
    if m.get("lastclick_orders") is not None:
        bottom[1].caption("광고 클릭 주문만 세면 {:.0f}건".format(m["lastclick_orders"]))
    st.caption("근거: 한도 A(내 입력) · 총 지출 {} · 실제 비용·광고 덕분 주문 {} (시즌·검색 경유를 뺀 추정)".format(
        ui.grade("A", virtual), ui.grade(eff_grade, virtual)))
    bars = [(n, v, c) for n, v, c in (("손님 1명 한도", margin, viz.PRIMARY), ("실제 비용(추정)", est, viz.GRAY_DARK),
                                      ("마지막 클릭만 센 비용", last, viz.GRAY)) if v]
    if len(bars) >= 2:
        viz.hbar([b[0] for b in bars], [b[1] for b in bars], [ui.won(b[1]) for b in bars], [b[2] for b in bars],
                 "손님 1명 비용, 한도와 견줘 보기" if margin else "손님 1명 비용 견줘 보기 (한도 미입력)",
                 "chart_cac_compare", height=200)
    gap = m.get("margin_gap")
    if gap is not None and est and margin:
        if gap > 0:
            st.warning("주문 1건당 약 {} 손해예요. (계산: 손님 1명 비용 {} − 한 개 팔면 남는 돈 {})".format(
                ui.won(gap), ui.won(est), ui.won(margin)))
        else:
            st.success("손님 1명 비용이 한 개 팔아 남는 돈보다 약 {} 적어요.".format(ui.won(-gap)))
    if est and last and last > est:
        st.caption("광고 클릭으로 잡힌 주문만 세면 손님 1명이 {} 보이지만, 광고를 보고 나중에 검색해서 산 주문까지 합치면 {}.".format(
            ui.josa(ui.won(last), "으로"), ui.josa(ui.won(est), "이에요")))


def rule_id(f: diagnose.Finding) -> str:
    """진단 카드를 가리키는 id ('t-rule-<규칙 id>' 컨테이너)."""
    safe = str(f.id).replace(".", "-")        # 규칙 id는 'rule.placement_quality' → 't-rule-placement_quality'
    return safe if safe.startswith("rule-") else "rule-" + safe


def finding_card(f: diagnose.Finding, m: dict, virtual: bool, eff_grade: str) -> None:
    with st.container(border=True, key=guide.tid(rule_id(f))):
        focused = guide.focus() == rule_id(f)
        st.markdown("{}**{}** · :blue-badge[{} 단계]".format(board.mark(focused), f.title, f.funnel))
        st.write(f.message)
        if f.advice:
            st.write("→ " + f.advice)
        if f.caveat:
            st.caption("주의: " + f.caveat)
        if guide.here(rule_id(f)):
            st.caption(board.mark(True) + "지금 설명하고 있는 카드예요")
        st.caption(rule_grade_text(f.grade) + (" · 가상 데이터라 연습용이에요" if virtual else ""))
        if f.changes:
            st.write("다음 달에 바꿀 칸: " + ", ".join(c.label for c in f.changes))
        with st.expander("근거 숫자 보기"):
            for k, v in f.evidence.items():
                st.write("{}: **{}** ({})".format(METRIC_NAMES.get(k, k), v, ui.grade(metric_grade(k, eff_grade), virtual)))


def findings_section(findings: List[diagnose.Finding], m: dict, virtual: bool, eff_grade: str) -> None:
    fired = diagnose.fired(findings)
    st.markdown("#### 진단: 고쳐 볼 곳 {}개".format(len(fired)))
    if not fired:
        st.success("이번 달은 고칠 곳이 보이지 않아요. 같은 세팅으로 한 달 더 해 보세요.")
    for f in fired:
        finding_card(f, m, virtual, eff_grade)
    rest = [f for f in findings if f.status != "fired"]
    if rest:
        with st.expander("문제없음 {}개 · 데이터 부족 {}개".format(sum(f.status == "passed" for f in rest),
                                                          sum(f.status == "no_data" for f in rest))):
            for f in rest:
                st.write("{} {} ".format("✓" if f.status == "passed" else "–", f.title)
                         + ("(올린 자료에 필요한 숫자가 없어요)" if f.status == "no_data" else ""))


def _funnel_fig(labels, values, key: str, title: str) -> None:
    import plotly.graph_objects as go
    fig = go.Figure(go.Funnel(y=labels, x=values, textinfo="value+percent previous", marker=dict(color=viz.PRIMARY),
                              connector=dict(line=dict(color=viz.GRAY))))
    viz._base(fig, 260, title)
    viz.show(fig, key)


def _meta_lastclick_orders(sel, start, end) -> Optional[float]:
    """스토어 일별 통계의 메타 마지막 클릭 주문 합 (엔진 지표와 같은 기간: 광고 기간 ~ 끝난 뒤 RESIDUAL_DAYS일)."""
    store = sel.get("store_daily")
    if store is None or not len(store) or "orders_meta" not in store or not store["orders_meta"].notna().any():
        return None
    if start is None or end is None:
        period = effect.ad_period(sel)
        if not period:
            return None
        start, end = period
    rend = pd.Timestamp(end) + pd.Timedelta(days=effect.RESIDUAL_DAYS)
    win = store[(store["date"] >= pd.Timestamp(start)) & (store["date"] <= rend)]
    return float(win["orders_meta"].sum())


def trend_section(sel, m: dict, virtual: bool = False, start=None, end=None) -> None:
    """손님이 어디서 빠지는지(퍼널)와 날짜별 지출. 숫자는 올린 보고서와 지표 계산 결과 그대로."""
    meta, naver = sel.get("meta_daily"), sel.get("naver_daily")
    has_meta = (meta is not None and len(meta) and "impressions" in meta and m.get("link_clicks") and m.get("meta_sessions"))
    has_naver = (naver is not None and len(naver) and {"impressions", "clicks"} <= set(naver.columns)
                 and naver["impressions"].sum() > 0)
    st.markdown("#### 손님이 어디서 빠졌나요")
    tabs = []
    if has_meta:
        tabs.append("메타")
    if has_naver:
        tabs.append("네이버")
    tabs.append("날짜별 지출")
    boxes = dict(zip(tabs, st.tabs(tabs)))
    if has_meta:
        with boxes["메타"]:
            orders = _meta_lastclick_orders(sel, start, end)
            labels = ["광고를 본 횟수", "링크 클릭", "스토어 방문"]
            vals = [float(meta["impressions"].sum()), float(m["link_clicks"]), float(m["meta_sessions"])]
            if orders is not None:
                labels.append("광고 클릭 주문(마지막 클릭)")
                vals.append(orders)
            _funnel_fig(labels, vals, "chart_funnel_meta", "메타 광고: 본 사람 → 주문")
            st.caption("각 줄의 퍼센트는 바로 윗줄 대비예요. 본 횟수·링크 클릭은 올린 메타 보고서 전체, 스토어 방문·주문은 "
                       "광고 기간부터 끝난 뒤 {}일까지 스마트스토어 통계라 기간이 달라요. 주문은 마지막 클릭 기준이라 "
                       "위 '광고 덕분 주문'과 달라요. {}".format(effect.RESIDUAL_DAYS, ui.grade("A", virtual)))
    if has_naver:
        with boxes["네이버"]:
            labels = ["검색 결과에 보인 횟수", "클릭"]
            vals = [float(naver["impressions"].sum()), float(naver["clicks"].sum())]
            if "store_orders" in naver and naver["store_orders"].notna().any():
                labels.append("주문")
                vals.append(float(naver["store_orders"].sum()))
            _funnel_fig(labels, vals, "chart_funnel_naver",
                        "네이버 검색광고: 보임 → 주문" if len(vals) == 3 else "네이버 검색광고: 보임 → 클릭")
            st.caption(ui.grade("A", virtual))
    with boxes["날짜별 지출"]:
        import plotly.graph_objects as go
        fig = go.Figure()
        for df, col, name, color in ((meta, "spend", "메타", viz.PRIMARY), (naver, "cost", "네이버", viz.GRAY_DARK)):
            if df is not None and len(df) and col in df and df[col].sum() > 0:
                d = df.groupby("date")[col].sum().reset_index()
                fig.add_trace(go.Bar(x=d["date"], y=d[col], name=name, marker_color=color,
                                     hovertemplate="%{x|%m/%d} " + name + " %{y:,.0f}원<extra></extra>"))
        if fig.data:
            viz._base(fig, 260)
            fig.update_layout(barmode="stack", showlegend=True, legend=dict(orientation="h", y=1.12, x=0),
                              yaxis_title="하루 지출(원)", xaxis_title=None)
            viz.show(fig, "chart_daily_spend")
            st.caption("날짜별로 매체마다 얼마를 썼는지예요. " + ui.grade("A", virtual))
        else:
            st.caption("올린 자료에 날짜별 지출이 없어요.")


def lift_chart(eff: effect.Effect) -> go.Figure:
    fig = go.Figure(go.Bar(x=["광고 전후 비교\n(시즌 포함)", "시즌을 뺀 진짜 변화"],
                           y=[(eff.naive_lift or 0) * 100, (eff.corrected_lift or 0) * 100],
                           marker_color=[viz.GRAY, viz.PRIMARY],
                           text=[pct(eff.naive_lift), pct(eff.corrected_lift)], textposition="outside"))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="우리 가게 이름 검색량 변화 (%)", showlegend=False)
    return fig


def effect_text(m: dict) -> str:
    """오른쪽 대화가 읽어 줄 효과 확인 글 (왼쪽 카드와 같은 숫자)."""
    eff = m.get("effect")
    if eff is None or eff.naive_lift is None:
        return "스마트스토어 일별 통계(브랜드 검색·카테고리 검색 열 포함)를 함께 올리면 광고 효과를 가려낼 수 있어요. 지금은 올린 자료로 효과를 가리지 못했어요."
    return ("광고 전후만 비교하면 {} 보이지만, 연말 검색 증가를 빼면 {}. 광고를 보고 나중에 검색해서 산 주문은 약 {:.0f}건으로 추정해요. "
            "(근거 {})".format(ui.josa(pct(eff.naive_lift), "으로"), ui.josa(pct(eff.corrected_lift), "이에요"),
                              eff.extra_brand_orders, eff.grade))


def effect_section(m: dict, virtual: bool) -> str:
    """효과 확인. 반환: 이 숫자들의 근거 등급."""
    eff = m.get("effect")
    st.markdown("#### 효과 확인")
    if eff is None or eff.naive_lift is None:
        with st.container(border=True, key=guide.tid("effect")):
            st.markdown("{}스마트스토어 일별 통계(브랜드 검색·카테고리 검색 열 포함)를 함께 올리면 광고 효과를 가려낼 수 있어요."
                        .format(board.mark(guide.focus() == "effect")))
            if guide.here("effect"):
                st.caption(board.mark(True) + "지금 설명하고 있는 곳이에요")
        return "D"
    g = eff.grade
    with st.container(border=True, key=guide.tid("effect")):
        if guide.focus() == "effect":
            st.markdown(board.mark(True) + "**지금 설명하고 있는 곳이에요**")
        a, b = st.columns([1, 1])
        with a:
            st.metric("광고 전후 비교 (시즌 포함)", pct(eff.naive_lift))
            st.metric("시즌을 뺀 진짜 변화 · {}".format(ui.grade(g, virtual)), pct(eff.corrected_lift))
            st.write("전후만 비교하면 {} 보이지만, 연말 검색 증가를 빼면 {}. 광고 효과를 부풀려 보지 않도록 시즌을 뺀 숫자를 기준으로 삼아요."
                     .format(ui.josa(pct(eff.naive_lift), "으로"), ui.josa(pct(eff.corrected_lift), "이에요")))
        with b:
            viz.show(lift_chart(eff), "chart_lift")
        line = "광고를 보고 나중에 검색해서 산 주문은 약 {:.0f}건으로 추정해요.".format(eff.extra_brand_orders)
        if eff.truth_brand_orders is not None:
            line += " (가상 데이터의 정답은 {:.0f}건)".format(eff.truth_brand_orders)
        st.write(line)
        if eff.survey_ad_share:
            lo, hi = eff.survey_ad_share
            st.write("설문에서 '광고 덕분에 알았다'는 답은 {:.0f}~{:.0f}%예요. ({})".format(lo * 100, hi * 100, ui.grade("A", virtual)))
        st.caption("{} · 시즌은 광고와 상관없는 카테고리 검색 추세로 뺐어요.".format(ui.grade(g, virtual)))
        guide.here("effect")
    return g


def next_month_plan(plan: plan_io.Plan, findings: List[diagnose.Finding]):
    """(다음 달 계획, 바뀐 칸 표) 또는 (None, None)."""
    try:
        return plan_io.next_month(plan, findings)
    except Exception:  # noqa: BLE001
        return None, None


def next_text(new_plan, diff) -> str:
    """오른쪽 대화가 읽어 줄 '다음 달에 바뀌는 칸' 글."""
    if new_plan is None:
        return "다음 달 세팅을 만들지 못했어요. 계획 파일을 내려받아 보관한 뒤, ① 세팅에서 다시 시작해 주세요."
    if not len(diff):
        return ("이번 달 진단으로 바꿀 칸은 없어요. 같은 세팅으로 한 달 더 이어갈 수 있어요. "
                "**왼쪽 '다음 달 세팅 만들기'** 를 누르면 {}개월 차로 넘어가요.".format(new_plan.month_index))
    rows = "\n".join("- **{}**: {} → {} ({})".format(r["label"], r["before"], r["after"], r["note"])
                     for _, r in diff.head(6).iterrows())
    more = "\n- 그 밖에 {}칸".format(len(diff) - 6) if len(diff) > 6 else ""
    return ("다음 달에는 {}칸을 바꿔요.\n{}{}\n\n**왼쪽 '다음 달 세팅 만들기'** 를 누르면 {}개월 차 세팅에 반영돼요."
            .format(len(diff), rows, more, new_plan.month_index))


def next_month_section(new_plan, diff) -> None:
    st.markdown("#### 다음 달에 바뀌는 칸")
    with st.container(border=True, key=guide.tid("next")):
        if guide.focus() == "next":
            st.markdown(board.mark(True) + "**지금 설명하고 있는 곳이에요**")
        if new_plan is None:
            st.error("다음 달 세팅을 만들지 못했어요. 계획 파일을 내려받아 보관한 뒤, ① 세팅에서 다시 시작해 주세요.")
            return
        if len(diff):
            st.dataframe(diff, hide_index=True, width="stretch", column_config={
                "field_id": None, "label": st.column_config.TextColumn("칸 이름", width="medium"),
                "before": st.column_config.TextColumn("지금", width="medium"),
                "after": st.column_config.TextColumn("다음 달", width="medium"),
                "note": st.column_config.TextColumn("왜 바꾸나요", width="large")})
        else:
            st.info("이번 달 진단으로 바꿀 칸은 없어요. 같은 세팅으로 한 달 더 이어갈 수 있어요.")
        if st.button("다음 달 세팅 만들기", type="primary", key="next_month", icon=":material/arrow_forward:"):
            state.start_next_month(new_plan)
            st.toast("{}개월 차 세팅을 만들었어요. 바뀐 칸은 '이번 달에 바뀐 칸'에 모아 뒀어요.".format(new_plan.month_index), icon="✅")
            st.switch_page(ui.PAGES["setup"])
        guide.here("next")


def details(sel, m: dict, virtual: bool, eff_grade: str) -> None:
    with st.expander("자세한 숫자 보기"):
        rows = [{"지표": METRIC_NAMES.get(k, k), "값": fmt(k, v), "근거": ui.grade(metric_grade(k, eff_grade), virtual)}
                for k, v in m.items() if k != "effect" and v is not None]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        ui.grade_legend()
    if virtual:
        with st.expander("가상 데이터가 가정 범위 안에 있는지 점검"):
            st.dataframe(datacheck.check(data.demo_bundle()), hide_index=True, width="stretch")


def finding_text(f: diagnose.Finding, virtual: bool) -> str:
    """오른쪽 대화가 읽어 줄 진단 카드 설명 (왼쪽 카드와 같은 글)."""
    parts = ["{} · {} 단계".format(f.title, f.funnel), f.message]
    if f.advice:
        parts.append("→ " + f.advice)
    if f.caveat:
        parts.append("주의: " + f.caveat)
    if f.changes:
        parts.append("다음 달에 바꿀 칸: " + ", ".join(c.label for c in f.changes))
    parts.append(rule_grade_text(f.grade) + (" · 가상 데이터라 연습용이에요" if virtual else ""))
    return "\n\n".join(parts[1:])


def guide_steps(findings: List[diagnose.Finding], m: dict, virtual: bool, new_plan, diff) -> list:
    """오른쪽 대화가 하나씩 설명할 항목: 걸린 진단 카드 → 효과 확인 → 다음 달에 바뀌는 칸."""
    steps = [{"id": rule_id(f), "say": "이 카드예요", "title": f.title, "body": finding_text(f, virtual),
              "field": f.changes[0].field_id if f.changes else None,
              "ctx": {"rule": f.id, "rule_title": f.title}} for f in diagnose.fired(findings)]
    steps.append({"id": "effect", "say": "효과는 여기서 봐요", "title": "효과 확인", "body": effect_text(m),
                  "field": None, "ctx": {"rule": "effect"}})
    steps.append({"id": "next", "say": "다음 달은 여기예요", "title": "다음 달에 바뀌는 칸", "body": next_text(new_plan, diff),
                  "field": diff.iloc[0]["field_id"] if diff is not None and len(diff) else None, "ctx": {"rule": "next"}})
    return steps


def analysis_board(plan: plan_io.Plan, s_ctx: dict) -> Optional[dict]:
    """왼쪽 작업판: 자료 고르기 → 지표 → 진단 카드 → 효과 확인 → 다음 달 칸. 대화에 넘길 항목을 돌려준다(자료가 없으면 None)."""
    st.caption("{}개월 차 계획 기준으로 봐요.".format(plan.month_index))
    bundle, virtual = pick_bundle()
    if bundle is None:
        guide.set_focus(None)
        return None
    sel, case, mode = select_case(bundle)
    start, end = pick_period(sel, virtual)
    if virtual:
        st.info("연습용 가상 데이터예요. 실제 광고 결과가 아니라서 숫자 옆에 '가상'을 붙였어요.")
    s = plan.store
    margin = s.get("margin_per_order")
    m = findings = None
    with st.status("결과를 분석하는 중이에요…", expanded=False) as status:
        try:
            status.update(label="지표를 계산하는 중…")
            if virtual and case:
                m, findings = data.demo_case(case, mode, start, end, float(s.get("budget") or 0), margin)
            else:
                m, findings = data.analyze(sel, start, end, float(s.get("budget") or 0), margin)
            status.update(label="분석 끝: 진단 규칙 {}개를 확인했어요".format(len(findings)), state="complete")
        except Exception:  # noqa: BLE001
            status.update(label="분석하지 못했어요", state="error")
    if m is None:
        st.error("올린 자료로 지표를 계산하지 못했어요. 열 이름이 광고 관리자에서 내보낸 그대로인지 확인하고, 다시 올려 주세요.")
        guide.set_focus(None)
        return None
    st.session_state["diag_done"] = True
    eff = m.get("effect")
    eff_grade = eff.grade if eff is not None else "D"
    new_plan, diff = next_month_plan(plan, findings)
    steps = guide_steps(findings, m, virtual, new_plan, diff)
    sig = ("diag", plan.month_index, plan.created, str(s.get("name", "")), st.session_state.get("diag_src"), case, mode,
           tuple(x["id"] for x in steps))
    board.ensure(CHAT_KEY, sig, steps, s_ctx)
    board.point(CHAT_KEY)
    kpis(m, virtual, eff_grade)
    trend_section(sel, m, virtual, start, end)
    findings_section(findings, m, virtual, eff_grade)
    effect_section(m, virtual)
    details(sel, m, virtual, eff_grade)
    st.divider()
    next_month_section(new_plan, diff)
    guide.scroll()
    n_fired = len(diagnose.fired(findings))
    intro = ("결과를 봤어요. 고쳐 볼 곳이 {}개예요. 하나씩 설명할게요. 모르는 건 아래에 물어봐도 돼요.".format(n_fired) if n_fired
             else "결과를 봤어요. 이번 달은 고칠 곳이 보이지 않아요. 효과 확인과 다음 달 칸을 같이 볼게요.")
    return {"steps": steps, "intro": intro}


def render() -> None:
    state.init()
    st.title("③ 진단")
    ui.stepper(2)
    plan = state.build_plan()
    if plan is None:
        with st.container(border=True):
            st.markdown("#### 아직 진단할 계획이 없어요")
            st.write("① 세팅을 끝내면 이 단계가 열려요. 먼저 연습해 보고 싶다면 예시 계획(소연베이크)을 불러올 수 있어요.")
            st.button("예시 계획으로 진단해 보기", type="primary", key="diag_demo_plan", on_click=state.load_demo_plan,
                      icon=":material/play_arrow:")
            ui.plan_upload("diag_plan_upload")
            ui.next_link("setup", "① 세팅으로 가기")
        return
    s = st.session_state
    guide.css()
    guide.toggle()
    with st.container(key="diag_cols"):     # 좁은 화면에서는 CSS가 오른쪽(대화)을 위로 올린다
        left, right = st.columns([7, 5])
        with left, guide.board_container("diag"):
            res = analysis_board(plan, {"store": dict(s["store"]), "budget_plan": dict(s["budget_plan"]), "media": list(s["media"])})
        with right:
            if res is None:
                board.ensure(CHAT_KEY, ("diag-none", plan.month_index), [], {"store": dict(s["store"]), "budget_plan": dict(s["budget_plan"])})
                board.render_chat(CHAT_KEY, [], "결과 파일을 올리거나 '예시 케이스'를 고르면 걸린 진단을 하나씩 설명해 드려요. "
                                  "궁금한 건 지금 물어봐도 돼요.", "다음 카드")
            else:
                board.render_chat(CHAT_KEY, res["steps"], res["intro"], "다음 카드")
    guide.live()


if __name__ == "__main__":
    render()
