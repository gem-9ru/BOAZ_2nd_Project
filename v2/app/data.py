"""느린 일(네이버 조회·엑셀 읽기·지표 계산)을 st.cache_data로 한 번만 하게 감싼다.

- 시장 조사는 live=False면 저장본(시연 캐시)만 쓴다. 키가 없어도 같은 화면이 나온다.
- 같은 입력이면 같은 결과라서 캐시해도 안전하다.
"""
from io import BytesIO
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from v2.engine import diagnose, ingest, market, metrics, naver_api


@st.cache_data(show_spinner=False)
def _market_saved(seeds: Tuple[str, ...]):
    """저장본(시연 캐시)만 쓰는 조회. 같은 입력이면 같은 결과라서 캐시해도 안전하다."""
    return market.build(list(seeds), online=False)


def market_report(seeds: Tuple[str, ...], live: bool):
    """내 손님 찾기 결과 (MarketReport 또는 None, 실패 문장 또는 None).

    실시간 조회는 st.cache_data에 넣지 않는다: 실패가 캐시되면 '다시 찾기'가 같은 실패를 돌려주고,
    실패 문장도 캐시 때문에 사라진다. (네이버 응답은 naver_api가 디스크에 따로 저장해 둔다.)
    실패 문장은 조회 직후에 바로 읽는다. 다음 호출이 성공하면 지워지기 때문이다.
    """
    if not live:
        return _market_saved(tuple(seeds)), None
    report = market.build(list(seeds), online=True)
    return report, naver_api.last_error()


@st.cache_data(show_spinner=False)
def demo_bundle() -> ingest.Bundle:
    return ingest.demo()


@st.cache_data(show_spinner=False)
def read_upload(files: Tuple[Tuple[str, bytes], ...]) -> ingest.Bundle:
    """올린 파일들(이름, 내용) → 결과 묶음. 엑셀 1개면 시트별로, 그 밖에는 CSV로 읽는다."""
    named = []
    for name, raw in files:
        buf = BytesIO(raw)
        buf.name = name
        named.append(buf)
    excel = [f for f in named if f.name.lower().endswith((".xlsx", ".xlsm"))]
    csvs = [f for f in named if f not in excel]
    bundle = ingest.read_excel(excel[0]) if excel else ingest.Bundle()
    if csvs:
        extra = ingest.read_csvs(csvs)
        bundle.problems += extra.problems
        for name, t in extra.tables.items():
            bundle.tables.setdefault(name, t)
    return bundle


@st.cache_data(show_spinner=False)
def demo_case(case: str, mode: str, start: pd.Timestamp, end: pd.Timestamp, budget: float,
              margin: Optional[float]) -> Tuple[dict, List[diagnose.Finding]]:
    return analyze(demo_bundle().select(case, mode), start, end, budget, margin)


def analyze(bundle: ingest.Bundle, start: Optional[pd.Timestamp], end: Optional[pd.Timestamp],
            budget: float, margin: Optional[float]) -> Tuple[dict, List[diagnose.Finding]]:
    """결과 묶음 → (지표, 진단 결과)."""
    ctx = metrics.Context(budget=budget, margin_per_order=margin or None, start=start, end=end)
    m = metrics.case_metrics(bundle, ctx)
    return m, diagnose.evaluate(m)
