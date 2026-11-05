"""AARRR 기반 광고 예산 시뮬레이터 — Streamlit 프로토타입 v0.6.

실행: streamlit run app/main.py

화면 (기능명세_4개도구.md 1장): ① 시작 ② 광고 관리자 ③ 로그 분석 ④ 어트리뷰션 ⑤ 자동화 ⑥ 결과·우선순위.
각 탭 맨 위에는 '이 화면이 답하는 질문' 한 줄과 결과 숫자 하나만 두고, 나머지는 접기 안에 넣는다.
결과 숫자는 모든 입력이 모인 뒤 계산되므로, 탭마다 맨 위 자리(head)를 먼저 만들고 마지막에 채운다.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))


def _drop_stale_modules():
    """배포 서버는 push 뒤 이 파일만 다시 읽고, 이미 불러온 엔진·차트 모듈은 예전 것을 계속 쓴다 (11/5 두 번 발생).
    엔진·앱 파일의 수정 시각이 바뀌었으면 그 모듈들을 지워서 새 코드로 다시 불러오게 한다."""
    files = list((ROOT / "src").rglob("*.py")) + [ROOT / "app" / "charts.py", ROOT / "app" / "helpbot.py"]
    stamp = max(f.stat().st_mtime for f in files)
    if getattr(sys, "_aarrr_code_stamp", None) != stamp:
        for name in [m for m in sys.modules if m in ("src", "charts", "helpbot") or m.startswith("src.")]:
            del sys.modules[name]
        sys._aarrr_code_stamp = stamp


_drop_stale_modules()

import charts  # noqa: E402
import helpbot  # noqa: E402
from helpbot import SCREEN_HELP  # noqa: E402
from src.engine import (Channel, FunnelParams, MetaCurve, NaverCurve, budget_scan,  # noqa: E402
                        lever_table, optimize_allocation, simulate)
from src.engine import attribution as A  # noqa: E402
from src.engine import coach as CO  # noqa: E402
from src.engine import automation as AU  # noqa: E402
from src.engine import data_loader as dl  # noqa: E402
from src.engine import defaults as D  # noqa: E402
from src.engine import naver_source as ns  # noqa: E402
from src.engine.acquisition import LEARNING_EVENTS_PER_WEEK, RevShareCurve, cpc_from_cpm, learning_check  # noqa: E402
from src.engine.experiment import days_needed, sample_size  # noqa: E402
from src.engine.insights import biggest_drop, insights, prescription, warnings, won  # noqa: E402
from src.engine.optimize import compare_options  # noqa: E402

st.set_page_config(page_title="AARRR 광고 예산 시뮬레이터", page_icon="📈", layout="wide")

# 지표 정의서(실행계획 7장) 기반 툴팁 — 광고 용어를 모르는 사용자 기준으로 풀어 씀
HELP = {
    "new": "12개월 동안 새로 온 손님 수 (광고로 온 손님 + 지인 추천으로 온 손님)",
    "paid_cac": "광고로 손님 1명을 데려오는 데 든 돈 (CAC) = 광고비 ÷ 광고로 온 손님 수",
    "ltv": "손님 1명이 첫 구매 후 12개월 동안 남겨 주는 돈 (LTV, 매출 × 마진)",
    "ltv_cac": "손님이 남겨 주는 돈 ÷ 데려오는 데 든 돈 (LTV/CAC). 1보다 작으면 손님을 데려올수록 손해",
    "payback": "손님 1명을 데려오는 데 쓴 광고비를 그 손님이 남겨 주는 돈으로 되찾기까지 걸리는 개월 수",
    "profit": "12개월 동안 남는 돈 = 매출 × 마진율 − 광고비 − 메시지 발송비",
    "roas": "광고비 1원당 첫 구매 매출 (ROAS). 재구매는 빠져 있어 실제 가치보다 작게 보일 수 있음",
}

OMTM_PLAIN = {"new_customers": "새 손님 수 최대로", "profit": "1년 동안 남는 돈 최대로", "roas": "광고비 대비 첫 매출(ROAS) 최대로"}
TAB_NAMES = list(SCREEN_HELP)

ss = st.session_state


@st.cache_data(show_spinner=False)
def load_keywords(hints: tuple, online: bool):
    return ns.keyword_tool(list(hints), online=online)


@st.cache_data(show_spinner=False)
def load_estimate(keyword: str, online: bool):
    return ns.bid_estimate(keyword, device=D.NAVER_DEVICE, online=online)


@st.cache_data(show_spinner=False)
def load_paths():
    return A.load_ga4_paths()


def cached(name: str, key, fn):
    """입력이 바뀔 때만 다시 계산 (최적화처럼 느린 계산용)."""
    store = ss.setdefault("_cache", {})
    if name not in store or store[name][0] != key:
        store[name] = (key, fn())
    return store[name][1]


def question(q: str):
    st.markdown(f"#### ❓ {q}")


def pct(v):
    if v is None or v != v:
        return "-"
    return f"{v:.2%}" if abs(v) < 0.01 else f"{v:.1%}"


def signed(v):
    return ("+" if v >= 0 else "−") + won(abs(v))


# 과금 방식별로 체인 각 단계 숫자를 어디서 받나 (밸류체인 v3 3장·8장, 조사 00-3 "카드 아래 체인 막대")
# ("got", 출처) 매체·정산이 직접 줌 / ("fill", 메우는 방법) 우리가 UTM·쿠폰·주문으로 메워야 함 / ("skip", 이유) 거치지 않음
CHAIN_COVER = {
    "click": [("got", "매체"), ("got", "매체"), ("fill", "UTM"), ("fill", "UTM·주문"), ("fill", "주문"), ("fill", "추천 코드")],
    "impression": [("got", "매체"), ("got", "매체"), ("fill", "UTM"), ("fill", "UTM·주문"), ("fill", "주문"), ("fill", "추천 코드")],
    "purchase": [("fill", "캡처"), ("fill", "캡처·링크"), ("skip", "바로 ④"), ("got", "정산서·쿠폰"), ("fill", "주문 (자사몰만)"), ("fill", "추천 코드")],
}


def chain_bar(billing: str) -> str:
    """①~⑥ 칸: 받는 칸은 실선, 메워야 하는 칸은 점선, 💰는 돈을 내는 단계."""
    pay = D.BILLING[billing][1][:1]
    cells = []
    for (num, name, _), (state, src) in zip(D.CHAIN, CHAIN_COVER.get(billing, CHAIN_COVER["click"])):
        border = "2px solid #4C78A8" if state == "got" else "2px dashed rgba(127,127,127,.6)"
        cells.append(f'<div style="flex:1;min-width:0;border:{border};border-radius:6px;padding:2px 5px;font-size:12px;'
                     f'opacity:{0.45 if state == "skip" else 1}">{num} {name}{" 💰" if num == pay else ""}'
                     f'<br><span style="font-size:11px;opacity:.75">{src}</span></div>')
    return '<div style="display:flex;gap:4px;margin:2px 0 10px">' + "".join(cells) + "</div>"


# ───────────────────────────── 플로팅 도움말 ─────────────────────────────
st.markdown("""<style>
.st-key-help_fab {position: fixed; bottom: 4.5rem; right: 1.5rem; z-index: 1000; width: auto;}
.st-key-help_fab > div > div > button {border-radius: 999px; box-shadow: 0 2px 8px rgba(0,0,0,.25);}
</style>""", unsafe_allow_html=True)
help_fab = st.container(key="help_fab")  # 내용은 계산이 끝난 뒤 맨 아래에서 채움 (지금 숫자로 답하려고)

with st.sidebar:
    st.header("처음이신가요?")
    st.markdown("**🧭 광고 코치**부터 시작하세요. 아는 숫자 몇 개만 넣으면\n"
                "1. 손님 1명 데려오는 데 **최대 얼마까지** 써도 되는지\n"
                "2. **광고가 맞는 상품**인지\n"
                "3. **첫 달에 무엇을** 할지 알려 드립니다.\n\n"
                "한 달 광고해 본 뒤 숫자 3개를 넣으면 계속할지·줄일지 판정해 드립니다.")
    st.caption("오른쪽 ①~⑥ 탭은 데이터가 생기면 여는 **다음 단계**입니다. 코치에 넣은 숫자로 미리 채워집니다. "
               "모르는 말은 오른쪽 아래 💬 도우미에게 물어보세요.")

st.title("📈 광고 예산 시뮬레이터")
st.caption("광고를 처음 하는 사장님의 첫 광고를 함께 정하는 코치입니다. 손님 1명에 쓸 수 있는 돈, 첫 채널, 첫 달 예산을 알려 주고, "
           "한 달 뒤 결과로 계속할지 판정합니다. 데이터가 쌓이면 다음 단계(①~⑥)에서 채널 배분·퍼널·자동화까지 같은 기준으로 비교합니다. "
           "(AARRR 프레임워크 · 고객 밸류체인 · 프로토타입 v0.7)")

_all_tabs = st.tabs(["🧭 광고 코치"] + [f"{n} · 다음 단계" if i == 0 else n for i, n in enumerate(TAB_NAMES)])
coach_tab, tabs = _all_tabs[0], _all_tabs[1:]
heads = []
for t in tabs:
    with t:
        heads.append(st.container())
        st.divider()

# ───────────────────────────── 🧭 광고 코치 (주 사용자: 광고를 처음 하는 사장님) ─────────────────────────────
# 기준: 초보자_코치_설계안.md 8장 확정 값. 계산 규칙은 src/engine/coach.py
coach = {}
with coach_tab:
    st.markdown("#### ❓ 광고를 처음 하시나요? 아는 숫자만 넣어 주세요")
    st.caption("손님 흐름: " + " → ".join(CO.PLAIN_STEPS) + ". 광고는 앞쪽(봤다·눌렀다)에 돈을 내고, 남는 돈은 '샀다'와 '다시 샀다'에서 생깁니다.")
    q1, q2 = st.columns(2)
    category = q1.selectbox("무엇을 파나요?", CO.CATEGORIES)
    stores = q2.multiselect("어디서 파나요? (여러 곳이면 모두)", CO.STORES, default=["스마트스토어"])
    q3, q4 = st.columns(2)
    price = q3.number_input("1개 팔면 받는 돈 (원)", min_value=0, max_value=100_000_000, value=None, step=1_000,
                            placeholder="예: 35000", help="손님이 한 번 결제하는 평균 금액")
    profit = q4.number_input("1개 팔면 남는 돈 (원)", min_value=0, max_value=100_000_000, value=None, step=1_000,
                             placeholder="예: 14000", help="받는 돈에서 원가·포장·배송비·판매 수수료를 뺀 금액")
    q5, q6, q7 = st.columns(3)
    repurchase = q5.radio("한 번 산 손님이 다시 사나요?", list(CO.REPURCHASE_PRESETS), index=1,
                          help="1년 동안 다시 사는 횟수로 바꿔 계산합니다: 거의 안 삼 0번 / 가끔 0.5번 / 자주 2번 (모두 가정값)")
    max_budget = q6.number_input("한 달에 광고에 쓸 수 있는 최대 금액 (원)", min_value=0, max_value=1_000_000_000, value=None,
                                 step=100_000, placeholder="예: 1000000")
    baseline = q7.number_input("광고 없이 한 달에 보통 몇 개 팔리나요? (모르면 비워 두기)", min_value=0, max_value=10_000_000,
                               value=None, step=1, help="한 달 뒤 판정에서 광고 없이도 팔렸을 판매를 빼는 데 씁니다.")
    keyword = st.text_input("손님이 이 상품을 찾을 때 검색할 만한 단어 (선택)", placeholder="예: 원두커피",
                            help="네이버에서 한 달에 몇 번 검색되는지, 클릭 1번이 대략 얼마인지 가져옵니다.")
    if any(s in stores for s in ("스마트스토어", "쿠팡")):
        st.caption("오픈마켓에서 팔면 판매 수는 마켓 통계 화면에서 보고, 같은 손님이 다시 샀는지는 확인하기 어렵습니다.")

    if not (price and profit and max_budget):
        st.info("**1개 팔면 받는 돈, 남는 돈, 한 달 최대 광고비**를 넣으면 답이 나옵니다.", icon="✏️")
    elif profit > price:
        st.error("남는 돈이 받는 돈보다 클 수 없습니다. 다시 확인해 주세요.")
    else:
        be = CO.breakeven(profit, CO.REPURCHASE_PRESETS[repurchase])
        # 네이버 검색 데이터 (선택): 월 검색수 → 자사몰 첫 채널, 예상 클릭 비용 → 신호등
        monthly_search, naver_cpc = None, None
        kw = keyword.strip().replace(" ", "")
        if kw:
            _online = ns.api_available()
            kdf = load_keywords((kw,), _online)
            if kdf is not None and kw in set(kdf["keyword"]):
                monthly_search = float(kdf.set_index("keyword").loc[kw, "total_qc"])
            est = load_estimate(kw, _online)
            if est is not None and (est["clicks"] > 0).any():
                nc = NaverCurve({kw: est})
                spend0 = min(CO.test_budget(max_budget, be.first)[0], nc.capacity) or nc.capacity
                if nc.clicks(spend0) > 0:
                    naver_cpc = spend0 / nc.clicks(spend0)
        ch_name, ch_reason = CO.first_channel(stores, monthly_search)
        if "메타" in ch_name:
            cpc_guess, cpc_src = float(D.META_BASE_CPC), "메타 대략값 (가정)"
        elif naver_cpc:
            cpc_guess, cpc_src = naver_cpc, f"네이버 예상 실적 '{kw}' (최근 4주 → 한 달)" + ("" if "네이버" in ch_name else ", 이 채널 대신 참고")
        else:
            cpc_guess, cpc_src = float(D.META_BASE_CPC), "대략값 (검색어를 넣으면 네이버 예상치로 바뀜)"
        cpc_in = st.number_input("클릭 1번 비용을 알면 넣으세요 (원, 모르면 비워 두기)", min_value=0, max_value=100_000, value=None, step=50)
        cpc = float(cpc_in) if cpc_in else cpc_guess
        if cpc_in:
            cpc_src = "직접 입력"
        need, need_year = CO.required_rate(cpc, be.first), CO.required_rate(cpc, be.year)
        light, light_msg = CO.signal(need)
        budget0, budget_warn = CO.test_budget(max_budget, be.first)
        coach = dict(price=float(price), margin=profit / price, budget=float(budget0), keyword=kw, be=be, cpc=cpc,
                     channel=ch_name, repurchase=repurchase)

        st.divider()
        st.markdown("#### 답 1. 손님 1명 데려오는 데 최대 얼마까지 써도 되나요?")
        a1, a2 = st.columns([1, 2])
        a1.metric("첫 구매만으로도 남는 한도", won(be.first))
        a2.markdown(f"손님 1명을 데려오는 데 **{won(be.first)}**까지는 첫 구매만으로도 남습니다.  \n"
                    + (f"다시 사는 손님이 '{repurchase}' 정도라면 **{won(be.year)}**까지도 괜찮습니다. "
                       "다만 이 값은 **가정**입니다 (실제 재구매 기록이 생기면 바뀝니다)." if be.year > be.first else
                       "다시 사는 손님이 거의 없다면 이 금액이 그대로 한도입니다."))

        st.markdown("#### 답 2. 광고가 맞는 상품인가요?")
        getattr(st, {"🟢": "success", "🟡": "warning", "🔴": "error"}[light])(
            f"{light} 클릭 1번에 약 **{won(cpc)}**이면, 눌러 들어온 **100명 중 {need * 100:.1f}명**이 사야 남습니다. {light_msg}  \n"
            f"참고 기준: 공개 샘플 쇼핑몰에서 검색광고로 온 손님은 100명 중 {CO.REFERENCE_RATES['GA4 공개 샘플 유료 검색 유입'] * 100:.2f}명, "
            f"전체는 {CO.REFERENCE_RATES['GA4 공개 샘플 전체'] * 100:.2f}명이 샀습니다 (한 쇼핑몰 값이라 업종 평균은 아님)."
            + (f"  \n다시 사는 손님까지 치면 100명 중 {need_year * 100:.1f}명이면 됩니다 (가정값)." if be.year > be.first else ""))
        st.caption(f"클릭 비용 출처: {cpc_src}")

        st.markdown("#### 답 3. 첫 달에 무엇을 할까요?")
        c1, c2 = st.columns(2)
        with c1.container(border=True):
            st.markdown(f"**첫 광고: {ch_name}**  \n{ch_reason}"
                        + (f"  \n(검색어 '{kw}' 네이버 월 검색 {monthly_search:,.0f}회)" if monthly_search is not None else ""))
            st.metric("첫 달 시험 예산", won(budget0), help=f"월 최대 금액과 '손님 1명 한도 × {CO.TEST_SALES}건' 중 작은 쪽. "
                      f"판매 {CO.TEST_SALES}건이면 손님 1명 비용을 ±18% 정도로 잴 수 있습니다.")
            if budget_warn:
                st.warning(budget_warn)
            if light == "🔴":
                st.markdown(f"**광고 대신 해 볼 것: 공동구매·제휴** (팔린 만큼만 냄)  \n"
                            f"판매액의 **{profit / price:.0%} 이하**를 수수료로 주는 공동구매라면 남습니다.")
        with c2.container(border=True):
            st.markdown("**광고 전에 준비할 것 3가지**")
            st.checkbox("상세페이지에 후기 3개 이상, 사진·가격·배송 안내 정리", key="prep_1")
            st.checkbox("광고 전용 링크나 쿠폰 코드 하나 만들기 (광고로 팔린 것만 따로 세려고)", key="prep_2",
                        help="이게 없으면 한 달 뒤 광고 없이 팔린 것까지 섞여 결과가 좋아 보일 수 있습니다.")
            st.checkbox("판매처 통계 화면 찾아 두기 (쓴 돈·클릭·판매 수를 볼 곳)", key="prep_3")

        st.divider()
        st.markdown("#### 한 달 뒤: 숫자 3개만 넣으면 계속할지 알려 드립니다")
        m1, m2, m3, m4 = st.columns(4)
        days = m1.number_input("광고를 며칠 돌렸나요?", 0, 366, 30)
        spent = m2.number_input("쓴 돈 (원)", 0, 1_000_000_000, value=None, step=10_000)
        clicks_in = m3.number_input("클릭 수", 0, 100_000_000, value=None, step=10)
        m4.caption("광고 관리자 화면에서 그대로 옮겨 적으세요.")
        s1, s2, s3 = st.columns(3)
        coupon_n = s1.number_input("쿠폰·전용 링크로 팔린 수", 0, 10_000_000, value=None, step=1)
        report_n = s2.number_input("광고 화면에 나온 판매(전환) 수", 0, 10_000_000, value=None, step=1)
        total_n = s3.number_input("이번 달 전체 판매 수", 0, 10_000_000, value=None, step=1)
        if spent is not None and clicks_in is not None and any(v is not None for v in (coupon_n, report_n, total_n)):
            basis = CO.ad_sales(coupon_n, report_n, total_n, baseline)
            v = CO.judge(int(days), float(spent), float(clicks_in), basis, be, cpc, ch_name)
            getattr(st, v.level)(f"**{v.title}**  \n{v.detail}")
            notes = [f"광고로 온 판매: {basis.value:,.0f}건 ({basis.source})"]
            if basis.side_by_side:
                notes.append(f"쿠폰 {basis.side_by_side[0]:,.0f}건 · 광고 화면 {basis.side_by_side[1]:,.0f}건 "
                             "(쿠폰은 쿠폰을 안 쓴 손님을 놓치고, 광고 화면은 광고 없이 샀을 손님이 섞입니다. 실제는 둘 사이일 가능성이 큽니다.)")
            if basis.warning:
                notes.append(basis.warning)
            if v.cpa:
                notes.append(f"손님 1명 데려오는 데 든 돈 {won(v.cpa)} (한도 {won(be.first)}, 재구매 포함 가정 {won(be.year)})")
            if v.next_budget is not None and v.step in (1, 2, 3, 4):
                notes.append(f"다음 달 예산 제안: {won(v.next_budget)}")
            st.caption("  \n".join(notes))
        else:
            st.caption("쓴 돈, 클릭 수, 판매 수(셋 중 아는 것)를 넣으면 판정합니다.")
    st.info("더 알고 싶으면 오른쪽 **① 시작 · 다음 단계**부터 보세요. 위에 넣은 숫자(판매가·남는 돈·시험 예산·검색어)로 미리 채워져 있습니다.", icon="➡️")

# ───────────────────────────── ① 시작 ─────────────────────────────
with tabs[0]:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("무엇을 팔고, 얼마가 남나요?")
        business = st.text_input("무엇을 파나요? (메모용, 계산에는 쓰이지 않음)", placeholder="예: 동네 필라테스 스튜디오, 원두 온라인몰 …")
        task = st.selectbox("광고를 본 손님이 해 줬으면 하는 행동 (핵심 과업)", D.CORE_TASKS,
                            help="이 행동을 한 사람을 '새 손님'으로 셉니다.")
        if task == "직접 입력":
            task = st.text_input("행동 이름", value="전환") or "전환"
        a1, a2 = st.columns(2)
        aov = a1.number_input("1회 평균 결제 금액 (원, 객단가)", 1_000.0, 10_000_000.0,
                              max(1_000.0, coach.get("price", float(D.AOV))), step=1_000.0,
                              help="손님이 한 번 결제할 때 평균 금액. 결과를 가장 크게 바꾸는 숫자입니다.")
        margin = a2.slider("매출 중 남는 비율 (마진율)", 0.0, 1.0, round(coach.get("margin", float(D.MARGIN)), 2), 0.01,
                           help="1만 원어치 팔면 원가·배송비·수수료를 빼고 얼마가 남는지. 0.35 = 3,500원")
        st.caption(f"→ 1회 결제당 남는 돈 {won(aov * margin)}. 기본값(6만 원·35%)은 예시라, 우리 가게 숫자로 꼭 바꿔 주세요.")
        with st.expander("더 알면 바꾸기: 한 달 구매 횟수"):
            freq = st.number_input("단골이 한 달에 사는 횟수", 0.1, 10.0, float(D.PURCHASE_FREQ), step=0.1,
                                   help="그달에 다시 온 손님이 평균 몇 번 결제하는지 (월 구매 빈도). UCI 분석 후 교체 예정인 임시값")
        st.subheader("목표와 예산")
        omtm = st.radio("가장 중요한 목표 하나 (OMTM)", list(D.OMTM_OPTIONS), horizontal=True, format_func=OMTM_PLAIN.get, index=1,
                        help="'더 나은 예산안'을 찾을 때 이 목표를 기준으로 삼습니다. 잘 모르겠으면 '1년 동안 남는 돈'.")
        budget = st.number_input("한 달 광고비 (원)", min_value=0, max_value=1_000_000_000, value=int(coach.get("budget", D.MONTHLY_BUDGET)),
                                 step=100_000, format="%d")
        st.caption(f"= 한 달 {won(budget)}, 1년이면 {won(budget * 12)}")
    with c2:
        st.subheader("데이터 준비 체크리스트")
        st.caption("현업 마케팅의 첫 단계는 '측정 준비'입니다. 해 둔 것에 체크하면 쓸 수 있는 기능을 자동으로 정합니다.")
        chk_utm = st.checkbox("광고 링크에 UTM 꼬리표를 붙였다", help="어느 광고로 들어왔는지 GA4가 알 수 있게 하는 꼬리표")
        chk_ga4 = st.checkbox(f"GA4에서 '{task}'을(를) 주요 이벤트(전환)로 설정했다")
        chk_ref = st.checkbox("GA4 '원치 않는 추천 목록'에 내 도메인·결제 대행사를 넣었다",
                              help="안 넣으면 결제 후 돌아온 방문이 '외부 유입(referral)'으로 잡혀 ④ 어트리뷰션이 왜곡됩니다.")
        chk_csv = st.checkbox("네이버·메타 광고 성과 파일(CSV)이 있다")
        data_level = 1 if chk_csv or (chk_utm and chk_ga4) else 0
        if data_level:
            st.success("**1단계 (내 데이터 사용)**: " + " · ".join(
                x for x, ok in [("광고 성과 CSV로 클릭당 비용·전환율 보정", chk_csv), ("④에 내 전환 경로 파일 업로드", chk_utm and chk_ga4)] if ok))
        else:
            st.info("**0단계 (기본값 체험)**: 공개 데이터 기본값으로 계산합니다. UTM과 GA4 주요 이벤트를 설정하면 내 데이터로 바꿀 수 있습니다.")
        if not chk_ref and (chk_utm or chk_ga4):
            st.warning("'원치 않는 추천' 설정이 없으면 ④에서 내 도메인을 직접 적어 자기 참조를 걸러 주세요.")
        upload = None
        if chk_csv:
            f = st.file_uploader("광고 성과 CSV (date, source, spend, clicks, conversions …)", type="csv")
            if f is None:
                st.caption("템플릿 예시: `app/sample_ad_performance.csv` — 파일이 없으면 예시 파일로 보여줍니다.")
                f = ROOT / "app" / "sample_ad_performance.csv"
            try:
                raw = pd.read_csv(f)
                # 매체마다 컬럼 이름이 달라서(Meta "지출 금액", 네이버 "총비용" 등) 템플릿 컬럼에 매핑
                fields = {"source": "매체 (utm_source)", "spend": "광고비", "clicks": "클릭", "conversions": "전환 (핵심 과업)"}
                cols = list(raw.columns)
                with st.expander("컬럼 매핑", expanded=not set(fields) <= set(cols)):
                    mapping = {k: st.selectbox(label, cols, index=cols.index(k) if k in cols else 0, key=f"map_{k}")
                               for k, label in fields.items()}
                df_up = pd.DataFrame({k: raw[v] for k, v in mapping.items()})
                for k in ("spend", "clicks", "conversions"):
                    df_up[k] = pd.to_numeric(df_up[k].astype(str).str.replace(",", ""), errors="coerce")
                if df_up[["spend", "clicks", "conversions"]].isna().all().any():
                    st.error("광고비·클릭·전환에 숫자 컬럼을 매핑해 주세요.")
                else:
                    g = df_up.groupby(df_up["source"].astype(str).str.lower())[["spend", "clicks", "conversions"]].sum()
                    g["CPC"] = g["spend"] / g["clicks"]
                    g["CVR"] = g["conversions"] / g["clicks"]
                    g["CPA"] = g["spend"] / g["conversions"]
                    st.dataframe(g.style.format({"spend": "{:,.0f}", "clicks": "{:,.0f}", "conversions": "{:,.0f}",
                                                 "CPC": "{:,.0f}", "CVR": "{:.2%}", "CPA": "{:,.0f}"}))
                    upload = g
                    st.caption("매체 이름이 naver·meta인 행의 클릭당 비용·전환율이 기본값보다 우선합니다.")
            except Exception as e:  # noqa: BLE001
                st.error(f"CSV를 읽지 못했습니다: {e}")

# ─────────────────────────── ② 광고 관리자 ───────────────────────────
with tabs[1]:
    api_ok = ns.api_available()
    top = st.columns([2, 1])
    with top[0]:
        hint_text = st.text_input("손님이 검색할 만한 단어 (쉼표로 최대 5개)", value=coach.get("keyword") or ns.SAMPLE_KEYWORD,
                                  help="예: 필라테스, 원두커피. 이 단어와 비슷한 검색어도 함께 찾아 줍니다.")
    with top[1]:
        online = st.toggle("네이버에서 지금 바로 조회", value=api_ok, disabled=not api_ok,
                           help="끄면 미리 저장해 둔 결과만 씁니다 (인터넷 없이 시연할 때).")
        if not api_ok:
            st.caption("⚠️ API 키가 없어 저장해 둔 결과로 동작합니다.")
    hints = tuple(h.strip().replace(" ", "") for h in hint_text.split(",") if h.strip())[:5]
    kw_df = load_keywords(hints, online) if hints else None
    fallback = False
    if kw_df is None:
        fallback = True
        kw_df = load_keywords((ns.SAMPLE_KEYWORD,), False)
        st.warning(f"'{hint_text}' 검색 결과를 가져오지 못해 예시 단어 '{ns.SAMPLE_KEYWORD}'로 대신 보여줍니다.")

    estimates, recs, selected = {}, None, []
    if kw_df is not None:
        base_hints = (ns.SAMPLE_KEYWORD,) if fallback else hints
        default_sel = [k for k in base_hints if k in set(kw_df["keyword"])] or kw_df["keyword"].head(3).tolist()
        selected = st.multiselect("광고를 걸 검색어 (최대 8개)", kw_df["keyword"].tolist(), default=default_sel, max_selections=8)
        recs = ns.recommend_keywords(kw_df, seeds=list(base_hints))
        if len(recs):
            st.success("💡 **추천 검색어**: " + ", ".join(f"`{k}`" for k in recs["keyword"])
                       + "  \n검색하는 사람이 적당히 많고(월 1천~3만 회) 경쟁 광고주가 적은 단어입니다.")
        with st.spinner("입찰가별 예상 실적을 불러오는 중…"):
            for kw in selected:
                est = load_estimate(kw, online and not fallback)
                if est is not None and (est["clicks"] > 0).any():
                    estimates[kw] = est
        missing = [k for k in selected if k not in estimates]
        if missing:
            st.caption(f"네이버 예상 클릭이 없어 계산에서 뺀 검색어: {', '.join(missing)}")
    naver_curve = NaverCurve(estimates) if estimates else NaverCurve({})
    if not estimates:
        st.info("광고를 걸 수 있는 네이버 검색어가 없어 네이버 광고비는 0으로 계산합니다.")

    st.subheader("예산 나누기")
    m1, m2 = st.columns([1, 1])
    with m1:
        naver_share = st.slider("네이버 검색광고에 쓸 비율 (%)", 0, 100, int(D.CHANNEL_SHARES["naver"] * 100), step=5,
                                help="나머지는 메타(인스타그램·페이스북) 광고에 씁니다. ⑥에서 더 나은 비율을 알려줍니다.")
        naver_budget = budget * naver_share / 100
        meta_budget = budget - naver_budget
        st.markdown(f"**네이버** 월 {won(naver_budget)} · **메타** 월 {won(meta_budget)}")
        st.caption("과금 방식: 네이버 검색 = {} ({}) · 메타 = 입력 방식에 따라 노출당(① 접촉) 또는 클릭·시청당(② 반응)".format(*D.BILLING["click"]))
        if naver_curve.capacity > 0:
            st.caption(f"고른 검색어로 네이버에 쓸 수 있는 돈은 한 달 최대 {won(naver_curve.capacity)}입니다.")
    with m2:
        meta_cpc_input = st.number_input("메타 클릭 1번당 비용 (원, CPC)", 50.0, 20_000.0, float(D.META_BASE_CPC), step=50.0,
                                         help="메타 광고 관리자의 'CPC(링크 클릭당 비용)'. 타깃을 쪼개지 않는 캠페인 하나(Advantage+ 판매 캠페인) 기준")
    learn_slot = st.container()
    chain_slot = st.container()
    with st.expander("고급 설정 (메타 세부 설정 · 가이드 · 검색어 전체 보기)"):
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**메타 비용**")
            use_cpm = st.checkbox("CPC 대신 노출당 비용(CPM)과 클릭률(CTR)로 입력", help="메타는 노출당 과금이 기본이고 CPC는 결과값입니다.")
            if use_cpm:
                cpm = st.number_input("CPM (1,000회 노출당 비용, 원)", 100.0, 100_000.0, 7_000.0, step=500.0)
                ctr = st.number_input("CTR (클릭률, %)", 0.05, 20.0, 1.0, step=0.05) / 100
                meta_cpc_input = cpc_from_cpm(cpm, ctr)
                st.caption(f"→ CPC = CPM ÷ (1000 × CTR) = {meta_cpc_input:,.0f}원. 소재가 지쳐 CTR이 떨어지면 CPC가 오릅니다.")
            meta_sat = st.slider("예산을 늘릴 때 클릭 단가가 오르는 정도", 0.0, 2.0, float(D.META_SATURATION), 0.05,
                                 help="0.3 = 광고비를 100만 원 늘릴 때마다 클릭당 비용이 30% 오름 (가정값)")
            ad_sets = st.number_input("메타 광고 세트 수", 1, 20, 1, help="학습 가능 예산 점검에 씁니다.")
            st.markdown("**메타 손님 가정** (근거 데이터 없음 · 가정값)")
            meta_cvr_in = st.slider("메타 손님의 구매 확률 (③ 퍼널 평균 손님 = 1)", 0.1, 2.0, float(D.META_CVR_MULT), 0.05,
                                    help="가정값입니다. 광고 성과 CSV를 올리면 실제 값으로 바뀝니다.")
            meta_ret_mult = st.slider("메타 손님이 다시 오는 정도 (네이버 손님 = 1)", 0.1, 2.0, float(D.META_RETENTION_MULT), 0.05)
            st.markdown("**증분 계수** (광고가 없었어도 왔을 손님을 뺀 비율, 모르면 1)")
            i1, i2 = st.columns(2)
            naver_incr = i1.number_input("네이버", 0.0, 1.0, 1.0, 0.05, help="메타 전환 상승 테스트·지역 실험 같은 증분 실험 결과가 있을 때만 바꾸세요.")
            meta_incr = i2.number_input("메타", 0.0, 1.0, 1.0, 0.05)
        with g2:
            targets_df = dl.meta_targets()
            meta_targets = st.multiselect("연령·성별을 나눠 볼 때 (선택)", targets_df["target"].tolist(),
                                          help="Advantage+ 판매 캠페인은 타깃 자동화가 전제라 기본은 나누지 않습니다. 나누면 Kaggle 상대 CPA 배수를 곱합니다.")
            st.plotly_chart(charts.meta_target_bars(targets_df, meta_targets), use_container_width=True)
            goal = st.selectbox("메타 광고 목표", D.META_GUIDE_GOALS, index=2)
            product = st.selectbox("상품·서비스 유형", D.META_GUIDE_PRODUCTS)
            st.markdown(f"- **캠페인**: {D.META_GUIDE['campaign'][goal]}\n- **구조**: {D.META_GUIDE['structure'][product]}\n"
                        f"- **소재**: {D.META_GUIDE['creative'][product]}")
            st.caption("규칙 기반 운영 가이드입니다. 계산에는 쓰이지 않습니다.")
        if kw_df is not None:
            k1, k2 = st.columns([1, 1])
            k1.plotly_chart(charts.keyword_scatter(kw_df, selected), use_container_width=True)
            tier_filter = k2.multiselect("검색량 크기", ["대표", "세부", "롱테일"], default=["대표", "세부"])
            k2.dataframe(kw_df[kw_df["tier"].isin(tier_filter)].head(100)[
                ["keyword", "tier", "total_qc", "comp", "mobile_ctr", "mobile_clicks"]].rename(columns={
                "keyword": "검색어", "tier": "크기", "total_qc": "한 달 검색 수", "comp": "광고 경쟁",
                "mobile_ctr": "광고 클릭률(%)", "mobile_clicks": "광고 클릭 수(평균)"}), height=300, hide_index=True)
    target_mult = dl.target_multiplier(meta_targets)
    meta_cpc = meta_cpc_input * target_mult
    if upload is not None and "meta" in upload.index:
        meta_cpc = float(upload.loc["meta", "CPC"])  # 1단계: 내 실제 CPC가 우선
    meta_curve = MetaCurve(meta_cpc, meta_sat)
    meta_billing = "impression" if use_cpm else "click"   # 매체 × 과금 설정 (밸류체인 v3 4-1)
    with chain_slot:
        st.markdown(f"**네이버 검색 · {D.BILLING['click'][0]}**" + chain_bar("click"), unsafe_allow_html=True)
        st.markdown(f"**메타 · {D.BILLING[meta_billing][0]}**" + chain_bar(meta_billing), unsafe_allow_html=True)
        st.caption("채널마다 어디까지 숫자를 잴 수 있는지: 실선 = 매체가 숫자를 줌 · 점선 = UTM·쿠폰·자사 주문으로 메워야 함 · 💰 = 돈을 내는 단계")
    spends = [naver_budget, meta_budget]
    alloc = None
    with st.expander("곡선과 검색어별 예산 보기", expanded=True):
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(charts.bid_curves(estimates, naver_curve if estimates else None), use_container_width=True)
        c1.caption("네이버 예상 실적(최근 4주)을 한 달 기준으로 환산했습니다 (× 30.4/28 ≈ 1.09). 평평해질수록 포화입니다.")
        c2.plotly_chart(charts.meta_curve(meta_curve, max(budget, 1)), use_container_width=True)
        if estimates:
            alloc = naver_curve.allocation(naver_budget, D.SATURATION_RATIO)
            show = alloc.assign(saturated=alloc["saturated"].map({True: "⚠️ 포화", False: "✅ 여유"}))
            st.dataframe(show.rename(columns={"keyword": "검색어", "spend": "한 달 광고비", "clicks": "한 달 클릭", "bid": "권장 입찰가",
                                              "marginal_cpc": "클릭 1번 더 얻는 비용", "cpc": "평균 클릭당 비용", "saturated": "상태"})
                         .style.format({"한 달 광고비": "{:,.0f}", "한 달 클릭": "{:,.0f}", "권장 입찰가": "{:,.0f}",
                                        "클릭 1번 더 얻는 비용": "{:,.0f}", "평균 클릭당 비용": "{:,.0f}"}, na_rep="-"), hide_index=True)

    st.subheader("공동구매·판매 수수료 (구매당, 선택)")
    st.caption("인플루언서 공동구매, 라이브커머스, 제휴처럼 **팔린 만큼 돈을 내는** 방식입니다. 월 광고 예산을 나눠 쓰지 않고, 켜면 따로 더해집니다. "
               "숫자는 모두 직접 넣는 값입니다 (기본값을 지어내지 않음).")
    gonggu = None
    if st.toggle("공동구매(구매당)도 함께 계산", key="gg_on"):
        gtype = st.radio("돈 내는 방식", ["판매액의 %", "판매 1건당 금액 (구매 CPA)"], horizontal=True)
        q1, q2, q3, q4 = st.columns(4)
        if gtype.startswith("판매액"):
            gg_rate = q1.number_input("수수료율 (%)", 0.0, 90.0, value=None, step=1.0,
                                      help="판매액 중 인플루언서·플랫폼에 주는 비율. 공구는 보통 20~50%라는 업계 자료가 있습니다 (대행사·블로그 자료).")
            gg_fee = 0.0
        else:
            gg_fee = q1.number_input("판매 1건당 금액 (원)", 0.0, 10_000_000.0, value=None, step=1_000.0)
            gg_rate = 0.0
        gg_sales = q2.number_input("1회 예상 판매량 (건)", 0, 1_000_000, value=None, step=10, help="한 번 진행할 때 팔릴 주문 수. 이 수가 상한입니다.")
        gg_n = q3.number_input("한 달 진행 횟수", 0.0, 10.0, 1.0, step=0.5)
        gg_up = q4.number_input("회당 착수금 (원)", 0, 100_000_000, 0, step=50_000, help="콘텐츠 제작비처럼 판매와 무관하게 먼저 주는 돈")
        r1, r2 = st.columns(2)
        gg_store = r1.radio("판매가 일어나는 곳", ["우리 쇼핑몰 (자사몰)", "외부 몰·인플루언서 몰"],
                            help="외부 몰에서 팔면 그 손님의 재구매(⑤)를 우리가 볼 수 없어 재구매 0으로 계산합니다.")
        gg_incr = r2.number_input("증분 계수 (공구가 없었어도 샀을 손님 빼기, 모르면 1)", 0.0, 1.0, 1.0, 0.05)
        if not st.checkbox("전용 링크(UTM)나 쿠폰 코드를 만들었다", key="gg_track"):
            st.warning("전용 링크나 쿠폰 코드가 없으면 다음 달 검토에서 이 채널의 ③·④ 실적이 0으로 나옵니다. 판매 정산서만으로는 우리 쪽 주문과 이을 수 없습니다.")
        price_ok = (gg_rate is not None) and (gg_fee is not None)
        if price_ok and gg_sales:
            gonggu = Channel("gonggu", "공동구매", RevShareCurve((gg_rate or 0) / 100, gg_sales, gg_n, gg_up, fee_per_sale=gg_fee or 0),
                             1.0, 1.0 if gg_store.startswith("우리") else 0.0, billing="purchase", incr_mult=gg_incr)
            gm1, gm2 = st.columns(2)
            gm1.metric("구매 1건당 비용", won(gonggu.curve.cost_per_purchase(aov)),
                       help="수수료형 = 수수료율 × 객단가 + 착수금 ÷ 판매 수 / 건당 고정형 = 건당 금액 + 착수금 ÷ 판매 수")
            gm2.metric("한 달 비용 (팔린 만큼)", won(gonggu.curve.cost(gonggu.curve.sales(), aov)),
                       help=f"판매 {gonggu.curve.sales():,.0f}건 기준. ⑥에서 공동구매를 켰을 때와 껐을 때를 비교합니다.")
            spends.append(0.0)
        else:
            st.caption("돈 내는 금액과 1회 예상 판매량을 넣으면 계산합니다.")
        st.markdown("**공동구매는 어디까지 잴 수 있나**" + chain_bar("purchase"), unsafe_allow_html=True)

# ─────────────────────────── ③ 로그 분석 ───────────────────────────
with tabs[2]:
    f1, f2 = st.columns([1, 1])
    with f1:
        fun_file = st.file_uploader("내 GA4 유입경로 CSV (선택) — 없으면 GA4 공개 샘플", type="csv",
                                    help="GA4 유입경로 탐색 보고서를 내보낸 파일. 형식: 세그먼트(매체·기기) 열 + 단계별 사용자 수 열 (예: segment, 방문, 상담, 계약)")
        fun_df, up_tab, seg_cvr, seg_label = None, None, None, "GA4 매체별"
        if fun_file is not None:
            try:
                fun_df = pd.read_csv(fun_file)
            except Exception as e:  # noqa: BLE001
                st.error(f"퍼널 CSV를 읽지 못했습니다: {e}")
        if fun_df is not None:
            cols = list(fun_df.columns)
            numeric = [c for c in cols if pd.to_numeric(fun_df[c].astype(str).str.replace(",", ""), errors="coerce").notna().mean() > 0.9]
            seg_opts = ["(없음)"] + [c for c in cols if c not in numeric]
            u1, u2 = st.columns(2)
            seg_pick = u1.selectbox("세그먼트 열 (매체·기기)", seg_opts, index=1 if len(seg_opts) > 1 else 0)
            seg_col = None if seg_pick == "(없음)" else seg_pick
            unit = u2.radio("숫자 기준", ["사용자 수", "세션 수"], horizontal=True,
                            help="GA4 보고서는 사용자·세션 기준이 섞여 있습니다. 한 기준으로 통일된 파일을 올려 주세요.")
            step_cols = st.multiselect("단계 열 (첫 단계부터 순서대로)", numeric, default=numeric)
            if len(step_cols) >= 2:
                up_tab = dl.segment_rates(fun_df, seg_col, step_cols)
                medium = st.selectbox("퍼널 기본값으로 쓸 세그먼트", [dl.GA4_ALL] + [i for i in up_tab.index if i != dl.GA4_ALL])
                base_steps, src = dl.upload_funnel(fun_df, step_cols, seg_col, medium)
                overall = up_tab.columns[len(step_cols)]
                seg_cvr = lambda m: float(up_tab.loc[m, overall]) if m in up_tab.index else None  # noqa: E731
                seg_label = "내 퍼널 CSV"
                if unit == "세션 수":
                    st.caption("세션 기준 전환율은 같은 사람이 여러 번 방문하면 사용자 기준보다 낮게 나옵니다.")
            else:
                st.warning("단계 열을 2개 이상 골라 주세요. 그동안은 GA4 샘플을 씁니다.")
                fun_df = None
        if fun_df is None:
            mediums = dl.ga4_mediums() or [dl.GA4_ALL]
            medium = st.selectbox("기본값으로 쓸 실제 쇼핑몰 기록 (GA4 샘플 매체)", mediums,
                                  help="'전체'가 기본입니다. 'cpc'를 고르면 검색광고로 들어온 방문자만의 비율을 씁니다.")
            base_steps, src = dl.funnel_steps(medium)
        steps_df = pd.DataFrame([{"단계": n, "전환율": round(r, 3)} for n, r in base_steps])
        steps_df.loc[len(steps_df) - 1, "단계"] = "④ 구매" if task == "구매" else f"④ 구매({task})"   # 라벨만 교체 (밸류체인 D3)
        edited = st.data_editor(steps_df, num_rows="dynamic", hide_index=True, key=f"steps_editor_{src}",
                                column_config={"전환율": st.column_config.NumberColumn(
                                    "다음 단계로 가는 비율", min_value=0.0, max_value=1.0, step=0.01, format="%.2f")})
        edited = edited.dropna()
        steps = [(str(n), float(r)) for n, r in zip(edited["단계"], edited["전환율"])]
        funnel_edited = not steps_df.dropna().reset_index(drop=True).equals(edited.reset_index(drop=True))
        st.caption(f"출처: {src}. 첫 단계(광고 클릭 → 페이지 도착)는 기록이 없어 임시값입니다.")
    funnel_slot = f2.container()
    opp_slot = st.container()
    with st.expander("세그먼트 비교 (매체·기기별 단계 전환율)"):
        if up_tab is not None and len(up_tab) > 1:
            seg = up_tab
            st.caption("올린 퍼널 CSV의 세그먼트별 비교입니다.")
        else:
            dim = st.radio("나눠 볼 기준", ["medium", "device"], horizontal=True, format_func={"medium": "유입 매체", "device": "기기"}.get)
            seg = dl.segment_table(dim)
        if seg is None or len(seg) < 2:
            st.caption("비교할 세그먼트가 없습니다.")
        else:
            rate_cols = [c for c in seg.columns if c not in ("visitors", "purchases", "small")]
            overall = rate_cols[-1]
            allv = seg.loc[dl.GA4_ALL]

            def _hl(col):
                if col.name not in rate_cols:
                    return [""] * len(col)
                return ["color: #999" if seg.loc[i, "small"] else
                        ("background-color: #d9f0d3" if v > allv[col.name] * 1.1 else
                         "background-color: #f6d5d5" if v < allv[col.name] * 0.9 else "") for i, v in col.items()]
            st.dataframe(seg.drop(columns=["small"]).style.apply(_hl)
                         .format({c: "{:.1%}" for c in rate_cols} | {"visitors": "{:,.0f}", "purchases": "{:,.0f}"}),
                         width="stretch", column_config={"visitors": "방문자", "purchases": "완료"})
            st.caption(f"초록 = 전체보다 10% 이상 높음, 빨강 = 10% 이상 낮음, 회색 = 방문자 {dl.SEGMENT_MIN_USERS:,}명 미만. "
                       "(data deleted)는 마스킹 편향으로 뺐습니다. 이 샘플에서는 기기보다 매체 차이가 큽니다.")
            names = [i for i in seg.index if i != dl.GA4_ALL]
            s1, s2 = st.columns(2)
            a_seg = s1.selectbox("비교할 세그먼트 A", names, index=0)
            b_seg = s2.selectbox("비교할 세그먼트 B", names, index=names.index("cpc") if "cpc" in names else min(1, len(names) - 1))
            z, p = dl.two_prop_z(seg.loc[a_seg, "purchases"], seg.loc[a_seg, "visitors"], seg.loc[b_seg, "purchases"], seg.loc[b_seg, "visitors"])
            st.markdown(f"{overall} **{a_seg} {seg.loc[a_seg, overall]:.2%}** vs **{b_seg} {seg.loc[b_seg, overall]:.2%}** · "
                        f"z = {z:.2f}, p = {p:.3g} → " + ("**우연이 아닐 가능성이 높은 차이** (p < 0.05)" if p < 0.05 else "우연일 수 있는 차이"))
            st.caption("매체별 전환율 차이는 ⑥ 계산에서 네이버 검색광고의 구매 확률 배수(cpc ÷ 전체)로 쓰입니다. 광고 성과 CSV가 있으면 그것이 우선합니다.")

# ─────────────────── ⑤ 자동화: 재구매 가정 (엔진 파라미터라 먼저 받음) ───────────────────
with tabs[4]:
    badge_slot = st.container()
    with st.expander("지금 재구매·추천 가정 (자동화 전)"):
        r1, r2 = st.columns(2)
        with r1:
            ret_src, fit = "임시값 (UCI 코호트 결과 대기)", None
            segments = dl.retention_segments()
            retail = [i for i, x in enumerate(segments) if "소매" in x or "제외" in x]
            rseg = st.selectbox("재구매 기본값으로 쓸 손님 유형", segments, index=retail[0] if retail else 0) if segments else None
            ret_table = dl.retention_curve_table(segment=rseg)
            if ret_table is not None and len(ret_table) >= 3:
                hold = dl.fit_retention(ret_table, fit_months=min(6, int(ret_table["months_since"].max()) - 1))
                fit = dl.fit_retention(ret_table)
                ret_src = f"UCI 코호트 적합 ({rseg or '전체'}) · 이후 기간 오차 MAE {hold.get('holdout_mae', float('nan')):.3f}"
            floor = st.slider("오래 지나도 꾸준히 오는 단골 비율", 0.0, 0.6, round(fit["floor"], 3) if fit else float(D.RETENTION_FLOOR), 0.005,
                              key=f"floor_{rseg}_{fit is not None}")
            decay = st.slider("첫 구매 후 손님이 떠나는 속도", 0.1, 5.0, round(fit["decay"], 2) if fit else float(D.RETENTION_DECAY), 0.05,
                              key=f"decay_{rseg}_{fit is not None}")
            st.caption(f"출처: {ret_src}")
        with r2:
            invite_rate = st.slider("단골 1명이 한 달에 소개하는 사람 수", 0.0, 2.0, float(D.INVITE_RATE), 0.05, help="모르면 0")
            invite_conv = st.slider("소개받은 사람이 실제 손님이 되는 비율", 0.0, 1.0, float(D.INVITE_CONV), 0.01)
            referral_reward = st.number_input("추천 1명당 보상 (원, 혜택비)", 0, 1_000_000, 0, step=1_000,
                                              help="추천한 사람·추천받은 사람에게 주는 적립금·쿠폰. ⑥ 추천에는 매출이 없고 이 비용만 있습니다. "
                                                   "추천으로 온 손님의 매출은 그 손님의 ④ 구매·⑤ 재구매에서 셉니다.")
        ret_chart_slot = st.container()

params = FunnelParams(steps=steps, retention_floor=floor, retention_decay=decay, purchase_freq=freq,
                      aov=aov, margin=margin, invite_rate=invite_rate, invite_conv=invite_conv, referral_reward=referral_reward)

# 채널 전환율 배수: CSV > GA4 매체별 > 기본값 중 하나만 (MECE #4). 어트리뷰션 보정은 ④에서 그 위에 한 번만
naver_cvr_base, naver_cvr_src = dl.resolve_cvr_mult("naver", D.NAVER_CVR_MULT, params.cvr, medium, upload,
                                                     seg_cvr=seg_cvr, seg_label=seg_label)
meta_cvr_base, meta_cvr_src = dl.resolve_cvr_mult("meta", meta_cvr_in, params.cvr, medium, upload,
                                                   seg_cvr=seg_cvr, seg_label=seg_label)
if meta_cvr_src.startswith("가정값") and meta_cvr_in != D.META_CVR_MULT:
    meta_cvr_src = "직접 입력"
base_channels = [
    Channel("naver", "네이버 검색", naver_curve, naver_cvr_base, D.NAVER_RETENTION_MULT, billing="click", incr_mult=naver_incr),
    Channel("meta", "메타", meta_curve, meta_cvr_base, meta_ret_mult, billing=meta_billing, incr_mult=meta_incr),
] + ([gonggu] if gonggu else [])

# ─────────────────────────── ④ 어트리뷰션 ───────────────────────────
with tabs[3]:
    a1, a2 = st.columns([1, 1])
    with a1:
        path_file = st.file_uploader("내 전환 경로 CSV (path, conversions, revenue) — 없으면 GA4 샘플", type="csv",
                                     help="path는 접점을 ' > '로 연결 (예: naver > meta > direct). GA4 BigQuery·MMP 경로 리포트를 이 형식으로 내보내세요.")
        paths = None
        if path_file is not None:
            try:
                paths = A.from_upload(pd.read_csv(path_file))
                path_src = f"올린 파일 ({len(paths):,}개 경로)"
            except Exception as e:  # noqa: BLE001
                st.error(f"경로 CSV를 읽지 못했습니다: {e}")
        if paths is None:
            paths = load_paths()
            path_src = "GA4 샘플 (구매 5,692건)"
        domains_text = st.text_input("내 도메인 (자기 참조로 거를 주소, 쉼표로)", ", ".join(A.SELF_DOMAINS) if path_file is None else "",
                                     help="결제·로그인 페이지에서 돌아온 방문이 외부 유입으로 잡히지 않게 거릅니다.")
    with a2:
        clean = st.toggle("정제 후 (자기 참조 제거)", value=True, help="끄면 정제 전 결과를 봅니다. 시연: referral 기여가 어떻게 바뀌는지")
        st.caption(f"데이터: {path_src}. 전환 인정 기간: 경로에 접점 시각이 없어 적용하지 않음 (GA4 기본 30일)")
    table, sp, attr_verdict, model, k_naver, k_meta = None, pd.Series(dtype=float), "경로 데이터가 없습니다.", "last", 1.0, 1.0
    if paths is not None and len(paths):
        domains = [d.strip() for d in domains_text.split(",") if d.strip()]
        cleaned = A.clean_paths(paths, domains, clean=clean)
        table = A.credit_table(cleaned)
        sp = A.spread(table.drop(index=A.UNKNOWN, errors="ignore"))
        attr_verdict = A.verdict(table)
        t1, t2 = st.columns([1, 1])
        with t1:
            show = table.rename(columns=A.MODELS)
            show["변동폭 (%p)"] = table.max(axis=1) - table.min(axis=1)
            st.dataframe(show.style.format("{:.1f}"), width="stretch")
            st.caption(f"구매 중 접점 1개짜리 경로 {A.single_touch_share(cleaned):.1%}. 값은 채널에 **배분된** 기여(%)이며, 그 채널이 만든 전환은 아닙니다."
                       + (f" 정제 전 referral 접점의 {A.self_ref_share(paths):.1%}가 '{A.SELF_DOMAINS[0]}' 자기 참조입니다."
                          if path_file is None else ""))
        t2.plotly_chart(charts.attribution_bars(table.head(6), A.MODELS), use_container_width=True)

        st.subheader("보정 전후 배분")
        b1, b2, b3 = st.columns(3)
        model = b1.selectbox("보정에 쓸 모델", list(A.MODELS), format_func=A.MODELS.get, index=1,
                             help="마지막 클릭 = 보정 없음 (매체 보고·많은 도구의 기본 관점)")
        path_chs = [c for c in table.index if c != A.UNKNOWN]
        opts = ["(연결 안 함)"] + path_chs
        guess = {"naver": next((c for c in ("naver", "cpc", "paid_search") if c in path_chs), "(연결 안 함)"),
                 "meta": next((c for c in ("meta", "paid_social", "social", "facebook", "instagram") if c in path_chs), "(연결 안 함)")}
        map_naver = b2.selectbox("네이버 검색광고 = 경로의", opts, index=opts.index(guess["naver"]))
        map_meta = b3.selectbox("메타 = 경로의", opts, index=opts.index(guess["meta"]))
        k = A.correction_factors(table, model)
        k_naver = float(k.get(map_naver, 1.0)) if map_naver != "(연결 안 함)" else 1.0
        k_meta = float(k.get(map_meta, 1.0)) if map_meta != "(연결 안 함)" else 1.0
        st.caption(f"보정계수 k = {A.MODELS[model]} 기여 ÷ 마지막 클릭 기여. 식별 불가를 뺀 채널 전체에서 총 전환이 보존되도록 정규화 → "
                   f"네이버 {k_naver:.2f}배 · 메타 {k_meta:.2f}배. 이 배수는 구매 확률 배수 위에 한 번만 곱합니다.")
    attr_slot = st.container()
    with st.expander("매체가 보고한 전환 수와 GA4 숫자가 왜 다를까? (체크리스트)"):
        r1, r2 = st.columns(2)
        rep = r1.number_input("매체가 보고한 전환 수 (예: 메타 광고 관리자)", min_value=0, value=0)
        ga = r2.number_input("같은 기간 GA4 전환 수 (같은 채널)", min_value=0, value=0)
        if rep and ga:
            st.metric("매체 보고 ÷ GA4", f"{rep / ga:.2f}배")
        for item in A.REPORT_GAP_CHECKLIST:
            st.markdown(f"- {item}")

channels = [
    Channel("naver", "네이버 검색", naver_curve, naver_cvr_base * k_naver, D.NAVER_RETENTION_MULT, billing="click", incr_mult=naver_incr),
    Channel("meta", "메타", meta_curve, meta_cvr_base * k_meta, meta_ret_mult, billing=meta_billing, incr_mult=meta_incr),
] + ([gonggu] if gonggu else [])
corrected = abs(k_naver - 1) > 1e-9 or abs(k_meta - 1) > 1e-9

# ─────────────────────────── ⑤ 자동화: 시나리오 ───────────────────────────
with tabs[4]:
    with badge_slot:
        cols = st.columns(len(AU.BADGES))
        for c, (badge, desc) in zip(cols, AU.BADGES):
            c.markdown(f"**{badge}**", help=desc)
    st.caption("입력은 모두 직접 넣는 값입니다 (기본값 없음). **증분 반응률**은 메시지를 받은 사람과 받지 않은 대조군의 구매율 차이입니다. "
               "발송 도구의 '클릭 후 구매율'을 넣으면 효과가 부풀려집니다. 모르면 비워 두고 손익분기 반응률만 보세요.")
    auto_results = []
    scols = st.columns(3)
    for col, key in zip(scols, AU.SCENARIOS):
        sc = AU.SCENARIOS[key]
        with col.container(border=True):
            on = st.checkbox(f"**{sc['label']}**", key=f"auto_on_{key}")
            st.caption(f"대상: {sc['target']} · 효과: {sc['effect']} · {sc['message']}")
            if not on:
                continue
            reach = st.number_input("도달 가능 비율 (%)", 0.0, 100.0, value=None, step=5.0, key=f"reach_{key}",
                                    help="대상 중 채널 친구이거나 광고성 정보 수신에 동의한 사람의 비율")
            cost = st.number_input("건당 발송비 (원)", 0.0, 1_000.0, value=None, step=1.0, key=f"cost_{key}", help="사용 중인 발송 대행사 단가")
            resp = st.number_input("증분 반응률 (%) — 모르면 비워 두기", 0.0, 100.0, value=None, step=0.1, key=f"resp_{key}")
            disc = st.number_input("쿠폰 할인율 (%, 선택)", 0.0, 90.0, value=0.0, step=5.0, key=f"disc_{key}")
            dormant_n = st.number_input("휴면 기준: 첫 구매 후 몇 개월", 1, 11, 3, key=f"n_{key}",
                                        help="업종별 구매 주기를 모르므로 직접 입력") if key == "dormant" else 3
            if reach is None or cost is None:
                st.caption("도달 가능 비율과 건당 발송비를 넣으면 계산합니다.")
                continue
            inp = AU.ScenarioInput(key, reach / 100, cost, None if resp is None else resp / 100, disc / 100, int(dormant_n))
            r = AU.run_scenario(channels, spends, params, inp)
            auto_results.append(r)
            st.metric("손익분기 반응률", pct(r["breakeven"]), help="받은 사람 중 이 비율 이상이 '더' 사야 발송비를 메웁니다 (재구매 효과 제외, 보수적)")
            st.markdown(f"월 발송 {r['sends_month']:,.0f}건 · 월 발송비 {won(r['cost_month'])}")
            if r["profit_delta"] is not None:
                st.metric("1년 동안 남는 돈 변화", signed(r["profit_delta"]), delta="발송비·할인 뺀 뒤", delta_color="off")
                if r["ad_alt_delta"] is not None:
                    st.plotly_chart(charts.money_compare(["메시지", "같은 돈을 광고에"], [r["profit_delta"], r["ad_alt_delta"]]),
                                    use_container_width=True, key=f"cmp_{key}")
            with st.expander("대조군 실험 설계"):
                p0 = st.number_input("대조군(메시지 안 받은 대상)의 구매율 (%) — 모르면 비워 두기", 0.0, 100.0, value=None, step=0.5, key=f"p0_{key}")
                if p0:
                    s = sample_size(p0 / 100, r["breakeven"] / (p0 / 100))
                    d = days_needed(s["n_per_group"] / 0.1, r["sends_month"])
                    st.markdown(f"대상의 10%를 **대조군으로 남기고** 보내지 않습니다. 손익분기만큼의 차이({pct(r['breakeven'])}p)를 확인하려면 "
                                f"그룹마다 {s['n_per_group']:,.0f}명 → 대조군 10%로 모으면 약 **{d:,.0f}일**" if d < 10_000 else
                                "지금 발송량으로는 대조군 실험이 어렵습니다. 발송 대상을 넓히거나 기간을 길게 잡으세요.")
                else:
                    st.caption("대조군 구매율을 알면 필요한 표본과 기간을 계산합니다. 처음엔 10% 대조군으로 2~4주 보내 이 값을 먼저 재세요.")
    has_resp = any(r["profit_delta"] is not None for r in auto_results)
    auto_params, auto_cost = AU.combine(params, auto_results, params.months) if has_resp else (None, None)
    with ret_chart_slot:
        st.plotly_chart(charts.retention_curve(auto_params or params, actual=ret_table), use_container_width=True)
        if auto_params is not None:
            st.caption("곡선은 반응률을 넣은 자동 메시지를 반영한 재구매 비율입니다.")

# ─────────────────────── 계산 (입력이 바뀔 때만 최적화 재계산) ───────────────────────
res = simulate(channels, spends, params)
ckey = repr((omtm, budget, spends, params, [(c.key, c.cvr_mult, c.retention_mult, c.incr_mult, c.billing, None if c.budgeted else vars(c.curve)) for c in channels], sorted(estimates), meta_cpc, meta_sat))
opt, opt_profit, opt_roas, levers, scan = cached("opt", ckey, lambda: (
    optimize_allocation(channels, budget, params, omtm),
    optimize_allocation(channels, budget, params, "profit"),
    optimize_allocation(channels, budget, params, "roas"),
    lever_table(channels, spends, params),
    budget_scan(channels, spends, params)))
opt = dict(opt, omtm=omtm, base_value={"new_customers": res.summary["new_customers"], "profit": res.summary["profit_12m"],
                                       "roas": res.summary["roas"] or 0.0}[omtm])
res_opt = simulate(channels, opt["spends"], params)
pmf = res.summary["ltv_cac"] is not None and res.summary["ltv_cac"] < D.PMF_LTV_CAC_THRESHOLD
okey = repr((ckey, repr(auto_params), None if auto_cost is None else np.round(auto_cost, 2).tolist(), pmf))
options = cached("options", okey, lambda: compare_options(channels, spends, params, levers, budget, None,
                                                          auto_params, auto_cost, pmf_warning=pmf))

# 보정 전후 배분 (④)
with attr_slot:
    if corrected:
        before = cached("opt_before", repr((ckey, naver_cvr_base, meta_cvr_base)),
                        lambda: optimize_allocation(base_channels, budget, params, "profit"))
        rows = []
        for name, sp_ in [("보정 전 최적 (마지막 클릭)", before["spends"]), (f"보정 후 최적 ({A.MODELS[model]})", opt_profit["spends"])]:
            s = simulate(channels, sp_, params).summary
            rows.append({"배분": name, "네이버 (월)": sp_[0], "메타 (월)": sp_[1], "1년 동안 남는 돈 (보정 가정)": s["profit_12m"]})
        st.dataframe(pd.DataFrame(rows).style.format({c: "{:,.0f}" for c in ["네이버 (월)", "메타 (월)", "1년 동안 남는 돈 (보정 가정)"]}),
                     hide_index=True, width="stretch")
        st.caption("두 배분 모두 보정 후 가정으로 1년 이익을 계산했습니다. 차이 = 마지막 클릭만 믿고 배분했을 때 놓치는 돈. "
                   "⑥ '채널 재배분'은 보정 가정에서 계산합니다.")
    else:
        st.caption("'보정에 쓸 모델'을 마지막 클릭이 아닌 것으로 바꾸고 경로 채널을 네이버·메타에 연결하면 보정 전후 배분을 비교합니다.")

# ─────────────────────────── ⑥ 결과·우선순위 ───────────────────────────


def kpis(s):
    cols = st.columns(4) + st.columns(3)
    cols[0].metric("1년 동안 남는 돈", won(s["profit_12m"]), help=HELP["profit"])
    cols[1].metric("새 손님 (1년)", f"{s['new_customers']:,.0f}명", help=HELP["new"])
    cols[2].metric("손님 1명 데려오는 비용 (CAC)", won(s["paid_cac"]), help=HELP["paid_cac"])
    cols[3].metric("손님 1명이 1년간 남기는 돈 (LTV)", won(s["ltv_12m"]), help=HELP["ltv"])
    cols[4].metric("남기는 돈 ÷ 데려오는 비용", f"{s['ltv_cac']:.2f}배" if s["ltv_cac"] else "-", help=HELP["ltv_cac"])
    cols[5].metric("광고비 본전 찾는 기간", f"{s['payback_month']}개월" if s["payback_month"] else "36개월 넘음", help=HELP["payback"])
    cols[6].metric("광고비 1원당 첫 매출 (ROAS)", f"{s['roas']:.2f}원" if s["roas"] else "-", help=HELP["roas"])


def verdict(s, opt_profit_spends):
    """신호등 + 쉬운 문장."""
    ratio, cac, ltv = s["ltv_cac"], s["paid_cac"], s["ltv_12m"]
    if ratio is None:
        return "info", "광고비가 0원이라 광고 효과를 계산할 수 없습니다. ① 시작에서 한 달 광고비를 넣어 주세요."
    if ratio < 1:
        return "error", (f"🔴 **지금 조건이면 광고를 할수록 손해입니다 (PMF 경고).** 손님 1명을 데려오는 데 {won(cac)}이 드는데, "
                         f"그 손님이 1년 동안 남겨 주는 돈은 {won(ltv)}뿐입니다. 광고비 증액은 보류하고 유지·활성화 선택지를 먼저 봅니다. "
                         "(① 객단가·마진이 우리 가게 숫자와 맞는지도 확인하세요.)")
    if s["profit_12m"] < 0:
        return "warning", (f"🟡 **손님 한 명 한 명은 남는 장사지만, 1년 안에는 아직 적자입니다** ({won(s['profit_12m'])}). "
                           f"광고비 본전을 찾는 데 {s['payback_month'] or '36+'}개월이 걸려서입니다.")
    msg = f"🟢 **광고가 돈을 벌어 줍니다.** 1년 동안 {won(s['profit_12m'])}이 남고, 광고비 본전은 {s['payback_month']}개월이면 찾습니다."
    if sum(opt_profit_spends) < budget * 0.9:
        msg += f"  \n다만 한 달 {won(sum(opt_profit_spends))} 정도만 써도 이익이 가장 큽니다."
    return "success", msg


def exp_card(row):
    """선택지별 실험 설계 카드 (명세 6장, 10-3)."""
    name = row["option"]
    if name == "광고비 증액":
        st.markdown("**지역·기간 분할 실험**: 비슷한 지역(또는 주) 두 묶음 중 한쪽만 예산을 10% 늘리고 2~4주 비교합니다. "
                    "매체 보고 전환이 아니라 **전체 매출·문의 수**로 비교해야 증분이 보입니다.")
    elif name == "채널 재배분":
        st.markdown("**기간 분할 실험**: 추천 배분으로 2주 → 원래 배분으로 2주를 번갈아 집행하고 같은 기간 전체 전환을 비교합니다. "
                    "④ 기여 보정은 인과가 아니므로, 이 실험이 보정 가정을 확인합니다.")
    elif name == "퍼널 개선":
        step_names = [n for n, _ in params.steps]
        label = row["detail"].replace(" (이탈 감소) 10%", "")
        i = step_names.index(label) if label in step_names else int(np.argmin([r for _, r in params.steps]))
        st.markdown(f"**A/B 테스트**: '{step_names[i]}' 단계를 두 버전으로 만들어 손님을 반씩 나눕니다. 바꿔 볼 것: {prescription(step_names[i])}")
        lift = st.slider("확인하고 싶은 개선 (지금보다 %)", 1, 50, 10, key="ab_lift") / 100
        e1, e2 = st.columns(2)
        alpha = e1.selectbox("유의수준 α (우연을 효과로 착각할 위험)", [0.05, 0.1, 0.01], key="ab_alpha")
        power = e2.selectbox("검정력 1−β (진짜 효과를 찾아낼 확률)", [0.8, 0.9], key="ab_power")
        base_rate = params.steps[i][1]
        s = sample_size(base_rate, lift, alpha, power)
        monthly_in = res.funnel.iloc[i]["count"] / 12
        days = days_needed(s["n_total"], monthly_in)
        st.markdown(f"통과율 **{base_rate:.1%} → {s['p2']:.1%}** 확인에 A·B 각각 **{s['n_per_group']:,.0f}명** · 광고로 이 단계에 한 달 {monthly_in:,.0f}명 → "
                    + (f"약 **{days:,.0f}일**" if days < 10_000 else "지금 손님 수로는 어려움")
                    + (" (너무 길면 광고 외 방문자까지 포함해 실험하세요)" if days > 60 else ""))
    elif name.startswith("공동구매"):
        st.markdown("**전용 쿠폰으로 실제 판매 확인**: 공구마다 전용 쿠폰 코드나 링크를 만들어 자사 주문에서 그 코드의 구매 수·재구매를 셉니다. "
                    "외부 몰에서 팔면 정산서로 판매 수만 확인하고, 재구매는 볼 수 없다는 점을 표시합니다. "
                    "증분은 공구 기간 전후의 같은 상품 자연 판매와 비교해 대략 확인합니다.")
    else:
        st.markdown("**대조군(홀드아웃) 실험**: 대상의 10%에게는 보내지 않고 두 그룹의 구매율 차이(증분 반응률)를 잽니다. "
                    "필요한 인원·기간은 ⑤ 시나리오 카드의 '대조군 실험 설계'에서 계산합니다.")


with tabs[5]:
    warn = warnings(res, alloc)
    lvl, msg = verdict(res.summary, opt_profit["spends"])
    getattr(st, lvl)(msg)
    defaults_used = [name for name, used in [("① 객단가·마진 기본값", aov == D.AOV and margin == D.MARGIN),
                                             ("② 예시 검색어", hint_text == ns.SAMPLE_KEYWORD), ("③ GA4 샘플 퍼널", fun_df is None and not funnel_edited),
                                             ("④ 보정 없음(마지막 클릭)", not corrected), ("⑤ 자동 메시지 미입력", auto_params is None)] if used]
    if defaults_used:
        st.caption("기본값 사용 중: " + " · ".join(defaults_used))
    st.subheader("4가지 선택지 비교 (같은 기준: 1년 동안 남는 돈 증가)")
    o1, o2 = st.columns([3, 2])
    with o1:
        def _cost(r):
            if r["gain"] != r["gain"]:
                return "-"
            return {"known": f"{won(r['cost'])} (이미 뺌)", "zero": "0원 (같은 예산)",
                    "ceiling": f"모름 → {won(r['cost'])}까지 써도 이득"}[r["cost_kind"]]
        tbl = pd.DataFrame({"선택지": options["option"] + np.where(options["disabled"], " (PMF 경고로 보류)", ""),
                            "내용": options["detail"], "1년 남는 돈 증가": options["gain"], "비용": options.apply(_cost, axis=1)})
        st.dataframe(tbl.style.format({"1년 남는 돈 증가": lambda v: "-" if v != v else f"{v:+,.0f}원"})
                     .apply(lambda r: ["color: #999"] * len(r) if "보류" in r["선택지"] else [""] * len(r), axis=1),
                     hide_index=True, width="stretch")
    o2.plotly_chart(charts.options_bars(options), use_container_width=True)
    st.caption("모든 숫자는 '가정이 맞다면'의 예측입니다. 아래 실험 카드로 확인한 뒤 실행하세요.")
    for _, row in options.iterrows():
        if row["gain"] != row["gain"]:
            continue
        with st.expander(f"🧪 {row['option']} — 실험으로 확인하기"):
            exp_card(row)
    if warn:
        with st.expander(f"먼저 확인할 것 ({len(warn)})", expanded=any(lv == "error" for lv, _ in warn)):
            for wl, text in warn:
                getattr(st, wl)(text)
    st.subheader("지금 계획의 주요 숫자")
    st.caption(f"채널별 구매 확률 배수: 네이버 {channels[0].cvr_mult:.2f}배 ({naver_cvr_src}{f' × 어트리뷰션 {k_naver:.2f}' if k_naver != 1 else ''}) · "
               f"메타 {channels[1].cvr_mult:.2f}배 ({meta_cvr_src}{f' × 어트리뷰션 {k_meta:.2f}' if k_meta != 1 else ''}) · "
               f"메타 재방문 배수 {meta_ret_mult:.2f}배 ({'가정값' if meta_ret_mult == D.META_RETENTION_MULT else '직접 입력'}) · "
               f"증분 계수 네이버 {naver_incr:.2f} · 메타 {meta_incr:.2f}" + ("" if naver_incr < 1 or meta_incr < 1 else " (측정값 없음, 기본 1)"))
    kpis(res.summary)
    with st.expander("계획별 비교와 그래프"):
        def plan_row(name, sp_, r):
            s = r.summary
            return {"계획": name, "네이버 (월)": sp_[0], "메타 (월)": sp_[1], "아끼는 돈 (월)": budget - sum(sp_),
                    "새 손님": s["new_customers"], "LTV/CAC": s["ltv_cac"], "ROAS": s["roas"], "1년 동안 남는 돈": s["profit_12m"]}
        rows = [plan_row("지금 계획", spends, res), plan_row(f"추천 계획 ({OMTM_PLAIN[omtm]})", opt["spends"], res_opt)]
        if omtm != "profit":
            rows.append(plan_row("남는 돈이 가장 큰 계획", opt_profit["spends"], simulate(channels, opt_profit["spends"], params)))
        if omtm != "roas":
            rows.append(plan_row("ROAS가 가장 높은 계획", opt_roas["spends"], simulate(channels, opt_roas["spends"], params)))
        st.dataframe(pd.DataFrame(rows).style.format({"네이버 (월)": "{:,.0f}", "메타 (월)": "{:,.0f}", "아끼는 돈 (월)": "{:,.0f}",
                                                      "새 손님": "{:,.0f}", "LTV/CAC": "{:.2f}", "ROAS": "{:.2f}", "1년 동안 남는 돈": "{:,.0f}"},
                                                     na_rep="-"), hide_index=True, width="stretch")
        st.caption("💡 ROAS(첫 매출)만 보고 짠 예산과 실제로 남는 돈이 가장 큰 예산은 다를 수 있습니다.")
        c1, c2 = st.columns(2)
        c1.plotly_chart(charts.aarrr_funnel(res.funnel, res.summary), use_container_width=True)
        c2.plotly_chart(charts.cum_profit(res.monthly, res_opt.monthly, f"추천 계획 ({OMTM_PLAIN[omtm]})"), use_container_width=True)
        c1.plotly_chart(charts.revenue_split(res.monthly), use_container_width=True)
        c2.plotly_chart(charts.budget_scan_chart(scan, budget), use_container_width=True)
        c1.plotly_chart(charts.payback(res.customer_cum_profit, res.summary["paid_cac"]), use_container_width=True)
        c2.plotly_chart(charts.tornado(levers), use_container_width=True)
        core = levers[levers["core"]][["lever", "extra_spend", "up", "breakeven_cost"]].rename(columns={
            "lever": "10% 좋아지면", "extra_spend": "더 쓰는 광고비", "up": "1년 동안 남는 돈 변화", "breakeven_cost": "이만큼까지 써도 이득"})
        st.dataframe(core.style.format({"더 쓰는 광고비": "{:,.0f}", "1년 동안 남는 돈 변화": "{:+,.0f}", "이만큼까지 써도 이득": "{:,.0f}"},
                                       na_rep="-"), hide_index=True, width="stretch")
        st.caption("남는 돈은 모두 광고비를 뺀 뒤의 금액입니다. 전체 전환율·객단가·구매 횟수 10%는 계산상 효과가 같아 '손님 1명당 매출' 하나로 묶었습니다.")
    with st.expander("이렇게 해 보세요 (인사이트 카드)"):
        for card in insights(res, levers, opt, D.OMTM_OPTIONS[omtm], scan, opt_profit, opt_roas, recs):
            st.markdown(f"**{card['title']}**  \n📊 근거: {card['evidence']}  \n🧪 해 볼 일: {card['action']}")
    with st.expander("자세히 보기: 채널별·월별 표 (CSV 다운로드)"):
        bc = res.by_channel[["label", "billing", "budget", "spend", "clicks", "cpc", "marginal_cpc", "new_customers", "cac", "ltv_12m"]].rename(columns={
            "label": "채널", "billing": "과금 방식", "budget": "배정한 돈", "spend": "실제로 쓸 수 있는 돈", "clicks": "클릭", "cpc": "평균 클릭당 비용",
            "marginal_cpc": "클릭 1번 더 얻는 비용", "new_customers": "새 손님", "cac": "손님 1명 데려오는 비용", "ltv_12m": "손님 1명이 1년간 남기는 돈"})
        st.dataframe(bc.style.format("{:,.0f}", subset=[c for c in bc.columns if c not in ("채널", "과금 방식", "새 손님")], na_rep="-")
                     .format("{:,.1f}", subset=["새 손님"], na_rep="-"), hide_index=True, width="stretch")
        monthly = res.monthly.rename(columns={
            "month": "개월", "spend": "광고비", "clicks": "클릭", "paid_new": "광고로 온 새 손님", "referral_new": "추천으로 온 새 손님",
            "new_customers": "새 손님 합계", "active": "그달 구매한 손님", "orders": "주문 수", "revenue": "매출",
            "new_revenue": "새 손님 매출", "repeat_revenue": "재구매 매출", "gross_profit": "남는 돈(광고비 전)",
            "extra_cost": "메시지 비용", "referral_reward": "추천 보상", "profit": "남는 돈(광고비 후)", "cum_profit": "누적 남는 돈"})
        st.dataframe(monthly.style.format("{:,.0f}"), hide_index=True, width="stretch")
        st.download_button("월별 표 CSV 내려받기", monthly.to_csv(index=False).encode("utf-8-sig"), "monthly.csv", "text/csv")

# ─────────────────────── 탭 맨 위: 질문 한 줄 + 결과 숫자 하나 ───────────────────────
with heads[0]:
    question("1년 뒤 광고가 남겨 주는 돈은 얼마인가요?")
    st.metric("지금 계획의 1년 동안 남는 돈", won(res.summary["profit_12m"]),
              delta=f"LTV/CAC {res.summary['ltv_cac']:.2f}배" if res.summary["ltv_cac"] else None, delta_color="off", help=HELP["profit"])

with heads[1]:
    question("이 예산을 어느 매체·키워드에 얼마나 쓸까?")
    sat = alloc[alloc["saturated"] & (alloc["spend"] > 0)]["keyword"].tolist() if alloc is not None else []
    st.metric("남는 돈이 가장 큰 배분 (한 달)", f"네이버 {won(opt_profit['spends'][0])} · 메타 {won(opt_profit['spends'][1])}",
              delta=("포화: " + ", ".join(f"'{k}'" for k in sat)) if sat else "포화된 검색어 없음", delta_color="off")
    base_p = res.summary["profit_12m"]
    nxt = {c.label: simulate(channels, [s + (10_000 if i == j else 0) for j, s in enumerate(spends)], params).summary["profit_12m"] - base_p
           for i, c in enumerate(channels) if c.budgeted}
    best_ch = max(nxt, key=nxt.get)
    st.caption(f"다음 1만 원(매달)을 어디에 쓰면 가장 많이 남나: **{best_ch}** (1년 {signed(nxt[best_ch])}). "
               "채널별 한계 이익이 같아질 때까지 나누는 것이 최적입니다.")
with learn_slot:
    meta_cvr = params.cvr * channels[1].cvr_mult
    if meta_budget > 0 and meta_cvr > 0:
        lc = learning_check(meta_budget, int(ad_sets), meta_cpc / meta_cvr)
        if not lc["ok"]:
            st.warning(f"메타 학습 가능 예산 부족: 광고 세트 {int(ad_sets)}개 × 주 약 {LEARNING_EVENTS_PER_WEEK}건 × 예상 CPA {won(meta_cpc / meta_cvr)} "
                       f"= 주 {won(lc['weekly_needed'])}이 필요한데, 주 예산은 {won(lc['weekly_budget'])}입니다 (세트당 주 {lc['events_per_set']:.1f}건). "
                       "광고 세트를 합치거나 최적화 이벤트를 앞 단계(장바구니 등)로 바꾸세요. (50건은 메타 도움말 검색 요약 기준)")

with funnel_slot:
    st.plotly_chart(charts.activation_funnel(params), use_container_width=True)
    st.metric(f"광고 클릭 → {task}까지 가는 비율 (전환율, CVR)", f"{params.cvr:.2%}")

steps_lv = levers[levers["key"].str.startswith("step_")].sort_values("up", ascending=False)
if len(steps_lv):
    best = steps_lv.iloc[0]
    bname = best["lever"].replace("단계: ", "").replace(" (이탈 감소)", "")
    with heads[2]:
        question("손님이 어디서 새고, 그 단계를 고치면 얼마가 남나?")
        st.metric("가장 큰 기회", bname, delta=f"이탈 10% 감소 → 1년 {signed(best['up'])}", delta_color="off")
    with opp_slot:
        rate = dict(params.steps)[bname]
        per_month = res.summary["paid_new"] / 12
        extra = per_month * ((1 - (1 - rate) * 0.9) / rate - 1) if rate > 0 else 0.0
        dname, drate = biggest_drop(params)
        with st.container(border=True):
            st.markdown(f"**가장 큰 기회: '{bname}'** — 이탈 10% 감소 시 광고로 온 손님 월 **+{extra:,.1f}명**, "
                        f"1년 동안 남는 돈 **{signed(best['up'])}** (개선에 이만큼까지 써도 이득)  \n처방: {prescription(bname)}"
                        + (f"  \n가장 많이 새는 곳은 '{dname}'(100명 중 {drate * 100:.0f}명 통과)이지만, 고쳤을 때 효과는 '{bname}'이 가장 큽니다."
                           if dname != bname else ""))

with heads[3]:
    question("매체가 보고한 숫자를 믿고 예산을 나눠도 되나?")
    if len(sp):
        st.metric("모델을 바꿨을 때 채널 기여의 최대 변동폭", f"{sp.iloc[0]:.1f}%p", delta=str(sp.index[0]), delta_color="off")
    st.info(attr_verdict + ("" if clean else "  \n⚠️ 지금은 **정제 전** 결과입니다."), icon="⚖️")

with heads[4]:
    question("장바구니 이탈·재구매·휴면 메시지가 광고비보다 나은가?")
    withp = [r for r in auto_results if r["profit_delta"] is not None]
    if withp:
        b = max(withp, key=lambda r: r["profit_delta"])
        st.metric(f"가장 나은 시나리오: {b['label']}", signed(b["profit_delta"]),
                  delta=f"같은 돈을 광고에: {signed(b['ad_alt_delta']) if b['ad_alt_delta'] is not None else '-'}", delta_color="off")
    elif auto_results:
        b = min(auto_results, key=lambda r: r["breakeven"])
        st.metric(f"손익분기 반응률 ({b['label']})", pct(b["breakeven"]), delta="반응률을 넣으면 이익을 계산", delta_color="off")
    else:
        st.metric("손익분기 반응률", "-", delta="아래에서 시나리오를 켜고 도달 비율·발송비를 넣으세요", delta_color="off")

with heads[5]:
    question("광고비 증액 · 채널 재배분 · 퍼널 개선 · 자동 메시지 중 무엇을 먼저 할까?")
    top_opt = options.dropna(subset=["gain"])
    top_opt = top_opt[~top_opt["disabled"].astype(bool)]
    if len(top_opt):
        t = top_opt.iloc[0]
        sp_gain = float(options.loc[options["option"] == "광고비 증액", "gain"].iloc[0])
        ratio = f" (광고비 +10%의 {t['gain'] / sp_gain:.1f}배)" if t["option"] != "광고비 증액" and sp_gain > 0 else ""
        st.metric("먼저 할 것", t["option"], delta=f"1년 {signed(t['gain'])}{ratio}", delta_color="off")
        if t["cost_kind"] == "ceiling":
            st.caption(f"비용을 모르는 개선은 1년 동안 최대 {won(t['cost'])}까지 쓸 가치가 있습니다.")

st.divider()
st.caption("데이터: 네이버 검색광고 API(예측값, 최근 4주 → 월 환산), GA4 공개 샘플(퍼널·구매 경로), Kaggle Sales Conversion Optimization(상대 배수만). "
           "리텐션·구매 빈도는 UCI Online Retail II 분석 후 교체 예정. 결과는 출발점을 잡기 위한 추정치이며, 내 숫자를 넣을수록 정확해집니다.")

# ─────────────────────── 플로팅 도움말 챗봇 (규칙 기반) ───────────────────────
top_row = top_opt.iloc[0] if len(top_opt) else None
help_ctx = {
    "profit": res.summary["profit_12m"], "ltv": res.summary["ltv_12m"], "cac": res.summary["paid_cac"],
    "ltv_cac": res.summary["ltv_cac"], "roas": res.summary["roas"], "payback": res.summary["payback_month"],
    "cvr": params.cvr, "aov": aov, "margin": margin, "pmf": pmf,
    "verdict": verdict(res.summary, opt_profit["spends"])[1],
    "top_option": None if top_row is None else (top_row["option"], float(top_row["gain"]), top_row["cost_kind"], float(top_row["cost"])),
    "best_step": (bname, float(best["up"]), prescription(bname)) if len(steps_lv) else None,
    "attribution": attr_verdict,
}


@st.fragment
def help_chat(ctx):
    """질문할 때 앱 전체가 아니라 이 채팅만 다시 그린다 (답은 마지막 전체 계산 결과 ctx로)."""
    screen = st.selectbox("지금 보고 있는 화면", TAB_NAMES, key="help_screen")
    chat = ss.setdefault("help_chat", [])
    box = st.container()   # 대화가 위, 입력이 아래 (채팅 순서). 입력은 아래에서 받지만 답은 이 자리에 그림
    picked = st.pills("이런 걸 물어볼 수 있어요", helpbot.SUGGESTIONS[screen], key=f"help_pick_{len(chat)}")
    typed = st.chat_input("궁금한 걸 물어보세요 (예: ROAS가 뭐야?)", key="help_input")
    q = typed or picked
    if q:
        chat.append(("user", q))
        chat.append(("assistant", helpbot.answer(q, ctx, screen, won)))
    with box:
        if not chat:
            with st.chat_message("assistant", avatar="💬"):
                st.markdown("안녕하세요! 광고 용어 뜻, 지금 계산된 내 숫자, 숫자의 출처, 무엇부터 할지 물어보세요.")
        for role, text in chat[-8:]:
            with st.chat_message(role, avatar="💬" if role == "assistant" else "🙂"):
                st.markdown(text)
    if chat and st.button("대화 지우기", key="help_clear"):
        ss["help_chat"] = []
        st.rerun(scope="fragment")
    with st.expander("전체 용어 사전"):
        for term, (desc, ex) in helpbot.GLOSSARY.items():
            st.markdown(f"- **{term}**: {desc}" + (f" — {ex}" if ex else ""))


with help_fab:
    with st.popover("💬 도우미"):
        help_chat(help_ctx)
