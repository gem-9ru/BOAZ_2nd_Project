"""Plotly 차트 모음 (화면에서 쓰는 것만)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.engine import defaults as D

AARRR_COLORS = {"획득": "#4C78A8", "활성화": "#59A14F", "유지": "#F28E2B", "추천": "#E15759"}  # 행동 축 (밸류체인 v3)
MONEY_COLOR = "#B07AA1"  # 돈 축 (매출·남는 돈). 수익은 단계가 아님
CUR, OPT = "#4C78A8", "#F28E2B"


def _layout(fig, title=None, height=360):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=80 if title else 30, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    if title:
        fig.update_layout(title=title, title_y=0.98, title_yanchor="top")
    return fig


def _qc(n: float) -> str:
    return f"{n / 10_000:g}만" if n >= 10_000 else (f"{n / 1_000:g}천" if n >= 1_000 else f"{n:,.0f}")


def tier_caption() -> str:
    """검색어 구간 설명 (defaults.KEYWORD_TIERS): 예) '300 미만 롱테일 · 300~1만 세부 · 1만 이상 대표'."""
    tiers = sorted(D.KEYWORD_TIERS)                     # (0 롱테일), (300 세부), (1만 대표)
    parts = []
    for i, (th, name) in enumerate(tiers):
        nxt = tiers[i + 1][0] if i + 1 < len(tiers) else None
        if th == 0:
            parts.append(f"{_qc(nxt)} 미만 {name}")
        elif nxt is None:
            parts.append(f"{_qc(th)} 이상 {name}")
        else:
            parts.append(f"{_qc(th)}~{_qc(nxt)} {name}")
    return " · ".join(parts)


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
    # 선·분류·설명 모두 defaults.KEYWORD_TIERS 하나에서 (검수 A9)
    for x, name in [(th, nm) for th, nm in D.KEYWORD_TIERS if th > 0]:
        fig.add_vline(x=x, line_dash="dot", line_color="gray", annotation_text=f"{name} ↑", annotation_position="top right")
    fig.update_xaxes(type="log", title="한 달 검색 수 (로그 눈금) · " + tier_caption())
    fig.update_yaxes(title="광고 클릭률 (%)")
    return _layout(fig, "검색어별 검색 수와 광고 클릭률 (색: 광고 경쟁)")


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
    fig.update_yaxes(title="한 달 예상 클릭")
    return _layout(fig, "네이버: 광고비를 늘리면 클릭이 얼마나 늘까? (네이버 예상치)")


def meta_curve(curve, max_spend):
    t = curve.curve_table(max_spend)
    fig = go.Figure(go.Scatter(x=t["spend"], y=t["clicks"], mode="lines", name="메타 클릭", line=dict(color=CUR)))
    fig.update_xaxes(title="월 광고비 (원)")
    fig.update_yaxes(title="월 클릭")
    return _layout(fig, "메타: 광고비를 늘리면 클릭이 얼마나 늘까?", 300)


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
    fig.update_yaxes(title="그달 다시 구매하는 비율", tickformat=".0%", range=[0, 1.05])
    return _layout(fig, "첫 구매 후 손님이 다시 오는 비율 (리텐션 곡선)", 300)


def activation_funnel(params, clicks=1000):
    names, vals, cur = ["클릭"], [clicks], clicks
    for n, r in params.steps:
        cur *= r
        names.append(n)
        vals.append(cur)
    fig = go.Figure(go.Funnel(y=names, x=vals, texttemplate="%{value:,.1f}<br>%{percentInitial:.1%}", marker=dict(color=AARRR_COLORS["활성화"])))
    return _layout(fig, f"광고 클릭 {clicks:,}번이면 단계마다 몇 명이 남을까?", 300)


def aarrr_funnel(funnel: pd.DataFrame, summary: dict):
    df = funnel[funnel["count"] > 0] if (funnel["count"] > 0).any() else funnel
    fig = go.Figure(go.Funnel(
        y=[f"[{a}] {s}" for a, s in zip(df["aarrr"], df["stage"])], x=df["count"],
        textinfo="value+percent previous", texttemplate="%{value:,.0f}",
        marker=dict(color=[AARRR_COLORS[a] for a in df["aarrr"]])))
    title = f"1년 손님 흐름 (AARRR)<br><sup>매출 {summary['revenue'] / 1e4:,.0f}만 원 · 남는 돈 {summary['profit_12m'] / 1e4:,.0f}만 원</sup>"
    return _layout(fig, title, 420)


def cum_profit(cur: pd.DataFrame, opt: pd.DataFrame = None, opt_label="추천 계획"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cur["month"], y=cur["cum_profit"], mode="lines+markers", name="지금 계획", line=dict(color=CUR)))
    if opt is not None:
        fig.add_trace(go.Scatter(x=opt["month"], y=opt["cum_profit"], mode="lines+markers", name=opt_label,
                                 line=dict(color=OPT, dash="dash")))
    fig.add_hline(y=0, line_color="gray")
    fig.update_xaxes(title="개월", dtick=1)
    fig.update_yaxes(title="누적 남는 돈 (원)")
    return _layout(fig, "1년 동안 누적으로 남는 돈", 360)


def revenue_split(monthly: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["new_revenue"], name="신규 매출", stackgroup="rev",
                             line=dict(color="#4C78A8")))
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["repeat_revenue"], name="재구매 매출", stackgroup="rev",
                             line=dict(color="#F28E2B")))
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["spend"], name="광고비", mode="lines", line=dict(color="gray", dash="dot")))
    fig.update_xaxes(title="개월", dtick=1)
    fig.update_yaxes(title="원")
    return _layout(fig, "달마다 매출: 새 손님 vs 다시 온 손님", 340)


def budget_scan_chart(scan: pd.DataFrame, current_budget: float):
    fig = go.Figure(go.Scatter(x=scan["monthly_budget"], y=scan["profit_12m"], mode="lines+markers", line=dict(color=CUR),
                               hovertemplate="월 %{x:,.0f}원<br>12개월 이익 %{y:,.0f}원<extra></extra>"))
    fig.add_vline(x=current_budget, line_dash="dot", annotation_text="현재 예산")
    fig.add_hline(y=0, line_color="gray")
    fig.update_xaxes(title="한 달 광고비 (원, 지금 네이버·메타 비율 유지)")
    fig.update_yaxes(title="1년 동안 남는 돈 (원)")
    return _layout(fig, "광고비를 얼마나 써야 가장 많이 남을까?", 320)


def tornado(levers: pd.DataFrame):
    df = levers.copy()
    df["span"] = df["up"].abs() + df["down"].abs()
    df = df.sort_values("span")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df["lever"], x=df["down"], orientation="h", name="−10%", marker_color="#BAB0AC"))
    fig.add_trace(go.Bar(y=df["lever"], x=df["up"], orientation="h", name="+10% (초록 = 이익 증가, 빨강 = 감소)",
                         marker_color=["#59A14F" if v >= 0 else "#E15759" for v in df["up"]]))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="1년 동안 남는 돈 변화 (원)")
    return _layout(fig, "10% 개선했을 때 남는 돈 변화", 80 + 40 * len(df))


def meta_target_bars(targets: pd.DataFrame, selected):
    df = targets.sort_values("rel_cpa")
    colors = [CUR if t in selected else "#BAB0AC" for t in df["target"]]
    fig = go.Figure(go.Bar(
        x=df["target"], y=df["rel_cpa"], marker_color=colors,
        error_y=dict(type="data", symmetric=False, array=df["high"] - df["rel_cpa"], arrayminus=df["rel_cpa"] - df["low"]),
        customdata=df["purchases"], hovertemplate="%{x}<br>상대 CPA %{y:.2f}배<br>구매 %{customdata}건<extra></extra>"))
    fig.add_hline(y=1.0, line_dash="dot", annotation_text="전체 평균 = 1")
    fig.update_yaxes(title="구매 1건 비용 (평균 = 1, 막대 끝 선은 오차 범위)")
    return _layout(fig, "메타: 연령·성별마다 구매 1건 얻는 비용 (Kaggle)", 300)


def payback(curve, cac, months=24):
    x = list(range(1, months + 1))
    fig = go.Figure(go.Scatter(x=x, y=curve[:months], mode="lines+markers", name="손님 1명이 남겨 준 돈 (누적)",
                               line=dict(color=MONEY_COLOR)))
    if cac:
        fig.add_hline(y=cac, line_dash="dash", line_color="#E15759", annotation_text=f"손님 1명 데려오는 비용 {cac:,.0f}원")
    fig.update_xaxes(title="첫 구매 후 개월", dtick=2)
    fig.update_yaxes(title="손님 1명이 남겨 준 돈 누적 (원)")
    return _layout(fig, "광고비 본전은 언제 찾을까? (손님 1명 기준)", 320)


def attribution_bars(table: pd.DataFrame, models: dict):
    """채널(행) × 모델(열) 기여 비중(%) 묶음 막대."""
    fig = go.Figure()
    colors = ["#4C78A8", "#F28E2B", "#E15759", "#76B7B2", "#59A14F"]
    for (key, label), color in zip(models.items(), colors):
        fig.add_trace(go.Bar(x=table.index, y=table[key], name=label, marker_color=color,
                             hovertemplate="%{x} · " + label + " %{y:.1f}%<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="배분된 기여 (%)")
    fig = _layout(fig, "모델별로 채널에 배분된 기여", 440)
    fig.update_layout(margin=dict(t=140), legend=dict(y=1.0))
    return fig


def options_bars(opts: pd.DataFrame):
    """⑥ 4개 선택지의 12개월 이익 증분."""
    df = opts.dropna(subset=["gain"]).iloc[::-1]
    colors = ["#BAB0AC" if d else ("#59A14F" if g >= 0 else "#E15759") for d, g in zip(df["disabled"], df["gain"])]
    fig = go.Figure(go.Bar(y=df["option"], x=df["gain"], orientation="h", marker_color=colors,
                           text=[f"{v / 1e4:+,.0f}만 원" for v in df["gain"]], textposition="auto"))
    fig.update_xaxes(title="1년 동안 남는 돈 증가 (원, 광고비·발송비를 뺀 뒤)")
    return _layout(fig, None, 60 + 50 * len(df))


def money_compare(labels, values, title=None):
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=[OPT, CUR][: len(labels)] + ["#BAB0AC"] * max(0, len(labels) - 2),
                           text=[f"{v / 1e4:+,.0f}만 원" for v in values], textposition="auto"))
    fig.update_yaxes(title="1년 동안 남는 돈 증가 (원)")
    return _layout(fig, title, 300)


def breakeven_map(g: dict):
    """손익분기 재구매율 지도: 판매가 × 1년 재구매 횟수. 초록 = 남음, 빨강 = 손해, 선 = 본전, 점 = 지금 내 위치."""
    z = np.sign(g["profit"]) * np.log1p(np.abs(g["profit"]) / 1_000)   # 크기 차이가 커서 로그로 눌러 색만 보이게
    fig = go.Figure(go.Heatmap(
        x=g["prices"], y=g["reps"], z=z, zmid=0, colorscale=[[0, "#c0392b"], [0.5, "#f4f1ea"], [1, "#2e9e5b"]], showscale=False,
        customdata=g["profit"], hovertemplate="판매가 %{x:,.0f}원 · 재구매 %{y:.1f}번<br>손님 1명당 %{customdata:,.0f}원<extra></extra>"))
    fig.add_trace(go.Scatter(x=g["prices"], y=g["boundary"], mode="lines", name="본전 선", line=dict(color="black", width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=[g["my_price"]], y=[g["my_rep"]], mode="markers+text", name="지금 내 위치", text=["지금"],
                             textposition="top center", marker=dict(size=14, color="white", line=dict(color="black", width=2))))
    fig.update_xaxes(title="판매가 (원)", tickformat=",")
    fig.update_yaxes(title="1년 동안 다시 사는 횟수", range=[0, float(g["reps"][-1])])
    return _layout(fig, height=380)
