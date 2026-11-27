"""3 시뮬레이션: 실측 범위로 20만 번 가상 집행 (희수 8장 ③).

노출 = 예산 ÷ CPM × 1,000 → 링크 클릭 = 노출 × 클릭률 → 도착 = 클릭 × 클릭→도착.
지표마다 2 보정의 범위에서 하나씩 뽑아 계산하고, 가운데 80%를 보여 준다.
한계: 예산을 크게 늘릴 때 단가 상승·학습 기간은 반영하지 않는다 (Jin 외 2017의 포화 구조는 미반영).
"""
from typing import Dict, Optional

import numpy as np

from . import posterior
from ..specs import loop as _loop

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


def tried(arm: Dict, budget: float, days: Optional[int] = None) -> Dict:
    """써 본 적 있는 금액인지 (AN-05 · ALT-24): 세트당 총액이 실제로 쓴 돈 이하이고,
    기간을 주면 하루 금액(총액 ÷ 기간)도 하루에 가장 많이 써 본 돈 이하여야 '써 본 금액'.
    기간은 방문자 수 범위를 바꾸지 않는다(총액 기준 계산) — 바뀌는 건 하루 금액과 '가설' 여부."""
    total_ok = budget <= arm["spend"]
    daily = budget / days if days else None
    daily_ok = daily is None or not arm.get("daily_max") or daily <= arm["daily_max"] + 0.5
    floor = _loop().get("meta_daily_min")
    return {"tried": bool(total_ok and daily_ok), "days": days, "daily": daily,
            "daily_max": arm.get("daily_max"), "daily_tried": bool(daily_ok),
            # 하루 금액이 메타 하루 최소보다 적으면 광고가 안 나갈 수 있어요 (총예산 < 하루 최소 × 기간)
            "daily_min": floor, "below_daily_min": bool(daily is not None and floor and daily < floor)}


def _thousand(x: float) -> int:
    """천 원 단위 반올림 (0.5는 올림 — 파이썬 round는 2,500 → 2,000)."""
    return int(x / 1000 + 0.5) * 1000


def next_test_budget(total: float, days: int = 4) -> Dict:
    """Test & Roll: 다음 테스트에 쓸 몫 = 전체 예산의 약 7.6~20% (Feit & Berman 2019, 오븐로그 실측 기준). 두 세트로 나눈다.
    세트마다 적어도 '메타 하루 최소 × 기간' (그보다 적으면 광고가 안 나가요 — 같은 화면의 경고와 맞춤, 감사 9)."""
    t = _loop()["test_and_roll"]
    lo, hi = total * t["share_lo"], total * t["share_hi"]
    least = -(-int((_loop().get("meta_daily_min") or 0) * days) // 1000) * 1000
    per_lo = max(_thousand(lo / 2), least)
    return {"total": float(total), "share_lo": t["share_lo"], "share_hi": t["share_hi"],
            "per_set_lo": per_lo, "per_set_hi": max(_thousand(hi / 2), per_lo), "per_set_least": least,
            "source": "Feit & Berman 2019 Test & Roll (오븐로그 실측으로 맞춘 몫)"}


def judge_chance(arm: Dict, budget: float, sets: int = 2, runs: int = RUNS, seed: int = 0) -> float:
    """세트마다 budget을 쓰면 두 세트 합쳐 링크 클릭이 판정 최소(rules.yaml min_clicks, 30번) 넘게 모일 가능성 (축소안 v5 ③).
    새 세트도 지금 세트처럼 반응한다고 가정: 세트마다 사후 분포에서 따로 뽑고, 실제 클릭 수의 우연(포아송)도 더한다.
    테스트가 '성공'할 확률이 아니라 '판단할 수 있을' 가능성이다."""
    rng = np.random.default_rng(seed)
    clicks = sum(budget / d["cpm"] * 1000 * d["ctr"] for d in (posterior.draws(arm, n=runs, seed=seed + i) for i in range(sets)))
    return float((rng.poisson(clicks) >= _loop()["alerts"]["min_clicks"]).mean())


def grid(arm: Dict, days: int = 4, runs: int = RUNS, seed: int = 0) -> Dict:
    """③ 예산 슬라이더 결과표 (최종안(1)): 3,000~30,000원은 1,000원, 그 위 100,000원까지는 5,000원 단위로 미리 계산해 두면 움직일 때 바로 바뀐다.
    방문자 수는 예산에 비례하므로 표본(원당 방문자)을 한 번만 뽑아 금액마다 곱한다 (run과 같은 seed라 같은 숫자).
    hard = 두 세트 합쳐 클릭 30번이 모일 가능성이 judge_min보다 낮음 → '이 금액이면 결과를 판단하기 어려워요'."""
    cfg = _loop()
    g = cfg["simulation"]["grid"]
    need = cfg["alerts"]["min_clicks"]
    d = posterior.draws(arm, n=runs, seed=seed)
    visit_rate = 1000 / d["cpm"] * d["ctr"] * d["click_to_visit"]            # 1원당 방문자
    clicks_per_won = sum(1000 / x["cpm"] * x["ctr"] for x in (d, posterior.draws(arm, n=runs, seed=seed + 1)))   # 두 세트
    rng = np.random.default_rng(seed)
    rows = []
    budgets = list(range(int(g["lo"]), int(g["mid"]) + 1, int(g["step"]))) + list(range(int(g["mid"]) + int(g["step_hi"]), int(g["hi"]) + 1, int(g["step_hi"])))
    for b in budgets:
        judge = float((rng.poisson(clicks_per_won * b) >= need).mean())
        rows.append({"budget": b, "visits": _band(visit_rate * b), "judge": judge,
                     "hard": judge < cfg["simulation"]["judge_min"], **tried(arm, float(b), days)})
    return {"arm": arm["name"], "days": days, "rows": rows, "mid": int(g["mid"]), "many_from": int(cfg["simulation"]["many_from"])}
