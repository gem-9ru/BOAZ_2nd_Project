"""2 보정: 숫자 하나 대신 가능한 범위로.

- 비율(클릭률, 클릭→도착)은 베타 분포 Beta(1+성공, 1+실패)  (희수 8장 ②, 다정 M1)
- 원당 횟수(노출·클릭·도착 ÷ 지출)는 감마 분포 Gamma(1+횟수, 지출)  → CPM·CPC·1,000원당 도착  (다정: CPM 범위)
- 노출이 적은 칸의 클릭률은 전체 평균 쪽으로 당긴다 (경험적 베이즈 축소, Efron & Morris 1975, 다정 M2)
"""
from typing import Dict, List, Tuple

import numpy as np

from ..specs import loop as _loop

DRAWS = int(_loop()["simulation"]["runs"])   # rules.yaml loop.simulation.runs
MIN_IMPRESSIONS = 100     # 이보다 노출이 적은 노출 위치는 '참고만'


def draws(a: Dict, n: int = DRAWS, seed: int = 0) -> Dict[str, np.ndarray]:
    """세트 하나의 지표 표본 n개. 같은 seed면 같은 표본."""
    rng = np.random.default_rng(seed)
    spend = max(a["spend"], 1e-9)
    imp, clk, lpv = a["impressions"], a["link_clicks"], a["landing_page_views"]
    per_won_imp = rng.gamma(1 + imp, 1 / spend, n)
    per_won_clk = rng.gamma(1 + clk, 1 / spend, n)
    per_won_lpv = rng.gamma(1 + lpv, 1 / spend, n)
    return {
        "cpm": 1000 / per_won_imp,
        "ctr": rng.beta(1 + clk, 1 + max(imp - clk, 0), n),
        "cpc": 1 / per_won_clk,
        "click_to_visit": rng.beta(1 + lpv, 1 + max(clk - lpv, 0), n),
        "visits_per_1000won": per_won_lpv * 1000,
    }


def interval(a: Dict, key: str, level: float = 0.9, seed: int = 0) -> Tuple[float, float]:
    d = draws(a, seed=seed)[key]
    tail = (1 - level) / 2
    return float(np.quantile(d, tail)), float(np.quantile(d, 1 - tail))


def intervals(a: Dict, level: float = 0.9, seed: int = 0) -> Dict[str, Tuple[float, float]]:
    tail = (1 - level) / 2
    return {k: (float(np.quantile(v, tail)), float(np.quantile(v, 1 - tail))) for k, v in draws(a, seed=seed).items()}


def shrink(rows: List[Dict], min_impressions: int = MIN_IMPRESSIONS) -> List[Dict]:
    """노출 위치별 클릭률을 전체 평균 쪽으로. 노출이 적을수록 많이 당긴다.
    사전분포 Beta(κm, κ(1-m)): m = 전체 클릭률, κ는 칸 사이의 실제 차이(표본 잡음을 뺀 분산)로 정한다."""
    n = np.array([r["impressions"] for r in rows], float)
    c = np.array([r["link_clicks"] for r in rows], float)
    if n.sum() <= 0:
        return [{**r, "ctr_adjusted": None, "reference_only": True} for r in rows]
    m = c.sum() / n.sum()
    p = np.divide(c, n, out=np.full_like(c, m), where=n > 0)
    between = float((n * (p - m) ** 2).sum() / n.sum() - m * (1 - m) * len(rows) / n.sum())
    kappa = float(np.clip(m * (1 - m) / between - 1, 1, 1e6)) if between > 0 else 1e6
    out = []
    for r, ni, ci in zip(rows, n, c):
        out.append({**r, "ctr_adjusted": float((ci + kappa * m) / (ni + kappa)), "reference_only": bool(ni < min_impressions)})
    return out
