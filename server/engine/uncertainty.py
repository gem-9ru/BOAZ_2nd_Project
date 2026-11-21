"""작은 표본에서 '얼마나 확실한가'를 숫자로: 베타 사후분포 (사전분포 Beta(1,1)).

광고비가 작으면 클릭·도착이 수십 건이라 비율 하나로 단정하면 틀리기 쉽다 (설계서 7장).
scipy 없이 numpy 표본으로 계산하고, seed를 고정해 같은 입력이면 같은 답을 낸다.
"""
from typing import Tuple

import numpy as np

DRAWS = 200_000


def _draws(successes: float, trials: float, rng: np.random.Generator) -> np.ndarray:
    return rng.beta(1 + successes, 1 + max(trials - successes, 0), DRAWS)


def beta_interval(successes: float, trials: float, level: float = 0.9, seed: int = 0) -> Tuple[float, float]:
    """비율의 사후 구간. 시행이 0이면 아무것도 모름 → (0, 1)."""
    if trials <= 0:
        return 0.0, 1.0
    d = _draws(successes, trials, np.random.default_rng(seed))
    tail = (1 - level) / 2
    return float(np.quantile(d, tail)), float(np.quantile(d, 1 - tail))


def prob_better(a_succ: float, a_n: float, b_succ: float, b_n: float, seed: int = 0) -> float:
    """B의 비율이 A보다 클 확률."""
    rng = np.random.default_rng(seed)
    return float((_draws(b_succ, b_n, rng) > _draws(a_succ, a_n, rng)).mean())


def straddles(lo: float, hi: float, threshold: float) -> bool:
    """구간이 기준값을 걸치면 '판단 보류'."""
    return lo < threshold < hi
