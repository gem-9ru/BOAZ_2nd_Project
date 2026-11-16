"""② 실행: 광고를 켜기 전 준비 체크리스트와 결과를 올릴 날."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import datetime as dt  # noqa: E402

import streamlit as st  # noqa: E402

import plotly.graph_objects as go  # noqa: E402

from v2.app import board, guide, state, ui, viz  # noqa: E402

AD_DAYS = 30        # 한 달 집행 (가상 데이터와 같은 기간)
RESIDUAL_DAYS = 7   # 광고가 끝난 뒤에도 남는 효과를 보는 날 (effect.RESIDUAL_DAYS와 같게)
CHAT_KEY = "rd_run"
# 체크리스트 항목 → 도움말에 줄 칸 (없으면 None)
ITEM_FIELDS = {"baseline": None, "budget": "meta.adset.daily_budget", "tag": "meta.ad.tracking_url",
               "bizmoney": "naver.pre.bizmoney"}


def result_day(start: dt.date) -> dt.date:
    """결과 파일을 올릴 날: 광고 끝나고 잔존 7일이 지난 다음 날."""
    return start + dt.timedelta(days=AD_DAYS - 1 + RESIDUAL_DAYS + 1)


def checklist_items(media: list) -> list:
    """(키, 글, 설명). 매체에 맞는 것만."""
    items = [
        ("baseline", "광고 켜기 전 4주 기록을 저장했어요",
         "스마트스토어 통계의 방문·검색 유입과, 네이버 데이터랩의 우리 가게 이름 검색량을 캡처해 두세요. 광고 효과를 가려내는 기준선이에요."),
        ("budget", "광고 관리자의 하루 예산이 세팅값 시트와 같아요",
         "예산을 비우면 계속 돈이 나가고, 너무 크면 하루에 한도를 넘겨 쓸 수 있어요."),
    ]
    if "meta" in media:
        items.append(("tag", "메타 광고에 추적 꼬리표를 붙였고, 눌러서 스토어가 열리는지 확인했어요",
                      "꼬리표가 있어야 스토어 통계에서 메타 광고로 온 손님을 구분해요."))
    if "naver" in media:
        items.append(("bizmoney", "네이버 비즈머니를 충전하고 사업자 정보를 등록했어요",
                      "충전금이 없으면 광고가 켜지지 않아요."))
    return items


@st.fragment
def checklist(media: list) -> None:
    """할 일 목록이라 체크박스. 체크해도 이 부분만 다시 그려요. 안내 중인 항목에는 캐릭터가 붙어요."""
    items = checklist_items(media)
    saved = st.session_state["run_checks"]
    state_now = {}
    for key, text, why in items:
        ui.init_widget("chk_" + key, bool(saved.get(key)))
        with st.container(border=True, key=guide.tid("run-" + key)):
            state_now[key] = st.checkbox(text, key="chk_" + key)
            st.caption(why)
            if guide.here("run-" + key):
                st.caption(board.mark(True) + "지금 안내하는 항목이에요")
    st.session_state["run_checks"] = state_now
    n = sum(state_now.values())
    st.progress(n / len(items), text="준비 {}/{}".format(n, len(items)))
    if n == len(items):
        st.success("준비가 모두 끝났어요. 광고를 켜도 좋아요.")


def guide_steps(media: list, start: dt.date) -> list:
    """오른쪽 대화가 하나씩 안내할 항목: 체크리스트 → 결과 올릴 날 → 다음 할 일."""
    steps = [{"id": "run-" + key, "say": "이 항목이에요", "title": text,
              "body": "{}\n\n끝냈으면 왼쪽 칸에 체크하고 '다음'을 눌러요.".format(why),
              "field": ITEM_FIELDS.get(key), "ctx": {"checklist": key}} for key, text, why in checklist_items(media)]
    steps.append({"id": "run-date", "say": "결과 올릴 날이에요", "title": "결과를 올릴 날",
                  "body": "광고를 켜는 날을 왼쪽에서 고르면 날짜가 계산돼요. 지금 고른 날 기준으로는 **{}** 에 결과 파일을 올리면 돼요. "
                          "광고를 본 뒤 나중에 검색해서 산 주문까지 보려고 {}일을 더 기다려요."
                  .format(result_day(start).strftime("%Y년 %m월 %d일"), RESIDUAL_DAYS),
                  "field": None, "ctx": {"checklist": "date"}})
    steps.append({"id": "run-next", "say": "다음은 여기예요", "title": "다음 할 일",
                  "body": "광고를 켜고 한 달 뒤 결과를 올리면 돼요. 연습은 지금 예시 케이스로도 할 수 있어요. "
                          "**왼쪽 아래 '③ 진단으로 가기'** 를 눌러 이어가요.",
                  "field": None, "ctx": {"checklist": "next"}})
    return steps


def work_board(plan, bp: dict, s) -> None:
    """왼쪽 작업판: 하루 예산 · 체크리스트 · 결과 올릴 날 · 다음 할 일."""
    st.caption("{}개월 차 · 하루 예산은 세팅값 시트 그대로예요.".format(plan.month_index))
    cols = iter(st.columns(len(s["media"]) + 1, border=True))
    if "naver" in s["media"]:
        next(cols).metric("네이버 하루 예산", ui.won(bp.get("naver_daily")))
    if "meta" in s["media"]:
        next(cols).metric("메타 하루 예산", ui.won(bp.get("meta_daily")))
    next(cols).metric("한 달 광고비", ui.won(s["store"].get("budget")))

    st.markdown("#### 광고를 켜기 전에")
    checklist(s["media"])

    st.markdown("#### 결과를 올릴 날")
    with st.container(border=True, key=guide.tid("run-date")):
        default = s["ad_start"] or (dt.date.today() + dt.timedelta(days=1))
        ui.init_widget("w_ad_start", default)
        start = st.date_input("광고를 켜는 날", key="w_ad_start")
        s["ad_start"] = start
        end = start + dt.timedelta(days=AD_DAYS - 1)
        up = result_day(start)
        d1, d2, d3 = st.columns(3, border=True)
        multi_year = len({start.year, end.year, up.year}) > 1
        fmt_day = (lambda d: "{}년 {}월 {}일".format(d.year, d.month, d.day)) if multi_year else (lambda d: d.strftime("%m월 %d일"))
        d1.metric("광고 켜는 날", fmt_day(start))
        d2.metric("광고 끝나는 날", fmt_day(end))
        d2.caption("{}일 동안".format(AD_DAYS))
        left_days = (up - dt.date.today()).days
        d3.metric("결과 올리는 날", fmt_day(up),
                  help="광고가 끝나고 {}일 더 기다린 다음 날이에요.".format(RESIDUAL_DAYS))
        d3.caption("오늘부터 {}일 뒤".format(left_days) if left_days >= 0 else "{}일 지났어요".format(-left_days))
        timeline(start)
        st.info("광고를 본 뒤 나중에 검색해서 산 주문까지 보려고 {}일을 더 기다린 다음, 위 날짜에 결과 파일을 올려 주세요.".format(RESIDUAL_DAYS))
        st.caption("올릴 파일: 메타 광고 보고서(일·광고 세트 단위), 네이버 광고 키워드별 일별 보고서, 스마트스토어 일별 통계. 엑셀 한 파일이나 CSV 여러 개 모두 돼요.")
        if guide.here("run-date"):
            st.caption(board.mark(True) + "지금 안내하는 항목이에요")
    st.divider()
    with st.container(border=True, key=guide.tid("run-next")):
        st.markdown("**다음 할 일: 한 달 뒤 결과를 올려요.** (연습은 지금 예시 케이스로도 할 수 있어요.)")
        ui.next_link("diag", "③ 진단으로 가기", ":material/arrow_forward:")
        if guide.here("run-next"):
            st.caption(board.mark(True) + "지금 안내하는 항목이에요")


def timeline(start: dt.date) -> None:
    """일정 타임라인: 광고 30일 → 기다리는 7일 → 결과 올리는 날. 막대 안에 글자로 뜻을 쓴다."""
    end = start + dt.timedelta(days=AD_DAYS - 1)
    wait_end = end + dt.timedelta(days=RESIDUAL_DAYS)
    up = result_day(start)
    fig = go.Figure()
    for label, a, b, color in (("광고 {}일".format(AD_DAYS), start, end + dt.timedelta(days=1), viz.PRIMARY),
                               ("기다리는 {}일".format(RESIDUAL_DAYS), end + dt.timedelta(days=1), wait_end + dt.timedelta(days=1), viz.GRAY)):
        fig.add_trace(go.Bar(y=["일정"], x=[(b - a).days * 86400000], base=[a], orientation="h", marker_color=color, text=label,
                             textposition="inside", insidetextanchor="middle", hoverinfo="skip",
                             textfont=dict(color="#FFFFFF" if color == viz.PRIMARY else viz.TEXT)))
    fig.add_trace(go.Scatter(x=[up], y=["일정"], mode="markers+text", text=["결과 올리는 날"], textposition="top center",
                             marker=dict(symbol="diamond", size=14, color=viz.TEXT), hoverinfo="skip"))
    viz._base(fig, 180)
    fig.update_layout(barmode="overlay", margin=dict(l=10, r=10, t=30, b=10))
    fig.update_yaxes(visible=False)
    fig.update_xaxes(type="date", tickformat="%m/%d", range=[start - dt.timedelta(days=1), up + dt.timedelta(days=4)])
    viz.show(fig, "chart_run_timeline")


def render() -> None:
    state.init()
    st.title("② 실행")
    ui.stepper(1)
    if not state.setup_done():
        ui.empty_locked("① 세팅에서 세팅값 시트까지 만들면 이 단계가 열려요.", "① 세팅으로 가기", "setup")
        return
    s = st.session_state
    plan = state.build_plan()
    bp = s["budget_plan"]
    start = s.get("w_ad_start") or s["ad_start"] or (dt.date.today() + dt.timedelta(days=1))   # 방금 고른 날도 바로 반영
    steps = guide_steps(s["media"], start)
    sig = ("run", plan.month_index, plan.created, str(plan.store.get("name", "")), tuple(x["id"] for x in steps))
    board.ensure(CHAT_KEY, sig, steps, {"store": dict(s["store"]), "budget_plan": dict(bp), "media": list(s["media"])})
    guide.css()
    guide.toggle()
    board.point(CHAT_KEY)
    with st.container(key="run_cols"):     # 좁은 화면에서는 CSS가 오른쪽(대화)을 위로 올린다
        left, right = st.columns([7, 5])
        with left, guide.board_container("run"):
            work_board(plan, bp, s)
            guide.scroll()
        with right:
            board.render_chat(CHAT_KEY, steps, "광고를 켜기 전에 확인할 게 {}가지 있어요. 하나씩 같이 볼게요. "
                              "모르는 건 아래에 물어봐도 돼요.".format(len(checklist_items(s["media"]))), "다음")
    guide.live()


if __name__ == "__main__":
    render()
