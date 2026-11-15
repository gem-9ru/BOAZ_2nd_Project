"""① 세팅: 챗봇 대화(오른쪽)가 가게 정보 → 내 손님 → 예산 → 광고 관리자 칸 질문을 차례로 묻고,
왼쪽 작업판이 답하는 대로 채워진다. 대화가 끝나면 세팅값 시트와 내려받기.

대화 엔진 v2/engine/conversation.py · 대화 화면 v2/app/chat.py · 상태 연결 v2/app/state.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from v2.app import chat, guide, state, ui  # noqa: E402
from v2.engine import conversation, intake, plan_io  # noqa: E402

MEDIA_NAMES = {"meta": "메타 (인스타그램·페이스북)", "naver": "네이버 검색광고"}
NAVER_COLOR, META_COLOR = "#4C78A8", "#C8661A"


def _s() -> dict:
    return st.session_state


_tid = guide.tid

GUIDE_SAY = {"store": "여기에 들어가요", "market": "찾은 검색 단어예요", "budget": "예산을 이렇게 나눴어요",
             "field": "이 칸에 들어가요"}


def _focus(cs: dict) -> None:
    """지금 오른쪽 대화가 말하는 칸·카드를 캐릭터가 가리키도록 정한다."""
    ph = cs["phase"]
    fid, label = None, ""
    if ph == "store":
        fid, label = "store-" + str(cs["step"]), conversation.STORE_LABEL.get(cs["step"], "")
    elif ph == "market" and (cs.get("market") or {}).get("recommended"):
        fid, label = "market", "내 손님 판"
    elif ph == "budget" and cs.get("plan"):
        fid, label = "budget", "예산 판"
    elif ph == "ask":
        fid = str(cs["step"]).replace(".", "-")     # 칸 이름은 세팅 보드 줄이 그릴 때 알려 준다 (guide.here의 label)
    guide.set_focus(fid, GUIDE_SAY["field" if ph == "ask" else ph] if fid else "", label, chat.position(cs) if fid else "")


# ───────────────────────── 왼쪽 작업판 ─────────────────────────

def _store_card(cs: dict, open_: bool) -> None:
    focus = cs["step"] if cs["phase"] == "store" else None
    s = cs["store"]
    with st.expander("가게 카드", expanded=open_, icon=":material/storefront:"):
        for key, label in conversation.STORE_STEPS:
            v = s.get({"margin": "margin", "channel": "store_type"}.get(key, key))
            if v in (None, ""):
                shown = "아직"
            elif key in ("price", "budget", "margin"):
                shown = ui.won(v)
                if key == "margin" and s.get("price"):
                    shown += " (판매가의 {}%)".format(int(round(100.0 * v / s["price"])))
            elif key == "channel":
                shown = next(c for c in conversation.CHANNELS if conversation.CHANNEL_KEY[c] == v)
            else:
                shown = str(v)
            with st.container(border=(key == focus), key=_tid("store-" + key)):
                st.markdown("{}**{}** · {}".format(":material/arrow_right: " if key == focus else "", label, shown))
                guide.here("store-" + key)
        st.markdown("**광고 매체** · " + "·".join(MEDIA_NAMES[m] for m in cs["media"]))


def _audience_charts(report) -> None:
    aud = next(iter(report.audiences.values()), None) if getattr(report, "audiences", None) else None
    if not aud:
        return
    ages = aud.get("ages") or {}
    if ages:
        fig = go.Figure(go.Bar(x=["{}대".format(a) for a in ages], y=[round(v * 100) for v in ages.values()],
                               marker_color=NAVER_COLOR))
        fig.update_layout(title="누가 찾나요 (연령별 %, 여성 {}%)".format(round(aud.get("female", 0) * 100)),
                          height=220, margin=dict(l=10, r=10, t=40, b=10), yaxis_title=None, xaxis_title=None)
        st.plotly_chart(fig, key="chart_age", use_container_width=True)
    monthly = aud.get("monthly") or {}
    if monthly:
        fig = go.Figure(go.Scatter(x=list(monthly), y=list(monthly.values()), mode="lines+markers",
                                   line=dict(color=NAVER_COLOR)))
        fig.update_layout(title="언제 찾나요 (월별 검색 관심도)", height=220, margin=dict(l=10, r=10, t=40, b=10),
                          yaxis_title=None, xaxis_title=None)
        st.plotly_chart(fig, key="chart_month", use_container_width=True)
    st.caption(ui.grade(aud.get("grade", "B")))


def _market_board(cs: dict, open_: bool) -> None:
    m = cs.get("market") or {}
    if not m.get("recommended"):
        return
    with st.expander("내 손님 판", expanded=open_, icon=":material/groups:"):
        with st.container(key=_tid("market"), border=(cs["phase"] == "market")):
            guide.here("market")
            if m.get("headline"):
                st.markdown("**{}**".format(m["headline"]))
            report = _s().get("market")
            if report is not None and m.get("headline"):
                _audience_charts(report)
            for g in m.get("groups") or []:
                st.markdown("· {} · {}개 · 월 검색 {:,}회 · 대표 {}".format(
                    g.get("intent", ""), int(g.get("count", 0) or 0), int(g.get("total_qc", 0) or 0), g.get("top_keyword", "")))
            st.markdown("**광고 검색어** · " + ", ".join("`{}`".format(w) for w in (m.get("picked") or m["recommended"])[:10]))
            if m.get("negatives"):
                st.markdown("**제외어** · " + ", ".join("`{}`".format(w) for w in m["negatives"][:8]))


def _budget_board(cs: dict, open_: bool) -> None:
    p = cs.get("plan")
    if not p:
        return
    with st.expander("예산 판", expanded=open_, icon=":material/payments:"):
        with st.container(key=_tid("budget"), border=(cs["phase"] == "budget")):
            guide.here("budget")
            nf, mf = p.get("naver_forecast") or {}, p.get("meta_forecast") or {}
            lo, hi = state.expected_orders(p)
            cells = [("한 달 광고비", ui.won(p.get("budget"))), ("예상 주문", "{:.0f}~{:.0f}건".format(lo, hi)),
                     ("네이버 하루 예산", ui.won(p.get("naver_daily"))), ("예상 네이버 클릭", "{:,.0f}회".format(nf.get("clicks", 0) or 0)),
                     ("메타 하루 예산", ui.won(p.get("meta_daily"))), ("예상 메타 도달", "{:,.0f}명".format(mf.get("reach", 0) or 0))]
            for i in range(0, len(cells), 2):
                row = st.columns(2)
                for col, (label, val) in zip(row, cells[i:i + 2]):
                    col.metric(label, val)
            st.caption("예상 주문은 클릭 × 구매율 가정이에요. " + ui.grade("D"))
            margin = (cs.get("store") or {}).get("margin") or 0
            if margin and p.get("budget"):
                be = p["budget"] / margin
                if hi < be:
                    st.warning("광고비를 본전으로 돌리려면 {:.0f}건 넘게 팔려야 하는데, 예상은 최대 {:.0f}건이에요. "
                               "첫 달은 손해일 수 있어요.".format(be, hi))
                else:
                    st.caption("본전은 약 {:.0f}건이에요. 예상 주문이 넘어도 실제로는 달라질 수 있어요.".format(be))
            for n in p.get("notes") or []:
                st.caption(n)


def _setting_board(cs: dict) -> None:
    """세팅 보드: 매체 → 단계 → 칸 줄 (답하면 값이 바로 바뀜). 지금 묻는 칸은 굵은 테두리."""
    s = _s()
    store = conversation.to_store(cs)
    store["keywords"] = list(store.get("seeds") or [])
    ctx = state.make_ctx(store, cs["media"], cs.get("plan"), s.get("market"))
    sheet = intake.build_sheet(conversation.to_answers(cs), ctx)
    focus = cs["step"] if cs["phase"] == "ask" else None
    st.markdown("#### 세팅 보드")
    st.caption("광고 관리자 칸이에요. 오른쪽 대화에서 답하면 이 값이 바로 바뀌어요.")
    for media, mdf in sheet.groupby("media", sort=False):
        st.markdown("**{}**".format(MEDIA_NAMES.get(media, media)))
        for stage, sdf in mdf.groupby("stage", sort=False):
            with st.expander("{} · {}칸".format(stage, len(sdf)), expanded=bool(focus and focus in set(sdf["field_id"]))):
                for _, r in sdf.iterrows():
                    here = r["field_id"] == focus
                    with st.container(border=here, key=_tid(r["field_id"])):
                        a, b, c = st.columns([3, 5, 2])
                        a.markdown("{}**{}**".format(":material/arrow_right: " if here else "", r["label"]))
                        b.write(str(r["value"]) or "-")
                        c.markdown(ui.kind_badge(r["kind_label"]))
                        if here:
                            guide.here(r["field_id"].replace(".", "-"), str(r["label"]))


def work_board(cs: dict) -> None:
    ph = cs["phase"]
    _store_card(cs, open_=ph in ("store", "confirm") or (ph == "market" and not (cs.get("market") or {}).get("recommended")))
    _market_board(cs, open_=ph == "market")
    _budget_board(cs, open_=ph == "budget")
    if ph == "ask":
        _setting_board(cs)


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
        st.warning("세팅이 아직 끝나지 않았어요. 오른쪽 대화에서 질문에 답해 주세요.")
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
    if s.get("chat") is None:
        st.button("답 고치기 (대화 열기)", on_click=state.restore_chat, key="sheet_redo", icon=":material/edit:",
                  help="불러온 계획의 답을 대화로 다시 고쳐요.")
    else:
        st.caption("답을 고치려면 오른쪽 대화의 '지난 답 고치기'를 누르세요.")


# ───────────────────────── 화면 ─────────────────────────

def render() -> None:
    state.init()
    st.title("① 세팅")
    ui.stepper(0)
    s = _s()
    if s.get("chat") is None and not state.setup_done():
        state.start_chat()
    chat.process_pending()
    cs = s.get("chat")
    if cs is None:                      # 불러온 계획: 세팅값 시트만 (원하면 대화를 열어 고침)
        step_sheet()
        return
    guide.css()
    guide.toggle()
    _focus(cs)
    with st.container(key="setup_cols"):   # 좁은 화면에서는 CSS가 오른쪽(대화)을 위로 올린다
        left, right = st.columns([7, 5])
        with right:
            chat.render()
        with left, guide.board_container("setup"):
            if s["chat"]["phase"] == "done":
                step_sheet()
            else:
                work_board(s["chat"])
                guide.scroll()
    guide.live()


if __name__ == "__main__":
    render()
