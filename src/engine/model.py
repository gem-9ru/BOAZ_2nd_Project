"""AARRR 엔진 v0: 채널별 월 단위 12개월 코호트 시뮬레이션.

획득   광고비 → 클릭                       (acquisition.py 포화 곡선)
활성화 클릭 × 단계별 전환율 × 채널 배수      → 유료 신규 고객
유지   r(t) = floor + (1 − floor)·e^(−decay·t), r(0) = 1 (첫 구매 달)
수익   활성 고객 × 월 구매 빈도 × 객단가 × 마진 − 광고비
추천   활성 고객(t) × 초대율 × 초대 전환율 → t+1달 신규 고객 (기본 0)
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
    months: int = D.MONTHS

    @property
    def cvr(self) -> float:
        """클릭 → 핵심 과업 완료 (단계별 전환율의 곱)."""
        return float(np.prod([min(max(r, 0.0), 1.0) for _, r in self.steps])) if self.steps else 0.0

    def retention(self, n: int, mult: float = 1.0) -> np.ndarray:
        t = np.arange(n, dtype=float)
        r = self.retention_floor + (1 - self.retention_floor) * np.exp(-self.retention_decay * t)
        r = np.clip(r * self.retention_scale * mult, 0.0, 1.0)
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


def simulate(channels: Sequence[Channel], spends: Sequence[float], params: FunnelParams) -> SimResult:
    """spends: 채널별 월 광고비 (12개월 동일하게 집행)."""
    M = params.months
    freq, aov, margin = params.purchase_freq, params.aov, params.margin
    k_ref = params.invite_rate * params.invite_conv
    cvr = params.cvr

    spend_m = np.zeros(M)
    clicks_m = np.zeros(M)
    paid_new_m = np.zeros(M)
    paid_active_m = np.zeros(M)
    paid_first_rev = 0.0
    ch_rows, ltv_weights, gp_curves = [], [], []

    for ch, alloc in zip(channels, spends):
        alloc = max(float(alloc), 0.0)
        actual = ch.curve.spendable(alloc)
        clicks = ch.curve.clicks(alloc)
        new = clicks * cvr * ch.cvr_mult
        r_ch = params.retention(M, ch.retention_mult)
        cohorts = np.full(M, new)
        active = np.convolve(cohorts, r_ch)[:M]
        spend_m += actual
        clicks_m += clicks
        paid_new_m += cohorts
        paid_active_m += active
        paid_first_rev += new * M * freq * aov
        ltv = float(r_ch.sum() * params.value_per_active())
        ltv_weights.append(new)
        gp_curves.append(params.retention(36, ch.retention_mult) * params.value_per_active())
        ch_rows.append({
            "channel": ch.key, "label": ch.label, "budget": alloc, "spend": actual,
            "unspent": alloc - actual, "clicks": clicks,
            "cpc": actual / clicks if clicks > 0 else np.nan,
            "marginal_cpc": ch.curve.marginal_cpc(actual) if actual > 0 else np.nan,
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
    profit_m = gp_m - spend_m

    monthly = pd.DataFrame({
        "month": np.arange(1, M + 1), "spend": spend_m, "clicks": clicks_m,
        "paid_new": paid_new_m, "referral_new": ref_new_m, "new_customers": new_m,
        "active": active_m, "orders": orders_m, "revenue": revenue_m,
        "new_revenue": new_rev_m, "repeat_revenue": repeat_rev_m,
        "gross_profit": gp_m, "profit": profit_m, "cum_profit": np.cumsum(profit_m),
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
        "profit_12m": float(profit_m.sum()),
        "roas": paid_first_rev / spend_total if spend_total > 0 else None,
        "ltv_12m": ltv,
        "ltv_cac": ltv / paid_cac if paid_cac else None,
        "payback_month": payback,
        "breakeven_month": breakeven,
        "cvr": cvr,
        "viral_k": k_ref,
    }

    # AARRR 퍼널 (12개월 합계). 채널 배수는 마지막 단계(과업 완료)에 반영
    clicks_by_ch = by_channel["clicks"].values if len(by_channel) else np.zeros(0)
    mult = np.array([c.cvr_mult for c in channels])
    stages = [("획득", "클릭", float(clicks_m.sum()))]
    cum = 1.0
    for i, (name, rate) in enumerate(params.steps):
        cum *= min(max(rate, 0.0), 1.0)
        last = i == len(params.steps) - 1
        cnt = float((clicks_by_ch * cum * (mult if last else 1.0)).sum()) * M
        stages.append(("활성화", name, cnt))
    retained = float(sum(paid_new_m[c] * params.retention(M)[M - 1 - c] for c in range(M - 1)))
    stages.append(("유지", "12개월차 재구매 고객", retained))
    stages.append(("추천", "추천 신규 고객", float(ref_new_m.sum())))
    funnel = pd.DataFrame(stages, columns=["aarrr", "stage", "count"])

    return SimResult(list(channels), params, monthly, by_channel, summary, funnel)
