"""광고 코치 v2 (Streamlit). 실행: streamlit run v2/app/main.py

- 쪽(page)은 st.navigation으로 나눈다: 홈 · ① 세팅 · ② 실행 · ③ 진단
- 화면 사이에 나눠 쓰는 값은 st.session_state (state.py)
- 네이버·Claude 키가 없어도 저장된 예시 데이터와 문장 틀로 끝까지 동작한다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from v2.app import state, ui  # noqa: E402
from v2.engine import plan_io  # noqa: E402

st.set_page_config(page_title="광고 코치", page_icon=":material/campaign:", layout="wide")
state.init()

# 공통 화면 다듬기 (UX_설계원칙.md 7장 점검):
# - 위 여백을 줄여 노트북 화면에서도 채팅 입력칸이 처음부터 보이게
# - 파일 올리기 칸의 영어 안내를 한국어로 (사장님이 '무엇을 하는 칸인지' 바로 알게)
APP_CSS = """<style>
.block-container{padding-top:2.25rem}
@media (max-width:640px){.block-container{padding-top:1rem}}
/* 채팅 기록 높이를 화면 높이에 맞춰, 빠른 답 버튼과 입력칸이 스크롤 없이 보이게 (기본 480px 고정 대신) */
div:has(> .stVerticalBlock[class*="_history"]){--chat-h:clamp(300px, calc(100vh - 560px), 600px);flex:0 0 var(--chat-h) !important;height:var(--chat-h) !important;min-height:0 !important;max-height:var(--chat-h) !important}
.stVerticalBlock[class*="_history"]{min-height:0 !important}
[data-testid="stFileUploaderDropzoneInstructions"]>div>span{font-size:0;line-height:0}
[data-testid="stFileUploaderDropzoneInstructions"]>div>span:first-child::after{content:"여기로 파일을 끌어다 놓으세요";
 font-size:.9rem;line-height:1.4;display:block}
[data-testid="stFileUploaderDropzoneInstructions"]>div>span:last-child::after{content:"파일 한 개씩 올려요";
 font-size:.8rem;line-height:1.4;display:block}
[data-testid="stFileUploaderDropzone"] button{font-size:0}
[data-testid="stFileUploaderDropzone"] button::after{content:"파일 고르기";font-size:.9rem}
</style>"""
st.markdown(APP_CSS, unsafe_allow_html=True)


@st.dialog("처음부터 다시 할까요?")
def confirm_reset() -> None:
    """입력한 내용이 모두 지워지는, 되돌리기 어려운 행동이라서만 모달을 쓴다."""
    st.write("지금까지 입력한 가게 정보·질문 답·세팅값이 모두 지워져요. 필요하면 먼저 계획 파일을 내려받으세요.")
    plan = state.build_plan()
    if plan is not None:
        st.download_button("계획 파일 먼저 내려받기", plan_io.to_json(plan), file_name=state.plan_file_name(plan),
                           mime="application/json", key="dlg_dl_plan")
    if st.button("지우고 처음부터", type="primary", key="dlg_reset"):
        state.reset()
        st.switch_page(ui.PAGES["home"])


def sidebar() -> None:
    with st.sidebar:
        plan = state.build_plan()
        if plan is not None:
            st.caption("{}개월 차 · {} 계획".format(plan.month_index, plan.store.get("name", "")))
            st.download_button("계획 파일 내려받기", plan_io.to_json(plan), file_name=state.plan_file_name(plan),
                               mime="application/json", icon=":material/download:", key="side_dl_plan")
            st.divider()                # 위에 보여 줄 게 있을 때만 구분선 (메뉴 아래 빈 줄 두 개 방지)
        if st.button("처음부터 다시", icon=":material/restart_alt:", key="side_reset"):
            confirm_reset()


pages = [
    st.Page(ui.PAGES["home"], title="홈", icon=":material/home:", default=True),
    st.Page(ui.PAGES["setup"], title="① 세팅", icon=":material/tune:", url_path="setup"),
    st.Page(ui.PAGES["run"], title="② 실행", icon=":material/play_circle:", url_path="run"),
    st.Page(ui.PAGES["diag"], title="③ 진단", icon=":material/monitoring:", url_path="diagnose"),
]
nav = st.navigation(pages)
sidebar()
nav.run()
