"""안내 캐릭터 공용 부품: ① 세팅 · ② 실행 · ③ 진단이 같이 쓴다.

- 오른쪽 대화가 지금 말하는 칸·카드(focus)를 왼쪽 작업판에서 캐릭터가 가리킨다.
- 화면은 먼저 set_focus()로 가리킬 대상을 정하고, 작업판의 칸·카드(st.container(key="t-<id>")) 안에서 here("<id>")를 부른다.
- 캐릭터는 장식이다. 같은 내용이 오른쪽 대화와 강조 테두리·화살표 글에도 있어야 한다 (UX 설계원칙).
- '캐릭터 보이기' 토글은 쪽을 옮겨도 고른 값을 기억한다.
"""
from typing import Optional

import streamlit as st

from v2.app import ui

COLS_KEYS = ("setup_cols", "run_cols", "diag_cols")     # 좁은 화면에서 대화를 위로 올릴 열 묶음 키
TOGGLE_KEY = "w_guide"
PREF_KEY = "guide_pref"
FOCUS_KEY = "guide_focus"

CSS = """<style>
.coach{display:flex;justify-content:flex-end;align-items:center;gap:8px;margin:2px 0;
 animation:coach-in .5s ease-out both}
.coach-face{display:inline-flex;gap:6px;align-items:center;justify-content:center;width:34px;height:34px;
 border-radius:50%;background:#2F5D8A;flex:none}
.coach-face i{width:6px;height:6px;border-radius:50%;background:#fff;display:block}
.coach-bubble{background:#F7F8FA;border:2px solid #2F5D8A;border-radius:12px;padding:3px 10px;
 font-size:.85rem;color:#2B3340}
.coach-hand{color:#2F5D8A;font-weight:700}
[class*="st-key-t-"]:has(.coach){border:3px solid #2F5D8A !important;background:#F4F7FB}
@keyframes coach-in{from{transform:translateX(60px);opacity:0}to{transform:none;opacity:1}}
@media (prefers-reduced-motion:reduce){.coach{animation:none}}
@media (min-width:641px){
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


def set_focus(fid: Optional[str], say: str = "") -> None:
    """지금 가리킬 대상 (컨테이너 키에서 't-'를 뺀 것). None이면 아무것도 가리키지 않음."""
    st.session_state[FOCUS_KEY] = (fid, say) if fid else None


def focus() -> Optional[str]:
    cur = st.session_state.get(FOCUS_KEY)
    return cur[0] if cur else None


def here(my_id: str) -> bool:
    """내 컨테이너가 지금 가리키는 대상이면 캐릭터와 말풍선을 그린다 (끄면 안 그림, 좁은 화면에서는 CSS가 숨김).
    반환: 내가 가리키는 대상인가 (호출한 쪽이 강조 글·테두리를 정할 때 쓴다)."""
    cur = st.session_state.get(FOCUS_KEY)
    if not cur or cur[0] != my_id:
        return False
    if enabled():
        st.markdown('<div class="coach"><span class="coach-bubble">{}</span><span class="coach-hand">&#9654;</span>'
                    '<span class="coach-face"><i></i><i></i></span></div>'.format(cur[1] or FIELD_SAY),
                    unsafe_allow_html=True)
    return True


def scroll(fid: Optional[str] = None) -> None:
    """부모 문서에서 가리킬 칸을 화면 가운데로. 막혀 있거나 좁은 화면(대화가 위)이면 조용히 건너뛴다."""
    fid = fid or focus()
    if not fid:
        return
    import streamlit.components.v1 as components
    js = ("<script>try{var p=window.parent;if(p.innerWidth>640){var e=p.document.querySelector('.st-key-t-" + fid +
          "');if(e){e.scrollIntoView({block:'center',behavior:'smooth'});}}}catch(x){}</script>")
    components.html(js, height=0)
