"""3 시뮬레이션: 실측 범위로 20만 번 가상 집행 (희수 8장 ③).

노출 = 예산 ÷ CPM × 1,000 → 링크 클릭 = 노출 × 클릭률 → 도착 = 클릭 × 클릭→도착.
지표마다 2 보정의 범위에서 하나씩 뽑아 계산하고, 가운데 80%를 보여 준다.
한계: 예산을 크게 늘릴 때 단가 상승·학습 기간은 반영하지 않는다 (Jin 외 2017의 포화 구조는 미반영).
"""
from typing import Dict

import numpy as np

from . import posterior

RUNS = posterior.DRAWS
BINS = 20


def _band(x: np.ndarray) -> Dict[str, float]:
    return {"median": float(np.median(x)), "lo": float(np.quantile(x, 0.1)), "hi": float(np.quantile(x, 0.9))}


def run(arm: Dict, budget: float, runs: int = RUNS, seed: int = 0) -> Dict:
    d = posterior.draws(arm, n=runs, seed=seed)
    impressions = budget / d["cpm"] * 1000
    clicks = impressions * d["ctr"]
    visits = clicks * d["click_to_visit"]
    counts, edges = np.histogram(clicks, bins=BINS, range=(float(np.quantile(clicks, 0.001)), float(np.quantile(clicks, 0.999))))
    counts[0] += int((clicks < edges[0]).sum())       # 범위 밖도 끝 칸에 넣어 합이 runs가 되게
    counts[-1] += int((clicks > edges[-1]).sum())
    return {
        "budget": float(budget), "runs": runs, "arm": arm["name"],
        "impressions": _band(impressions), "link_clicks": _band(clicks), "visits": _band(visits),
        "histogram": [{"lo": float(lo), "hi": float(hi), "count": int(k)} for lo, hi, k in zip(edges[:-1], edges[1:], counts)],
        "limits": "예산을 크게 늘리면 단가가 오르거나 학습 기간이 생길 수 있지만, 이 계산에는 반영하지 않았어요.",
    }
