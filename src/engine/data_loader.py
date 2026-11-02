"""엔진 기본값 로더: data/processed/ 산출물이 있으면 그것을, 없으면 defaults.py 값을 쓴다.

| 파일 | 기대 컬럼 | 담당 |
|---|---|---|
| data/processed/ga4_funnel.csv (없으면 data/raw/ga4/ga4_funnel.csv) | medium, visit_users, view_users, cart_users, checkout_users, purchase_users | B |
| data/processed/fb_target_metrics.csv | target, rel_cpa, purchases | A |
"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from . import defaults as D

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
GA4_ALL = "전체"


def _ga4_table() -> Optional[pd.DataFrame]:
    for path in (PROCESSED / "ga4_funnel.csv", ROOT / "data" / "raw" / "ga4" / "ga4_funnel.csv"):
        if path.exists():
            df = pd.read_csv(path)
            if set(D.GA4_EVENTS) <= set(df.columns):
                return df
    return None


def ga4_mediums() -> List[str]:
    df = _ga4_table()
    if df is None or "medium" not in df.columns:
        return []
    return [GA4_ALL] + sorted(df["medium"].dropna().unique().tolist())


def funnel_steps(medium: str = GA4_ALL) -> Tuple[List[Tuple[str, float]], str]:
    """(단계 목록, 출처 설명). 첫 단계 '랜딩 도착'은 GA4에 없어 기본값 유지."""
    df = _ga4_table()
    if df is None:
        return list(D.FUNNEL_STEPS), "기본값 (GA4 파일 없음)"
    if medium != GA4_ALL and "medium" in df.columns:
        df = df[df["medium"] == medium]
    s = df[D.GA4_EVENTS].sum()
    if s.iloc[0] <= 0:
        return list(D.FUNNEL_STEPS), "기본값"
    rates = [float(s.iloc[i + 1] / s.iloc[i]) if s.iloc[i] > 0 else 0.0 for i in range(len(D.GA4_EVENTS) - 1)]
    steps = [D.FUNNEL_STEPS[0]] + [(name, r) for (name, _), r in zip(D.FUNNEL_STEPS[1:], rates)]
    return steps, f"GA4 샘플 ({medium}, 사용자 {int(s.iloc[0]):,}명)"


def meta_targets() -> pd.DataFrame:
    """타깃별 상대 CPA 배수 + 95% 구간 (구매 건수를 포아송으로 보고 근사)."""
    path = PROCESSED / "fb_target_metrics.csv"
    if path.exists():
        df = pd.read_csv(path)[["target", "rel_cpa", "purchases"]]
        source = "fb_target_metrics.csv"
    else:
        df = pd.DataFrame([(k, v[0], v[1]) for k, v in D.META_TARGETS.items()],
                          columns=["target", "rel_cpa", "purchases"])
        source = "Kaggle (defaults.py)"
    half = 1.96 / np.sqrt(df["purchases"].clip(lower=1))
    df["low"] = df["rel_cpa"] * np.exp(-half)
    df["high"] = df["rel_cpa"] * np.exp(half)
    df["source"] = source
    return df.reset_index(drop=True)


def target_multiplier(targets: List[str]) -> float:
    """고른 타깃들의 상대 CPA 배수 (구매 건수 가중). 아무것도 안 고르면 1.0 (전체 평균)."""
    if not targets:
        return 1.0
    df = meta_targets()
    d = df[df["target"].isin(targets)]
    if d.empty:
        return 1.0
    return float(np.average(d["rel_cpa"], weights=d["purchases"]))


def keyword_tier(monthly_qc: float) -> str:
    for threshold, name in D.KEYWORD_TIERS:
        if monthly_qc >= threshold:
            return name
    return D.KEYWORD_TIERS[-1][1]


def describe_sources() -> Dict[str, str]:
    return {
        "ga4": "data/processed/ga4_funnel.csv" if (PROCESSED / "ga4_funnel.csv").exists() else "data/raw/ga4/ga4_funnel.csv",
        "meta": meta_targets()["source"].iloc[0],
    }
