"""홈: 무엇을 해 주는지 한 줄 + 숫자 하나 + 예시로 바로 해 보기."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from v2.app import state, ui  # noqa: E402
from v2.engine import specs  # noqa: E402


def counts() -> dict:
    """첫 화면에 보여 줄 숫자: 광고 관리자 칸 수 vs 사장님께 묻는 질문 수."""
    return {"fields": len(specs.all_fields()), "asked": len(state.asked_questions(["meta", "naver"]))}


def render() -> None:
    state.init()
    c = counts()
    st.title("광고 코치")
    st.subheader("처음 광고하는 사장님이 질문 {}개로 세팅을 끝내고, 한 달 뒤 다음 달에 바꿀 칸을 받아요.".format(c["asked"]))
    st.caption("광고 관리자 칸은 모두 {}개예요. 사장님께 묻는 건 {}개뿐이고, 나머지는 기본값과 이유를 보여 드려요."
               .format(c["fields"], c["asked"]))

    with st.container(border=True):
        st.markdown("**예시로 먼저 보기: 소연베이크**")
        st.write("1인 구움과자 가게, 하루 주문 2~3건, 한 달 30만 원으로 광고를 처음 해 보려는 사장님이에요. "
                 "네이버 키가 없어도 저장된 예시 데이터로 끝까지 해 볼 수 있어요.")
        if st.button("예시로 해 보기: 소연베이크", type="primary", icon=":material/play_arrow:", key="home_demo"):
            state.load_demo(to_step=1)
            st.switch_page(ui.PAGES["setup"])

    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.markdown("**내 가게로 시작하기**")
            st.write("가게 정보부터 차례로 물어봐요.")
            if st.button("내 가게로 시작", key="home_mine", icon=":material/storefront:"):
                state.reset()
                st.switch_page(ui.PAGES["setup"])
    with right:
        with st.container(border=True):
            st.markdown("**지난 달에 이어서 하기**")
            ui.plan_upload("home_plan_upload")

    st.divider()
    st.markdown("#### 이렇게 흘러가요")
    a, b, c3 = st.columns(3)
    for col, title, text, key in (
        (a, "① 세팅", "가게 정보 → 내 손님 찾기 → 예산·예측 → 질문 → 광고 관리자에 옮겨 적을 세팅값 시트", "setup"),
        (b, "② 실행", "광고를 켜기 전 준비 체크리스트와, 결과를 올릴 날짜", "run"),
        (c3, "③ 진단", "한 달 뒤 결과를 올리면 어디가 문제인지 알려 주고, 다음 달에 바꿀 칸을 만들어 줘요", "diag"),
    ):
        with col.container(border=True):
            st.markdown("**{}**".format(title))
            st.write(text)
            ui.next_link(key, "{} 열기".format(title))
    ui.grade_legend()


if __name__ == "__main__":
    render()
