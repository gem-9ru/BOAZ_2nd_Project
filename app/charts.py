"""Plotly 차트 모음 (화면에서 쓰는 것만)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

AARRR_COLORS = {"획득": "#4C78A8", "활성화": "#59A14F", "유지": "#F28E2B", "수익": "#B07AA1", "추천": "#E15759"}
CUR, OPT = "#4C78A8", "#F28E2B"


def _layout(fig, title=None, height=360):
    fig.update_layout(title=title, height=height, margin=dict(l=10, r=10, t=80 if title else 30, b=10),
                      title_y=0.98, title_yanchor="top",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    return fig


def keyword_scatter(kw: pd.DataFrame, selected):
    df = kw.head(200).copy()
    df["선택"] = np.where(df["keyword"].isin(selected), "선택", "후보")
    fig = go.Figure()
    for comp, color in [("높음", "#E15759"), ("중간", "#F28E2B"), ("낮음", "#59A14F")]:
        d = df[df["comp"] == comp]
        fig.add_trace(go.Scatter(
            x=d["total_qc"], y=d["mobile_ctr"], mode="markers", name=f"경쟁 {comp}",
            marker=dict(color=color, size=np.where(d["선택"] == "선택", 14, 7),
                        line=dict(width=np.where(d["선택"] == "선택", 2, 0), color="black")),
            text=d["keyword"], hovertemplate="%{text}<br>월 검색수 %{x:,.0f}<br>모바일 CTR %{y:.2f}%<extra></extra>"))
    for x, label in [(1_000, "세부 ↑"), (30_000, "대표 ↑")]:
        fig.add_vline(x=x, line_dash="dot", line_color="gray", annotation_text=label, annotation_position="top right")
    fig.update_xaxes(type="log", title="월 검색수 (PC+모바일, 로그) · 롱테일 < 1천 ≤ 세부 < 3만 ≤ 대표")
    fig.update_yaxes(title="모바일 CTR (%)")
    return _layout(fig, "키워드 검색량 vs CTR (색: 경쟁 정도)")


def bid_curves(estimates: dict, naver_curve):
    fig = go.Figure()
    for kw, df in estimates.items():
        fig.add_trace(go.Scatter(x=df["cost"], y=df["clicks"], mode="lines+markers", name=kw, line_shape="hv",
                                 customdata=df["bid"],
                                 hovertemplate=kw + "<br>입찰가 %{customdata:,.0f}원<br>비용 %{x:,.0f}원<br>클릭 %{y:,.0f}<extra></extra>"))
    if naver_curve is not None and naver_curve.capacity > 0:
        t = naver_curve.curve_table()
        fig.add_trace(go.Scatter(x=t["spend"], y=t["clicks"], mode="lines", name="네이버 합계 (최적 조합)",
                                 line=dict(color="gray", dash="dash", width=3)))
    fig.update_xaxes(title="월 광고비 (원)")
    fig.update_yaxes(title="월 예상 클릭")
    return _layout(fig, "입찰가별 예상 실적 → 광고비-클릭 곡선 (네이버 예측값)")


def meta_curve(curve, max_spend):
    t = curve.curve_table(max_spend)
    fig = go.Figure(go.Scatter(x=t["spend"], y=t["clicks"], mode="lines", name="메타 클릭", line=dict(color=CUR)))
    fig.update_xaxes(title="월 광고비 (원)")
    fig.update_yaxes(title="월 클릭")
    return _layout(fig, "메타 광고비-클릭 (CPC 상승 반영)", 300)


def retention_curve(params, months=12, actual: pd.DataFrame = None):
    r = params.retention(months + 1)
    fig = go.Figure(go.Scatter(x=list(range(months + 1)), y=r, mode="lines+markers", name="시뮬레이션 곡선",
                               line=dict(color=AARRR_COLORS["유지"])))
    if actual is not None:
        a = actual[actual["months_since"] <= months]
        fig.add_trace(go.Scatter(x=a["months_since"], y=a["retention"], mode="markers", name="실제 코호트 평균",
                                 marker=dict(color="gray", size=9, symbol="x")))
    fig.add_hline(y=params.retention_floor, line_dash="dot", annotation_text=f"바닥값 {params.retention_floor:.0%}")
    fig.update_xaxes(title="첫 구매 후 경과 개월")
    fig.update_yaxes(title="월 범위 리텐션", tickformat=".0%", range=[0, 1.05])
    return _layout(fig, "리텐션 곡선 r(t)", 300)


def activation_funnel(params, clicks=1000):
    names, vals, cur = ["클릭"], [clicks], clicks
    for n, r in params.steps:
        cur *= r
        names.append(n)
        vals.append(cur)
    fig = go.Figure(go.Funnel(y=names, x=vals, texttemplate="%{value:,.1f}<br>%{percentInitial:.1%}", marker=dict(color=AARRR_COLORS["활성화"])))
    return _layout(fig, f"클릭 {clicks:,}회 기준 활성화 퍼널", 300)


def aarrr_funnel(funnel: pd.DataFrame, summary: dict):
    df = funnel[funnel["count"] > 0] if (funnel["count"] > 0).any() else funnel
    fig = go.Figure(go.Funnel(
        y=[f"[{a}] {s}" for a, s in zip(df["aarrr"], df["stage"])], x=df["count"],
        textinfo="value+percent previous", texttemplate="%{value:,.0f}",
        marker=dict(color=[AARRR_COLORS[a] for a in df["aarrr"]])))
    title = f"AARRR 퍼널 (12개월 합계) · 수익: 매출 {summary['revenue'] / 1e4:,.0f}만 원, 이익 {summary['profit_12m'] / 1e4:,.0f}만 원"
    return _layout(fig, title, 420)


def cum_profit(cur: pd.DataFrame, opt: pd.DataFrame = None, opt_label="최적안"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cur["month"], y=cur["cum_profit"], mode="lines+markers", name="현재안", line=dict(color=CUR)))
    if opt is not None:
        fig.add_trace(go.Scatter(x=opt["month"], y=opt["cum_profit"], mode="lines+markers", name=opt_label,
                                 line=dict(color=OPT, dash="dash")))
    fig.add_hline(y=0, line_color="gray")
    fig.update_xaxes(title="개월", dtick=1)
    fig.update_yaxes(title="누적 이익 (원)")
    return _layout(fig, "12개월 누적 이익", 360)


def revenue_split(monthly: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["new_revenue"], name="신규 매출", stackgroup="rev",
                             line=dict(color="#4C78A8")))
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["repeat_revenue"], name="재구매 매출", stackgroup="rev",
                             line=dict(color="#F28E2B")))
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["spend"], name="광고비", mode="lines", line=dict(color="gray", dash="dot")))
    fig.update_xaxes(title="개월", dtick=1)
    fig.update_yaxes(title="원")
    return _layout(fig, "월별 매출: 신규 vs 재구매", 340)


def budget_scan_chart(scan: pd.DataFrame, current_budget: float):
    fig = go.Figure(go.Scatter(x=scan["monthly_budget"], y=scan["profit_12m"], mode="lines+markers", line=dict(color=CUR),
                               hovertemplate="월 %{x:,.0f}원<br>12개월 이익 %{y:,.0f}원<extra></extra>"))
    fig.add_vline(x=current_budget, line_dash="dot", annotation_text="현재 예산")
    fig.add_hline(y=0, line_color="gray")
    fig.update_xaxes(title="월 총예산 (원, 현재 배분 비율 유지)")
    fig.update_yaxes(title="12개월 이익 (원)")
    return _layout(fig, "예산 규모별 12개월 이익", 320)


def tornado(levers: pd.DataFrame):
    df = levers.copy()
    df["span"] = df["up"].abs() + df["down"].abs()
    df = df.sort_values("span")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df["lever"], x=df["down"], orientation="h", name="−10%", marker_color="#BAB0AC"))
    fig.add_trace(go.Bar(y=df["lever"], x=df["up"], orientation="h", name="+10% (초록 = 이익 증가, 빨강 = 감소)",
                         marker_color=["#59A14F" if v >= 0 else "#E15759" for v in df["up"]]))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="12개월 이익 변화 (원)")
    return _layout(fig, "레버별 12개월 이익 민감도 (토네이도)", 80 + 40 * len(df))


def meta_target_bars(targets: pd.DataFrame, selected):
    df = targets.sort_values("rel_cpa")
    colors = [CUR if t in selected else "#BAB0AC" for t in df["target"]]
    fig = go.Figure(go.Bar(
        x=df["target"], y=df["rel_cpa"], marker_color=colors,
        error_y=dict(type="data", symmetric=False, array=df["high"] - df["rel_cpa"], arrayminus=df["rel_cpa"] - df["low"]),
        customdata=df["purchases"], hovertemplate="%{x}<br>상대 CPA %{y:.2f}배<br>구매 %{customdata}건<extra></extra>"))
    fig.add_hline(y=1.0, line_dash="dot", annotation_text="전체 평균 = 1")
    fig.update_yaxes(title="상대 CPA (캠페인 통제, 95% 구간)")
    return _layout(fig, "메타 타깃별 구매당 비용 배수 (Kaggle)", 300)


def payback(curve, cac, months=24):
    x = list(range(1, months + 1))
    fig = go.Figure(go.Scatter(x=x, y=curve[:months], mode="lines+markers", name="고객 1명 누적 이익",
                               line=dict(color=AARRR_COLORS["수익"])))
    if cac:
        fig.add_hline(y=cac, line_dash="dash", line_color="#E15759", annotation_text=f"유료 CAC {cac:,.0f}원")
    fig.update_xaxes(title="첫 구매 후 개월", dtick=2)
    fig.update_yaxes(title="누적 매출총이익 (원)")
    return _layout(fig, "회수 기간: 고객 1명의 누적 이익 vs CAC", 320)
