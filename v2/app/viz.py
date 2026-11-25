"""화면 공용 차트: 파란 단색(#2F5D8A) + 회색, 라벨과 숫자를 같이 써서 색만으로 뜻을 전하지 않는다.
숫자는 엔진이 계산한 값만 받아서 그린다 (여기서 새로 만들지 않음)."""
from typing import Optional, Sequence

import plotly.graph_objects as go
import streamlit as st

PRIMARY, PRIMARY_LIGHT, GRAY, GRAY_DARK, TEXT = "#2F5D8A", "#8FA9C4", "#8A94A3", "#6B7280", "#2B3340"
CONFIG = {"displayModeBar": False}


def _base(fig: go.Figure, height: int = 240, title: Optional[str] = None) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40 if title else 10, b=10), title=title,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=TEXT, size=13), showlegend=False)
    return fig


def show(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, key=key, config=CONFIG, use_container_width=True)


def donut(labels: Sequence[str], values: Sequence[float], title: str, center: str = "", key: str = "donut") -> None:
    """예산 나눔 도넛: 조각마다 이름·금액·비율을 글자로 쓴다."""
    fig = go.Figure(go.Pie(labels=list(labels), values=list(values), hole=0.55, sort=False,
                           marker=dict(colors=[PRIMARY, GRAY, PRIMARY_LIGHT][:len(values)], line=dict(color="#FFFFFF", width=2)),
                           texttemplate="%{label}<br>%{value:,.0f}원 (%{percent})", textposition="outside"))
    _base(fig, 240, title)
    if center:
        fig.add_annotation(text=center, showarrow=False, font=dict(size=14, color=TEXT))
    fig.update_layout(margin=dict(l=40, r=40, t=44, b=10))
    show(fig, key)


def hbar(labels: Sequence[str], values: Sequence[float], texts: Sequence[str], colors: Sequence[str], title: str,
         key: str, height: int = 220) -> None:
    """가로 막대: 막대 끝에 값 글자."""
    fig = go.Figure(go.Bar(y=list(labels), x=list(values), orientation="h", marker_color=list(colors),
                           text=list(texts), textposition="outside", cliponaxis=False))
    _base(fig, height, title)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(visible=False, range=[0, max(values) * 1.35 if values and max(values) > 0 else 1])
    show(fig, key)
