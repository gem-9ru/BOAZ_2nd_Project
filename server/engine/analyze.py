"""③ 분석: 결과 묶음 → 진단 하나 · 바꿀 칸 (분석 루프의 '이번에 알게 된 것'·다음 세팅에 쓴다).

판정 순서 (설계서 7장, 계획 Task 6):
1. 규칙을 깔때기 순서로 보고 처음 걸린 것 하나를 고른다 (판단 보류 규칙은 빼고).
2. 그 규칙의 지표가 비율이면 베타 구간이 기준값을 걸칠 때 '판단 보류'로 바꾼다.
3. 걸린 규칙이 없고 링크 클릭이 100 미만이면 rule.hold_small_sample로 '판단 보류'.
4. 그 외는 '정상'.
"""
from typing import Dict, List, Optional, Tuple

import pandas as pd

from . import diagnose, metrics, specs
from .ingest import Bundle
from .uncertainty import beta_interval, straddles

HOLD_RULE = "rule.hold_small_sample"
FUNNEL_ORDER = ["노출", "클릭", "도착", "구매", "예산", "측정"]


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


def analyze(b: Bundle, metrics_override: Optional[dict] = None) -> dict:
    daily = b.tables["meta_daily"].df
    n = _counts(daily)
    m = metrics.case_metrics(b)
    m.update(metrics_override or {})
    findings = diagnose.evaluate(m)

    fired = sorted((f for f in findings if f.status == "fired" and f.id != HOLD_RULE),
                   key=lambda f: FUNNEL_ORDER.index(f.funnel) if f.funnel in FUNNEL_ORDER else len(FUNNEL_ORDER))
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
            return {"status": "hold",
                    "finding": {"id": f.id, "title": f.title, "funnel": f.funnel,
                                "message": f"{f.message} 다만 숫자가 적어 기준에 걸쳐 있어요. 아직 단정하기 일러요."},
                    "changes": changes}
        return {"status": "fired", "finding": {"id": f.id, "title": f.title, "funnel": f.funnel, "message": f.message},
                "changes": _changes(f)}

    hold = next((f for f in findings if f.id == HOLD_RULE and f.status == "fired"), None)
    if hold:
        return {"status": "hold", "finding": {"id": hold.id, "title": hold.title, "funnel": hold.funnel,
                                              "message": hold.message},
                "changes": _changes(hold)}

    return {"status": "normal",
            "finding": {"id": "normal", "title": "큰 문제는 없어요", "funnel": "",
                        "message": "깔때기에서 걸린 문제가 없어요. 같은 설정으로 계속 돌리며 지켜보세요."},
            "changes": []}
