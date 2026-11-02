"""A/B 테스트 표본 크기 계산 (두 비율 비교, 양측 검정).

n(그룹당) = (z_{1-α/2}·√(2·p̄(1−p̄)) + z_{1-β}·√(p1(1−p1) + p2(1−p2)))² / (p2 − p1)²
"""
import math
from typing import Dict

from scipy.stats import norm


def sample_size(p1: float, relative_lift: float, alpha: float = 0.05, power: float = 0.8) -> Dict[str, float]:
    """기준 전환율 p1을 relative_lift(예: 0.10 = 10%)만큼 올린 효과를 잡는 데 필요한 그룹당 표본."""
    p2 = min(p1 * (1 + relative_lift), 0.999)
    if not (0 < p1 < 1) or p2 <= p1:
        return {"p1": p1, "p2": p2, "n_per_group": float("nan"), "n_total": float("nan")}
    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    p_bar = (p1 + p2) / 2
    num = (z_a * math.sqrt(2 * p_bar * (1 - p_bar)) + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    n = math.ceil(num / (p2 - p1) ** 2)
    return {"p1": p1, "p2": p2, "n_per_group": n, "n_total": 2 * n}


def days_needed(n_total: float, monthly_traffic: float) -> float:
    """해당 단계에 한 달 동안 들어오는 사용자 수로 실험 기간(일) 추정."""
    if monthly_traffic <= 0 or n_total != n_total:
        return float("inf")
    return math.ceil(n_total / (monthly_traffic / 30))
