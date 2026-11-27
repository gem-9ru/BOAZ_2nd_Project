"""분석 루프 전체를 한 번에: 업로드한 메타 결과 파일(Bundle) → 화면 7블록에 쓸 dict."""
from typing import Dict, Optional

from . import alerts as alerts_mod, backtest, baseline, check, funnel, matrix, next_step, posterior, summary, verdict
from .. import analyze as diagnose


def run(bundle, seed: int = 0, settings: Optional[Dict] = None) -> Dict:
    c = check.run(bundle)
    s = summary.run(bundle)
    arms = s["arms"]
    v = None
    replay = []
    # 한 세트가 한 번도 안 나갔으면(지출·노출 0, 예: 심사 거절) 판정하지 않는다 — 노출 0인 세트가 '확실히 낫다'로 나오고
    # 다음 세팅 표가 빈 CPM으로 나누다 500이 났다 (감사 5)
    if len(arms) >= 2 and all(x["spend"] > 0 and x["impressions"] > 0 for x in arms[:2]):
        a, b = arms[0], arms[1]
        v = verdict.compare(a, b, seed=seed)
        v["min_budget"] = verdict.min_budget(a, seed=seed)
        replay = verdict.daily_replay(bundle, a["name"], b["name"])
    al = alerts_mod.run(bundle, c, s, settings=settings)
    if v is not None:
        k = {x["kind"] for x in al}
        v = verdict.apply_caps(v, small_sample="small_sample" in k, spend_gap="spend_gap" in k)
        replay = verdict.cap_replay(replay, v)
    m = matrix.run(s, c, v, al, settings=settings)
    diag = diagnose.analyze(bundle)
    return {
        "settings": dict(settings or {}),
        "alerts": al,
        "blocked": alerts_mod.blocked(al),
        "matrix": m,
        "backtest": backtest.run(bundle, seed=seed),
        "check": c,
        "summary": s,
        "intervals": {x["name"]: posterior.intervals(x, seed=seed) for x in arms},
        "placements": posterior.shrink(s["placements"]),
        "placements_by_set": posterior.shrink(s.get("placements_by_set") or []) if s.get("placements_by_set") else [],
        "funnel": funnel.run(arms),
        "verdict": v,
        "baseline": baseline.run(arms),   # 세트 1개: 기준값과 비교한 신호 (축소안 v5 ①b)
        "replay": replay,
        "diagnosis": {"status": diag["status"], "finding": diag["finding"]},
        "next": next_step.run(v, diag, m["change"]),
    }
