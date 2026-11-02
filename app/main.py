"""AARRR 기반 광고 예산 시뮬레이터 — Streamlit 프로토타입.

실행: streamlit run app/main.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import charts  # noqa: E402
from src.engine import (Channel, FunnelParams, MetaCurve, NaverCurve, budget_scan,  # noqa: E402
                        lever_table, optimize_allocation, simulate)
from src.engine import defaults as D  # noqa: E402
from src.engine import data_loader as dl  # noqa: E402
from src.engine import naver_source as ns  # noqa: E402
from src.engine.experiment import days_needed, sample_size  # noqa: E402
from src.engine.insights import insights, prescription, warnings, won  # noqa: E402

st.set_page_config(page_title="AARRR 광고 예산 시뮬레이터", page_icon="📈", layout="wide")

# 지표 정의서(실행계획 7장) 기반 툴팁 — 광고 용어를 모르는 사용자 기준으로 풀어 씀
HELP = {
    "new": "12개월 동안 새로 온 손님 수 (광고로 온 손님 + 지인 추천으로 온 손님)",
    "paid_cac": "광고로 손님 1명을 데려오는 데 든 돈 (CAC) = 광고비 ÷ 광고로 온 손님 수",
    "blended_cac": "추천 손님까지 포함했을 때 손님 1명당 광고비 = 광고비 ÷ 전체 새 손님 수",
    "ltv": "손님 1명이 첫 구매 후 12개월 동안 남겨 주는 돈 (LTV, 매출 × 마진)",
    "ltv_cac": "손님이 남겨 주는 돈 ÷ 데려오는 데 든 돈 (LTV/CAC). 1보다 작으면 손님을 데려올수록 손해",
    "payback": "손님 1명을 데려오는 데 쓴 광고비를 그 손님이 남겨 주는 돈으로 되찾기까지 걸리는 개월 수",
    "profit": "12개월 동안 남는 돈 = 매출 × 마진율 − 광고비",
    "roas": "광고비 1원당 첫 구매 매출 (ROAS). 재구매는 빠져 있어 실제 가치보다 작게 보일 수 있음",
    "cpc": "클릭 1번에 드는 평균 광고비 (CPC)",
    "mcpc": "클릭을 1번 더 얻는 데 드는 추가 비용 (한계 CPC). 예산을 늘릴수록 비싸짐",
}

# 사이드바 용어 사전: (용어, 쉬운 설명, 비유·예시)
GLOSSARY = [
    ("AARRR", "손님이 우리 가게와 만나는 5단계: 알게 됨(획득) → 써 봄(활성화) → 다시 옴(유지) → 돈을 냄(수익) → 소개함(추천)",
     "광고는 첫 단계만 책임지지만, 이익은 다섯 단계를 다 거쳐야 생깁니다."),
    ("CPC (클릭당 비용)", "광고를 한 번 클릭할 때 내는 돈", "CPC 700원 = 클릭 100번에 7만 원"),
    ("전환율 (CVR)", "광고를 클릭한 사람 중 실제로 구매(또는 예약·상담)까지 한 사람의 비율",
     "전환율 1% = 100명이 클릭하면 1명이 구매"),
    ("CAC (고객 획득 비용)", "광고로 손님 1명을 데려오는 데 든 돈", "CPC 700원 ÷ 전환율 1% = 7만 원"),
    ("객단가", "손님이 한 번 결제할 때 평균 금액", "커피 원두 1봉 2만 원, 필라테스 10회권 30만 원"),
    ("마진율", "매출 중 원가·배송비 등을 빼고 남는 비율", "1만 원 팔아 3,500원 남으면 35%"),
    ("리텐션 (재방문율)", "첫 구매 후 시간이 지나도 다시 구매하는 손님 비율", "3개월 뒤 리텐션 10% = 100명 중 10명이 그달에도 구매"),
    ("LTV (고객 생애 가치)", "손님 1명이 일정 기간 동안 남겨 주는 돈의 합", "여기서는 12개월 동안 남기는 이익"),
    ("LTV/CAC", "손님이 남겨 주는 돈 ÷ 데려오는 데 든 돈", "1보다 크면 남는 장사, 작으면 밑지는 장사"),
    ("ROAS (광고 수익률)", "광고비 1원당 매출. 광고 매체가 보여주는 대표 숫자", "ROAS 2 = 광고비 100만 원으로 매출 200만 원 (재구매는 빠짐)"),
    ("회수 기간", "광고비로 데려온 손님에게서 그 광고비를 되찾는 데 걸리는 개월 수", "짧을수록 현금 흐름이 안전"),
    ("포화", "같은 키워드에 돈을 더 넣어도 클릭이 잘 안 늘고 클릭당 비용만 오르는 상태", "이미 꽉 찬 가게 앞에 전단지를 더 뿌리는 것"),
    ("한계 CPC", "예산을 조금 더 늘렸을 때 추가로 얻는 클릭 1번의 비용", "평균보다 훨씬 비싸면 포화 신호"),
    ("퍼널", "클릭 → 방문 → 관심 → 구매 시작 → 구매 완료처럼 손님이 거치는 단계와 각 단계에서 남는 비율",
     "깔때기처럼 아래로 갈수록 사람이 줄어듭니다."),
    ("OMTM", "지금 가장 중요한 목표 지표 하나 (One Metric That Matters)", "최적화는 이 숫자를 가장 크게 만드는 예산 배분을 찾습니다."),
    ("A/B 테스트", "두 가지 화면(A·B)을 손님을 나눠 보여주고 어느 쪽이 더 잘 되는지 비교하는 실험", ""),
]

OMTM_PLAIN = {"new_customers": "새 손님 수 최대로", "profit": "1년 동안 남는 돈 최대로", "roas": "광고비 대비 첫 매출(ROAS) 최대로"}

ss = st.session_state


@st.cache_data(show_spinner=False)
def load_keywords(hints: tuple, online: bool):
    return ns.keyword_tool(list(hints), online=online)


@st.cache_data(show_spinner=False)
def load_estimate(keyword: str, online: bool):
    return ns.bid_estimate(keyword, device=D.NAVER_DEVICE, online=online)


def guide(text: str):
    """탭 맨 위 '이 화면에서 할 일' 안내."""
    st.info(text, icon="🧭")


with st.sidebar:
    st.header("처음이신가요?")
    st.markdown("1. **① 시작**: 무엇을 팔고 월 광고비가 얼마인지 적어요\n"
                "2. **② 광고 채널**: 네이버에 쓸 검색어를 넣고 네이버·메타(인스타그램·페이스북) 비율을 정해요\n"
                "3. **③ 손님 흐름**: 결제 금액·남는 비율을 우리 가게 숫자로 바꿔요\n"
                "4. **④ 결과**: 1년 뒤 남는 돈과 더 나은 예산안을 봐요\n"
                "5. **⑤ 개선 순서**: 광고비를 늘릴지, 다른 걸 먼저 고칠지 봐요")
    st.caption("숫자를 몰라도 기본값으로 바로 결과가 나옵니다. 아는 숫자부터 하나씩 바꿔 보세요.")
    st.header("📖 용어 사전")
    for term, desc, ex in GLOSSARY:
        with st.expander(term):
            st.markdown(desc + (f"  \n\n💡 {ex}" if ex else ""))

st.title("📈 광고 예산 시뮬레이터")
st.caption("광고비를 쓰면 손님이 얼마나 오고, 다시 오고, 1년 뒤 얼마가 남는지 미리 계산해 봅니다. "
           "광고비를 늘릴지 · 네이버와 메타(인스타그램·페이스북) 중 어디에 쓸지 · 가게의 어느 부분을 먼저 고칠지 알려줍니다. "
           "(AARRR 프레임워크 · 프로토타입 v0.4)")

tabs = st.tabs(["① 시작", "② 광고 채널", "③ 손님 흐름", "④ 결과", "⑤ 개선 순서"])

# ───────────────────────────── ① 시작 ─────────────────────────────
with tabs[0]:
    guide("무엇을 팔고, 광고로 손님이 무엇을 해 주길 바라는지, 한 달에 광고비를 얼마 쓸지 정해 주세요. "
          "나머지는 기본값으로 채워져 있어 바로 ④ 결과를 볼 수 있습니다.")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("무엇을 위한 광고인가요?")
        business = st.text_input("무엇을 파나요? (메모용, 계산에는 쓰이지 않음)", placeholder="예: 동네 필라테스 스튜디오, 원두 온라인몰 …")
        task = st.selectbox("광고를 본 손님이 해 줬으면 하는 행동", D.CORE_TASKS,
                            help="이 행동을 한 사람을 '새 손님'으로 셉니다. (핵심 과업)")
        if task == "직접 입력":
            task = st.text_input("행동 이름", value="전환") or "전환"
        omtm = st.radio("가장 중요한 목표 하나 (OMTM)", list(D.OMTM_OPTIONS), horizontal=True,
                        format_func=OMTM_PLAIN.get, index=1,
                        help="앱이 '더 나은 예산안'을 찾을 때 이 목표를 기준으로 삼습니다. 잘 모르겠으면 '1년 동안 남는 돈'을 고르세요.")
        budget = st.number_input("한 달 광고비 (원)", min_value=0, max_value=1_000_000_000,
                                 value=D.MONTHLY_BUDGET, step=100_000, format="%d")
        st.caption(f"= 한 달 {won(budget)}, 1년이면 {won(budget * 12)}")
    with c2:
        st.subheader("가진 데이터")
        level = st.radio("광고를 해 본 기록이 있나요?", ["아직 없어요 (기본값으로 계산)", "있어요 (광고 성과 CSV 파일 올리기)"],
                         help="네이버·메타 광고 관리자에서 내려받은 성과 파일이 있으면 내 실제 클릭당 비용·전환율로 계산합니다.")
        upload = None
        if level.startswith("있어요"):
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
                    st.info("클릭당 비용(CPC)·전환율(CVR)·구매 1건당 비용(CPA)을 전체 합계로 계산했습니다. "
                            "매체 이름이 naver·meta인 행의 숫자로 기본값을 내 실제 숫자로 바꿉니다.")
            except Exception as e:  # noqa: BLE001
                st.error(f"CSV를 읽지 못했습니다: {e}")
        with st.expander("기본값은 어디서 왔나요?"):
            st.markdown(
                "- **광고 클릭 수**: 네이버 검색광고가 알려주는 실시간 예상치 ✅ / 메타(인스타그램·페이스북)는 직접 넣은 클릭당 비용에 "
                "연령·성별별 차이(Kaggle 광고 데이터)를 곱함 ✅\n"
                "- **클릭 후 구매까지 비율**: 실제 온라인몰(구글 GA4 샘플) 방문자 기록 ✅ (광고 클릭 → 방문 단계만 임시값)\n"
                "- **재구매·결제 금액**: 실제 온라인 쇼핑몰 거래 데이터(UCI) 분석 후 교체 예정 — 지금은 임시값\n"
                "- 금액(결제 금액·클릭당 비용)은 원화로 직접 넣고, 지인 추천은 기본 0으로 둡니다")

# ─────────────────────────── ② 획득 설계 ───────────────────────────
with tabs[1]:
    guide("손님이 네이버에서 검색할 만한 단어를 넣으면, 네이버가 알려주는 예상 클릭 수로 광고 효과를 계산합니다. "
          "아래에서 네이버와 메타(인스타그램·페이스북)에 예산을 어떻게 나눌지 정하세요.")
    api_ok = ns.api_available()
    top = st.columns([2, 1])
    with top[0]:
        hint_text = st.text_input("손님이 검색할 만한 단어 (쉼표로 최대 5개)", value=ns.SAMPLE_KEYWORD,
                                  help="예: 필라테스, 원두커피. 이 단어와 비슷한 검색어도 함께 찾아 줍니다.")
    with top[1]:
        online = st.toggle("네이버에서 지금 바로 조회", value=api_ok, disabled=not api_ok,
                           help="끄면 미리 저장해 둔 결과만 씁니다 (인터넷 없이 시연할 때).")
        if not api_ok:
            st.caption("⚠️ .env 키가 없어 오프라인 모드로 동작합니다.")
    hints = tuple(h.strip().replace(" ", "") for h in hint_text.split(",") if h.strip())[:5]
    kw_df = load_keywords(hints, online) if hints else None
    fallback = False
    if kw_df is None:
        fallback = True
        kw_df = load_keywords((ns.SAMPLE_KEYWORD,), False)
        st.warning(f"'{hint_text}' 검색 결과를 가져오지 못해 예시 단어 '{ns.SAMPLE_KEYWORD}'로 대신 보여줍니다. "
                   "'네이버에서 지금 바로 조회'가 켜져 있는지 확인해 주세요.")

    estimates, recs = {}, None
    if kw_df is not None:
        base_hints = (ns.SAMPLE_KEYWORD,) if fallback else hints
        default_sel = [k for k in base_hints if k in set(kw_df["keyword"])] or kw_df["keyword"].head(3).tolist()
        selected = st.multiselect("광고를 걸 검색어 (최대 8개)",
                                  kw_df["keyword"].tolist(), default=default_sel, max_selections=8,
                                  help="고른 검색어마다 '광고비를 얼마 쓰면 클릭이 몇 번 나오는지' 네이버 예상치를 불러옵니다.")
        recs = ns.recommend_keywords(kw_df, seeds=list(base_hints))
        if len(recs):
            st.success("💡 **추천 검색어**: " + ", ".join(f"`{k}`" for k in recs["keyword"])
                       + "  \n검색하는 사람이 적당히 많고(월 1천~3만 회) 경쟁 광고주가 적은 단어입니다. 위 목록에 추가해 보세요.")
        with st.expander("비슷한 검색어 전체 보기 (검색량·경쟁 정도)"):
            k1, k2 = st.columns([1, 1])
            with k1:
                st.plotly_chart(charts.keyword_scatter(kw_df, selected), use_container_width=True)
            with k2:
                tier_filter = st.multiselect("검색량 크기", ["대표", "세부", "롱테일"], default=["대표", "세부"],
                                             help="한 달 검색 횟수 기준: 3만 회 이상 '대표'(인기·비쌈), 1천~3만 회 '세부'(알짜), 1천 회 미만 '롱테일'(소수)")
                st.dataframe(kw_df[kw_df["tier"].isin(tier_filter)].head(100)[
                    ["keyword", "tier", "total_qc", "comp", "mobile_ctr", "mobile_clicks"]].rename(columns={
                    "keyword": "검색어", "tier": "크기", "total_qc": "한 달 검색 수", "comp": "광고 경쟁",
                    "mobile_ctr": "광고 클릭률(%)", "mobile_clicks": "광고 클릭 수(평균)"}), height=300, hide_index=True)
        with st.spinner("입찰가별 예상 실적을 불러오는 중…"):
            for kw in selected:
                est = load_estimate(kw, online and not fallback)
                if est is not None and (est["clicks"] > 0).any():
                    estimates[kw] = est
        missing = [k for k in selected if k not in estimates]
        if missing:
            st.caption(f"네이버 예상 클릭이 없어 계산에서 뺀 검색어: {', '.join(missing)}")

    naver_curve = NaverCurve(estimates) if estimates else None
    if naver_curve is None:
        st.info("광고를 걸 수 있는 네이버 검색어가 없어 네이버 광고비는 0으로 계산합니다. 다른 검색어를 넣어 보세요.")
        naver_curve = NaverCurve({})

    st.divider()
    st.subheader("예산 나누기")
    m1, m2 = st.columns([1, 1])
    with m1:
        naver_share = st.slider("네이버 검색광고에 쓸 비율 (%)", 0, 100, int(D.CHANNEL_SHARES["naver"] * 100), step=5,
                                help="나머지는 메타(인스타그램·페이스북) 광고에 씁니다. ④ 결과에서 더 나은 비율을 알려줍니다.")
        naver_budget = budget * naver_share / 100
        meta_budget = budget - naver_budget
        st.markdown(f"**네이버** 월 {won(naver_budget)} · **메타** 월 {won(meta_budget)}")
        if naver_curve.capacity > 0:
            st.caption(f"고른 검색어로 네이버에 쓸 수 있는 돈은 한 달 최대 {won(naver_curve.capacity)}입니다. "
                       "그보다 많이 넣으면 검색하는 사람이 부족해 다 쓰지 못합니다.")
    with m2:
        targets_df = dl.meta_targets()
        meta_targets = st.multiselect("메타 광고를 보여줄 사람 (연령·성별)", targets_df["target"].tolist(),
                                      help="연령·성별에 따라 구매 1건을 얻는 비용이 다릅니다 (Kaggle 광고 데이터). 비워 두면 전체 평균으로 계산합니다.")
        target_mult = dl.target_multiplier(meta_targets)
        with st.expander("메타 세부 설정 (모르면 그대로 두세요)", expanded=False):
            meta_cpc_input = st.number_input("클릭 1번당 비용 (원, CPC)", 50.0, 20_000.0, float(D.META_BASE_CPC), step=50.0,
                                             help="메타 광고 관리자에서 보이는 'CPC(링크 클릭당 비용)'. 모르면 기본값 700원")
            meta_sat = st.slider("예산을 늘릴 때 클릭 단가가 오르는 정도", 0.0, 2.0, float(D.META_SATURATION), 0.05,
                                 help="0.3 = 광고비를 100만 원 늘릴 때마다 클릭당 비용이 30% 오름 (같은 사람에게 반복 노출되어 비싸짐)")
            meta_cvr_mult = st.slider("메타 손님의 구매 확률 (네이버 검색 손님 = 1)", 0.1, 2.0, float(D.META_CVR_MULT), 0.05,
                                      help="검색한 사람은 이미 사려는 마음이 있어 구매 확률이 높습니다. 0.7 = 네이버 손님의 70%")
            meta_ret_mult = st.slider("메타 손님이 다시 오는 정도 (네이버 손님 = 1)", 0.1, 2.0, float(D.META_RETENTION_MULT), 0.05)
        meta_cpc = meta_cpc_input * target_mult
        if upload is not None and "meta" in upload.index:
            meta_cpc = float(upload.loc["meta", "CPC"])  # 1단계: 내 실제 CPC가 타깃 배수보다 우선
        st.caption(f"메타 클릭 1번당 비용: {meta_cpc:,.0f}원" + (f" (입력 {meta_cpc_input:,.0f}원 × 고른 연령·성별 보정 {target_mult:.2f}배)"
                                                          if upload is None or "meta" not in upload.index else " (올린 CSV 기준)"))
    meta_curve = MetaCurve(meta_cpc, meta_sat)
    spends = [naver_budget, meta_budget]

    g1, g2 = st.columns([3, 2])
    with g1:
        st.plotly_chart(charts.bid_curves(estimates, naver_curve if estimates else None), use_container_width=True)
        st.caption("곡선이 처음엔 가파르다가 점점 평평해집니다. 평평해질수록 광고비를 더 넣어도 클릭이 잘 안 는다는 뜻(포화)입니다.")
    with g2:
        st.plotly_chart(charts.meta_target_bars(targets_df, meta_targets), use_container_width=True)
        st.caption("막대가 1보다 낮으면 평균보다 싸게 구매를 얻는 연령·성별, 높으면 비싼 연령·성별입니다.")
        with st.expander("메타 광고 만드는 방법 가이드"):
            goal = st.selectbox("광고 목표", D.META_GUIDE_GOALS, index=2)
            product = st.selectbox("상품·서비스 유형", D.META_GUIDE_PRODUCTS)
            st.markdown(f"- **캠페인**: {D.META_GUIDE['campaign'][goal]}\n"
                        f"- **구조**: {D.META_GUIDE['structure'][product]}\n"
                        f"- **소재**: {D.META_GUIDE['creative'][product]}\n"
                        + (f"- **타깃**: 고른 타깃의 상대 CPA {target_mult:.2f}배" if meta_targets else
                           "- **타깃**: 위에서 연령·성별을 고르면 상대 CPA를 함께 봅니다"))
            st.caption("일반적인 운영 원칙을 정리한 규칙 기반 가이드입니다. 계산에는 쓰이지 않습니다.")
        st.plotly_chart(charts.meta_curve(meta_curve, max(budget, 1)), use_container_width=True)
    alloc = None
    if estimates:
        alloc = naver_curve.allocation(naver_budget, D.SATURATION_RATIO)
        st.markdown("**네이버 예산을 검색어별로 이렇게 나누면 좋아요**")
        st.caption("클릭을 가장 싸게 얻을 수 있는 검색어부터 예산을 채웠습니다. '권장 입찰가'는 네이버 광고 관리자에 넣을 클릭당 최대 금액입니다.")
        show = alloc.assign(saturated=alloc["saturated"].map({True: "⚠️ 포화 (돈을 더 넣어도 효과 작음)", False: "✅ 여유"}))
        st.dataframe(show.rename(columns={"keyword": "검색어", "spend": "한 달 광고비", "clicks": "한 달 클릭", "bid": "권장 입찰가",
                                          "marginal_cpc": "클릭 1번 더 얻는 비용", "cpc": "평균 클릭당 비용", "saturated": "상태"})
                     .style.format({"한 달 광고비": "{:,.0f}", "한 달 클릭": "{:,.0f}", "권장 입찰가": "{:,.0f}",
                                    "클릭 1번 더 얻는 비용": "{:,.0f}", "평균 클릭당 비용": "{:,.0f}"}, na_rep="-"),
                     hide_index=True)
    st.caption("네이버 숫자는 네이버가 내놓은 예상치(한 달, 모바일 기준)라 실제와 다를 수 있습니다.")

# ─────────────────────────── ③ 퍼널 설정 ───────────────────────────
with tabs[2]:
    guide(f"광고를 클릭한 사람이 {task}까지 몇 %나 가는지, 그리고 한 번 온 손님이 얼마나 다시 오고 얼마를 쓰는지 정합니다. "
          "우리 가게 숫자를 알면 바꾸고, 모르면 기본값을 그대로 두세요. 특히 '1회 평균 결제 금액'과 '남는 비율'은 결과를 크게 바꿉니다.")
    st.subheader(f"클릭한 사람 중 몇 %가 {task}까지 갈까요? (활성화)")
    f1, f2 = st.columns([1, 1])
    with f1:
        mediums = dl.ga4_mediums() or [dl.GA4_ALL]
        medium = st.selectbox("기본값으로 쓸 실제 쇼핑몰 기록 (구글 GA4 샘플)", mediums,
                              help="'전체'가 기본입니다. 'cpc'를 고르면 검색광고로 들어온 방문자만의 비율을 씁니다.")
        base_steps, src = dl.funnel_steps(medium)
        steps_df = pd.DataFrame([{"단계": n, "전환율": round(r, 3)} for n, r in base_steps])
        steps_df.loc[len(steps_df) - 1, "단계"] = f"{task} 완료"
        edited = st.data_editor(steps_df, num_rows="dynamic", hide_index=True, key="steps_editor",
                                column_config={"전환율": st.column_config.NumberColumn(
                                    "다음 단계로 가는 비율", min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
                                    help="0.23 = 이전 단계 사람 100명 중 23명이 이 단계까지 옴")})
        edited = edited.dropna()
        steps = [(str(n), float(r)) for n, r in zip(edited["단계"], edited["전환율"])]
        st.caption(f"출처: {src}. 첫 단계(광고 클릭 → 페이지 도착)는 기록이 없어 임시값입니다. "
                   "표의 숫자를 직접 고치거나 행을 추가·삭제할 수 있습니다.")
    st.subheader("한 번 온 손님은 얼마나 다시 오고, 얼마를 쓸까요? (유지 · 수익 · 추천)")
    r1, r2, r3 = st.columns(3)
    with r1:
        # UCI 코호트 결과(data/processed/cohort_retention.csv)가 있으면 곡선을 적합해 기본값으로
        ret_table, ret_src, fit = None, "임시값 (UCI 코호트 결과 대기)", None
        segments = dl.retention_segments()
        retail = [i for i, x in enumerate(segments) if "소매" in x or "제외" in x]  # 도매 분리 후 세그먼트를 기본으로
        seg = st.selectbox("재구매 기본값으로 쓸 손님 유형", segments, index=retail[0] if retail else 0) if segments else None
        ret_table = dl.retention_curve_table(segment=seg)
        if ret_table is not None and len(ret_table) >= 3:
            fit = dl.fit_retention(ret_table, fit_months=min(6, int(ret_table["months_since"].max()) - 1))
            full = dl.fit_retention(ret_table)
            ret_src = f"UCI 코호트 적합 ({seg or '전체'}) · 앞 6개월로 맞춘 뒤 이후 오차 MAE {fit.get('holdout_mae', float('nan')):.3f}"
            fit = full
        st.markdown("**다시 오는 손님 (리텐션)**")
        floor = st.slider("오래 지나도 꾸준히 오는 단골 비율", 0.0, 0.6, round(fit["floor"], 3) if fit else float(D.RETENTION_FLOOR), 0.005,
                          key=f"floor_{seg}_{fit is not None}",
                          help="0.06 = 처음 온 손님 100명 중 6명은 몇 달이 지나도 매달 다시 구매 (리텐션 바닥값)")
        decay = st.slider("첫 구매 후 손님이 떠나는 속도", 0.1, 5.0, round(fit["decay"], 2) if fit else float(D.RETENTION_DECAY), 0.05,
                          key=f"decay_{seg}_{fit is not None}",
                          help="클수록 첫 달 이후 손님이 빨리 줄어듭니다. 아래 곡선 그래프로 모양을 확인하세요 (리텐션 감소율)")
        st.caption(f"출처: {ret_src}")
    with r2:
        st.markdown("**쓰는 돈 (수익)**")
        aov = st.number_input("1회 평균 결제 금액 (원, 객단가)", 1_000.0, 10_000_000.0, float(D.AOV), step=1_000.0,
                              help="손님이 한 번 결제할 때 평균 금액")
        freq = st.number_input("단골이 한 달에 사는 횟수", 0.1, 10.0, float(D.PURCHASE_FREQ), step=0.1,
                               help="그달에 다시 온 손님이 평균 몇 번 결제하는지 (월 구매 빈도)")
        margin = st.slider("매출 중 남는 비율 (마진율)", 0.0, 1.0, float(D.MARGIN), 0.01,
                           help="1만 원어치 팔면 원가·배송비·수수료를 빼고 얼마가 남는지. 0.35 = 3,500원")
        st.caption(f"→ 1회 결제당 남는 돈 {won(aov * margin)}")
    with r3:
        st.markdown("**지인 소개 (추천)**")
        invite_rate = st.slider("단골 1명이 한 달에 소개하는 사람 수", 0.0, 2.0, float(D.INVITE_RATE), 0.05,
                                help="모르면 0으로 두세요. 추천 이벤트를 할 계획이 있을 때 바꿔 보세요.")
        invite_conv = st.slider("소개받은 사람이 실제 손님이 되는 비율", 0.0, 1.0, float(D.INVITE_CONV), 0.01)
        st.caption(f"→ 단골 100명이 한 달에 새 손님 {invite_rate * invite_conv * 100:.1f}명을 데려옴 (가정값)")
    params = FunnelParams(steps=steps, retention_floor=floor, retention_decay=decay, purchase_freq=freq,
                          aov=aov, margin=margin, invite_rate=invite_rate, invite_conv=invite_conv)
    with f2:
        st.plotly_chart(charts.activation_funnel(params), use_container_width=True)
        st.metric(f"광고 클릭 → {task}까지 가는 비율 (전환율, CVR)", f"{params.cvr:.2%}",
                  help="위 표의 비율을 모두 곱한 값입니다.")
        st.caption(f"= 광고를 {1 / params.cvr:,.0f}번 클릭해야 손님 1명이 {task}합니다." if params.cvr > 0 else "")
    st.plotly_chart(charts.retention_curve(params, actual=ret_table), use_container_width=True)
    if ret_table is None:
        st.caption("재구매 비율은 실제 쇼핑몰 거래 데이터(UCI) 분석 결과가 나오면 자동으로 바뀝니다. 지금은 임시값입니다.")

# 1단계 CSV 보정: 퍼널이 정해진 뒤 채널별 전환율 배수 = 내 CVR / 퍼널 CVR
naver_cvr_mult, naver_ret_mult = D.NAVER_CVR_MULT, D.NAVER_RETENTION_MULT
if upload is not None and params.cvr > 0:
    if "meta" in upload.index:
        meta_cvr_mult = float(upload.loc["meta", "CVR"] / params.cvr)
    if "naver" in upload.index:
        naver_cvr_mult = float(upload.loc["naver", "CVR"] / params.cvr)
channels = [
    Channel("naver", "네이버 검색", naver_curve, naver_cvr_mult, naver_ret_mult),
    Channel("meta", "메타", meta_curve, meta_cvr_mult, meta_ret_mult),
]

# ─────────────── 계산 (④·⑤ 공용, 입력이 바뀔 때만 최적화 재계산) ───────────────
res = simulate(channels, spends, params)
cache_key = repr((omtm, budget, spends, params, [(c.key, c.cvr_mult, c.retention_mult) for c in channels],
                  sorted(estimates), meta_cpc, meta_sat))
if ss.get("opt_key") != cache_key:
    with st.spinner("최적 배분을 계산하는 중…"):
        opt = optimize_allocation(channels, budget, params, omtm)
        opt_profit = opt if omtm == "profit" else optimize_allocation(channels, budget, params, "profit")
        opt_roas = opt if omtm == "roas" else optimize_allocation(channels, budget, params, "roas")
        ss["opt_cache"] = (opt, opt_profit, opt_roas, lever_table(channels, spends, params), budget_scan(channels, spends, params))
        ss["opt_key"] = cache_key
opt, opt_profit, opt_roas, levers, scan = ss["opt_cache"]
res_opt = simulate(channels, opt["spends"], params)
opt["omtm"] = omtm
opt["base_value"] = {"new_customers": res.summary["new_customers"], "profit": res.summary["profit_12m"],
                     "roas": res.summary["roas"] or 0.0}[omtm]


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
    """④ 맨 위 '한눈에 결론': 신호등 + 쉬운 문장 한두 줄."""
    ratio, cac, ltv = s["ltv_cac"], s["paid_cac"], s["ltv_12m"]
    best = sum(opt_profit_spends)
    if ratio is None:
        return "info", "광고비가 0원이라 광고 효과를 계산할 수 없습니다. ① 시작에서 한 달 광고비를 넣어 주세요."
    if ratio < 1:
        return "error", (f"🔴 **지금 조건이면 광고를 할수록 손해입니다.** 손님 1명을 데려오는 데 {won(cac)}이 드는데, "
                         f"그 손님이 1년 동안 남겨 주는 돈은 {won(ltv)}뿐입니다.  \n"
                         "광고비를 늘리기보다 ⑤ 개선 순서에서 구매 비율·재구매·결제 금액을 먼저 올려 보세요. "
                         "(③에서 '1회 평균 결제 금액'과 '남는 비율'이 우리 가게 숫자와 맞는지도 확인하세요.)")
    if s["profit_12m"] < 0:
        return "warning", (f"🟡 **손님 한 명 한 명은 남는 장사지만, 1년 안에는 아직 적자입니다** ({won(s['profit_12m'])}). "
                           f"광고비 본전을 찾는 데 {s['payback_month'] or '36+'}개월이 걸려서입니다. 기간을 길게 보거나 예산 배분을 바꿔 보세요.")
    msg = (f"🟢 **광고가 돈을 벌어 줍니다.** 1년 동안 {won(s['profit_12m'])}이 남고, "
           f"광고비 본전은 {s['payback_month']}개월이면 찾습니다.")
    if best < budget * 0.9:
        msg += f"  \n다만 한 달 {won(best)} 정도만 써도 이익이 가장 큽니다. 그 이상은 돈을 더 넣어도 효과가 줄어듭니다."
    return "success", msg


# ─────────────────────────── ④ 시뮬레이션 ───────────────────────────
with tabs[3]:
    if upload is not None:
        st.caption(f"올린 광고 성과 파일로 보정함: 구매 확률 네이버 {naver_cvr_mult:.2f}배 / 메타 {meta_cvr_mult:.2f}배, 메타 클릭당 비용 {meta_cpc:,.0f}원")
    st.subheader("한눈에 결론")
    lvl, msg = verdict(res.summary, opt_profit["spends"])
    getattr(st, lvl)(msg)
    fmt = {"profit": won, "roas": lambda v: f"{v:.2f}원", "new_customers": lambda v: f"{v:,.0f}명"}[omtm]
    o1, o2 = st.columns([1, 2])
    with o1:
        st.metric(f"내 목표 · {OMTM_PLAIN[omtm]}", fmt(opt["base_value"]), delta=f"추천안이면 {fmt(opt['value'])}",
                  delta_color="off", border=True, help="① 시작에서 고른 목표(OMTM). 추천안은 이 숫자를 가장 크게 만드는 예산 배분입니다.")
    with o2:
        unused = budget - sum(opt["spends"])
        st.markdown(f"**지금 계획**: 네이버 월 {won(spends[0])} · 메타 월 {won(spends[1])}  \n"
                    f"**추천 계획**: 네이버 월 {won(opt['spends'][0])} · 메타 월 {won(opt['spends'][1])}"
                    + (f" · 쓰지 않고 아끼기 월 {won(unused)}" if unused > 1 else ""))
        st.caption("추천 계획은 앱이 여러 배분을 계산해 보고 내 목표가 가장 좋아지는 조합을 고른 것입니다.")
    st.subheader("지금 계획의 주요 숫자")
    st.caption("숫자 옆 ⓘ에 마우스를 올리면 뜻을 볼 수 있습니다. 왼쪽 사이드바의 용어 사전도 참고하세요.")
    kpis(res.summary)
    a1, a2 = st.columns([1, 1])
    with a1:
        st.plotly_chart(charts.aarrr_funnel(res.funnel, res.summary), use_container_width=True)
        st.caption("광고 클릭부터 재구매까지 1년 동안 손님 수가 단계마다 어떻게 줄어드는지 보여줍니다.")
    with a2:
        st.plotly_chart(charts.cum_profit(res.monthly, res_opt.monthly, f"추천 계획 ({OMTM_PLAIN[omtm]})"),
                        use_container_width=True)
        st.caption("선이 0 위로 올라가는 달부터 광고가 이익을 내기 시작합니다.")
    st.subheader("계획별 비교")

    def plan_row(name, sp, r):
        s = r.summary
        return {"계획": name, "네이버 (월)": sp[0], "메타 (월)": sp[1], "아끼는 돈 (월)": budget - sum(sp),
                "새 손님": s["new_customers"], "손님 1명 데려오는 비용": s["paid_cac"], "남기는 돈÷데려오는 비용": s["ltv_cac"],
                "ROAS": s["roas"], "1년 동안 남는 돈": s["profit_12m"]}

    rows = [plan_row("지금 계획", spends, res), plan_row(f"추천 계획 ({OMTM_PLAIN[omtm]})", opt["spends"], res_opt)]
    if omtm != "profit":
        rows.append(plan_row("남는 돈이 가장 큰 계획", opt_profit["spends"], simulate(channels, opt_profit["spends"], params)))
    if omtm != "roas":
        rows.append(plan_row("ROAS가 가장 높은 계획", opt_roas["spends"], simulate(channels, opt_roas["spends"], params)))
    st.dataframe(pd.DataFrame(rows).style.format({
        "네이버 (월)": "{:,.0f}", "아끼는 돈 (월)": "{:,.0f}", "메타 (월)": "{:,.0f}", "새 손님": "{:,.0f}",
        "손님 1명 데려오는 비용": "{:,.0f}", "남기는 돈÷데려오는 비용": "{:.2f}", "ROAS": "{:.2f}", "1년 동안 남는 돈": "{:,.0f}"}, na_rep="-"),
        hide_index=True, width="stretch")
    st.caption("💡 광고 매체가 보여주는 ROAS(광고비 대비 첫 매출)만 보고 예산을 짜면, 재구매와 남는 비율을 놓쳐 "
               "실제로 남는 돈이 가장 큰 계획과 달라질 수 있습니다. 손해가 나는 구간에서는 예산을 덜 쓰는 것이 정답일 수도 있습니다.")
    b1, b2 = st.columns([1, 1])
    with b1:
        st.plotly_chart(charts.revenue_split(res.monthly), use_container_width=True)
        st.caption("시간이 지날수록 재구매 매출이 쌓입니다. 이 부분은 ROAS에 잡히지 않습니다.")
    with b2:
        st.plotly_chart(charts.budget_scan_chart(scan, budget), use_container_width=True)
        st.caption("가장 높은 지점이 남는 돈이 가장 큰 한 달 광고비입니다. 점선(지금 예산)이 그보다 오른쪽이면 너무 많이 쓰는 중입니다.")
    st.plotly_chart(charts.payback(res.customer_cum_profit, res.summary["paid_cac"]), use_container_width=True)
    st.caption("실선(손님 1명이 남겨 준 돈 누적)이 빨간 점선(데려오는 데 쓴 광고비)을 넘는 달이 본전을 찾는 시점입니다.")
    with st.expander("자세히 보기: 채널별 결과 (한 달 기준)"):
        bc = res.by_channel[["label", "budget", "spend", "clicks", "cpc", "marginal_cpc", "new_customers", "cac", "ltv_12m"]]
        st.dataframe(bc.rename(columns={"label": "채널", "budget": "배정한 돈", "spend": "실제로 쓸 수 있는 돈", "clicks": "클릭",
                                        "cpc": "평균 클릭당 비용", "marginal_cpc": "클릭 1번 더 얻는 비용", "new_customers": "새 손님",
                                        "cac": "손님 1명 데려오는 비용", "ltv_12m": "손님 1명이 1년간 남기는 돈"})
                     .style.format("{:,.0f}", subset=["배정한 돈", "실제로 쓸 수 있는 돈", "클릭", "평균 클릭당 비용",
                                                      "클릭 1번 더 얻는 비용", "손님 1명 데려오는 비용", "손님 1명이 1년간 남기는 돈"])
                     .format("{:,.1f}", subset=["새 손님"], na_rep="-"), hide_index=True, width="stretch")
    with st.expander("자세히 보기: 월별 상세 표"):
        st.dataframe(res.monthly.rename(columns={
            "month": "개월", "spend": "광고비", "clicks": "클릭", "paid_new": "광고로 온 새 손님", "referral_new": "추천으로 온 새 손님",
            "new_customers": "새 손님 합계", "active": "그달 구매한 손님", "orders": "주문 수", "revenue": "매출",
            "new_revenue": "새 손님 매출", "repeat_revenue": "재구매 매출", "gross_profit": "남는 돈(광고비 전)",
            "profit": "남는 돈(광고비 후)", "cum_profit": "누적 남는 돈"}).style.format("{:,.0f}"), hide_index=True, width="stretch")

# ─────────────────────────── ⑤ 개선 우선순위 ───────────────────────────
with tabs[4]:
    guide("광고비를 늘리는 것과 가게의 다른 부분(구매 비율, 재구매, 결제 금액)을 고치는 것 중 무엇이 이익을 더 키우는지 비교합니다. "
          "위에서부터 확인할 것 → 무엇을 먼저 고칠지 → 어떻게 실험할지 순서로 보세요.")
    warn = warnings(res, alloc)
    if warn:
        st.subheader("먼저 확인할 것")
        for lvl, text in warn:
            getattr(st, lvl)(text)
    t1, t2 = st.columns([3, 2])
    with t1:
        st.subheader("무엇을 고치면 이익이 가장 많이 늘까?")
        st.plotly_chart(charts.tornado(levers), use_container_width=True)
        st.caption("각 항목을 10% 좋게(초록) 또는 나쁘게(빨강) 바꿨을 때 1년 동안 남는 돈이 얼마나 변하는지입니다. "
                   "막대가 길수록 효과가 큰 항목이니 위에서부터 고치세요. "
                   "'단계: ○○ (이탈 감소)'는 그 단계에서 그만두는 사람을 10% 줄인다는 뜻입니다.")
    with t2:
        st.subheader("이렇게 해 보세요")
        for card in insights(res, levers, opt, D.OMTM_OPTIONS[omtm], scan, opt_profit, opt_roas, recs):
            with st.container(border=True):
                st.markdown(f"**{card['title']}**  \n📊 근거: {card['evidence']}  \n🧪 해 볼 일: {card['action']}")
        core = levers[levers["core"]][["lever", "up"]].rename(columns={"lever": "10% 좋아지면", "up": "1년 동안 남는 돈 변화"})
        st.dataframe(core.style.format({"1년 동안 남는 돈 변화": "{:+,.0f}"}), hide_index=True, width="stretch")
        top_step = levers[levers["key"].str.startswith("step_")].sort_values("up", ascending=False)
        if len(top_step):
            name = top_step.iloc[0]["lever"].replace("단계: ", "").replace(" (이탈 감소)", "")
            st.subheader("실험해 보기 (A/B 테스트)")
            st.markdown(f"'**{name}**' 단계를 두 가지 버전으로 만들어 손님을 반씩 나눠 보여주고 비교해 보세요.  \n"
                        f"- 바꿔 볼 것: {prescription(name)}  \n"
                        f"- 이 단계에서 그만두는 사람을 10% 줄이면 1년 동안 {won(top_step.iloc[0]['up'])}이 더 남습니다.")
            st.markdown("**실험에 손님이 몇 명 필요할까?**")
            st.caption("너무 적은 손님으로 비교하면 우연인지 진짜 효과인지 알 수 없습니다. 믿을 만한 결과에 필요한 인원을 계산합니다.")
            step_names = [n for n, _ in params.steps]
            exp_step = st.selectbox("실험할 단계", step_names, index=step_names.index(name) if name in step_names else 0)
            i = step_names.index(exp_step)
            base_rate = params.steps[i][1]
            lift = st.slider("얼마나 좋아지는 걸 확인하고 싶나요? (지금보다 %)", 1, 50, 10,
                             help="10 = 통과율이 지금의 1.1배가 되는 변화. 작은 변화일수록 더 많은 손님이 필요합니다.") / 100
            with st.expander("통계 설정 (모르면 그대로 두세요)"):
                e1, e2 = st.columns(2)
                alpha = e1.selectbox("유의수준 α (우연을 효과로 착각할 위험)", [0.05, 0.1, 0.01])
                power = e2.selectbox("검정력 1−β (진짜 효과를 찾아낼 확률)", [0.8, 0.9])
            ss_res = sample_size(base_rate, lift, alpha, power)
            monthly_in = res.funnel.iloc[i]["count"] / 12  # 이 단계에 들어오는 월 사용자 (퍼널 직전 단계)
            days = days_needed(ss_res["n_total"], monthly_in)
            st.markdown(f"통과율 **{base_rate:.1%} → {ss_res['p2']:.1%}** 변화를 확인하려면 A·B 각각 **{ss_res['n_per_group']:,.0f}명**, "
                        f"모두 {ss_res['n_total']:,.0f}명이 필요합니다.  \n지금 광고로 이 단계에 한 달 {monthly_in:,.0f}명이 오므로 "
                        + (f"약 **{days:,.0f}일**이 걸립니다." if days < 10_000 else "지금 손님 수로는 실험이 어렵습니다.")
                        + (" 너무 길다면 '얼마나 좋아지는 걸 확인하고 싶나요'를 크게 잡거나, 광고 외 손님까지 포함해 실험하세요." if days > 60 else ""))

st.divider()
st.caption("데이터: 네이버 검색광고 API(예측값), GA4 샘플 퍼널, Kaggle Sales Conversion Optimization(익명 기업, 상대 배수만 사용). "
           "리텐션·구매 빈도는 UCI Online Retail II(CC BY 4.0) 분석 후 교체 예정. 금액은 원화 입력값이며 외부 데이터 통화는 환산하지 않습니다. "
           "결과는 출발점을 잡기 위한 추정치이며, 우리 가게의 실제 숫자를 넣을수록 정확해집니다.")
