"""0 검증: 결과를 보기 전에 파일이 멀쩡한지부터 (희수 5장 ①②, Kohavi 외 2020).

- 합계 대조: 일자별 표의 합 = 노출 위치 표의 합 (지출·노출·링크 클릭)
- 게재 이상: 광고가 안 나간 날, 세트 사이 지출이 크게 다름
- 빠진 열: 랜딩 페이지 조회가 없으면 '도착'을 계산할 수 없음
"""
from typing import Dict, List

from ..specs import loop as _loop

TOTAL_METRICS = ("spend", "impressions", "link_clicks")
_ALERTS = _loop()["alerts"]
SKEW = _ALERTS["an_share_max"]   # 한 세트 지출의 이 비율 이상이 Audience Network로 가면 경고 (오븐로그 1차: 100%)


def _md(date) -> str:
    return f"{date.month}/{date.day}"


def run(bundle) -> Dict:
    daily = bundle.tables["meta_daily"].df
    place = bundle.tables["meta_placement"].df if "meta_placement" in bundle.tables else None
    adsets = sorted(daily["adset"].unique())

    totals: List[Dict] = []
    if place is not None:
        for m in TOTAL_METRICS:
            if m in daily.columns and m in place.columns:
                d, p = float(daily[m].sum()), float(place[m].sum())
                totals.append({"metric": m, "daily": d, "placement": p, "match": abs(d - p) <= max(1.0, _ALERTS["sum_mismatch"] * abs(d))})

    warnings: List[Dict] = []
    by_day = daily.groupby(["date", "adset"])[["spend", "impressions"]].sum().reset_index()
    for date, g in by_day.groupby("date"):
        off = g[(g["spend"] <= 0) & (g["impressions"] <= 0)]["adset"].tolist()
        if not off:
            continue
        if len(off) == len(adsets):
            who = "두 세트 모두" if len(adsets) == 2 else "모든 세트"
            warnings.append({"kind": "no_delivery", "date": str(date.date()), "text": f"{_md(date)} {who} 하루 종일 안 보여졌어요 → 관련 칸: 시작 시간 · 총예산",
                             "later": f"{_md(date)}은 광고가 안 나가서 비교에서 뺐어요"})
        else:
            warnings.append({"kind": "no_delivery", "date": str(date.date()), "text": f"{_md(date)}에 {', '.join(off)}만 안 보여졌어요 → 관련 칸: 시작 시간 · 총예산"})

    if place is not None and len(place):
        for name, g in place.groupby("adset"):
            total = float(g["spend"].sum())
            an = float(g[g["placement"].astype(str).str.contains("Audience Network", case=False)]["spend"].sum())
            if total > 0 and an / total >= SKEW:
                warnings.append({"kind": "placement_skew", "text": f"{name}: 자동 노출 위치가 돈의 {an / total:.0%}를 Audience Network(다른 앱 광고 자리)에 썼어요. 같은 설정도 회차마다 결과가 크게 달라질 수 있어요."})

    safety = [
        {"ok": True, "text": "모든 숫자는 메타 기여 기준(클릭 후 7일 또는 조회 후 1일)이에요."},
        {"ok": True, "text": "퍼널은 광고 관리자 숫자로 계산해요. 픽셀에 섞일 수 있는 팀·본인 방문은 넣지 않아요."},
    ]
    if len(adsets) >= 2:
        safety.append({"ok": False, "text": "두 세트를 동시에 돌렸다면 같은 사람을 두고 경쟁했을 수 있어요. 메타 'A/B 테스트'로 만들면 사람을 나눠서 보여 줘요."})

    missing: List[str] = []
    if "landing_page_views" not in daily.columns or float(daily["landing_page_views"].sum()) == 0:
        missing.append("랜딩 페이지 조회 열이 없어요. 내보낼 때 '랜딩 페이지 조회'를 넣어 주세요. (없으면 '도착'은 계산하지 못해요)")

    dates = sorted(daily["date"].unique())
    period = {"first": str(dates[0])[:10], "last": str(dates[-1])[:10]} if dates else None
    return {
        "period": period,
        "ok": not missing and all(t["match"] for t in totals),
        "read": {"days": int(daily["date"].nunique()), "adsets": len(adsets), "daily_rows": int(len(daily)),
                 "placement_rows": int(len(place)) if place is not None else 0},
        "totals": totals,
        "warnings": warnings,
        "safety": safety,
        "missing": missing,
    }
