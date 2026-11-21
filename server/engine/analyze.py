"""③ 분석: 결과 묶음 → 진단 하나 · 바꿀 칸 · 예상 범위 · 보고서 차트 데이터.

판정 순서 (설계서 7장, 계획 Task 6):
1. 규칙을 깔때기 순서로 보고 처음 걸린 것 하나를 고른다 (판단 보류 규칙은 빼고).
2. 그 규칙의 지표가 비율이면 베타 구간이 기준값을 걸칠 때 '판단 보류'로 바꾼다.
3. 걸린 규칙이 없고 링크 클릭이 100 미만이면 rule.hold_small_sample로 '판단 보류'.
4. 그 외는 '정상'.
예상 수치는 항상 범위 + 근거 등급. 한 숫자로 말하지 않는다.
"""
from typing import Dict, List, Optional, Tuple

import pandas as pd

from . import diagnose, metrics, specs
from .ingest import Bundle
from .uncertainty import beta_interval, prob_better, straddles

HOLD_RULE = "rule.hold_small_sample"
FUNNEL_ORDER = ["노출", "클릭", "도착", "구매", "예산", "측정"]
LABELS = {"link_ctr": "링크 클릭률", "visit_rate": "클릭 뒤 도착률", "an_click_share": "Audience Network 클릭 비중"}
MORE_DAYS_FACTOR = 2     # '기간 연장'이면 표본이 두 배쯤 모인다고 보고 범위를 다시 계산


def _counts(daily: pd.DataFrame) -> Dict[str, float]:
    return {c: float(daily[c].sum()) if c in daily.columns else 0.0
            for c in ("impressions", "link_clicks", "landing_page_views", "spend")}


def _ratio_counts(metric: str, m: dict, n: Dict[str, float]) -> Optional[Tuple[float, float]]:
    """비율 지표 → (성공, 시행). 모르는 지표면 None."""
    if metric == "link_ctr":
        trials = n["impressions"]
        return (m.get("link_ctr") or 0) * trials, trials
    if metric == "visit_rate":
        return n["landing_page_views"], n["link_clicks"]
    if metric == "an_click_share":
        trials = m.get("link_clicks") or n["link_clicks"]
        return (m.get("an_click_share") or 0) * trials, trials
    return None


def _interval(metric: str, m: dict, n: Dict[str, float], scale: float = 1) -> Optional[List[float]]:
    rc = _ratio_counts(metric, m, n)
    if not rc or rc[1] <= 0:
        return None
    lo, hi = beta_interval(rc[0] * scale, rc[1] * scale)
    return [round(lo, 5), round(hi, 5)]


def _rule(rule_id: str) -> dict:
    return next(r for r in specs.rules() if r["id"] == rule_id)


def _changes(f: diagnose.Finding) -> List[dict]:
    return [{"field_id": c.field_id, "label": c.label, "new": str(c.new), "note": c.note} for c in f.changes]


def _charts(b: Bundle) -> dict:
    daily = b.tables["meta_daily"].df
    n = _counts(daily)
    per_day = []
    for date, g in daily.groupby(daily["date"].dt.strftime("%Y-%m-%d")):
        imp, clk, spend = g["impressions"].sum(), g.get("link_clicks", pd.Series(dtype=float)).sum(), g["spend"].sum()
        per_day.append({"date": date, "spend": round(float(spend)),
                        "ctr": round(float(clk / imp), 5) if imp > 0 else None,
                        "cpm": round(float(spend / imp * 1000)) if imp > 0 else None})
    place = []
    if "meta_placement" in b.tables:
        p = b.tables["meta_placement"].df.groupby("placement")[["spend", "link_clicks"]].sum().reset_index()
        place = [{"placement": r.placement, "spend": round(float(r.spend)), "link_clicks": round(float(r.link_clicks))}
                 for r in p.sort_values("spend", ascending=False).itertuples()]
    return {"funnel": {"impressions": round(n["impressions"]), "link_clicks": round(n["link_clicks"]),
                       "landing_page_views": round(n["landing_page_views"])},
            "daily": per_day, "placement": place}


def _ab(daily: pd.DataFrame) -> Optional[dict]:
    sets = sorted(daily["adset"].dropna().unique())
    if len(sets) != 2 or not {"link_clicks", "impressions"} <= set(daily.columns):
        return None
    g = daily.groupby("adset")[["link_clicks", "impressions"]].sum()
    a, b = sets
    return {"a": a, "b": b, "prob_b_better": round(prob_better(g.loc[a, "link_clicks"], g.loc[a, "impressions"],
                                                               g.loc[b, "link_clicks"], g.loc[b, "impressions"]), 3)}


def _hold_expect(m: dict, n: Dict[str, float], ab: Optional[dict]) -> Optional[dict]:
    """판단 보류: 지금 범위 vs 같은 비율로 표본이 두 배일 때 범위. 표본이 는다는 가정이 들어가 '가설'."""
    cur = _interval("link_ctr", m, n)
    if not cur:
        return None
    return {"metric": "link_ctr", "label": LABELS["link_ctr"], "current": cur,
            "expected": _interval("link_ctr", m, n, scale=MORE_DAYS_FACTOR), "grade": "hypothesis",
            "prob_better": ab["prob_b_better"] if ab else None}


def analyze(b: Bundle, metrics_override: Optional[dict] = None) -> dict:
    daily = b.tables["meta_daily"].df
    n = _counts(daily)
    m = metrics.case_metrics(b)
    m.update(metrics_override or {})
    findings = diagnose.evaluate(m)
    ab = _ab(daily)

    fired = sorted((f for f in findings if f.status == "fired" and f.id != HOLD_RULE),
                   key=lambda f: FUNNEL_ORDER.index(f.funnel) if f.funnel in FUNNEL_ORDER else len(FUNNEL_ORDER))
    base = {"charts": _charts(b), "ab": ab}

    if fired:
        f = fired[0]
        rule = _rule(f.id)
        cond = (rule.get("when") or [{}])[0]
        iv = _interval(cond.get("metric", ""), m, n)
        if iv and straddles(iv[0], iv[1], float(cond["value"])):
            # 기준을 걸쳐 단정할 수 없음 → 그 규칙의 변경을 밀지 않고 '기간 늘리기'로 (설계서 14장)
            hold_rule = next(x for x in findings if x.id == HOLD_RULE) if any(x.id == HOLD_RULE for x in findings) else None
            changes = _changes(hold_rule) if hold_rule and hold_rule.status == "fired" else [
                {"field_id": "meta.adset.end_date", "label": "종료 날짜", "new": "7일 더 연장",
                 "note": "숫자가 더 모이면 판단할 수 있어요"}]
            return {**base, "status": "hold",
                    "finding": {"id": f.id, "title": f.title, "funnel": f.funnel,
                                "message": f"{f.message} 다만 숫자가 적어 기준에 걸쳐 있어요. 아직 단정하기 일러요."},
                    "changes": changes, "expect": _hold_expect(m, n, ab)}
        status = "fired"
        expect = None
        spec = rule.get("expect")
        if spec:
            cur = _interval(spec["metric"], m, n)
            if cur:
                expect = {"metric": spec["metric"], "label": LABELS.get(spec["metric"], spec["metric"]), "current": cur,
                          "expected": [round(cur[0] * (1 + spec["low"]), 5), round(cur[1] * (1 + spec["high"]), 5)],
                          "prob_better": None, "grade": spec.get("grade", "hypothesis")}
        return {**base, "status": status, "finding": {"id": f.id, "title": f.title, "funnel": f.funnel, "message": f.message},
                "changes": _changes(f), "expect": expect}

    hold = next((f for f in findings if f.id == HOLD_RULE and f.status == "fired"), None)
    if hold:
        expect = _hold_expect(m, n, ab)
        return {**base, "status": "hold", "finding": {"id": hold.id, "title": hold.title, "funnel": hold.funnel,
                                                      "message": hold.message},
                "changes": _changes(hold), "expect": expect}

    return {**base, "status": "normal",
            "finding": {"id": "normal", "title": "큰 문제는 없어요", "funnel": "",
                        "message": "깔때기에서 걸린 문제가 없어요. 같은 설정으로 계속 돌리며 지켜보세요."},
            "changes": [], "expect": None}
