"""4 판정: B가 나을 확률로 채택·유력·보류 (희수 8장 ④ 90/70% 규칙, 다정 M1 확률 계산).

- 판정 배지 지표: 1,000원당 도착 (11/22 회의 제안, 다정 79%와 같은 계산)
- 일자별 재현: 날마다 누적해서 다시 계산 → 며칠치로 고르면 뒤집힌다 (다정 M3, Lewis & Rao 2015)
- 최소 검증 예산: 기대 효과에서 '90% 확신으로 승자를 고를 확률'이 80% 이상이 되는 그룹당 예산 (희수 8장 ④, Feit & Berman 2019는 근거 인용)
"""
from typing import Dict, List, Optional

import numpy as np

from . import posterior, summary

BADGE = "visits_per_1000won"
METRICS = [  # (키, 이름, 클수록 좋은가)
    ("visits_per_1000won", "1,000원당 도착", True),
    ("cpm", "1,000회 노출당 비용", False),
    ("cpc", "링크 클릭당 비용", False),
    ("ctr", "링크 클릭률", True),
]
ADOPT, LIKELY = 0.9, 0.7


def level(p: float) -> str:
    return "채택" if p >= ADOPT else "유력" if p >= LIKELY else "보류"


def word(p: float, overlap: bool, better: str) -> str:
    """사이트 전체에서 쓰는 판정 문구 3개 (희수 90/70% + 다정 '말할 수 있음/방향만/말할 수 없음').
    p는 나은 쪽의 확률(0.5 이상). 95% 범위가 안 겹치면 확실."""
    if p >= ADOPT or not overlap:
        return "확실해요"
    return f"{better} 쪽이에요" if p >= LIKELY else "아직 몰라요"


def _q(x: np.ndarray, level_: float = 0.95):
    t = (1 - level_) / 2
    return float(np.quantile(x, t)), float(np.quantile(x, 1 - t))


def compare(a: Dict, b: Dict, seed: int = 0) -> Dict:
    da, db = posterior.draws(a, seed=seed), posterior.draws(b, seed=seed + 1)
    metrics = []
    for key, label, higher in METRICS:
        p = float((db[key] > da[key]).mean() if higher else (db[key] < da[key]).mean())
        ai, bi = _q(da[key]), _q(db[key])
        overlap = not (ai[1] < bi[0] or bi[1] < ai[0])
        better = "B" if p >= 0.5 else "A"
        metrics.append({"key": key, "label": label, "higher_is_better": higher, "prob_b_better": p,
                        "a_interval": ai, "b_interval": bi, "overlap": overlap, "better": better,
                        "word": word(max(p, 1 - p), overlap, better)})
    m = next(x for x in metrics if x["key"] == BADGE)
    conf = max(m["prob_b_better"], 1 - m["prob_b_better"])
    return {"a": a["name"], "b": b["name"], "metrics": metrics,
            "badge": {"metric": BADGE, "label": "1,000원당 도착", "better": m["better"], "prob": conf,
                      "level": level(conf), "word": m["word"]}}


def _prob_visits(a: Dict, b: Dict, n: int = 50_000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    la = rng.gamma(1 + a["landing_page_views"], 1 / max(a["spend"], 1e-9), n)
    lb = rng.gamma(1 + b["landing_page_views"], 1 / max(b["spend"], 1e-9), n)
    return float((lb > la).mean())


def daily_replay(bundle, a_name: str, b_name: str) -> List[Dict]:
    """날짜마다 그날까지 누적한 숫자로 'B가 나을 확률'을 다시 계산. 두 세트 다 아직 안 나간 날은 뺀다."""
    d = bundle.tables["meta_daily"].df
    cols = [c for c in summary.COUNTS if c in d.columns]
    out = []
    for date in sorted(d["date"].unique()):
        upto = d[d["date"] <= date]
        s = upto.groupby("adset")[cols].sum()
        if a_name not in s.index or b_name not in s.index or s.loc[a_name, "spend"] <= 0 or s.loc[b_name, "spend"] <= 0:
            continue
        a = summary.arm(a_name, *(float(s.loc[a_name].get(c, 0.0)) for c in summary.COUNTS))
        b = summary.arm(b_name, *(float(s.loc[b_name].get(c, 0.0)) for c in summary.COUNTS))
        out.append({"date": str(np.datetime_as_string(np.datetime64(date, "D"))), "prob": _prob_visits(a, b)})
    return out


def min_budget(a: Dict, lift: float = 0.2, confidence: float = ADOPT, power: float = 0.8, seed: int = 0,
               sims: int = 400, n_draws: int = 4000, max_per_group: int = 3_000_000) -> Dict:
    """A의 1,000원당 도착이 그대로이고 B가 lift만큼 좋을 때, 그룹마다 얼마를 써야
    'P(B>A) ≥ confidence'로 B를 고를 확률이 power 이상이 되는지. 1,000원 단위."""
    rate_a = a["landing_page_views"] / a["spend"] if a["spend"] else 0.0
    if rate_a <= 0:
        return {"per_group": None, "total": None, "lift": lift, "confidence": confidence, "power": None, "metric": BADGE}
    rate_b = rate_a * (1 + lift)

    def achieved(x: int) -> float:
        rng = np.random.default_rng(seed)
        ka, kb = rng.poisson(rate_a * x, sims), rng.poisson(rate_b * x, sims)
        la = rng.gamma(1 + ka[:, None], 1 / x, (sims, n_draws))
        lb = rng.gamma(1 + kb[:, None], 1 / x, (sims, n_draws))
        return float(((lb > la).mean(axis=1) >= confidence).mean())

    lo, hi = 1, max_per_group // 1000
    if achieved(hi * 1000) < power:
        return {"per_group": None, "total": None, "lift": lift, "confidence": confidence, "power": None, "metric": BADGE}
    while lo < hi:
        mid = (lo + hi) // 2
        if achieved(mid * 1000) >= power:
            hi = mid
        else:
            lo = mid + 1
    x = lo * 1000
    return {"per_group": x, "total": 2 * x, "lift": lift, "confidence": confidence, "power": achieved(x), "metric": BADGE}
