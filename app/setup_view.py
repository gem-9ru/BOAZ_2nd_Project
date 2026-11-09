"""코치 3단계 '광고 관리자 세팅 도우미' 화면 (MVP 7·7d). main.py에서 떼어 냄 (main.py가 더 커지지 않게).

7d 1단계: 처음에 매체를 고른다 (네이버 / 메타 / 둘 다 = 네이버 먼저). 고른 매체 카드에서만 찾고,
'뭐부터 해? / 어떻게 나눠?'는 카드 대신 코치 배분 숫자로 답한다 (setup_rag.route).
7d 3단계: 고른 매체의 세팅 순서를 한 단계씩 보여 주고, 단계마다 광고 세팅값(src/engine/ad_setup.py)을 모은다.
"이 값으로 할게요"로 다음 단계, "여기서 막혔어요"로 그 단계 카드에서 먼저 찾는 질문칸. 끝까지 가면 '광고 세팅값' 시트.
"""
import io
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from src.engine import ad_setup as AS
from src.engine import chat_intake as CI
from src.engine import coach as CO
from src.engine import measure as MS
from src.engine import setup_rag as SR
from src.engine.insights import won

PHASE_NAMES = {"naver": "네이버", "meta": "메타"}
PLACEHOLDER = {"naver": "예: 하루 예산 어디에 넣어?", "meta": "예: 목표 뭐 골라?"}
LINK_CHANNEL = {"naver": "naver_search", "meta": "meta"}
COPY_KINDS = {"title": "naver_title", "pl_title": "naver_title", "description": "naver_desc", "pl_description": "naver_desc",
              "promo1": "naver_promo1", "primary_text": "meta_text", "headline": "meta_headline"}


def card_source_md(c) -> str:
    links = " · ".join(f"[출처 {i + 1}]({u})" for i, u in enumerate(c.sources) if u.startswith("http"))
    return f"{c.check} {SR.CHECK_WORDS.get(c.check, '')} · `{c.id}` {c.title}" + (f" · {links}" if links else "")


def phase_of(ss) -> str:
    """지금 세팅 중인 매체. '둘 다'면 네이버 먼저, 넘어가기를 누르면 메타."""
    choice = ss.get("setup_media", "both")
    if choice == "both":
        return ss.get("setup_phase", "naver")
    return choice


# ── 광고 세팅값 (ad_setup 한 곳에서 계산, 사장님이 고친 값만 화면 상태에서) ─────────────────
def _wkey(media: str, key: str) -> str:
    return f"set_{media}_{key}"


def _to_widget(v):
    return ", ".join(v) if isinstance(v, list) else v


def _from_widget(v, like):
    if isinstance(like, list):
        return [x.strip() for x in str(v or "").split(",") if x.strip()]
    if isinstance(like, int) and not isinstance(like, bool) and isinstance(v, float):
        return int(v)
    return v


def _links(ss, stores: List[str], kw: str) -> Dict[str, str]:
    """3단계 '링크 만들기'에 넣은 상품 주소로 매체별 꼬리표 링크 (없으면 빈칸)."""
    url, store = ss.get("link_url") or "", ss.get("link_store") or (stores[0] if stores else "자사몰")
    camp = MS.campaign_name(CO.today_kst().strftime("%y%m"), ss.get("link_product") or "")
    return {m: (MS.build_link(url, ch, store, camp) or "") if url else "" for m, ch in LINK_CHANNEL.items()}


def settings_plan(a: dict, ss, stores: List[str]) -> AS.SettingsPlan:
    """세팅값 한 벌. 기본값은 ad_setup, 사장님이 고친 값(위젯 값이 마지막 기본값과 다름)만 덮어씀."""
    links = _links(ss, stores, a["kw"])
    args = dict(answer=a["answer"], stores=stores, pixel_ready=bool(ss.get("pixel_ready")), media=ss.get("setup_media", "both"),
                keyword=a["kw"], product=ss.get("set_copy_product") or a["kw"], month=CO.today_kst().strftime("%y%m"),
                powerlink=bool(ss.get("setup_powerlink")), naver_link=links["naver"], meta_link=links["meta"])
    base = AS.build_settings(**args)
    last = ss.get("_set_defaults", {})
    owner = {}
    for s in base.steps:
        for it in s.items:
            wk = _wkey(s.media, it.key)
            if wk in ss and wk in last and ss[wk] != last[wk]:
                owner[f"{s.media}.{it.key}"] = _from_widget(ss[wk], it.value)
    return AS.build_settings(**args, owner=owner) if owner else base


def _item_widget(ss, media: str, it: AS.Item, default):
    """세팅값 한 칸. 사장님이 안 고친 칸은 코치 숫자가 바뀌면 따라감 (마지막 기본값을 기억)."""
    wk = _wkey(media, it.key)
    d = _to_widget(default)
    last = ss.setdefault("_set_defaults", {})
    if wk not in ss or ss[wk] == last.get(wk):
        ss[wk] = d
    last[wk] = d
    label = f"{it.source} {it.label}"
    if not it.editable:
        st.markdown(f"{label}: **{AS.show(it.value)}**")
    elif isinstance(default, bool):
        st.toggle(label, key=wk)
    elif isinstance(default, (int, float)):
        st.number_input(label, key=wk, min_value=0, step=10)
    else:
        st.text_input(label, key=wk, placeholder="비워 두면 시트에도 빈칸" if it.source == AS.DRAFT else None)
    if it.note:
        st.caption(it.note)
    kind = COPY_KINDS.get(it.key)
    if kind and ss.get(wk):
        for msg in AS.check_copy(str(ss[wk]), kind):
            st.caption("⚠️ " + msg)


def _copy_box(ss, step: AS.Step, client):
    """광고 문구 초안: 키가 있으면 AI 초안 3개, 없으면 사장님 답으로 틀 채우기. 어느 쪽이든 글자 수·심사 표현 검사."""
    with st.expander("✍️ 광고 문구 초안 만들기", expanded=not ss.get("copy_drafts")):
        c1, c2, c3 = st.columns(3)
        c1.text_input("상품 이름", key="set_copy_product", placeholder="예: 수제 마카롱 6구")
        c2.text_input("강점 (사실만)", key="set_copy_strength", placeholder="예: 당일 제작")
        c3.text_input("혜택 (상세페이지와 같게)", key="set_copy_benefit", placeholder="예: 선물 포장 무료")
        if st.button("문구 초안 만들기", key=f"copy_make_{step.media}_{step.key}", disabled=not ss.get("set_copy_product")):
            p, s, b = ss.get("set_copy_product", ""), ss.get("set_copy_strength", ""), ss.get("set_copy_benefit", "")
            drafts = None
            if client is not None:
                try:
                    with st.spinner("문구 초안을 쓰는 중…"):
                        drafts = SR.draft_copy(client, p, s, b)
                except CI.IntakeUnavailable as e:
                    st.caption(f"AI 초안을 만들지 못해 틀 채우기로 보여 드려요 ({e}).")
            ss["copy_drafts"] = drafts or [AS.draft_copy(p, s, b)]
        for i, d in enumerate(ss.get("copy_drafts") or []):
            with st.container(border=True):
                fields = ([("naver_title", "네이버 제목"), ("naver_desc", "네이버 설명")] if step.media == "naver"
                          else [("meta_headline", "메타 제목"), ("meta_text", "메타 기본 문구")])
                for k, name in fields:
                    st.markdown(f"**{name}**: {d.get(k, '')}")
                    for msg in AS.check_copy(d.get(k, ""), k):
                        st.caption("⚠️ " + msg)
                if st.button("이 초안 쓰기", key=f"copy_use_{step.media}_{step.key}_{i}"):
                    keys = {it.key for it in step.items}
                    pre = "pl_" if any(k.startswith("pl_") for k in keys) else ""
                    put = ({pre + "title": d["naver_title"], pre + "description": d["naver_desc"], "promo1": d["naver_title"][:AS.NAVER_PROMO1_MAX]}
                           if step.media == "naver" else {"headline": d["meta_headline"], "primary_text": d["meta_text"]})
                    for k, v in put.items():
                        if k in keys:
                            ss[_wkey(step.media, k)] = v
                    st.rerun()


def _step_guide(a: dict, ss, plan: AS.SettingsPlan, phase: str, client):
    """고른 매체의 세팅 순서 (한 단계씩). 진행 위치는 세션 안에서만 (계획 가정 5)."""
    steps = plan.for_media(phase)
    if not steps:
        st.info(f"이번 코치 배분에서는 {PHASE_NAMES[phase]} 예산이 0원이라 세팅할 게 없어요. 위에서 다른 매체를 골라 보세요.", icon="🧭")
        return None
    pk = f"setup_pos_{phase}"
    pos = min(max(ss.get(pk, 0), 0), len(steps) - 1)
    step = steps[pos]
    st.progress((pos + 1) / len(steps))
    st.markdown(f"**{PHASE_NAMES[phase]} {pos + 1}/{len(steps)}단계 · {step.title}**  \n광고 관리자에서 찾을 곳: {step.where}")
    for it in step.items:
        _item_widget(ss, phase, it, _default_of(ss, phase, it))
    if any(it.key in COPY_KINDS for it in step.items):
        _copy_box(ss, step, client)
    if step.note:
        st.caption("💡 " + step.note)
    if step.bulk:
        st.caption("📦 " + step.bulk)
    cards = [SR.by_id(c) for c in step.cards if SR.by_id(c)]
    if cards:
        with st.expander(f"이 단계 근거 카드 {len(cards)}장"):
            for c in cards:
                body = c.body if len(c.body) <= 220 else c.body[:220].rsplit(" ", 1)[0] + "…"
                st.markdown(f"**{c.title}** {c.check}  \n{body}")
                st.caption(card_source_md(c))
    b1, b2, b3 = st.columns([1, 2, 2])
    if b1.button("← 이전", key=f"setup_prev_{phase}", disabled=pos == 0):
        ss[pk] = pos - 1
        st.rerun()
    last = pos == len(steps) - 1
    if b2.button("이 값으로 할게요 →" if not last else "이 값으로 할게요 (끝)", key=f"setup_next_{phase}", type="primary"):
        if last:
            ss[f"setup_done_{phase}"] = True
            st.toast(f"{PHASE_NAMES[phase]} 세팅값을 다 모았어요. 아래 '광고 세팅값 시트'에서 받아 가세요.", icon="✅")
        else:
            ss[pk] = pos + 1
        st.rerun()
    if b3.button("여기서 막혔어요", key=f"setup_stuck_{phase}"):
        ss["setup_stuck"] = (phase, step.key)
        ss["setup_last"] = None
    return step


def _default_of(ss, phase: str, it: AS.Item):
    """그 칸의 코치 기본값 (사장님이 고치기 전). settings_plan이 기억해 둔 기본 세팅값에서 찾음."""
    base = ss.get("_set_base") or {}
    return base.get(f"{phase}.{it.key}", it.value)


def _sheet(plan: AS.SettingsPlan, ss):
    """끝까지 가면(또는 언제든) '광고 세팅값' 시트: 광고 관리자에서 누르는 순서, 복사·엑셀·계획 파일 저장."""
    rows = plan.rows()
    if not rows:
        return
    done = [PHASE_NAMES[m] for m in ("naver", "meta") if ss.get(f"setup_done_{m}")]
    with st.expander("📋 광고 세팅값 시트" + (f" ({'·'.join(done)} 다 모음)" if done else ""), expanded=bool(done)):
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            for m, name in (("naver", "네이버"), ("meta", "메타")):
                part = df[df["매체"] == name]
                if not part.empty:
                    part.to_excel(xw, sheet_name=name, index=False)
        st.download_button("📥 엑셀로 받기", buf.getvalue(), file_name=f"광고세팅값_{CO.today_kst():%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="setup_xlsx")
        st.code("\n".join("\t".join([r["매체"], r["단계"], r["항목"], r["값"]]) for r in rows), language=None)
        st.caption("위 칸의 복사 버튼으로 붙여 넣을 수 있어요. 아래 '📄 내 계획 파일 받기'에도 이 세팅값이 함께 저장돼요. "
                   "대량 등록 파일 양식은 아직 받지 못해, 파일이 필요한 단계는 순서만 안내해요.")


def restore_settings(ss, settings: Dict):
    """계획 파일의 세팅값 중 사장님이 고친 칸(_edited)만 다시 넣음."""
    for key in settings.get("_edited") or []:
        if isinstance(key, str) and key in settings and "." in key:
            m, _, k = key.partition(".")
            ss[_wkey(m, k)] = _to_widget(settings[key])


# ── 질문하기 ───────────────────────────────────────────────────
def setup_ask(a: dict, ss, q: str, media: str, price: Optional[float], stores: List[str], plan: AS.SettingsPlan,
              img=None, step_cards: Optional[List[str]] = None):
    """질문 → (코치 배분 / 카드 찾기 → 키 있으면 답). 결과는 세션에 남겨 다시 그릴 때 씀. 키가 있으면 앞 대화 6턴 기억."""
    sp = a["split"]
    if SR.is_coach_question(q):
        kind, found = "coach", []
    else:
        found = SR.find_in(q, step_cards, media) if step_cards else SR.find(q, media=media)
        kind = "cards" if found else "none"
    res: Dict = {"q": q, "kind": kind, "found": [c.id for c, _ in found], "answer": None, "used": [], "note": None,
                 "coach": SR.coach_answer(sp, a["kw"], a["default_pick"] == "none") if kind == "coach" else None}
    client = CI.make_client()
    if found and client is not None:
        ctx = {"naver": sp.naver_spend, "meta": sp.meta.spend, "keyword": a["kw"], "price": price, "wins": a["mc"]["wins"],
               "stores": stores, "settings": AS.context_lines(plan, media)}
        try:
            image = (img.getvalue(), img.name) if img is not None else None
            with st.spinner("세팅 카드를 보고 답을 쓰는 중…"):
                out = SR.answer(client, q, found, ctx, image, history=ss.get("setup_hist"))
            res["answer"], res["used"] = out["answer"], [c.id for c in out["cards"]]
            ss["setup_hist"] = SR.trim_history((ss.get("setup_hist") or []) + [{"role": "user", "content": q},
                                                                                {"role": "assistant", "content": out["answer"]}])
        except ValueError as e:                      # 캡처 크기·형식
            res["note"] = str(e)
        except CI.IntakeUnavailable as e:
            res["note"] = f"지금은 답을 만들 수 없어 자료를 그대로 보여 드려요 ({e})."
    ss["setup_last"] = res


def _media_picker(a: dict, ss, stores: List[str]) -> str:
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
                ss["setup_phase"], ss["setup_last"], ss["setup_stuck"] = "meta", None, None
                st.rerun()
        elif c2.button("← 네이버로 돌아가기", key="setup_to_naver"):
            ss["setup_phase"], ss["setup_last"], ss["setup_stuck"] = "naver", None, None
            st.rerun()
    if phase == "naver" and AS.is_smartstore(stores):
        st.toggle("파워링크도 할래요 (키워드·문구 광고를 쇼핑검색에 더해서)", key="setup_powerlink",
                  help="스마트스토어는 쇼핑검색이 기본이에요. 켜면 파워링크 캠페인 단계(키워드·제외 키워드·제목·설명·확장 검색)가 더해져요.")
    return phase


def render(a: dict, ss, stores: List[str], price: Optional[float]):
    """세팅 도우미: 매체 고르기 → 매체별 단계 안내(광고 세팅값 모으기) → 질문칸 → 세팅값 시트."""
    st.markdown("#### 🙋 광고 관리자 세팅 도우미")
    phase = _media_picker(a, ss, stores)
    client = CI.make_client()
    base = AS.build_settings(a["answer"], stores, bool(ss.get("pixel_ready")), ss.get("setup_media", "both"), a["kw"],
                             ss.get("set_copy_product") or a["kw"], CO.today_kst().strftime("%y%m"), bool(ss.get("setup_powerlink")),
                             naver_link=_links(ss, stores, a["kw"])["naver"], meta_link=_links(ss, stores, a["kw"])["meta"])
    ss["_set_base"] = {f"{s.media}.{it.key}": it.value for s in base.steps for it in s.items}
    plan = settings_plan(a, ss, stores)
    for w in plan.warnings:
        st.caption("⚠️ " + w)
    step = _step_guide(a, ss, plan, phase, client)
    plan = settings_plan(a, ss, stores)          # 이번에 고친 칸까지 반영
    edited = [f"{s.media}.{it.key}" for s in plan.steps for it in s.items
              if ss.get(_wkey(s.media, it.key)) is not None and ss.get(_wkey(s.media, it.key)) != _to_widget(ss["_set_base"].get(f"{s.media}.{it.key}"))]
    ss["ad_settings"] = {**plan.to_settings(), "_edited": edited}
    stuck = ss.get("setup_stuck")
    st.divider()
    if stuck and stuck[0] == phase and step is not None and stuck[1] == step.key:
        st.markdown(f"**'{step.title}' 단계에서 막힌 곳을 물어보세요** (이 단계 카드에서 먼저 찾아요)")
    chip = st.pills("이런 걸 물어볼 수 있어요", SR.CHIPS[phase], key=f"setup_chip_{phase}")
    step_cards = step.cards if (stuck and step is not None and stuck[1] == step.key) else None
    img = None
    if chip and ss.get("_setup_chip_used") != (phase, chip):   # 칩을 누르면 바로 답 (입력칸에도 남겨 고쳐 다시 물을 수 있게)
        ss["setup_q"], ss["_setup_chip_used"] = chip, (phase, chip)
        setup_ask(a, ss, chip, phase, price, stores, plan)
    q = st.text_input(f"{PHASE_NAMES[phase]} 광고 관리자에서 막힌 곳", key="setup_q", placeholder=PLACEHOLDER[phase])
    if client is not None:
        img = st.file_uploader("화면 캡처 (선택, png·jpg 5MB 이하)", type=["png", "jpg", "jpeg"], key="setup_img")
        st.caption("계정 이름·카드 정보는 가리고 올려 주세요. 질문과 캡처는 답을 만들기 위해 Anthropic으로 보내집니다. 캡처는 저장하지 않아요. "
                   f"앞 대화 {SR.HISTORY_TURNS}턴까지 기억해 이어서 답해요.")
    if st.button("물어보기", key="setup_ask", disabled=not q):
        setup_ask(a, ss, q, phase, price, stores, plan, img, step_cards)
    _show_result(a, ss, plan)
    _sheet(plan, ss)


def _show_result(a: dict, ss, plan: AS.SettingsPlan):
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
    nums = plan.numbers
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
