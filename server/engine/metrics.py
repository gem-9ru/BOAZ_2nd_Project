"""지표 계산 (T03): 검사된 표 한 케이스 → 진단 규칙이 읽는 숫자.

모든 비율은 원래 숫자(지출·노출·클릭·주문)를 다시 합쳐서 계산한다. 리포트의 비율 열은 쓰지 않는다.
지표에 필요한 데이터가 없으면 그 지표는 None (규칙이 '데이터 없음'으로 건너뜀).
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from . import effect as E
from . import specs

DEFAULT_BUDGET = 300000
MIN_KEYWORD_CLICKS = 30


@dataclass
class Context:
    """사장님 계획에서 오는 값 (없으면 None)."""
    budget: Optional[float] = DEFAULT_BUDGET
    margin_per_order: Optional[float] = None
    start: Optional[pd.Timestamp] = None
    end: Optional[pd.Timestamp] = None
    target_sizes: Dict[str, float] = field(default_factory=dict)   # 광고 세트 타겟 이름 → 실효 타겟 크기


# 문장에 숫자를 넣을 때의 모양
PCT = {"budget_use", "an_click_share", "ig_spend_share", "saturation_max", "ctr_drop_max", "link_ctr",
       "visit_per_click", "cvr_meta", "cpc_rise", "naver_ctr", "corrected_lift", "naive_lift"}
WON = {"lastclick_cac", "est_cac", "meta_cpc_avg", "naver_daily_spend", "meta_daily_with_leftover", "margin_per_order",
       "total_spend", "meta_spend", "naver_spend"}
ONE_DEC = {"weekly_freq_max", "awareness_weekly_freq_min", "hidden_ratio", "segment_lift"}


def fmt(name: str, v) -> str:
    if v is None or (isinstance(v, float) and v != v):   # None·NaN은 '-'
        return "-"
    if isinstance(v, str):
        return v
    if name in PCT:
        return f"{v * 100:.1f}%" if abs(v) < 0.1 else f"{v * 100:.0f}%"
    if name in WON:
        return f"{round(v):,}"
    if name in ONE_DEC:
        return f"{v:.2f}" if v < 1 else f"{v:.1f}"
    if isinstance(v, float):
        return f"{v:,.0f}"
    return str(v)


def _won10(x: float) -> int:
    return int(round(x / 10.0)) * 10


def _target_size(label: Optional[str], ctx: Context) -> Optional[float]:
    if not label:
        return None
    if label in ctx.target_sizes:
        return ctx.target_sizes[label]
    a = specs.assumptions()["meta"]
    key = a["target_alias"].get(label, label)
    t = a["effective_target"].get(key)
    return float(t["value"]) if t else None


def _adset_frames(meta: pd.DataFrame):
    for adset, g in meta.groupby("adset"):
        yield adset, g.sort_values("date")


def _weekly_freq(g: pd.DataFrame) -> Optional[float]:
    days = g["date"].nunique()
    if days == 0:
        return None
    if "frequency_cum" in g and g["frequency_cum"].notna().any():
        f = g["frequency_cum"].max()
    elif "reach_cum" in g and g["reach_cum"].max() > 0:
        f = g["impressions"].sum() / g["reach_cum"].max()
    else:
        return None
    return float(f / (days / 7.0))


def _first_last_week(g: pd.DataFrame, num: str, den: str) -> Optional[tuple]:
    if g["date"].nunique() < 14 or num not in g or den not in g:
        return None
    d0, d1 = g["date"].min(), g["date"].max()
    first = g[g["date"] < d0 + pd.Timedelta(days=7)]
    last = g[g["date"] > d1 - pd.Timedelta(days=7)]
    if first[den].sum() <= 0 or last[den].sum() <= 0:
        return None
    return first[num].sum() / first[den].sum(), last[num].sum() / last[den].sum()


def case_metrics(bundle, ctx: Optional[Context] = None) -> Dict[str, object]:
    """bundle: ingest.Bundle (케이스·구분 하나로 고른 것)."""
    ctx = ctx or Context()
    m: Dict[str, object] = {}
    meta = bundle.get("meta_daily")
    place = bundle.get("meta_placement")
    naver = bundle.get("naver_daily")
    store = bundle.get("store_daily")
    survey = bundle.get("survey")

    meta_spend = float(meta["spend"].sum()) if meta is not None and len(meta) else 0.0
    naver_spend = float(naver["cost"].sum()) if naver is not None and len(naver) else 0.0
    total = meta_spend + naver_spend
    m.update(meta_spend=meta_spend, naver_spend=naver_spend, total_spend=total)
    m["budget_use"] = total / ctx.budget if ctx.budget and total > 0 else None

    # 예산 옮기기용
    if naver is not None and naver_spend > 0:
        days = naver.loc[naver["cost"] > 0, "date"].nunique() or 30
        m["naver_daily_spend"] = _won10(naver_spend / days)
        leftover = (ctx.budget or total) - naver_spend
        m["meta_daily_with_leftover"] = _won10(max(leftover, 0) / 30) if leftover > 0 else None

    # ── 메타 ──
    if meta is not None and len(meta):
        freqs, aw, drops, sats = [], [], [], []
        for adset, g in _adset_frames(meta):
            wf = _weekly_freq(g)
            if wf is not None:
                freqs.append(wf)
                if "campaign_objective" in g and (g["campaign_objective"] == "인지도").any():
                    aw.append(wf)
            fl = _first_last_week(g, "link_clicks", "impressions") if "link_clicks" in g else None
            if fl and fl[0] > 0:
                drops.append(1 - fl[1] / fl[0])
            size = _target_size(g["target"].iloc[0] if "target" in g else None, ctx)
            if size and "reach_cum" in g and g["reach_cum"].notna().any():
                sats.append(float(g["reach_cum"].max() / size))
        m["weekly_freq_max"] = max(freqs) if freqs else None
        m["awareness_weekly_freq_min"] = min(aw) if aw else None
        m["ctr_drop_max"] = max(drops) if drops else None
        m["saturation_max"] = max(sats) if sats else None
        if "link_clicks" in meta and meta["link_clicks"].sum() > 0:
            clicks = float(meta["link_clicks"].sum())
            m["link_clicks"] = clicks
            # 클릭률·클릭 비용은 트래픽 광고 세트만 (인지도 광고는 원래 클릭이 적어서 섞으면 잘못 걸림)
            traffic = meta[meta["campaign_objective"] != "인지도"] if "campaign_objective" in meta else meta
            if traffic["link_clicks"].sum() > 0 and traffic["impressions"].sum() > 0:
                m["link_ctr"] = float(traffic["link_clicks"].sum() / traffic["impressions"].sum())
                m["meta_cpc_avg"] = _won10(traffic["spend"].sum() / traffic["link_clicks"].sum())
            daily = traffic.groupby("date")[["spend", "link_clicks"]].sum().reset_index()
            fl = _first_last_week(daily, "spend", "link_clicks")
            m["cpc_rise"] = (fl[1] / fl[0] - 1) if fl else None

    # ── 노출 위치 ──
    if place is not None and len(place):
        clicks = place["link_clicks"].sum()
        spend = place["spend"].sum()
        an = place["placement"].str.contains("Audience Network", case=False, na=False)
        ig = place["placement"].str.contains("Instagram", case=False, na=False)
        m["an_click_share"] = float(place.loc[an, "link_clicks"].sum() / clicks) if clicks > 0 else None
        m["ig_spend_share"] = float(place.loc[ig, "spend"].sum() / spend) if spend > 0 else None

    # ── 네이버 ──
    if naver is not None and len(naver) and naver_spend > 0:
        m["naver_ctr"] = float(naver["clicks"].sum() / naver["impressions"].sum()) if naver["impressions"].sum() > 0 else None
        if "store_orders" in naver:
            kw = naver.groupby("keyword")[["clicks", "store_orders"]].sum()
            dead = kw[(kw["clicks"] >= MIN_KEYWORD_CLICKS) & (kw["store_orders"] < 0.5)]
            m["naver_dead_keywords"] = len(dead)
            m["naver_dead_keyword_names"] = ", ".join(dead.index.tolist()) if len(dead) else None

    # ── 스토어·효과 ──
    period = (ctx.start, ctx.end) if ctx.start is not None and ctx.end is not None else E.ad_period(bundle)
    if store is not None and len(store) and period:
        start, end = period
        eff = E.estimate(store, start, end, survey)
        m["effect"] = eff
        m["naive_lift"], m["corrected_lift"] = eff.naive_lift, eff.corrected_lift
        rend = end + pd.Timedelta(days=E.RESIDUAL_DAYS)
        win = store[(store["date"] >= start) & (store["date"] <= rend)]
        lc = float(win["orders_meta"].sum() + win["orders_naver_ad"].sum())
        m["lastclick_orders"] = lc
        m["est_orders"] = lc + eff.extra_brand_orders
        if "sessions_meta" in win and win["sessions_meta"].sum() > 0:
            m["meta_sessions"] = float(win["sessions_meta"].sum())
            m["cvr_meta"] = float(win["orders_meta"].sum() / win["sessions_meta"].sum())
            if m.get("link_clicks"):
                m["visit_per_click"] = float(win["sessions_meta"].sum() / m["link_clicks"])
        if total > 0 and lc > 0:
            m["lastclick_cac"] = total / lc
        if total > 0 and m["est_orders"] > 0:
            m["est_cac"] = total / m["est_orders"]
        if m.get("lastclick_cac") and m.get("est_cac"):
            m["hidden_ratio"] = m["lastclick_cac"] / m["est_cac"]
        if ctx.margin_per_order and m.get("est_cac"):
            m["margin_per_order"] = ctx.margin_per_order
            m["margin_gap"] = m["est_cac"] - ctx.margin_per_order
    return m
