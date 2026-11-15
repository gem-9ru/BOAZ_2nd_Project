"""② 실행 · ③ 진단 공용: 오른쪽 안내 대화(작은 상태 기계)와 작업판 부품.

안내 대화는 '항목(step)을 하나씩 안내'한다. 대화 상태는 st.session_state[chat_key]에 JSON처럼 단순한 dict로 둔다.
- 안내 글은 대화 기록에 쓰지 않고 항목 번호만 적어 두었다가 그릴 때 만든다 (그래서 숫자가 항상 지금 값).
- 칩·글 입력은 콜백이 상태만 바꾸고, 화면은 그 새 상태로 왼쪽 작업판과 오른쪽 대화를 그린다.
- 사장님이 쓴 질문은 v2/engine/helpdesk.answer(서비스 help)로 보내고, 지금 항목의 칸·규칙을 맥락으로 준다.
step 모양: {"id": 컨테이너 id('t-' 뺀 것), "say": 말풍선 글, "title": 제목, "body": 안내 글(마크다운),
           "field": 도움말에 줄 칸 id 또는 None, "ctx": 도움말에 더 줄 맥락 dict}
"""
from typing import Dict, List, Optional

import streamlit as st

from v2.app import guide, state, ui

CHAT_HEIGHT = 480
HELP_NOTE = {"help": "도움말에 미리 적어 둔 답이에요.", "coach": "사장님 숫자로 바로 계산한 답이에요.",
             "llm": "AI가 도움말을 바탕으로 쓴 답이에요. 틀릴 수 있으니 출처도 함께 확인해 주세요.", "none": ""}
HELP_FAIL = "지금은 답을 찾지 못했어요. 조금 뒤에 다시 물어봐 주세요."


def mark(focused: bool) -> str:
    """지금 설명 중인 칸·카드 앞에 붙일 글 (색이 아니라 화살표 아이콘 + 글자로도 구분)."""
    return ":material/arrow_right: " if focused else ""


# ── 대화 상태 ─────────────────────────────────────────────

def _fresh(sig: object, n: int) -> dict:
    """처음 상태: 첫 항목을 바로 안내."""
    turns = [{"role": "bot", "kind": "intro"}] + ([{"role": "bot", "kind": "step", "i": 0}] if n else [])
    return {"sig": sig, "pos": 0, "turns": turns, "n": n, "fields": [], "ids": [], "ctx": {}}


def ensure(chat_key: str, sig: object, steps: List[dict], ctx: Optional[dict] = None) -> dict:
    """대화 상태를 준비한다. sig(어느 자료를 보고 있는지)가 바뀌었으면 처음부터 다시."""
    s = st.session_state
    cs = s.get(chat_key)
    if not isinstance(cs, dict) or cs.get("sig") != sig or cs.get("n") != len(steps):
        cs = _fresh(sig, len(steps))
    cs["fields"] = [x.get("field") for x in steps]       # 콜백이 쓰도록 지금 항목 정보를 적어 둔다
    cs["ctxs"] = [x.get("ctx") or {} for x in steps]
    cs["ids"] = [x["id"] for x in steps]
    cs["says"] = [x.get("say", "") for x in steps]
    cs["ctx"] = dict(ctx or {})
    cs["n"] = len(steps)
    s[chat_key] = cs
    return cs


def pos(chat_key: str) -> int:
    cs = st.session_state.get(chat_key) or {}
    return int(cs.get("pos", 0))


def focus_id(chat_key: str) -> Optional[str]:
    cs = st.session_state.get(chat_key) or {}
    ids = cs.get("ids") or []
    p = int(cs.get("pos", 0))
    return ids[p] if 0 <= p < len(ids) else None


def point(chat_key: str) -> Optional[str]:
    """지금 항목을 캐릭터가 가리키게 정하고 그 id를 돌려준다."""
    cs = st.session_state.get(chat_key) or {}
    fid = focus_id(chat_key)
    p = int(cs.get("pos", 0))
    guide.set_focus(fid, (cs.get("says") or [""] * (p + 1))[p] if fid else "")
    return fid


def _next(chat_key: str, label: str) -> None:
    cs = st.session_state.get(chat_key)
    if not cs or cs["pos"] + 1 >= cs["n"]:
        return
    cs["pos"] += 1
    cs["turns"] += [{"role": "user", "kind": "text", "text": label}, {"role": "bot", "kind": "step", "i": cs["pos"]}]


def _restart(chat_key: str) -> None:
    cs = st.session_state.get(chat_key)
    if cs:
        new = _fresh(cs["sig"], cs["n"])
        new.update({k: cs[k] for k in ("fields", "ctxs", "ids", "says", "ctx")})
        st.session_state[chat_key] = new


def _ask(chat_key: str, text_key: str) -> None:
    """글로 쓴 질문 → 도움말 엔진. 지금 항목의 칸·규칙을 맥락으로 준다. 항목 위치는 그대로."""
    s = st.session_state
    text = (s.get(text_key) or "").strip()
    cs = s.get(chat_key)
    if not text or not cs:
        return
    p = cs["pos"]
    field = (cs.get("fields") or [None])[p] if p < len(cs.get("fields") or []) else None
    ctx = dict(cs.get("ctx") or {})
    ctx.update((cs.get("ctxs") or [{}])[p] if p < len(cs.get("ctxs") or []) else {})
    cs["turns"].append({"role": "user", "kind": "text", "text": text})
    try:
        ans = state.services().help(text, field, ctx)
        data = {"kind": str(getattr(ans, "kind", "none") or "none"), "sources": list(getattr(ans, "sources", None) or []),
                "stream": False}
        body = str(getattr(ans, "text", "") or "")
        stream = getattr(ans, "stream", None)
        if data["kind"] == "llm" and stream is not None:
            data["stream"] = True
            s[chat_key + "_stream"] = stream
        turn = {"role": "bot", "kind": "help", "text": body, "data": data}
    except Exception:  # noqa: BLE001  도움말이 깨져도 화면은 멈추지 않는다
        turn = {"role": "bot", "kind": "help", "text": HELP_FAIL, "data": {"kind": "none", "sources": [], "stream": False}}
    cs["turns"].append(turn)


# ── 그리기 ────────────────────────────────────────────────

def _md(text: object) -> str:
    return str(text).replace("$", "\\$").replace("~", "\\~").replace("\n", "  \n")


def _step_turn(cs: dict, i: int, steps: List[dict]) -> None:
    if i >= len(steps):
        st.markdown("(이 안내는 자료가 바뀌어 사라졌어요.)")
        return
    x = steps[i]
    st.markdown("**{}** · {}/{}".format(x["title"], i + 1, len(steps)))
    if x.get("body"):
        st.markdown(x["body"])


def _help_turn(chat_key: str, t: dict, live: bool) -> None:
    data = t.get("data") or {}
    s = st.session_state
    if data.get("stream") and live:
        gen = s.pop(chat_key + "_stream", None)
        if gen is not None:
            text = st.write_stream(gen)
            t["text"] = text if isinstance(text, str) else ""
        else:
            t["text"] = HELP_FAIL
            st.markdown(HELP_FAIL)
        data["stream"] = False
    elif t.get("text"):
        st.markdown(_md(t["text"]))
    note = HELP_NOTE.get(str(data.get("kind") or ""), "")
    if note:
        st.caption(note)
    if data.get("sources"):
        st.caption("출처  \n" + ui.sources_md(data["sources"]))


def render_chat(chat_key: str, steps: List[dict], intro: str, next_label: str, last_label: str = "처음부터 다시 듣기",
                placeholder: str = "궁금한 걸 물어보세요") -> None:
    """오른쪽 대화: 말풍선 기록(높이 고정) · 칩 · 입력창. ensure()를 먼저 불러 둘 것."""
    s = st.session_state
    cs = s[chat_key]
    text_key = chat_key + "_text"
    turns = cs["turns"]
    live = max([i for i, t in enumerate(turns) if t["kind"] == "help" and (t.get("data") or {}).get("stream")], default=-1)
    with st.container(height=CHAT_HEIGHT, key=chat_key + "_history"):
        for i, t in enumerate(turns):
            if t["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(_md(t["text"]))
                continue
            with st.chat_message("assistant"):
                if t["kind"] == "intro":
                    st.markdown(intro)
                elif t["kind"] == "step":
                    _step_turn(cs, int(t["i"]), steps)
                else:
                    _help_turn(chat_key, t, live=(i == live))
    if steps:
        with st.container(key=chat_key + "_chips"):
            if cs["pos"] + 1 < len(steps):
                st.button(next_label, key=chat_key + "_next", icon=":material/arrow_forward:", use_container_width=True,
                          on_click=_next, args=(chat_key, next_label))
            else:
                st.button(last_label, key=chat_key + "_again", icon=":material/replay:", use_container_width=True,
                          on_click=_restart, args=(chat_key,))
    st.chat_input(placeholder, key=text_key, on_submit=_ask, args=(chat_key, text_key))
