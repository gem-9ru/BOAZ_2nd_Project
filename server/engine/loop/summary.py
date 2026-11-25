"""1 실측 요약: 세트별 지출·노출·클릭·도착과 비율 (희수 4장 지표 정의), 노출 위치별 지출."""
from typing import Dict, Optional

COUNTS = ("spend", "impressions", "link_clicks", "landing_page_views")


def _div(a: float, b: float, k: float = 1.0) -> Optional[float]:
    return float(a / b * k) if b else None


def arm(name: str, spend: float, impressions: float, link_clicks: float, landing_page_views: float) -> Dict:
    """세트 하나의 합계와 비율. 다른 모듈은 이 dict만 받는다."""
    return {
        "name": name, "spend": float(spend), "impressions": float(impressions),
        "link_clicks": float(link_clicks), "landing_page_views": float(landing_page_views),
        "cpm": _div(spend, impressions, 1000), "ctr": _div(link_clicks, impressions),
        "cpc": _div(spend, link_clicks), "click_to_visit": _div(landing_page_views, link_clicks),
        "visits_per_1000won": _div(landing_page_views, spend, 1000), "cost_per_visit": _div(spend, landing_page_views),
    }


def run(bundle) -> Dict:
    from ..analyze import placement_label   # 보고서와 같은 한국어 이름

    daily = bundle.tables["meta_daily"].df
    cols = [c for c in COUNTS if c in daily.columns]
    sums = daily.groupby("adset")[cols].sum()
    arms = [arm(str(n), *(float(sums.loc[n].get(c, 0.0)) for c in COUNTS)) for n in sorted(sums.index)]
    # AN-05 기간 토글: 하루에 가장 많이 써 본 돈 (그보다 많이 하루에 쓰면 '가설')
    if "spend" in daily.columns and "date" in daily.columns:
        per_day = daily.groupby(["adset", "date"])["spend"].sum().groupby(level=0).max()
        for a in arms:
            a["daily_max"] = float(per_day.get(a["name"], 0.0))

    placements, by_set = [], []
    if "meta_placement" in bundle.tables:
        p = bundle.tables["meta_placement"].df.groupby("placement")[["spend", "impressions", "link_clicks"]].sum()
        total = float(p["spend"].sum()) or 1.0
        for name, r in p.sort_values("spend", ascending=False).iterrows():
            placements.append({"placement": str(name), "label": placement_label(str(name)), "spend": float(r["spend"]),
                               "share": float(r["spend"]) / total, "impressions": float(r["impressions"]),
                               "link_clicks": float(r["link_clicks"]), "ctr": _div(r["link_clicks"], r["impressions"])})
        # v4.2 AN-04 노출 위치별 탭: 세트 × 노출 위치 칸
        q = bundle.tables["meta_placement"].df
        if "adset" in q.columns:
            g = q.groupby(["adset", "placement"])[["spend", "impressions", "link_clicks"]].sum()
            set_total = q.groupby("adset")["spend"].sum()
            for (aset, name), r in g.sort_values("spend", ascending=False).iterrows():
                by_set.append({"adset": str(aset), "placement": str(name), "label": placement_label(str(name)),
                               "spend": float(r["spend"]), "share": float(r["spend"]) / (float(set_total[aset]) or 1.0),
                               "impressions": float(r["impressions"]), "link_clicks": float(r["link_clicks"]),
                               "ctr": _div(r["link_clicks"], r["impressions"])})
    return {"arms": arms, "placements": placements, "placements_by_set": by_set}
