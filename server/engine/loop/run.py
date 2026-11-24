"""분석 루프 전체를 한 번에: 업로드한 메타 결과 파일(Bundle) → 화면 7블록에 쓸 dict."""
from typing import Dict, Optional

from . import alerts as alerts_mod, backtest, check, funnel, matrix, next_step, posterior, summary, verdict
from .. import analyze as diagnose


def run(bundle, seed: int = 0, settings: Optional[Dict] = None) -> Dict:
    c = check.run(bundle)
    s = summary.run(bundle)
    arms = s["arms"]
    v = None
    replay = []
    if len(arms) >= 2:
        a, b = arms[0], arms[1]
        v = verdict.compare(a, b, seed=seed)
        v["min_budget"] = verdict.min_budget(a, seed=seed)
        replay = verdict.daily_replay(bundle, a["name"], b["name"])
    al = alerts_mod.run(bundle, c, s, settings=settings)
    if v is not None:
        k = {x["kind"] for x in al}
        v = verdict.apply_caps(v, small_sample="small_sample" in k, spend_gap="spend_gap" in k)
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
        "funnel": funnel.run(arms),
        "verdict": v,
        "replay": replay,
        "diagnosis": {"status": diag["status"], "finding": diag["finding"]},
        "next": next_step.run(v, diag, m["change"]),
    }
