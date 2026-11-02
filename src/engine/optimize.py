"""엔진이 만드는 판단: 예산 최적화, 레버 비교, 예산 규모 스캔."""
import itertools
from typing import Dict, List, Sequence

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from . import defaults as D
from .acquisition import Channel
from .model import FunnelParams, simulate

OMTM_KEYS = {"new_customers": "new_customers", "profit": "profit_12m", "roas": "roas"}


def omtm_value(channels: Sequence[Channel], spends: Sequence[float], params: FunnelParams, omtm: str) -> float:
    v = simulate(channels, spends, params).summary[OMTM_KEYS[omtm]]
    return float(v) if v is not None else 0.0


def _grid(n: int, steps: int, allow_under: bool):
    """합이 1(또는 1 이하)인 비율 격자."""
    for combo in itertools.product(range(steps + 1), repeat=n):
        total = sum(combo)
        if total == steps or (allow_under and total < steps):
            yield np.array(combo, dtype=float) / steps


def optimize_allocation(channels: Sequence[Channel], budget: float, params: FunnelParams, omtm: str) -> Dict:
    """월 총예산 안에서 OMTM을 최대화하는 채널 배분.

    - 신규 고객·ROAS: 예산을 모두 배분 (합 = 예산)
    - 12개월 이익: 예산 이하로 써도 됨 (손해 구간이면 덜 쓰는 것이 최적)
    격자 탐색으로 시작점을 잡고 scipy SLSQP로 다듬는다 (네이버 곡선이 꺾은선이라 격자가 안전장치).
    """
    n = len(channels)
    if n == 0 or budget <= 0:
        return {"spends": [0.0] * n, "value": 0.0}
    allow_under = omtm == "profit"
    steps = 50 if n <= 2 else (20 if n == 3 else 10)
    f = lambda x: omtm_value(channels, np.asarray(x) * budget, params, omtm)  # noqa: E731

    best_x, best_v = None, -np.inf
    for x in _grid(n, steps, allow_under):
        v = f(x)
        if v > best_v + 1e-9:
            best_x, best_v = x, v

    cons = [{"type": "ineq" if allow_under else "eq", "fun": lambda x: 1.0 - np.sum(x)}]
    try:
        res = minimize(lambda x: -f(x), best_x, method="SLSQP", bounds=[(0.0, 1.0)] * n,
                       constraints=cons, options={"maxiter": 100, "eps": 1e-3})
        if res.success and -res.fun > best_v and np.sum(res.x) <= 1.0 + 1e-6:
            best_x, best_v = np.clip(res.x, 0, 1), -res.fun
    except Exception:
        pass
    return {"spends": [float(v) for v in best_x * budget], "value": float(best_v)}


def lever_table(channels: Sequence[Channel], spends: Sequence[float], params: FunnelParams,
                pct: float = D.LEVER_PCT) -> pd.DataFrame:
    """레버를 ±pct 바꿨을 때 12개월 이익 변화 (토네이도 차트용)."""
    base = simulate(channels, spends, params).summary["profit_12m"]

    def run(sp, p):
        return simulate(channels, sp, p).summary["profit_12m"] - base

    def scale_step(i, f):
        # 단계 레버는 '이탈률'을 바꾼다: +10% = 이탈 10% 감소 (이미 높은 단계는 개선 여지가 작음)
        steps = [(n, min(1 - (1 - r) * (2 - f), 1.0) if j == i else r) for j, (n, r) in enumerate(params.steps)]
        return params.with_changes(steps=steps)

    def scale_all_steps(f):
        # 전체 전환율을 f배: 마지막 단계에 몰아서 반영
        steps = list(params.steps)
        name, r = steps[-1]
        steps[-1] = (name, min(r * f, 1.0))
        return params.with_changes(steps=steps)

    levers = [
        ("spend", "광고비", lambda f: run([s * f for s in spends], params)),
        ("cvr", "전환율 (클릭→목표 행동)", lambda f: run(spends, scale_all_steps(f))),
        ("retention", "재구매 (리텐션)", lambda f: run(spends, params.with_changes(retention_scale=params.retention_scale * f))),
        ("aov", "1회 결제 금액 (객단가)", lambda f: run(spends, params.with_changes(aov=params.aov * f))),
        ("freq", "한 달 구매 횟수", lambda f: run(spends, params.with_changes(purchase_freq=params.purchase_freq * f))),
    ]
    for i, (name, _) in enumerate(params.steps):
        levers.append((f"step_{i}", f"단계: {name} (이탈 감소)", lambda f, i=i: run(spends, scale_step(i, f))))
    if params.invite_rate > 0:
        levers.append(("invite", "초대율", lambda f: run(spends, params.with_changes(invite_rate=params.invite_rate * f))))

    rows = [{"key": k, "lever": label, "up": fn(1 + pct), "down": fn(1 - pct)} for k, label, fn in levers]
    df = pd.DataFrame(rows)
    df["core"] = df["key"].isin(["spend", "cvr", "retention", "aov"])
    df["base_profit"] = base
    return df.sort_values("up", ascending=False).reset_index(drop=True)


def budget_scan(channels: Sequence[Channel], spends: Sequence[float], params: FunnelParams,
                multipliers: Sequence[float] = (0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0)) -> pd.DataFrame:
    """현재 배분 비율을 유지한 채 총예산 규모만 바꿨을 때의 12개월 지표."""
    total = sum(spends)
    shares = [s / total for s in spends] if total > 0 else [1 / len(spends)] * len(spends)
    rows = []
    for m in multipliers:
        b = total * m
        s = simulate(channels, [b * w for w in shares], params).summary
        rows.append({"multiplier": m, "monthly_budget": b, "profit_12m": s["profit_12m"],
                     "new_customers": s["new_customers"], "spend_total": s["spend_total"]})
    return pd.DataFrame(rows)
