"""엔진: 채널별 월 단위 12개월 코호트 시뮬레이션. 고객 밸류체인 v3 (밸류체인_정의.md)를 따른다.

행동 축 (AARRR: ①② 획득, ③④ 활성화, ⑤ 유지, ⑥ 추천)
  ①② 접촉·반응  광고비 → 클릭                       (acquisition.py 곡선. 구매당 채널은 ④로 바로)
  ③④ 행동·구매  클릭 × 단계별 전환율 × 채널 배수 × 증분 계수 → 신규 고객 (첫 구매)
  ⑤ 재구매      r(t) = floor + (1 − floor)·e^(−decay·t), r(0) = 1 (첫 구매 달)
  ⑥ 추천        활성 고객(t) × 초대율 × 초대 전환율 → t+1달 신규 고객 (기본 0)
돈 축 (수익은 단계가 아니라 이 축으로 따로 셈)
  매출 = ④ 첫 구매 + ⑤ 재구매. 추천으로 온 고객의 매출도 그 고객의 ④·⑤에서만 센다 → ⑥에는 매출이 없다 (이중 집계 방지)
  남는 돈 = 매출 × 마진 − 광고비(구매당 수수료 포함) − 메시지 발송비 등 − 추천 보상(혜택비)
"""
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from . import defaults as D
from .acquisition import Channel


@dataclass
class FunnelParams:
    steps: List[Tuple[str, float]] = field(default_factory=lambda: list(D.FUNNEL_STEPS))
    retention_floor: float = D.RETENTION_FLOOR
    retention_decay: float = D.RETENTION_DECAY
    retention_scale: float = 1.0      # 레버 비교용: t ≥ 1 리텐션 전체 배수
    purchase_freq: float = D.PURCHASE_FREQ
    aov: float = D.AOV
    margin: float = D.MARGIN
    invite_rate: float = D.INVITE_RATE
    invite_conv: float = D.INVITE_CONV
    referral_reward: float = 0.0      # 혜택비: 추천으로 온 신규 고객 1명당 보상 (원). ⑥의 유일한 돈 항목
    months: int = D.MONTHS
    retention_bonus: Tuple[float, ...] = ()        # 자동화: 경과 t개월 리텐션에 더할 값 (t = 인덱스, t ≥ 1)
    reactivation: Optional[Tuple[int, float]] = None  # 자동화(휴면 복귀): (N, q) → t ≥ N이면 떠난 비율 (1 − r)의 q가 돌아옴
    season: Tuple[float, ...] = ()    # 월별 클릭 배수 (계절 지수, 시뮬레이션 1달째부터, 평균 1). 비면 매달 1.0

    def season_m(self, n: int) -> np.ndarray:
        """n개월 클릭 배수. 짧으면 반복, 비면 1.0. 광고비는 같고 클릭(→ 신규 고객)만 오르내림."""
        if not self.season:
            return np.ones(n)
        s = np.asarray(self.season, dtype=float)
        return np.resize(s, n)

    @property
    def cvr(self) -> float:
        """클릭 → ④ 구매(핵심 과업) (단계별 전환율의 곱)."""
        return float(np.prod([min(max(r, 0.0), 1.0) for _, r in self.steps])) if self.steps else 0.0

    def retention(self, n: int, mult: float = 1.0) -> np.ndarray:
        t = np.arange(n, dtype=float)
        r = self.retention_floor + (1 - self.retention_floor) * np.exp(-self.retention_decay * t)
        r = np.clip(r * self.retention_scale * mult, 0.0, 1.0)
        for i, b in enumerate(self.retention_bonus[:n]):
            if i >= 1:
                r[i] = min(r[i] + b, 1.0)
        if self.reactivation is not None:
            start, q = self.reactivation
            r[start:] = r[start:] + q * (1 - r[start:])
        r[0] = 1.0
        return r

    def value_per_active(self) -> float:
        """활성 고객 1명이 한 달에 남기는 매출총이익."""
        return self.purchase_freq * self.aov * self.margin

    def with_changes(self, **kw) -> "FunnelParams":
        return replace(self, **kw)


@dataclass
class SimResult:
    channels: List[Channel]
    params: FunnelParams
    monthly: pd.DataFrame
    by_channel: pd.DataFrame
    summary: Dict[str, Optional[float]]
    funnel: pd.DataFrame
    customer_cum_profit: Optional[np.ndarray] = None  # 유료 고객 1명의 누적 매출총이익 (36개월, 회수 기간 차트용)


def simulate(channels: Sequence[Channel], spends: Sequence[float], params: FunnelParams,
             extra_cost_m: Optional[Sequence[float]] = None) -> SimResult:
    """spends: 채널별 월 광고비 (12개월 동일하게 집행).
    extra_cost_m: 광고비 외 월 비용 (자동 메시지 발송비·쿠폰 할인 등). 길이 M 배열 또는 매달 같은 금액."""
    M = params.months
    freq, aov, margin = params.purchase_freq, params.aov, params.margin
    k_ref = params.invite_rate * params.invite_conv
    cvr = params.cvr

    spend_m = np.zeros(M)
    clicks_m = np.zeros(M)
    paid_new_m = np.zeros(M)
    paid_active_m = np.zeros(M)
    paid_first_rev = 0.0
    season = params.season_m(M)
    ch_rows, ltv_weights, gp_curves = [], [], []

    direct_new = 0.0  # ③을 거치지 않고 ④로 바로 오는 고객 (판매 수수료 채널)
    for ch, alloc in zip(channels, spends):
        if not ch.budgeted:
            # 과금 방식 '구매당': 예산과 무관하게 1회 판매량 × 횟수만큼 ④ 구매. 비용은 판매 매출의 수수료 + 착수금
            alloc = 0.0
            new = ch.curve.sales() * ch.incr_mult
            clicks = 0.0
            actual = ch.curve.cost(ch.curve.sales(), aov)
            direct_new += new
        else:
            alloc = max(float(alloc), 0.0)
            actual = ch.curve.spendable(alloc)
            clicks = ch.curve.clicks(alloc)
            new = clicks * cvr * ch.cvr_mult * ch.incr_mult
        r_ch = params.retention(M, ch.retention_mult)
        # 계절성: 예산형 채널의 클릭·신규만 달마다 배수. 구매당 채널(판매량 고정)은 그대로
        cohorts = np.full(M, new) * (season if ch.budgeted else 1.0)
        active = np.convolve(cohorts, r_ch)[:M]
        spend_m += actual
        clicks_m += clicks * (season if ch.budgeted else 1.0)
        paid_new_m += cohorts
        paid_active_m += active
        paid_first_rev += float(cohorts.sum()) * freq * aov
        ltv = float(r_ch.sum() * params.value_per_active())
        ltv_weights.append(new)
        gp_curves.append(params.retention(36, ch.retention_mult) * params.value_per_active())
        ch_rows.append({
            "channel": ch.key, "label": ch.label, "billing": D.BILLING[ch.billing][0], "budget": alloc, "spend": actual,
            "unspent": max(alloc - actual, 0.0), "clicks": clicks,
            "cpc": actual / clicks if clicks > 0 else np.nan,
            "marginal_cpc": ch.curve.marginal_cpc(actual) if (actual > 0 and ch.budgeted) else np.nan,
            "new_customers": new, "cac": actual / new if new > 0 else np.nan,
            "ltv_12m": ltv,
        })

    # 추천 코호트: 전체 활성 고객이 다음 달 신규를 만든다
    r_base = params.retention(M)
    ref_new_m = np.zeros(M)
    active_m = np.zeros(M)
    for m in range(M):
        ref_active = float(np.dot(ref_new_m[: m + 1][::-1], r_base[: m + 1]))
        active_m[m] = paid_active_m[m] + ref_active
        if m + 1 < M:
            ref_new_m[m + 1] = active_m[m] * k_ref

    new_m = paid_new_m + ref_new_m
    orders_m = active_m * freq
    revenue_m = orders_m * aov
    new_rev_m = new_m * freq * aov
    repeat_rev_m = revenue_m - new_rev_m
    gp_m = revenue_m * margin
    extra_m = np.zeros(M) if extra_cost_m is None else np.broadcast_to(np.asarray(extra_cost_m, dtype=float), (M,)).copy()
    reward_m = ref_new_m * params.referral_reward          # ⑥ 추천: 매출 없이 보상 비용만
    profit_m = gp_m - spend_m - extra_m - reward_m

    monthly = pd.DataFrame({
        "month": np.arange(1, M + 1), "spend": spend_m, "clicks": clicks_m,
        "paid_new": paid_new_m, "referral_new": ref_new_m, "new_customers": new_m,
        "active": active_m, "orders": orders_m, "revenue": revenue_m,
        "new_revenue": new_rev_m, "repeat_revenue": repeat_rev_m,
        "gross_profit": gp_m, "extra_cost": extra_m, "referral_reward": reward_m, "profit": profit_m, "cum_profit": np.cumsum(profit_m),
    })
    by_channel = pd.DataFrame(ch_rows)

    spend_total = float(spend_m.sum())
    paid_new = float(paid_new_m.sum())
    new_total = float(new_m.sum())
    w = np.array(ltv_weights)
    if w.sum() > 0:
        ltv = float(np.average(by_channel["ltv_12m"], weights=w))
        gp_curve = np.average(np.vstack(gp_curves), axis=0, weights=w)
    else:
        ltv = float(params.retention(M).sum() * params.value_per_active())
        gp_curve = params.retention(36) * params.value_per_active()
    paid_cac = spend_total / paid_new if paid_new > 0 else None
    payback = None
    if paid_cac is not None:
        hit = np.nonzero(np.cumsum(gp_curve) >= paid_cac)[0]
        payback = int(hit[0]) + 1 if len(hit) else None
    be = np.nonzero(monthly["cum_profit"].values >= 0)[0]
    breakeven = int(be[0]) + 1 if (len(be) and spend_total > 0) else None

    summary = {
        "budget_total": float(sum(max(float(s), 0.0) for s in spends)) * M,
        "spend_total": spend_total,
        "unspent_total": float(by_channel["unspent"].sum()) * M if len(by_channel) else 0.0,
        "clicks_total": float(clicks_m.sum()),
        "paid_new": paid_new,
        "referral_new": float(ref_new_m.sum()),
        "new_customers": new_total,
        "paid_cac": paid_cac,
        "blended_cac": spend_total / new_total if new_total > 0 else None,
        "revenue": float(revenue_m.sum()),
        "new_revenue": float(new_rev_m.sum()),
        "repeat_revenue": float(repeat_rev_m.sum()),
        "gross_profit": float(gp_m.sum()),
        "extra_cost": float(extra_m.sum()),
        "referral_reward": float(reward_m.sum()),
        "profit_12m": float(profit_m.sum()),
        "roas": paid_first_rev / spend_total if spend_total > 0 else None,
        "ltv_12m": ltv,
        "ltv_cac": ltv / paid_cac if paid_cac else None,
        "payback_month": payback,
        "breakeven_month": breakeven,
        "cvr": cvr,
        "viral_k": k_ref,
        "direct_new": direct_new * M,
    }

    # AARRR 퍼널 (12개월 합계). 채널 배수는 마지막 단계(④ 구매)에 반영
    clicks_by_ch = by_channel["clicks"].values if len(by_channel) else np.zeros(0)
    mult = np.array([c.cvr_mult * c.incr_mult for c in channels])
    stages = [("획득", "② 반응 (클릭)", float(clicks_m.sum()))]
    cum = 1.0
    for i, (name, rate) in enumerate(params.steps):
        cum *= min(max(rate, 0.0), 1.0)
        last = i == len(params.steps) - 1
        cnt = float((clicks_by_ch * cum * (mult if last else 1.0)).sum()) * M + (direct_new * M if last else 0.0)
        stages.append(("활성화", name, cnt))
    retained = float(sum(paid_new_m[c] * params.retention(M)[M - 1 - c] for c in range(M - 1)))
    stages.append(("유지", "⑤ 재구매 (12개월차 고객)", retained))
    stages.append(("추천", "⑥ 추천 (데려온 신규 고객 수, 매출은 그 고객의 ④·⑤에서 셈)", float(ref_new_m.sum())))
    funnel = pd.DataFrame(stages, columns=["aarrr", "stage", "count"])

    return SimResult(list(channels), params, monthly, by_channel, summary, funnel, np.cumsum(gp_curve))
