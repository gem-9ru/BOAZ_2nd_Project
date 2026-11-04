"""M4 마케팅 자동화: 메시지 시나리오 3종 → 엔진 파라미터 변경 + 월 발송비 (명세 5장).

입력은 모두 사용자 입력이다 (도달 가능 비율, 건당 발송비, 증분 반응률, 할인율). 기본값을 지어내지 않는다.
- 증분 반응률 = 메시지를 받은 사람의 구매율 − 받지 않은 대조군의 구매율. 모르면 None → 손익분기 반응률만 계산.
- 대상 수는 엔진 코호트(광고로 온 손님 기준)에서 계산한다.

시나리오 → 엔진
- cart:      매달 '과업 시작'까지 왔지만 완료하지 않은 사람 → 마지막 단계 전환율 상승 (과업 진행·완료 이탈 감소)
- repeat:    첫 구매 후 1·2개월차 손님에게 한 번씩 → 리텐션 t=1, 2 상승
- dormant:   첫 구매 후 N개월 이상 지나 그달 구매하지 않은 손님에게 매달 → t ≥ N에서 떠난 비율 중 일부 복귀 (바닥값 상승)
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np

from .acquisition import Channel
from .model import FunnelParams, simulate

SCENARIOS = {
    "cart": {
        "label": "장바구니 이탈",
        "target": "과업을 시작했지만 완료하지 않은 손님 (매달)",
        "effect": "과업 진행·완료 단계 이탈 감소",
        "message": "브랜드 메시지 (광고성). 알림톡은 장바구니 안내를 보낼 수 없음",
    },
    "repeat": {
        "label": "첫 구매 후 재구매",
        "target": "첫 구매 후 1개월차·2개월차 손님 (한 번씩)",
        "effect": "리텐션 1~2개월차 상승",
        "message": "브랜드 메시지 (광고성). 주문·배송 알림톡에 할인·채널 추가 유도를 넣으면 발송 불가",
    },
    "dormant": {
        "label": "휴면 복귀",
        "target": "첫 구매 후 N개월 이상 지났고 그달 구매하지 않은 손님 (매달)",
        "effect": "리텐션 바닥값 상승 (떠난 손님 일부 복귀)",
        "message": "브랜드 메시지 (광고성)",
    },
}

# 광고성 메시지 공통 제약 (정보통신망법 제50조 · 카카오 브랜드 메시지 가이드, 명세 5-1)
BADGES = [
    ("📣 브랜드 메시지", "세 시나리오 모두 광고성이라 알림톡이 아니라 브랜드 메시지로 보냅니다."),
    ("✅ 수신 동의 필요", "채널 친구이거나 광고성 정보 수신에 동의한 사람에게만 (제50조제1항). 동의는 2년마다 다시 확인 (제50조제8항)."),
    ("🕗 08:00~20:50 발송", "카카오 브랜드 메시지 발송 가능 시간. 법은 21시~다음 날 8시 광고에 별도 동의를 요구 (제50조제3항). 밤의 장바구니 이탈은 다음 날 아침으로 밀립니다."),
    ("🏷️ (광고) 표기", "(광고) 표시, 전송자 명칭·연락처, 수신 거부 방법을 넣어야 함 (제50조제4항). 위반 시 과태료 3천만 원 이하."),
]


@dataclass
class ScenarioInput:
    key: str
    reach: float                       # 도달 가능 비율 (0~1)
    cost_per_send: float               # 건당 발송비 (원)
    response: Optional[float] = None   # 증분 반응률 (0~1). None이면 손익분기만
    discount: float = 0.0              # 쿠폰 할인율 (0~1)
    dormant_months: int = 3            # 휴면 기준 N (사용자 입력, 명세 9장 #4)


def breakeven_rate(cost_per_send: float, aov: float, margin: float, discount: float = 0.0) -> float:
    """r* = 건당 발송비 ÷ (객단가 × (1 − 할인율) × 마진). 재구매 효과는 빼서 보수적으로."""
    unit = aov * (1 - discount) * margin
    return cost_per_send / unit if unit > 0 else float("inf")


def _cart_rates(steps) -> tuple:
    """(R, C): 클릭 1회당 '과업 시작' 통과 비율과 '과업 완료' 비율. 단계가 3개 미만이면 마지막 단계 하나만 대상."""
    rates = [min(max(r, 0.0), 1.0) for _, r in steps]
    k = max(len(rates) - 2, 0)
    return float(np.prod(rates[:k])) if k else 1.0, float(np.prod(rates))


def _sends(key: str, base, params: FunnelParams, inp: ScenarioInput) -> np.ndarray:
    M = params.months
    new = base.monthly["paid_new"].values + base.monthly["referral_new"].values
    if key == "cart":
        reached, done = _cart_rates(params.steps)
        mult = np.average([c.cvr_mult for c in base.channels], weights=np.maximum(base.by_channel["clicks"].values, 1e-12)) \
            if len(base.channels) else 1.0
        return base.monthly["clicks"].values * max(reached - done * mult, 0.0) * inp.reach
    if key == "repeat":
        sends = np.zeros(M)
        for lag in (1, 2):
            sends[lag:] += new[:-lag] * inp.reach
        return sends
    if key == "dormant":
        r = params.retention(M)
        sends = np.zeros(M)
        for m in range(M):
            for age in range(inp.dormant_months, m + 1):
                sends[m] += new[m - age] * (1 - r[age]) * inp.reach
        return sends
    raise ValueError(key)


def _apply(key: str, params: FunnelParams, inp: ScenarioInput) -> FunnelParams:
    rho = inp.response or 0.0
    if key == "cart":
        reached, done = _cart_rates(params.steps)
        if done <= 0:
            return params
        new_done = done + inp.reach * rho * max(reached - done, 0.0)
        steps = list(params.steps)
        name, r = steps[-1]
        steps[-1] = (name, min(r * new_done / done, 1.0))
        return params.with_changes(steps=steps)
    if key == "repeat":
        bonus = list(params.retention_bonus) + [0.0] * max(0, 3 - len(params.retention_bonus))
        bonus[1] += inp.reach * rho
        bonus[2] += inp.reach * rho
        return params.with_changes(retention_bonus=tuple(bonus))
    if key == "dormant":
        return params.with_changes(reactivation=(inp.dormant_months, inp.reach * rho))
    raise ValueError(key)


def run_scenario(channels: Sequence[Channel], spends: Sequence[float], params: FunnelParams,
                 inp: ScenarioInput) -> Dict:
    """시나리오 카드 숫자. 반응률이 없으면 profit_delta는 None."""
    base = simulate(channels, spends, params)
    sends_m = _sends(inp.key, base, params, inp)
    send_cost_m = sends_m * inp.cost_per_send
    out = {
        "key": inp.key, "label": SCENARIOS[inp.key]["label"],
        "sends_month": float(sends_m.mean()), "cost_month": float(send_cost_m.mean()), "cost_12m": float(send_cost_m.sum()),
        "breakeven": breakeven_rate(inp.cost_per_send, params.aov, params.margin, inp.discount),
        "profit_delta": None, "params": params, "extra_cost_m": send_cost_m, "ad_alt_delta": None,
    }
    # 같은 돈을 광고에 쓰면: 발송비만큼 현재 배분 비율로 광고비 증액
    total = sum(spends)
    if total > 0 and out["cost_month"] > 0:
        alt = simulate(channels, [s * (1 + out["cost_month"] / total) for s in spends], params).summary["profit_12m"]
        out["ad_alt_delta"] = alt - base.summary["profit_12m"]
    if inp.response is None:
        return out
    new_params = _apply(inp.key, params, inp)
    after = simulate(channels, spends, new_params)
    # 쿠폰 할인: 메시지로 늘어난 매출에만 적용 (늘어난 매출 × 할인율)
    disc_m = (after.monthly["revenue"].values - base.monthly["revenue"].values).clip(min=0) * inp.discount
    extra = send_cost_m + disc_m
    after = simulate(channels, spends, new_params, extra_cost_m=extra)
    out.update(params=new_params, extra_cost_m=extra,
               profit_delta=after.summary["profit_12m"] - base.summary["profit_12m"],
               extra_orders_12m=float(after.monthly["orders"].sum() - base.monthly["orders"].sum()))
    return out


def combine(params: FunnelParams, results: List[Dict], months: int) -> tuple:
    """여러 시나리오를 함께 켤 때의 (파라미터, 월 비용). 반응률이 입력된 시나리오만."""
    p, cost = params, np.zeros(months)
    for r in results:
        if r["profit_delta"] is None:
            continue
        inp_params = r["params"]
        if r["key"] == "cart":
            p = p.with_changes(steps=inp_params.steps)
        elif r["key"] == "repeat":
            p = p.with_changes(retention_bonus=inp_params.retention_bonus)
        elif r["key"] == "dormant":
            p = p.with_changes(reactivation=inp_params.reactivation)
        cost = cost + r["extra_cost_m"]
    return p, cost
