"""코치 3단계 '광고 관리자 세팅 도우미' 화면 (MVP 7·7d). main.py에서 떼어 냄 (main.py가 더 커지지 않게).

7d 1단계: 처음에 매체를 고른다 (네이버 / 메타 / 둘 다 = 네이버 먼저). 고른 매체 카드에서만 찾고,
'뭐부터 해? / 어떻게 나눠?'는 카드 대신 코치 배분 숫자로 답한다 (setup_rag.route).
"""
from typing import Dict, List, Optional

import streamlit as st

from src.engine import chat_intake as CI
from src.engine import guide as GD
from src.engine import setup_rag as SR
from src.engine.insights import won

PHASE_NAMES = {"naver": "네이버", "meta": "메타"}
PLACEHOLDER = {"naver": "예: 하루 예산 어디에 넣어?", "meta": "예: 목표 뭐 골라?"}


def card_source_md(c) -> str:
    links = " · ".join(f"[출처 {i + 1}]({u})" for i, u in enumerate(c.sources) if u.startswith("http"))
    return f"{c.check} {SR.CHECK_WORDS.get(c.check, '')} · `{c.id}` {c.title}" + (f" · {links}" if links else "")


def setup_numbers(a: dict, ss, stores: List[str]) -> dict:
    """세팅 카드 위 '내 숫자'에 쓸 값: 엔진·guide가 이미 계산한 것만 모음 (새 계산 없음)."""
    sp = a["split"]
    new = max(a["prediction"]["new"], 1e-9)
    only_ss = "스마트스토어" in stores and "자사몰" not in stores
    mp = GD.meta_plan(sp.meta.spend, a["budget0"] / new, bool(ss.get("pixel_ready")), stores, sp.meta.cpc)
    return {"naver": sp.naver_spend, "naver_daily": GD.daily_budget(sp.naver_spend), "meta": sp.meta.spend, "meta_daily": mp["daily"],
            "meta_rec_daily": mp["recommended_daily"], "meta_objective": mp["objective"],
            "bid": GD.naver_bid_at(sp.naver.curve, sp.naver_spend) if sp.has_naver else None,
            "shopping_min": GD.NAVER_MIN_BID["쇼핑검색"], "smartstore": only_ss or "스마트스토어" in stores,
            "keyword": a["kw"], "cpa": a["budget0"] / new, "be_first": a["be"].first,
            "no_ad": a["default_pick"] == "none"}


def phase_of(ss) -> str:
    """지금 세팅 중인 매체. '둘 다'면 네이버 먼저, 넘어가기를 누르면 메타."""
    choice = ss.get("setup_media", "both")
    if choice == "both":
        return ss.get("setup_phase", "naver")
    return choice


def setup_ask(a: dict, ss, q: str, media: str, price: Optional[float], stores: List[str], img=None):
    """질문 → (코치 배분 / 카드 찾기 → 키 있으면 답). 결과는 세션에 남겨 다시 그릴 때 씀."""
    sp = a["split"]
    kind, found = SR.route(q, media)
    res: Dict = {"q": q, "kind": kind, "found": [c.id for c, _ in found], "answer": None, "used": [], "note": None,
                 "coach": SR.coach_answer(sp, a["kw"], a["default_pick"] == "none") if kind == "coach" else None}
    client = CI.make_client()
    if found and client is not None:
        ctx = {"naver": sp.naver_spend, "meta": sp.meta.spend, "keyword": a["kw"], "price": price, "wins": a["mc"]["wins"],
               "stores": stores}
        try:
            image = (img.getvalue(), img.name) if img is not None else None
            out = SR.answer(client, q, found, ctx, image)
            res["answer"], res["used"] = out["answer"], [c.id for c in out["cards"]]
        except ValueError as e:                      # 캡처 크기·형식
            res["note"] = str(e)
        except CI.IntakeUnavailable as e:
            res["note"] = f"지금은 답을 만들 수 없어 자료를 그대로 보여 드려요 ({e})."
    ss["setup_last"] = res


def _media_picker(a: dict, ss) -> str:
    """처음에 매체 고르기 (7d 1단계). 코치 배분으로 미리 골라 두고, 사장님이 바꾸면 그대로 둠."""
    sp = a["split"]
    default = SR.default_media(sp.naver_spend, sp.meta.spend)
    if not ss.get("_setup_media_touched") or ss.get("setup_media") not in SR.MEDIA_CHOICES:
        ss["setup_media"] = default
    st.radio("어느 광고부터 세팅할까요?", list(SR.MEDIA_CHOICES), format_func=lambda k: SR.MEDIA_CHOICES[k], horizontal=True,
             key="setup_media", on_change=lambda: ss.__setitem__("_setup_media_touched", True))
    why = {"both": "코치 배분에 네이버·메타가 모두 있어서 둘 다 골라 뒀어요. 네이버는 검토(보통 영업일 1~2일)가 있어 먼저 해요.",
           "naver": "코치 배분에서 메타가 0원이라 네이버만 골라 뒀어요.",
           "meta": "코치 배분에서 네이버가 0원이라 메타만 골라 뒀어요."}[default]
    st.caption(f"{why} 코치 배분: 네이버 {won(sp.naver_spend)} · 메타 {won(sp.meta.spend)}. 바꿔도 돼요.")
    phase = phase_of(ss)
    if ss["setup_media"] == "both":
        c1, c2 = st.columns([3, 2])
        c1.markdown(f"**지금: {PHASE_NAMES[phase]} 세팅 중** ({'1' if phase == 'naver' else '2'}/2)")
        if phase == "naver":
            if c2.button("네이버 다 했어요 → 메타로", key="setup_to_meta"):
                ss["setup_phase"], ss["setup_last"] = "meta", None
                st.rerun()
        elif c2.button("← 네이버로 돌아가기", key="setup_to_naver"):
            ss["setup_phase"], ss["setup_last"] = "naver", None
            st.rerun()
    return phase


def render(a: dict, ss, stores: List[str], price: Optional[float]):
    """세팅 도우미: 매체 고르기 → 매체별 추천 질문 칩·질문칸 → 코치 숫자 답 / 카드(키 있으면 Claude 답)."""
    st.markdown("#### 🙋 광고 관리자 세팅 도우미")
    phase = _media_picker(a, ss)
    if a["default_pick"] == "none":
        st.caption("지금은 **광고 안 함**을 추천해요. 그래도 시작한다면 아래 안내대로 세팅하면 돼요.")
    chip = st.pills("이런 걸 물어볼 수 있어요", SR.CHIPS[phase], key=f"setup_chip_{phase}")
    client = CI.make_client()
    img = None
    if chip and ss.get("_setup_chip_used") != (phase, chip):   # 칩을 누르면 바로 답 (입력칸에도 남겨 고쳐 다시 물을 수 있게)
        ss["setup_q"], ss["_setup_chip_used"] = chip, (phase, chip)
        setup_ask(a, ss, chip, phase, price, stores)
    q = st.text_input(f"{PHASE_NAMES[phase]} 광고 관리자에서 막힌 곳", key="setup_q", placeholder=PLACEHOLDER[phase])
    if client is not None:
        img = st.file_uploader("화면 캡처 (선택, png·jpg 5MB 이하)", type=["png", "jpg", "jpeg"], key="setup_img")
        st.caption("계정 이름·카드 정보는 가리고 올려 주세요. 질문과 캡처는 답을 만들기 위해 Anthropic으로 보내집니다. 캡처는 저장하지 않아요.")
    if st.button("물어보기", key="setup_ask", disabled=not q):
        setup_ask(a, ss, q, phase, price, stores, img)
    _show_result(a, ss, stores)


def _show_result(a: dict, ss, stores: List[str]):
    res = ss.get("setup_last")
    if not res:
        return
    if res.get("kind") == "coach":
        with st.container(border=True):
            st.markdown(res["coach"])
            st.caption("🧮 코치 배분 숫자로 답했어요 (2단계 '답 보기'와 같은 계산).")
        return
    if not res["found"]:
        st.info("자료에 없어요. 네이버 검색광고·메타 광고 관리자 세팅에 관한 질문으로 다시 물어봐 주세요.", icon="🔎")
        return
    if res["note"]:
        st.warning(res["note"], icon="📝")
    if res["answer"]:
        with st.container(border=True):
            st.markdown(res["answer"])
            for cid in res["used"]:
                c = SR.by_id(cid)
                if c:
                    st.caption(card_source_md(c))
        return
    st.caption(f"'{res['q']}'에 맞는 세팅 자료예요 (답을 만드는 AI는 아직 연결 전이라 자료와 내 숫자를 함께 보여 드려요).")
    nums = setup_numbers(a, ss, stores)
    for s in SR.summaries([(SR.by_id(i), 0) for i in res["found"] if SR.by_id(i)]):
        c = SR.by_id(s["id"])
        mine = SR.my_numbers(c, nums)
        with st.container(border=True):
            if mine:
                st.markdown("🧮 **내 숫자**: " + " · ".join(mine))
            st.markdown(f"**{s['title']}** {s['check']}  \n{s['body']}")
            if s["screen"]:
                st.caption("화면에서 찾을 곳: " + s["screen"])
            st.caption(card_source_md(c))
