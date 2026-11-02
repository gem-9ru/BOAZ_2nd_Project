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
from src.engine.insights import insights, prescription, warnings, won  # noqa: E402

st.set_page_config(page_title="AARRR 광고 예산 시뮬레이터", page_icon="📈", layout="wide")

# 지표 정의서(실행계획 7장) 기반 툴팁
HELP = {
    "new": "광고(유료) + 추천으로 들어온 12개월 신규 고객 합계",
    "paid_cac": "유료 CAC = 광고비 / 광고로 온 신규 고객",
    "blended_cac": "혼합 CAC = 광고비 / 전체 신규 고객 (추천 포함)",
    "ltv": "12개월 LTV = 첫 구매 후 12개월 누적 매출총이익 (고객 1명)",
    "ltv_cac": "LTV/CAC = 12개월 LTV / 유료 CAC. 1보다 작으면 광고로 데려온 고객이 손해",
    "payback": "회수 기간 = 고객 1명의 누적 이익이 유료 CAC를 넘는 개월 수",
    "profit": "12개월 이익 = Σ(매출 × 마진) − 광고비",
    "roas": "ROAS(매체 기준) = 광고로 온 신규 고객의 첫 구매 매출 / 광고비. 재구매는 빠져 있음",
    "cpc": "CPC = 광고비 / 클릭",
    "mcpc": "한계 CPC = Δ비용 / Δ클릭. 다음 클릭 하나를 더 사는 비용",
}

ss = st.session_state


@st.cache_data(show_spinner=False)
def load_keywords(hints: tuple, online: bool):
    return ns.keyword_tool(list(hints), online=online)


@st.cache_data(show_spinner=False)
def load_estimate(keyword: str, online: bool):
    return ns.bid_estimate(keyword, device=D.NAVER_DEVICE, online=online)


st.title("📈 AARRR 기반 광고 예산 시뮬레이터")
st.caption("광고 예산이 획득 → 활성화 → 유지 → 수익 → 추천으로 어떻게 이어지는지 12개월을 시뮬레이션하고, "
           "예산을 늘릴지 · 채널을 바꿀지 · 퍼널의 어느 단계를 먼저 고칠지 알려줍니다. (프로토타입 v0.2)")

tabs = st.tabs(["① 시작", "② 획득 설계", "③ 퍼널 설정", "④ 시뮬레이션", "⑤ 개선 우선순위"])

# ───────────────────────────── ① 시작 ─────────────────────────────
with tabs[0]:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("무엇을 위한 광고인가요?")
        business = st.text_input("업종·서비스 (자유 입력, 계산에는 쓰이지 않음)", placeholder="예: 동네 필라테스 스튜디오, 원두 온라인몰 …")
        task = st.selectbox("핵심 과업 (광고로 유도할 행동)", D.CORE_TASKS)
        if task == "직접 입력":
            task = st.text_input("핵심 과업 이름", value="전환") or "전환"
        omtm = st.radio("OMTM (지금 가장 중요한 지표 하나)", list(D.OMTM_OPTIONS), horizontal=True,
                        format_func=D.OMTM_OPTIONS.get, index=1,
                        help="예산 최적화가 이 지표를 최대화합니다.")
        budget = st.number_input("월 광고 예산 (원)", min_value=0, max_value=1_000_000_000,
                                 value=D.MONTHLY_BUDGET, step=100_000, format="%d")
        st.caption(f"= {won(budget)} / 월, 12개월 {won(budget * 12)}")
    with c2:
        st.subheader("가진 데이터")
        level = st.radio("데이터 단계", ["0단계: 데이터 없음 (기본값 사용)", "1단계: 매체별 광고 성과 CSV 있음"])
        upload = None
        if level.startswith("1"):
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
                    st.info("합계 기준으로 CPC·CVR을 계산했습니다 (광고별 비율 평균이 아님). "
                            "source가 naver·meta인 행으로 메타 CPC와 채널별 전환율을 보정합니다.")
            except Exception as e:  # noqa: BLE001
                st.error(f"CSV를 읽지 못했습니다: {e}")
        st.markdown("**0단계 기본값 출처**")
        st.markdown(
            "- 획득: 네이버 검색광고 API 실시간 예상 실적 ✅ / 메타는 사용자 입력 CPC × Kaggle 타깃별 상대 CPA ✅\n"
            "- 활성화: GA4 샘플 사용자 기준 퍼널 ✅ (랜딩 도착 단계만 임시값)\n"
            "- 유지·수익: UCI Online Retail II 코호트 (도매 분리 후) 예정 — 지금은 임시값\n"
            "- 금액(객단가·CPC)은 원화로 직접 입력 · 추천은 가정값 (기본 0)")

# ─────────────────────────── ② 획득 설계 ───────────────────────────
with tabs[1]:
    api_ok = ns.api_available()
    top = st.columns([2, 1])
    with top[0]:
        hint_text = st.text_input("네이버 검색 키워드 (쉼표로 최대 5개, 업종 무관)", value=ns.SAMPLE_KEYWORD,
                                  help="입력한 키워드로 네이버 키워드 도구를 조회합니다.")
    with top[1]:
        online = st.toggle("네이버 API 실시간 조회", value=api_ok, disabled=not api_ok,
                           help="끄면 data/interim/naver_cache 의 저장된 응답만 씁니다 (오프라인 모드).")
        if not api_ok:
            st.caption("⚠️ .env 키가 없어 오프라인 모드로 동작합니다.")
    hints = tuple(h.strip().replace(" ", "") for h in hint_text.split(",") if h.strip())[:5]
    kw_df = load_keywords(hints, online) if hints else None
    fallback = False
    if kw_df is None:
        fallback = True
        kw_df = load_keywords((ns.SAMPLE_KEYWORD,), False)
        st.warning(f"'{hint_text}' 조회 결과가 없어 (오프라인이거나 캐시 없음) 예시 키워드 '{ns.SAMPLE_KEYWORD}' 캐시로 대신 보여줍니다.")

    estimates, recs = {}, None
    if kw_df is not None:
        base_hints = (ns.SAMPLE_KEYWORD,) if fallback else hints
        default_sel = [k for k in base_hints if k in set(kw_df["keyword"])] or kw_df["keyword"].head(3).tolist()
        selected = st.multiselect("광고할 키워드 선택 (입찰가 곡선을 불러옵니다, 최대 8개)",
                                  kw_df["keyword"].tolist(), default=default_sel, max_selections=8)
        k1, k2 = st.columns([1, 1])
        with k1:
            st.plotly_chart(charts.keyword_scatter(kw_df, selected), use_container_width=True)
        with k2:
            tier_filter = st.multiselect("유형", ["대표", "세부", "롱테일"], default=["대표", "세부"],
                                         help="월 검색수(PC+모바일): 3만 이상 대표, 1천~3만 세부, 1천 미만 롱테일")
            st.dataframe(kw_df[kw_df["tier"].isin(tier_filter)].head(100)[
                ["keyword", "tier", "total_qc", "comp", "mobile_ctr", "mobile_clicks"]].rename(columns={
                "keyword": "키워드", "tier": "유형", "total_qc": "월 검색수", "comp": "경쟁",
                "mobile_ctr": "모바일 CTR(%)", "mobile_clicks": "모바일 평균 클릭"}), height=300, hide_index=True)
        recs = ns.recommend_keywords(kw_df, seeds=list(base_hints))
        if len(recs):
            st.markdown("**세부 키워드 기회** (월 검색수 1천~3만 · 경쟁 낮음/중간 · 입력 키워드를 포함한 것 우선): "
                        + ", ".join(f"`{k}`" for k in recs["keyword"]) + " — 위 선택 목록에 추가해 보세요.")
        with st.spinner("입찰가별 예상 실적을 불러오는 중…"):
            for kw in selected:
                est = load_estimate(kw, online and not fallback)
                if est is not None and (est["clicks"] > 0).any():
                    estimates[kw] = est
        missing = [k for k in selected if k not in estimates]
        if missing:
            st.caption(f"예상 클릭이 0이거나 캐시가 없어 제외한 키워드: {', '.join(missing)}")

    naver_curve = NaverCurve(estimates) if estimates else None
    if naver_curve is None:
        st.info("사용할 수 있는 네이버 키워드가 없습니다. 네이버 예산은 0으로 계산합니다.")
        naver_curve = NaverCurve({})

    st.divider()
    st.subheader("채널별 예산")
    m1, m2 = st.columns([1, 1])
    with m1:
        naver_share = st.slider("네이버 비중 (%)", 0, 100, int(D.CHANNEL_SHARES["naver"] * 100), step=5)
        naver_budget = budget * naver_share / 100
        meta_budget = budget - naver_budget
        st.markdown(f"**네이버** {won(naver_budget)} / 월 · **메타** {won(meta_budget)} / 월")
        if naver_curve.capacity > 0:
            st.caption(f"선택한 키워드로 네이버에 쓸 수 있는 최대 광고비: 월 {won(naver_curve.capacity)}")
    with m2:
        targets_df = dl.meta_targets()
        meta_targets = st.multiselect("메타 타깃 (연령·성별)", targets_df["target"].tolist(),
                                      help="Kaggle 캠페인 통제 상대 CPA 배수를 입력 CPC에 곱합니다. 비우면 전체 평균(1배).")
        target_mult = dl.target_multiplier(meta_targets)
        with st.expander("메타 설정 (기본값 = 임시값)", expanded=False):
            meta_cpc_input = st.number_input("기본 CPC (원, 직접 입력)", 50.0, 20_000.0, float(D.META_BASE_CPC), step=50.0)
            meta_sat = st.slider("포화 정도 (100만 원당 CPC 상승률)", 0.0, 2.0, float(D.META_SATURATION), 0.05)
            meta_cvr_mult = st.slider("메타 전환율 배수 (검색 대비)", 0.1, 2.0, float(D.META_CVR_MULT), 0.05)
            meta_ret_mult = st.slider("메타 고객 리텐션 배수", 0.1, 2.0, float(D.META_RETENTION_MULT), 0.05)
        meta_cpc = meta_cpc_input * target_mult
        if upload is not None and "meta" in upload.index:
            meta_cpc = float(upload.loc["meta", "CPC"])  # 1단계: 내 실제 CPC가 타깃 배수보다 우선
        st.caption(f"메타 적용 CPC: {meta_cpc:,.0f}원" + (f" (입력 {meta_cpc_input:,.0f}원 × 타깃 배수 {target_mult:.2f})"
                                                       if upload is None or "meta" not in upload.index else " (1단계 CSV)"))
    meta_curve = MetaCurve(meta_cpc, meta_sat)
    spends = [naver_budget, meta_budget]

    g1, g2 = st.columns([3, 2])
    with g1:
        st.plotly_chart(charts.bid_curves(estimates, naver_curve if estimates else None), use_container_width=True)
    with g2:
        st.plotly_chart(charts.meta_target_bars(targets_df, meta_targets), use_container_width=True)
        st.plotly_chart(charts.meta_curve(meta_curve, max(budget, 1)), use_container_width=True)
    alloc = None
    if estimates:
        alloc = naver_curve.allocation(naver_budget, D.SATURATION_RATIO)
        st.markdown("**네이버 예산의 키워드별 배분** (한계 CPC가 낮은 구간부터 채움 · 한계 CPC가 평균의 2배를 넘으면 포화)")
        show = alloc.assign(saturated=alloc["saturated"].map({True: "⚠️ 포화", False: ""}))
        st.dataframe(show.rename(columns={"keyword": "키워드", "spend": "월 광고비", "clicks": "월 클릭", "bid": "권장 입찰가",
                                          "marginal_cpc": "한계 CPC", "cpc": "평균 CPC", "saturated": "포화"})
                     .style.format({"월 광고비": "{:,.0f}", "월 클릭": "{:,.0f}", "권장 입찰가": "{:,.0f}",
                                    "한계 CPC": "{:,.0f}", "평균 CPC": "{:,.0f}"}, na_rep="-"),
                     hide_index=True)
    st.caption("네이버 예상 실적은 네이버의 예측값(월간, 모바일)입니다. 실제 성과와 다를 수 있습니다.")

# ─────────────────────────── ③ 퍼널 설정 ───────────────────────────
with tabs[2]:
    st.subheader(f"활성화: 클릭 → {task}")
    f1, f2 = st.columns([1, 1])
    with f1:
        mediums = dl.ga4_mediums() or [dl.GA4_ALL]
        medium = st.selectbox("기본값 출처: GA4 샘플 유입 매체", mediums,
                              help="'전체'가 기본. cpc(유료 검색) 유입만의 퍼널도 고를 수 있습니다. (data deleted)는 비정상적으로 높으니 주의")
        base_steps, src = dl.funnel_steps(medium)
        steps_df = pd.DataFrame([{"단계": n, "전환율": round(r, 3)} for n, r in base_steps])
        steps_df.loc[len(steps_df) - 1, "단계"] = f"{task} 완료"
        edited = st.data_editor(steps_df, num_rows="dynamic", hide_index=True, key="steps_editor",
                                column_config={"전환율": st.column_config.NumberColumn(min_value=0.0, max_value=1.0, step=0.01, format="%.2f")})
        edited = edited.dropna()
        steps = [(str(n), float(r)) for n, r in zip(edited["단계"], edited["전환율"])]
        st.caption(f"출처: {src}. 첫 단계(광고 클릭 → 방문)는 GA4에 없어 임시값입니다. 값을 고치거나 단계를 추가·삭제할 수 있습니다.")
    st.subheader("유지 · 수익 · 추천")
    r1, r2, r3 = st.columns(3)
    with r1:
        floor = st.slider("리텐션 바닥값", 0.0, 0.6, float(D.RETENTION_FLOOR), 0.01, help="오래 지나도 남는 고객 비율 (곡선이 평평해지는 높이)")
        decay = st.slider("리텐션 감소율", 0.1, 5.0, float(D.RETENTION_DECAY), 0.1, help="첫 구매 후 얼마나 빨리 이탈하는지")
    with r2:
        aov = st.number_input("객단가 (원, 중앙값 기준)", 1_000.0, 10_000_000.0, float(D.AOV), step=1_000.0)
        freq = st.number_input("활성 고객 월 구매 빈도", 0.1, 10.0, float(D.PURCHASE_FREQ), step=0.1)
        margin = st.slider("마진율 (공헌이익률)", 0.0, 1.0, float(D.MARGIN), 0.01)
    with r3:
        invite_rate = st.slider("초대율 (활성 고객 1명이 한 달에 보내는 초대)", 0.0, 2.0, float(D.INVITE_RATE), 0.05)
        invite_conv = st.slider("초대 전환율", 0.0, 1.0, float(D.INVITE_CONV), 0.01)
        st.caption(f"추천 계수 = {invite_rate * invite_conv:.3f} (가정값)")
    params = FunnelParams(steps=steps, retention_floor=floor, retention_decay=decay, purchase_freq=freq,
                          aov=aov, margin=margin, invite_rate=invite_rate, invite_conv=invite_conv)
    with f2:
        st.plotly_chart(charts.activation_funnel(params), use_container_width=True)
        st.metric("클릭 → 과업 완료 전환율 (CVR)", f"{params.cvr:.2%}")
    st.plotly_chart(charts.retention_curve(params), use_container_width=True)
    st.caption("리텐션·구매 빈도는 UCI 코호트 분석(도매 고객 분리 후)이 나오면 교체합니다. 지금은 임시값입니다.")

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


def kpis(s, cols):
    cols[0].metric("신규 고객 (12개월)", f"{s['new_customers']:,.0f}명", help=HELP["new"])
    cols[1].metric("유료 CAC", won(s["paid_cac"]), help=HELP["paid_cac"])
    cols[2].metric("혼합 CAC", won(s["blended_cac"]), help=HELP["blended_cac"])
    cols[3].metric("LTV/CAC", f"{s['ltv_cac']:.2f}" if s["ltv_cac"] else "-", help=HELP["ltv_cac"])
    cols[4].metric("회수 기간", f"{s['payback_month']}개월" if s["payback_month"] else "36개월+", help=HELP["payback"])
    cols[5].metric("12개월 이익", won(s["profit_12m"]), help=HELP["profit"])
    cols[6].metric("ROAS (매체 기준)", f"{s['roas']:.2f}" if s["roas"] else "-", help=HELP["roas"])


# ─────────────────────────── ④ 시뮬레이션 ───────────────────────────
with tabs[3]:
    if upload is not None:
        st.caption(f"1단계 보정 적용: 전환율 배수 네이버 {naver_cvr_mult:.2f} / 메타 {meta_cvr_mult:.2f}, 메타 CPC {meta_cpc:,.0f}원")
    fmt = {"profit": won, "roas": lambda v: f"{v:.2f}", "new_customers": lambda v: f"{v:,.0f}명"}[omtm]
    o1, o2 = st.columns([1, 2])
    with o1:
        st.metric(f"OMTM · {D.OMTM_OPTIONS[omtm]}", fmt(opt["base_value"]), delta=f"최적안 {fmt(opt['value'])}",
                  delta_color="off", border=True, help="시작 화면에서 고른 단 하나의 목표. 최적안은 이 지표를 최대화합니다.")
    with o2:
        st.markdown(f"**현재안**: 네이버 {won(spends[0])} · 메타 {won(spends[1])} / 월  \n"
                    f"**최적안**: 네이버 {won(opt['spends'][0])} · 메타 {won(opt['spends'][1])} / 월"
                    + (f" (미사용 {won(budget - sum(opt['spends']))})" if budget - sum(opt["spends"]) > 1 else ""))
    st.subheader("현재안 KPI")
    kpis(res.summary, st.columns(7))
    a1, a2 = st.columns([1, 1])
    with a1:
        st.plotly_chart(charts.aarrr_funnel(res.funnel, res.summary), use_container_width=True)
    with a2:
        st.plotly_chart(charts.cum_profit(res.monthly, res_opt.monthly, f"최적안 ({D.OMTM_OPTIONS[omtm]} 기준)"),
                        use_container_width=True)
    st.subheader(f"현재안 vs 최적안 — OMTM: {D.OMTM_OPTIONS[omtm]}")

    def plan_row(name, sp, r):
        s = r.summary
        return {"안": name, "네이버 (월)": sp[0], "메타 (월)": sp[1], "미사용 (월)": budget - sum(sp),
                "신규 고객": s["new_customers"], "유료 CAC": s["paid_cac"], "LTV/CAC": s["ltv_cac"],
                "ROAS": s["roas"], "12개월 이익": s["profit_12m"]}

    rows = [plan_row("현재안", spends, res), plan_row(f"최적안 ({D.OMTM_OPTIONS[omtm]})", opt["spends"], res_opt)]
    if omtm != "profit":
        rows.append(plan_row("이익 최적안", opt_profit["spends"], simulate(channels, opt_profit["spends"], params)))
    if omtm != "roas":
        rows.append(plan_row("ROAS 최적안", opt_roas["spends"], simulate(channels, opt_roas["spends"], params)))
    st.dataframe(pd.DataFrame(rows).style.format({
        "네이버 (월)": "{:,.0f}", "미사용 (월)": "{:,.0f}", "메타 (월)": "{:,.0f}", "신규 고객": "{:,.0f}",
        "유료 CAC": "{:,.0f}", "LTV/CAC": "{:.2f}", "ROAS": "{:.2f}", "12개월 이익": "{:,.0f}"}, na_rep="-"),
        hide_index=True, width="stretch")
    st.caption("12개월 이익 최적안은 예산을 다 쓰지 않을 수 있습니다 (손해 구간에서는 덜 쓰는 것이 최적). "
               "ROAS 최적안과 이익 최적안이 다르면 ROAS만 보는 배분은 부분 최적화입니다.")
    b1, b2 = st.columns([1, 1])
    with b1:
        st.plotly_chart(charts.revenue_split(res.monthly), use_container_width=True)
    with b2:
        st.plotly_chart(charts.budget_scan_chart(scan, budget), use_container_width=True)
    st.markdown("**채널별 결과 (월 기준)**")
    bc = res.by_channel[["label", "budget", "spend", "clicks", "cpc", "marginal_cpc", "new_customers", "cac", "ltv_12m"]]
    st.dataframe(bc.rename(columns={"label": "채널", "budget": "배정 예산", "spend": "집행 가능", "clicks": "클릭",
                                    "cpc": "평균 CPC", "marginal_cpc": "한계 CPC", "new_customers": "신규 고객",
                                    "cac": "CAC", "ltv_12m": "12개월 LTV"})
                 .style.format("{:,.0f}", subset=["배정 예산", "집행 가능", "클릭", "평균 CPC", "한계 CPC", "CAC", "12개월 LTV"])
                 .format("{:,.1f}", subset=["신규 고객"], na_rep="-"), hide_index=True, width="stretch")
    st.plotly_chart(charts.payback(res.customer_cum_profit, res.summary["paid_cac"]), use_container_width=True)
    with st.expander("월별 상세 표"):
        st.dataframe(res.monthly.style.format("{:,.0f}"), hide_index=True, width="stretch")

# ─────────────────────────── ⑤ 개선 우선순위 ───────────────────────────
with tabs[4]:
    for lvl, text in warnings(res, alloc):
        getattr(st, lvl)(text)
    t1, t2 = st.columns([3, 2])
    with t1:
        st.plotly_chart(charts.tornado(levers), use_container_width=True)
        st.caption("광고비·전환율·리텐션·객단가·구매 빈도는 ±10%, 퍼널 단계는 '이탈률 ±10%'로 바꿨을 때의 12개월 이익 변화입니다.")
    with t2:
        st.subheader("인사이트")
        for card in insights(res, levers, opt, D.OMTM_OPTIONS[omtm], scan, opt_profit, opt_roas, recs):
            with st.container(border=True):
                st.markdown(f"**{card['title']}**  \n📊 {card['evidence']}  \n🧪 {card['action']}")
        core = levers[levers["core"]][["lever", "up"]].rename(columns={"lever": "레버 (+10%)", "up": "12개월 이익 변화"})
        st.dataframe(core.style.format({"12개월 이익 변화": "{:+,.0f}"}), hide_index=True, width="stretch")
        top_step = levers[levers["key"].str.startswith("step_")].sort_values("up", ascending=False)
        if len(top_step):
            name = top_step.iloc[0]["lever"].replace("단계: ", "").replace(" (이탈 감소)", "")
            st.subheader("실험 제안")
            st.markdown(f"- **{name}** 단계 A/B 테스트: {prescription(name)}. "
                        f"이탈을 10% 줄이면 12개월 이익 {won(top_step.iloc[0]['up'])} 증가 예상\n"
                        "- 표본 크기 계산기는 다음 버전에서 제공합니다.")

st.divider()
st.caption("데이터: 네이버 검색광고 API(예측값), GA4 샘플 퍼널, Kaggle Sales Conversion Optimization(익명 기업, 상대 배수만 사용). "
           "리텐션·구매 빈도는 UCI Online Retail II(CC BY 4.0) 분석 후 교체 예정. 금액은 원화 입력값이며 외부 데이터 통화는 환산하지 않습니다. "
           "단계별 데이터 출처가 달라 0단계 결과는 출발점이며, 자기 데이터를 넣을수록 정확해집니다.")
