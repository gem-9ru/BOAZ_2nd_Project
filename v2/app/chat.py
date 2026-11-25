"""① 세팅의 챗봇 대화 (오른쪽): 말풍선 기록 · 카드 · 칩 · 입력창 · 진행 표시 · 지난 답 고치기.

- 대화 상태는 st.session_state["chat"] (JSON으로 저장되는 dict, 엔진은 v2/engine/conversation.py).
- 누른 칩·쓴 글은 먼저 session_state["chat_pending"]에 적어 두고, 화면을 그리기 전에 process_pending()이 한 번에 처리한다
  (그래야 왼쪽 작업판이 같은 실행에서 새 상태로 그려진다).
- 숫자는 엔진이 준 값만 보여 준다. 도움말 답에는 출처와 ✅/△/❓ 확인 표시를 붙인다. kind=="llm"이면 한 글자씩 흘려 쓴다.
"""
from typing import List, Tuple

import streamlit as st

from v2.app import state, ui
from v2.engine import conversation

CHAT_HEIGHT = 480
DEMO_SEEDS_CHIP = "예시 단어로 찾기"
HELP_NOTE = {"help": "도움말에 미리 적어 둔 답이에요.", "coach": "사장님 숫자로 바로 계산한 답이에요.",
             "llm": "AI가 도움말을 바탕으로 쓴 답이에요. 틀릴 수 있으니 출처도 함께 확인해 주세요.",
             "none": ""}


# ── 입력 받기 (콜백은 적어 두기만) ─────────────────────────

def _push(kind: str, value: str) -> None:
    st.session_state["chat_pending"] = (kind, value)


def _on_submit() -> None:
    text = (st.session_state.get("chat_text") or "").strip()
    if text:
        _push("text", text)


def process_pending() -> None:
    """적어 둔 입력(글·칩·고치기·권장 답)을 엔진에 넘겨 새 대화 상태로 바꾼다."""
    s = st.session_state
    pending = s.get("chat_pending")
    if not pending or s.get("chat") is None:
        return
    s["chat_pending"] = None
    kind, value = pending
    sv, cs = state.services(), s["chat"]
    with st.spinner("확인하고 있어요…"):
        try:
            if kind == "text":
                new = conversation.handle(cs, value, sv)
            elif kind == "chip":
                new = conversation.choose(cs, value, sv)
            elif kind == "edit":
                new = conversation.edit(cs, value)
            else:
                new = conversation.skip_rest(cs, sv)
        except Exception:  # noqa: BLE001  엔진이 깨져도 화면은 멈추지 않는다
            s["chat_problem"] = "지금은 이 답을 처리하지 못했어요. 한 번 더 눌러 보시거나, 조금 뒤에 다시 해 주세요."
            return
    s["chat_problem"] = ""
    s["chat"] = new
    state.sync_from_chat()


# ── 말풍선 ────────────────────────────────────────────────

def _md(text: object) -> str:
    """사용자가 쓴 글이 마크다운 서식으로 읽히지 않게 하고, 줄바꿈은 살린다."""
    return str(text).replace("$", "\\$").replace("~", "\\~").replace("\n", "  \n")


def _confirm_card(t: conversation.Turn) -> None:
    st.markdown("이렇게 이해했어요.")
    with st.container(border=True):
        for it in t.data.get("items") or []:
            st.markdown("**{}** · {}".format(it["label"], it["value"] or "아직"))
    st.markdown("맞나요?")


def _market_card(t: conversation.Turn) -> None:
    d = t.data
    if not d.get("recommended"):
        st.warning(t.text)
        return
    with st.container(border=True):
        if d.get("headline"):
            st.markdown("**{}**".format(_md(d["headline"])))
        st.markdown("광고에 쓸 단어: " + ", ".join("`{}`".format(w) for w in d["recommended"][:8]))
        if d.get("negatives"):
            st.markdown("뺄 단어: " + ", ".join("`{}`".format(w) for w in d["negatives"][:6]))
        st.caption(ui.market_source(d.get("fetched")))
    st.markdown(t.text.split("\n\n")[-1])


def _budget_card(t: conversation.Turn) -> None:
    p = t.data.get("plan") or {}
    with st.container(border=True):
        st.markdown("**한 달 광고비** · {}".format(ui.won(p.get("budget"))))
        if p.get("naver_daily"):
            st.markdown("**네이버 하루 예산** · {}".format(ui.won(p.get("naver_daily"))))
        if p.get("meta_daily"):
            st.markdown("**메타 하루 예산** · {}".format(ui.won(p.get("meta_daily"))))
        for n in t.data.get("notes") or []:
            st.caption(n)


def _help_turn(cs: dict, t: conversation.Turn, live: bool) -> None:
    kind = str(t.data.get("kind") or "help")
    if t.data.get("stream") and live:
        gen = conversation.take_stream(cs)
        if gen is not None:
            text = st.write_stream(gen)
            st.session_state["chat"] = conversation.set_help_text(st.session_state["chat"], text if isinstance(text, str) else "")
        else:
            st.markdown("답을 불러오지 못했어요.")
    elif t.text:
        st.markdown(_md(t.text))
    note = HELP_NOTE.get(kind, "")
    if note:
        st.caption(note)
    if t.data.get("sources"):
        st.caption("출처  \n" + ui.sources_md(t.data["sources"]))


def _turn(cs: dict, t: conversation.Turn, live: bool) -> None:
    if t.role == "user":
        with st.chat_message("user"):
            st.markdown(_md(t.text))
        return
    with st.chat_message("assistant"):
        if t.kind == "confirm_card":
            _confirm_card(t)
        elif t.kind == "market_card":
            _market_card(t)
        elif t.kind == "budget_card":
            _budget_card(t)
        elif t.kind == "help":
            _help_turn(cs, t, live)
        elif t.kind == "error":
            st.error(t.text)
        elif t.kind == "done":
            st.success(t.text)
        else:
            st.markdown(_md(t.text))
        if t.kind in ("text", "confirm_card", "market_card", "budget_card") and t.data.get("qid"):
            if t.data.get("why"):
                st.caption("왜 묻나요? " + str(t.data["why"]))


# ── 위쪽 띠: 진행 · 고치기 · 권장 답 ─────────────────────

def position(cs: dict) -> str:
    """지금 위치 숫자 (예: "3/12"). 위쪽 진행 표시와 작업판의 캐릭터 말풍선이 같은 값을 쓴다.
    칸 질문 단계면 몇 번째 칸인지, 그 밖에는 몇 번째 단계인지."""
    p = conversation.progress(cs)
    if p["done"]:
        return ""
    if p["label"] == p["stages"][-1] and p["question_total"]:
        return "{}/{}".format(p["question_no"], p["question_total"])
    return "{}/{}".format(p["index"] + 1, len(p["stages"]))


def _progress(cs: dict) -> None:
    p = conversation.progress(cs)
    n = len(p["stages"])
    if p["done"]:
        st.progress(1.0, text="세팅 대화가 끝났어요")
        return
    text = "{}/{} · {}".format(p["index"] + 1, n, " → ".join(
        ("**{}**".format(x) if i == p["index"] else x) for i, x in enumerate(p["stages"])))
    if p["label"] == p["stages"][-1] and p["question_total"]:
        text += "  ({}/{}번째 칸)".format(p["question_no"], p["question_total"])
    st.progress(p["index"] / n, text=text)


def _tools(cs: dict) -> None:
    c1, c2 = st.columns(2)
    with c1.popover("지난 답 고치기", icon=":material/edit:", use_container_width=True):
        items = conversation.editable(cs)
        if not items:
            st.caption("아직 고칠 답이 없어요.")
        for it in items:
            st.button("{} · {}".format(it["label"], str(it["value"])[:26]), key="edit_" + it["key"],
                      on_click=_push, args=("edit", it["key"]), use_container_width=True)
    if cs["phase"] == "ask":
        c2.button("남은 질문은 권장 답으로", key="chat_skip_rest", icon=":material/fast_forward:",
                  on_click=_push, args=("skip", ""), use_container_width=True,
                  help="비워 둔 칸을 칸 사양의 권장 답이나 예시로 채워요. 시트에서 언제든 다시 고칠 수 있어요.")


def _chips(cs: dict) -> List[Tuple[str, str]]:
    """(보이는 글, 보낼 말). 마지막 bot 말풍선의 칩 + (예시일 때) 예시 단어."""
    last = conversation.last_turn(cs)
    if last is None or last.role != "bot" or cs["phase"] == "done":
        return []
    out = [(c, c) for c in last.chips]
    if st.session_state.get("is_demo") and cs["phase"] == "market" and cs["step"] == "seeds":
        out.insert(0, (DEMO_SEEDS_CHIP, ", ".join(state.DEMO_SEEDS)))
    return out


def _placeholder(cs: dict) -> str:
    if cs["phase"] == "done":
        return "궁금한 걸 물어보세요"
    return "여기에 답을 적어요. 모르는 건 물어봐도 돼요"


# ── 화면 ──────────────────────────────────────────────────

def render() -> None:
    """오른쪽 대화 전체를 그린다 (대화가 없으면 아무것도 그리지 않음)."""
    s = st.session_state
    cs = s.get("chat")
    if cs is None:
        return
    _progress(cs)
    _tools(cs)
    if s.get("chat_problem"):
        st.error(s["chat_problem"])
    history = st.container(height=CHAT_HEIGHT, key="chat_history")
    ts = conversation.turns(cs)
    streaming = max([i for i, t in enumerate(ts) if t.kind == "help" and t.data.get("stream")], default=-1)
    with history:
        for i, t in enumerate(ts):
            _turn(cs, t, live=(i == streaming))
    cs = s["chat"]    # 스트리밍이 끝난 글이 들어간 최신 상태
    chips = _chips(cs)
    if chips:
        with st.container(key="chat_chips"):
            for row in range(0, len(chips), 2):
                cols = st.columns(2)
                for j, (label, send) in enumerate(chips[row:row + 2]):
                    cols[j].button(label, key="chip_{}".format(row + j), use_container_width=True,
                               on_click=_push, args=("text" if label != send else "chip", send))
    st.chat_input(_placeholder(cs), key="chat_text", on_submit=_on_submit)
