"""몬테카를로: 한 달 광고로 온 손님이 1년 동안 남기는 돈의 분포 (노션 Q2).

한 달 시험 예산을 쓰고, 그 달에 온 새 손님이 12개월 동안 남기는 돈(첫 구매 + 재구매) − 광고비를 N번 뽑는다.
불확실한 입력을 데이터 신뢰 등급별 폭으로 흔든다 (defaults.GRADE_WIDTH, 로그정규, 표준편차 = ln(1 + 폭)):
  클릭 비용(채널별 등급), 구매 비율(퍼널, C), 재구매(D), 판매가·마진(A).
손님 1명 가치는 model.FunnelParams.per_customer_value 하나 (첫 달 1번 + 재구매, 손익분기 식과 같음). 폭이 0이면 one_month()와 같은 값이 나온다.
"""
from typing import Dict, Optional, Sequence

import numpy as np

from . import defaults as D

N_RUNS = 10_000         # 1만 번 (MVP 7c, 벡터 계산이라 약 1ms)
SEED = 20261109


def _sigma(grade: str) -> float:
    return float(np.log1p(D.GRADE_WIDTH[grade]))



def one_month(channels: Sequence, spends: Sequence[float], params) -> Dict[str, float]:
    """결정론: 한 달 광고 → 그 달 새 손님 → 12개월 남는 돈."""
    out = run(channels, spends, params, grades={}, n=1, widths=0.0)
    return {"profit": float(out["profits"][0]), "first_only": float(out["first_only"][0]), "new": float(out["new"][0])}


def run(channels: Sequence, spends: Sequence[float], params, grades: Dict[str, str], n: int = N_RUNS,
        seed: int = SEED, widths: Optional[float] = None) -> Dict:
    """grades: {"cpc_<채널 키>": 등급, "cvr": 등급, "retention": 등급, "aov": 등급, "margin": 등급}. 없는 항목은 흔들지 않음.
    widths=0이면 모든 폭 0 (검산용)."""
    rng = np.random.default_rng(seed)

    def draw(name: str) -> np.ndarray:
        g = grades.get(name)
        if g is None or widths == 0.0:
            return np.ones(n)
        return np.exp(rng.normal(0.0, _sigma(g), n))

    months = params.months
    cvr_f, ret_f, aov_f, margin_f = draw("cvr"), draw("retention"), draw("aov"), draw("margin")
    unit = params.aov * params.margin
    new_total = np.zeros(n)
    gp_total = np.zeros(n)
    spend_total = 0.0
    first_total = np.zeros(n)
    for ch, s in zip(channels, spends):
        s = max(float(s), 0.0)
        spend_total += ch.curve.spendable(s)
        clicks = ch.curve.clicks(s)
        new = clicks * params.cvr * ch.cvr_mult * ch.incr_mult / draw(f"cpc_{ch.key}") * cvr_f
        per = params.per_customer_value(months, ch.retention_mult, ret_f)
        new_total += new
        gp_total += new * per
        first_total += new             # 첫 구매는 딱 1번 (Q1)
    money = unit * aov_f * margin_f
    profits = gp_total * money - spend_total
    first_only = first_total * money - spend_total
    return {
        "profits": profits, "first_only": first_only, "new": new_total, "spend": spend_total,
        "wins": int(round(100 * float(np.mean(profits > 0)))),
        "wins_first": int(round(100 * float(np.mean(first_only > 0)))),
        "p10": float(np.percentile(profits, 10)), "p50": float(np.percentile(profits, 50)),
        "p90": float(np.percentile(profits, 90)), "n": n, "seed": seed,
    }


def action(wins: int) -> str:
    """결론 문장 (행동). 기준: 100번 중 80번 이상 / 50~79 / 50 미만 (사용자 결정 11/9, 보수적)."""
    if wins >= 80:
        return "go"
    if wins >= 50:
        return "small"
    return "prep"


ACTION_TEXT = {"go": "해 볼 만해요", "small": "작게 시험해 보세요", "prep": "지금은 광고보다 준비가 먼저예요"}
