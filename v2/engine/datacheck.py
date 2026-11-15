"""가상 데이터 점검 (T04): 가상 실제(sim) 숫자가 assumptions.yaml 범위대로 나왔는지 표로 보여 준다. 발표 10번 슬라이드용.

- 범위에서 TOLERANCE(5%)까지는 통과로 본다. 벗어나면 통과=False로 두고 그대로 보여 준다 (가정이 틀렸다는 뜻일 수 있음).
- 모드(mode) 열이 있으면 sim만 쓴다. 없으면 올린 데이터 전체를 쓴다.
"""
from typing import List, Optional, Tuple

import pandas as pd

from . import specs

COLUMNS = ["가정", "기대 범위", "관측값", "케이스", "통과"]
TOLERANCE = 0.05          # 범위 바깥 5%까지는 통과
SPEND_GAP_MAX = 0.10      # 예측(forecast)과 가상 실제(sim) 지출 차이 허용 10%
BRAND_KEYWORDS = ("소연베이크",)


def _in_range(v: float, low: float, high: float) -> bool:
    return low * (1 - TOLERANCE) <= v <= high * (1 + TOLERANCE)


def _row(name: str, expect: str, observed: str, case: str, ok: bool) -> dict:
    return {"가정": name, "기대 범위": expect, "관측값": observed, "케이스": case, "통과": bool(ok)}


def _won_range(low: float, high: float) -> str:
    return "{:,}~{:,}원 (±5% 여유)".format(int(low), int(high))


def _pct_range(low: float, high: float) -> str:
    return "{:.1f}~{:.1f}% (±5% 여유)".format(low * 100, high * 100)


def _use_mode(df: Optional[pd.DataFrame], mode: str) -> Optional[pd.DataFrame]:
    if df is None:
        return None
    if "mode" in df and (df["mode"] == mode).any():
        return df[df["mode"] == mode]
    return df


def _case_list(df: pd.DataFrame) -> List[Tuple[str, pd.DataFrame]]:
    if "case" not in df or df["case"].isna().all():
        return [("-", df)]
    return [(str(c), g) for c, g in df.groupby("case", sort=False)]


def _meta_rows(meta: pd.DataFrame) -> List[dict]:
    a = specs.assumptions()["meta"]
    alias = a["target_alias"]
    rows = []
    for case, g in _case_list(meta):
        for (obj, target), h in g.groupby(["campaign_objective", "target"], sort=False):
            spend, imp = h["spend"].sum(), h["impressions"].sum()
            if imp <= 0:
                continue
            cpm = spend / imp * 1000
            if obj == "트래픽":
                r, label = a["cpm"]["traffic"], "메타 CPM (트래픽)"
            elif alias.get(target) == "넓게":
                r, label = a["cpm"]["awareness_broad"], "메타 CPM (인지도·넓은 타겟)"
            else:
                r, label = a["cpm"]["awareness_narrow"], "메타 CPM (인지도·좁은 타겟)"
            rows.append(_row("{} [근거 {}]".format(label, r["grade"]), _won_range(r["low"], r["high"]),
                             "{:,}원".format(int(round(cpm))), case, _in_range(cpm, r["low"], r["high"])))
            if obj == "트래픽" and "link_clicks" in h:
                ctr = h["link_clicks"].sum() / imp
                lo, hi = 0.010, 0.020  # assumptions.yaml link_ctr 근거: AMPM 이커머스 평균 1.0~2.0%
                rows.append(_row("메타 링크 클릭률 [근거 {}]".format(a["link_ctr"]["grade"]), _pct_range(lo, hi),
                                 "{:.2f}%".format(ctr * 100), case, _in_range(ctr, lo, hi)))
    return rows


def _naver_rows(naver: pd.DataFrame, brand: Tuple[str, ...]) -> List[dict]:
    a = specs.assumptions()["naver"]
    rows = []
    for case, g in _case_list(naver[~naver["keyword"].isin(brand)]):
        clicks, imp, cost = g["clicks"].sum(), g["impressions"].sum(), g["cost"].sum()
        if clicks > 0:
            cpc = cost / clicks
            rows.append(_row("네이버 클릭당 비용 [근거 {}]".format(a["cpc"]["grade"]),
                             _won_range(a["cpc"]["low"], a["cpc"]["high"]),
                             "{:,}원".format(int(round(cpc))), case, _in_range(cpc, a["cpc"]["low"], a["cpc"]["high"])))
        if imp > 0:
            ctr = clicks / imp
            rows.append(_row("네이버 클릭률 [근거 {}]".format(a["ctr"]["grade"]),
                             _pct_range(a["ctr"]["low"], a["ctr"]["high"]),
                             "{:.2f}%".format(ctr * 100), case, _in_range(ctr, a["ctr"]["low"], a["ctr"]["high"])))
    return rows


def _spend_by_case(meta: Optional[pd.DataFrame], naver: Optional[pd.DataFrame], mode: str) -> dict:
    out = {}
    for df, col in ((meta, "spend"), (naver, "cost")):
        if df is None or "mode" not in df or "case" not in df:
            continue
        s = df[df["mode"] == mode].groupby("case")[col].sum()
        for case, v in s.items():
            out[case] = out.get(case, 0.0) + float(v)
    return out


def _gap_rows(meta: Optional[pd.DataFrame], naver: Optional[pd.DataFrame]) -> List[dict]:
    fc, sim = _spend_by_case(meta, naver, "forecast"), _spend_by_case(meta, naver, "sim")
    rows = []
    for case in fc:
        if case in sim and fc[case] > 0:
            gap = sim[case] / fc[case] - 1
            rows.append(_row("예측 대비 실제 지출 차이", "±{:.0f}% 이내".format(SPEND_GAP_MAX * 100),
                             "{:+.1f}%".format(gap * 100), case, abs(gap) <= SPEND_GAP_MAX))
    return rows


def check(bundle, brand_keywords: Tuple[str, ...] = BRAND_KEYWORDS) -> pd.DataFrame:
    """가정 vs 관측 표. 열: 가정, 기대 범위, 관측값, 케이스, 통과."""
    meta_all, naver_all = bundle.get("meta_daily"), bundle.get("naver_daily")
    rows = []
    meta, naver = _use_mode(meta_all, "sim"), _use_mode(naver_all, "sim")
    if meta is not None and len(meta):
        rows += _meta_rows(meta)
    if naver is not None and len(naver):
        rows += _naver_rows(naver, brand_keywords)
    rows += _gap_rows(meta_all, naver_all)
    return pd.DataFrame(rows, columns=COLUMNS)
