"""안내 캐릭터 공용 부품: ① 세팅 · ② 실행 · ③ 진단이 같이 쓴다.

- 오른쪽 대화가 지금 말하는 칸·카드(focus)를 왼쪽 작업판에서 캐릭터가 가리킨다.
- 화면은 먼저 set_focus()로 가리킬 대상을 정하고, 작업판의 칸·카드(st.container(key="t-<id>")) 안에서 here("<id>")를 부른다.
- 캐릭터는 장식이다. 같은 내용이 오른쪽 대화와 강조 테두리·화살표 글에도 있어야 한다 (UX 설계원칙).
- '캐릭터 보이기' 토글은 쪽을 옮겨도 고른 값을 기억한다.
"""
from html import escape as esc
from typing import Optional

import streamlit as st

from v2.app import ui

COLS_KEYS = ("setup_cols", "run_cols", "diag_cols")     # 좁은 화면에서 대화를 위로 올릴 열 묶음 키
TOGGLE_KEY = "w_guide"
PREF_KEY = "guide_pref"
FOCUS_KEY = "guide_focus"

CSS = """<style>
.coach{display:flex;justify-content:flex-end;align-items:center;gap:12px;margin:4px 0;
 animation:coach-in .5s ease-out both}
.coach-face{display:inline-flex;gap:8px;align-items:center;justify-content:center;width:48px;height:48px;
 border-radius:50%;background:#2F5D8A;flex:none;position:relative;box-shadow:0 2px 6px rgba(47,93,138,.35)}
.coach-face i{width:8px;height:8px;border-radius:50%;background:#fff;display:block;margin-bottom:6px}
.coach-face:after{content:"";position:absolute;left:15px;right:15px;bottom:11px;height:6px;
 border-bottom:3px solid #fff;border-radius:0 0 12px 12px}
.coach-bubble{position:relative;background:#F7F8FA;border:2px solid #2F5D8A;border-radius:12px;padding:6px 12px;
 font-size:.9rem;line-height:1.35;color:#2B3340;max-width:75%}
.coach-bubble:before{content:"";position:absolute;left:-10px;top:50%;margin-top:-8px;border-style:solid;
 border-width:8px 10px 8px 0;border-color:transparent #2F5D8A transparent transparent}
.coach-bubble:after{content:"";position:absolute;left:-6px;top:50%;margin-top:-6px;border-style:solid;
 border-width:6px 8px 6px 0;border-color:transparent #F7F8FA transparent transparent}
.coach-label{font-weight:700}
.coach-prog{display:inline-block;margin-left:6px;padding:0 8px;border-radius:999px;background:#2F5D8A;color:#fff;
 font-size:.78rem;font-weight:600}
.coach-say{display:block;color:#6B7686;font-size:.85rem}
.t-on{display:none}
[class*="st-key-t-"]{transition:opacity .2s ease,box-shadow .2s ease}
[class*="st-key-t-"]:has(.t-on){border:3px solid #2F5D8A !important;background:#F4F7FB;
 box-shadow:0 4px 14px rgba(47,93,138,.22)}
.sr-live{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
[data-testid="stElementContainer"]:has(.sr-live){position:absolute;height:0;margin:0;overflow:hidden}
@keyframes coach-in{from{transform:translateX(60px);opacity:0}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){.coach{animation:none}[class*="st-key-t-"]{transition:none}}
@media (min-width:641px){
 [class*="st-key-board_"]:has(.t-dim) [class*="st-key-t-"]:not(:has(.t-on)){opacity:.45}
 [class*="st-key-setup_cols"]>div>[data-testid="stHorizontalBlock"],
 [class*="st-key-run_cols"]>div>[data-testid="stHorizontalBlock"],
 [class*="st-key-diag_cols"]>div>[data-testid="stHorizontalBlock"]{align-items:flex-start}
 [class*="st-key-setup_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child,
 [class*="st-key-run_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child,
 [class*="st-key-diag_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child{position:sticky;top:4rem}
}
@media (max-width:640px){
 .coach{display:none}
 [class*="st-key-setup_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child,
 [class*="st-key-run_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child,
 [class*="st-key-diag_cols"]>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child{order:-1}
}
</style>"""
FIELD_SAY = "이 칸에 들어가요"


def tid(text: object) -> str:
    """칸·카드를 가리킬 수 있는 컨테이너 키: 't-' + id ('.'는 '-')."""
    return "t-" + str(text).replace(".", "-")


def css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def enabled() -> bool:
    s = st.session_state
    return bool(s.get(TOGGLE_KEY, s.get(PREF_KEY, True)))


def _remember() -> None:
    st.session_state[PREF_KEY] = bool(st.session_state.get(TOGGLE_KEY))


def toggle() -> bool:
    """'캐릭터 보이기' 스위치 (즉시 반영). 쪽을 옮기면 위젯 값이 사라지므로, 고른 값을 따로 기억했다가 매번 넣어 준다."""
    st.session_state[TOGGLE_KEY] = st.session_state.get(PREF_KEY, True)
    return bool(st.toggle("캐릭터 보이기", key=TOGGLE_KEY, on_change=_remember,
                          help="끄면 왼쪽 작업판에서 칸을 가리키는 캐릭터가 사라져요. 강조 테두리는 그대로예요."))


def board_container(name: str):
    """왼쪽 작업판 전체를 감싸는 컨테이너. 스포트라이트(다른 칸 흐리게)는 이 안에서만 일어나고 오른쪽 대화는 건드리지 않는다."""
    return st.container(key="board_" + name)


def set_focus(fid: Optional[str], say: str = "", label: str = "", prog: str = "") -> None:
    """지금 가리킬 대상 (컨테이너 키에서 't-'를 뺀 것). None이면 아무것도 가리키지 않음.
    label: 칸·카드 이름, prog: 오른쪽 대화가 보여 주는 진행 숫자 문자열(예: "3/12")."""
    st.session_state[FOCUS_KEY] = (fid, say, label, prog) if fid else None


def focus() -> Optional[str]:
    cur = st.session_state.get(FOCUS_KEY)
    return cur[0] if cur else None


def _label_prog() -> tuple:
    cur = st.session_state.get(FOCUS_KEY)
    return (cur[2], cur[3]) if cur and len(cur) > 3 else ("", "")


def here(my_id: str, label: Optional[str] = None) -> bool:
    """내 컨테이너가 지금 가리키는 대상이면 표시를 남기고 캐릭터와 말풍선을 그린다.
    - 표시(.t-on)는 캐릭터를 꺼도 남는다: 강조 테두리의 근거. 캐릭터를 켜면 .t-dim도 붙어 작업판의 다른 칸이 흐려진다.
    - 캐릭터·말풍선은 장식(aria-hidden): 같은 내용은 화면에 안 보이는 알림 영역(live)과 오른쪽 대화에 있다.
    label을 주면 이 칸의 이름으로 기억한다 (칸 이름을 그리는 쪽에서만 아는 경우).
    반환: 내가 가리키는 대상인가 (호출한 쪽이 강조 글·테두리를 정할 때 쓴다)."""
    cur = st.session_state.get(FOCUS_KEY)
    if not cur or cur[0] != my_id:
        return False
    if label:
        cur = (cur[0], cur[1], label, cur[3] if len(cur) > 3 else "")
        st.session_state[FOCUS_KEY] = cur
    on = enabled()
    html = '<i class="t-on{}" aria-hidden="true"></i>'.format(" t-dim" if on else "")
    if on:
        name, prog = _label_prog()
        html += ('<div class="coach" aria-hidden="true"><div class="coach-bubble">'
                 '<span class="coach-label">{}</span>{}<span class="coach-say">{}</span></div>'
                 '<span class="coach-face"><i></i><i></i></span></div>').format(
            esc(name), '<span class="coach-prog">{}</span>'.format(esc(prog)) if prog else "", esc(cur[1] or FIELD_SAY))
    st.markdown(html, unsafe_allow_html=True)
    return True


def live_text() -> str:
    """화면 읽기 프로그램이 읽어 줄 글: '지금 보는 칸: 종료 날짜 (3/12)'. 가리키는 대상이 없으면 빈 글."""
    cur = st.session_state.get(FOCUS_KEY)
    if not cur:
        return ""
    name, prog = _label_prog()
    name = name or (cur[1] or FIELD_SAY)
    return "지금 보는 칸: {}{}".format(name, " ({})".format(prog) if prog else "")


def live() -> None:
    """눈에는 안 보이는 aria-live 알림 영역. 작업판을 다 그린 뒤 쪽마다 한 번 부른다 (캐릭터를 꺼도 그대로 둔다)."""
    st.markdown('<div class="sr-live" role="status" aria-live="polite" aria-atomic="true">{}</div>'.format(esc(live_text())),
                unsafe_allow_html=True)
    scroll_chat()


CHAT_SCROLL_JS = (
    "<script>try{var p=window.parent,d=p.document;var go=function(){var m=d.querySelectorAll('[data-testid=\"stChatMessage\"]');"
    "if(!m.length)return;var e=m[m.length-1].closest('[class*=\"_history\"]');"
    "if(!e||p.getComputedStyle(e).overflowY==='visible')return;"
    "if(e.scrollHeight>e.clientHeight+1){e.scrollTo({top:e.scrollHeight,behavior:'auto'});}};"
    "go();setTimeout(go,120);setTimeout(go,400);}catch(x){}</script>")


def scroll_chat() -> None:
    """오른쪽 대화 기록(높이 고정 상자)을 매번 맨 아래 = 가장 새 말풍선으로 (위로 올려 읽는 건 그대로 가능). 작업판은 건드리지 않는다.
    움직임 줄이기 설정과 상관없이 바로 이동(부드러운 스크롤 없음)."""
    import streamlit.components.v1 as components
    n = st.session_state.get("_chat_scroll_n", 0) + 1       # 매번 다른 글이어야 쪽이 같은 틀을 다시 실행한다
    st.session_state["_chat_scroll_n"] = n
    components.html(CHAT_SCROLL_JS.replace("</script>", "/*{}*/</script>".format(n)), height=0)


def scroll(fid: Optional[str] = None) -> None:
    """부모 문서에서 가리킬 칸이 화면 밖일 때만 가운데로 (부드럽게, 움직임 줄이기 설정이면 바로). 막혀 있거나 좁은 화면이면 건너뜀."""
    fid = fid or focus()
    if not fid:
        return
    import streamlit.components.v1 as components
    js = ("<script>try{var p=window.parent;if(p.innerWidth>640){var e=p.document.querySelector('.st-key-t-" + esc(fid) +
          "');if(e){var r=e.getBoundingClientRect();var h=p.innerHeight||p.document.documentElement.clientHeight;"
          "if(r.top<70||r.bottom>h){var rm=p.matchMedia&&p.matchMedia('(prefers-reduced-motion: reduce)').matches;"
          "e.scrollIntoView({behavior:rm?'auto':'smooth',block:'center'});}}}}catch(x){}</script>")
    components.html(js, height=0)
