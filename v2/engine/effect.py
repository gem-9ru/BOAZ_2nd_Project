"""효과 확인 (T11): 시즌을 뺀 브랜드 검색 변화 + '광고 보고 나중에 검색해서 산 주문' 추정 + 설문 범위.

왜 필요한가 (다정 EDA, 11/12)
- 광고 전후만 비교하면 연말 시즌 때문에 광고를 안 해도 늘어 보인다 (C0: 전후 +31%).
- 스토어 유입 경로(마지막 클릭)로만 보면 광고를 보고 나중에 브랜드를 검색해서 산 주문이 빠진다.

방법
- 기준선: 광고 전 기간의 브랜드 검색 평균 × (광고 기간 카테고리 검색 ÷ 광고 전 카테고리 검색)
  → 광고와 상관없는 카테고리 검색 추세로 '광고가 없었다면'을 예상한다.
- 광고 덕분 브랜드 검색 = 실제 − 기준선 (0보다 작으면 0)
- 광고 덕분 검색 주문 = 광고 덕분 브랜드 검색 × 광고 기간 브랜드 검색의 주문 비율
"""
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd

RESIDUAL_DAYS = 7          # 광고가 끝난 뒤에도 남는 효과를 보는 날 수 (다정 가상 데이터와 같게)
AD_ANSWERS = ("인스타그램에서 본 광고", "네이버 검색")   # 설문에서 '광고 덕분'으로 볼 수 있는 응답


@dataclass
class Effect:
    start: pd.Timestamp
    end: pd.Timestamp
    naive_lift: Optional[float]          # 전후 비교 (시즌 포함)
    corrected_lift: Optional[float]      # 카테고리 검색으로 시즌을 뺀 변화
    extra_brand_search: float            # 광고 덕분 브랜드 검색 (추정)
    extra_brand_orders: float            # 광고 덕분 검색 주문 (추정)
    truth_brand_orders: Optional[float]  # 시뮬레이터 정답 (가상 데이터에만)
    survey_ad_share: Optional[Tuple[float, float]]  # 설문에서 광고 덕분 응답 비율 (낮게, 높게)
    grade: str = "D"


def ad_period(bundle) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
    """메타·네이버 표에 지출이 있는 첫날·마지막 날."""
    dates = []
    for name, spend in (("meta_daily", "spend"), ("naver_daily", "cost")):
        df = bundle.get(name)
        if df is not None and len(df) and spend in df:
            d = df.loc[df[spend].fillna(0) > 0, "date"]
            if len(d):
                dates += [d.min(), d.max()]
    return (min(dates), max(dates)) if dates else None


def estimate(store: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, survey: Optional[pd.DataFrame] = None) -> Effect:
    rend = end + pd.Timedelta(days=RESIDUAL_DAYS)
    base = store[store["date"] < start]
    win = store[(store["date"] >= start) & (store["date"] <= rend)]
    naive = corrected = None
    extra_search = extra_orders = 0.0
    if len(base) and len(win) and "brand_search" in store and base["brand_search"].mean() > 0:
        bb, wb = base["brand_search"].mean(), win["brand_search"].mean()
        naive = wb / bb - 1
        season = 1.0
        if "category_search" in store and base["category_search"].mean() > 0:
            season = win["category_search"].mean() / base["category_search"].mean()
        corrected = (wb / bb) / season - 1
        expected = bb * season * len(win)
        extra_search = max(0.0, win["brand_search"].sum() - expected)
        if "orders_brand_search" in store and win["brand_search"].sum() > 0:
            order_rate = win["orders_brand_search"].sum() / win["brand_search"].sum()
            extra_orders = extra_search * order_rate
    truth = None
    if "true_ad_brand_orders" in store and store["true_ad_brand_orders"].notna().any():
        truth = float(win["true_ad_brand_orders"].sum())
    share = None
    if survey is not None and len(survey) and survey["count"].sum() > 0:
        total = survey["count"].sum()
        ad = survey[survey["answer"].isin(AD_ANSWERS)]["count"].sum()
        insta_ad = survey[survey["answer"] == AD_ANSWERS[0]]["count"].sum()
        share = (insta_ad / total, ad / total)
    return Effect(start, end, naive, corrected, extra_search, extra_orders, truth, share)
