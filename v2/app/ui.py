"""화면 공용 부품: 단계 표시(스테퍼), 근거 등급 글, 계획 파일 올리기, 빈 화면."""
from typing import Optional

import streamlit as st

from v2.app import state
from v2.engine import plan_io

PAGES = {"home": "home.py", "setup": "setup.py", "run": "run.py", "diag": "diagnose.py"}
STEP_TITLES = ["① 세팅", "② 실행", "③ 진단"]


def won(n: object) -> str:
    try:
        return "{:,}원".format(int(round(float(n))))
    except (TypeError, ValueError):
        return "-"


_DIGIT_BATCHIM = {"0": True, "1": True, "2": False, "3": True, "4": False, "5": False, "6": True, "7": True,
                  "8": True, "9": False}


def has_batchim(text: object) -> bool:
    """마지막 글자에 받침이 있는가 (숫자는 읽는 소리 기준: 1 일, 3 삼, 10 십...)."""
    t = str(text).rstrip()
    while t and t[-1] in ")]}'\"·~":
        t = t[:-1]
    if not t:
        return False
    ch = t[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - ord("가")) % 28 != 0
    if ch in _DIGIT_BATCHIM:
        return _DIGIT_BATCHIM[ch]
    return False


def josa(text: object, kind: str) -> str:
    """값 뒤에 알맞은 조사를 붙인다. kind: 이에요 (예요) · 으로 (로) · 은 (는) · 이 (가) · 을 (를).
    예: josa('10,529원', '이에요') → '10,529원이에요', josa('3건', '으로') → '3건으로'"""
    t = str(text)
    b = has_batchim(t)
    if kind == "이에요":
        return t + ("이에요" if b else "예요")
    if kind == "으로":
        last = t.rstrip()[-1:]
        ieul = ("가" <= last <= "힣" and (ord(last) - ord("가")) % 28 == 8) or last in ("1", "7", "8")
        return t + ("로" if (not b or ieul) else "으로")
    if kind == "은":
        return t + ("은" if b else "는")
    if kind == "이":
        return t + ("이" if b else "가")
    if kind == "을":
        return t + ("을" if b else "를")
    raise ValueError(kind)


def init_widget(key: str, value: object) -> None:
    """키가 있는 입력칸의 처음 값을 session_state에 한 번만 넣는다. (칸에 value=/index=/default=를 함께 주면
    Streamlit이 '기본값과 session_state를 둘 다 줬다'는 경고를 띄우므로 이 방식만 쓴다.)"""
    if key not in st.session_state:
        st.session_state[key] = value


KIND_BADGE = {"질문": "blue", "사전 점검": "orange", "챗봇 작성": "violet", "자동": "gray", "기본값": "gray",
              "다음 사이클": "gray"}
KIND_ICON = {"질문": ":material/chat:", "사전 점검": ":material/fact_check:", "챗봇 작성": ":material/edit_note:",
             "자동": ":material/auto_fix_high:", "기본값": ":material/tune:", "다음 사이클": ":material/update:"}


def kind_badge(kind_label: object) -> str:
    """칸 종류 배지(아이콘 + 글자 라벨)를 마크다운으로."""
    k = str(kind_label)
    return ":{}-badge[{} {}]".format(KIND_BADGE.get(k, "gray"), KIND_ICON.get(k, ":material/label:"), k)


def sources_md(sources: list) -> str:
    """도움말 출처 줄: 확인 표시(✅ 공식 확인 · △ 다른 자료 · ❓ 확인 못 함)와 링크."""
    names = {"✅": "공식 도움말", "△": "공식 아님", "❓": "확인 못 함"}
    out = []
    for x in sources or []:
        chk = str(x.get("check") or "❓")
        title, url = str(x.get("title") or "출처"), str(x.get("url") or "")
        link = "[{}]({})".format(title, url) if url.startswith("http") else title
        out.append("{} {} · {}".format(chk, names.get(chk, ""), link).replace("  ", " "))
    return "  \n".join(out)


def grade(g: str, virtual: bool = False) -> str:
    """근거 등급 글. 가상 데이터면 '가상'을 붙여 실제 측정으로 오해하지 않게."""
    return "근거 {}{}".format(g, " (가상)" if virtual else "")


def grade_legend() -> None:
    st.caption("근거 등급: " + state.GRADES)


def stepper(current: int) -> None:
    """맨 위 3단계 표시. 끝난 단계는 ✓, 지금 단계는 ●."""
    done = [state.setup_done(), bool(st.session_state.get("run_checks")) and all(st.session_state["run_checks"].values()),
            bool(st.session_state.get("diag_done"))]
    cols = st.columns(3)
    for i, (col, title) in enumerate(zip(cols, STEP_TITLES)):
        mark = "✓" if done[i] and i != current else "●" if i == current else "○"
        col.markdown("**{} {}**".format(mark, title) if i == current else "{} {}".format(mark, title))
    month = int(st.session_state.get("month_index", 1))
    if month > 1:
        st.caption("지금 {}개월 차예요.".format(month))


def next_link(key: str, label: str, icon: Optional[str] = None) -> None:
    st.page_link(PAGES[key], label=label, icon=icon)


def plan_upload(key: str) -> None:
    """지난 달 계획 파일(.json)을 올려 이어 하기. 읽다가 틀리면 고치는 법을 바로 아래에 보여 준다."""
    f = st.file_uploader("지난 달 계획 파일 이어 하기 (.json)", type=["json"], key=key,
                         help="'계획 파일 내려받기'로 저장해 둔 파일이에요.")
    if f is None:
        return
    try:
        plan = plan_io.from_json(f.getvalue())
    except plan_io.PlanError as e:
        st.error(str(e))
        return
    state.load_plan(plan)
    st.toast("{}개월 차 계획을 불러왔어요.".format(plan.month_index), icon="✅")
    st.switch_page(PAGES["setup"])


def empty_locked(what: str, action_label: str, page_key: str) -> None:
    """잠김·빈 화면: 무엇이 생기면 열리는지 한 줄 + 다음 행동 하나."""
    with st.container(border=True):
        st.markdown("#### 아직 열 수 없어요")
        st.write(what)
        st.page_link(PAGES[page_key], label=action_label, icon=":material/arrow_forward:")
