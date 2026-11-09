"""획득 단계: 광고비 → 클릭 (포화 곡선).

- 네이버: 키워드별 '입찰가 → (비용, 클릭)' 예상 실적 점들로 곡선을 만든다.
  예상 실적은 계단 모양이라 점들의 위쪽 볼록 껍질(concave hull)을 쓰고,
  여러 키워드는 한계 CPC가 낮은 구간부터 채우는 방식으로 합친다 (= 네이버 안에서의 최적 배분).
  일 예산 상한으로 한 입찰가의 일부만 쓰는 것이 가능하므로 점 사이 선형 보간을 허용한다.
- 메타: CPC(s) = base_cpc × (1 + saturation × s / 100만 원). 클릭 = s / CPC(s).
- 구매당(rev_share, 과금 방식 '구매당': 공동구매·라이브커머스·제휴): 광고 예산을 쓰지 않고, 팔린 만큼 수수료를 낸다.
  구매당 비용 = 수수료율 × 객단가 + 착수금 ÷ 판매 수, 상한 = 1회 판매량 (밸류체인_정의.md 4-1, 조사 00-3)
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import defaults as D

SAT_UNIT = 1_000_000.0  # 메타 포화 노브의 기준 금액 (원)


def _upper_hull(points: List[tuple]) -> List[tuple]:
    """(비용, 클릭) 점들 중 '같은 돈으로 더 많은 클릭'인 점만 남긴 위쪽 볼록 껍질. (0,0)에서 시작."""
    pts = sorted(set(points))
    pareto, best = [(0.0, 0.0)], 0.0
    for cost, clicks in pts:
        if cost > 0 and clicks > best:
            pareto.append((cost, clicks))
            best = clicks
    hull: List[tuple] = []
    for p in pareto:
        while len(hull) >= 2:
            (ox, oy), (ax, ay) = hull[-2], hull[-1]
            if (ax - ox) * (p[1] - oy) - (ay - oy) * (p[0] - ox) >= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    return hull


class NaverCurve:
    """여러 키워드의 예상 실적을 합친 네이버 채널 곡선."""

    def __init__(self, estimates: Dict[str, pd.DataFrame]):
        segments = []
        self.points = {}
        for kw, df in estimates.items():
            pts = list(zip(df["cost"].astype(float), df["clicks"].astype(float)))
            bid_by_point = {(c, k): b for c, k, b in zip(df["cost"], df["clicks"], df["bid"])}
            hull = _upper_hull(pts)
            self.points[kw] = df
            for (c0, k0), (c1, k1) in zip(hull[:-1], hull[1:]):
                segments.append({
                    "keyword": kw, "dcost": c1 - c0, "dclicks": k1 - k0,
                    "bid": bid_by_point.get((c1, k1), np.nan),
                })
        segments.sort(key=lambda s: s["dclicks"] / s["dcost"], reverse=True)
        self.segments = segments
        self._cost = np.concatenate([[0.0], np.cumsum([s["dcost"] for s in segments])])
        self._clicks = np.concatenate([[0.0], np.cumsum([s["dclicks"] for s in segments])])
        self.capacity = float(self._cost[-1])  # 최고 입찰가에서도 더 쓸 수 없는 월 광고비 상한

    @property
    def keywords(self) -> List[str]:
        return list(self.points)

    def spendable(self, spend: float) -> float:
        return float(min(max(spend, 0.0), self.capacity))

    def clicks(self, spend: float) -> float:
        if self.capacity <= 0:
            return 0.0
        return float(np.interp(self.spendable(spend), self._cost, self._clicks))

    def marginal_cpc(self, spend: float) -> Optional[float]:
        s = self.spendable(spend)
        for i, seg in enumerate(self.segments):
            if s < self._cost[i + 1] or i == len(self.segments) - 1:
                return seg["dcost"] / seg["dclicks"]
        return None

    def allocation(self, spend: float, saturation_ratio: float = 2.0) -> pd.DataFrame:
        """주어진 네이버 예산에서 키워드별 광고비·클릭·권장 입찰가·한계 CPC·포화 여부."""
        left = self.spendable(spend)
        rows: Dict[str, dict] = {kw: {"keyword": kw, "spend": 0.0, "clicks": 0.0, "bid": 0.0, "marginal_cpc": np.nan}
                                 for kw in self.points}
        for seg in self.segments:
            if left <= 0:
                break
            frac = min(1.0, left / seg["dcost"])
            row = rows[seg["keyword"]]
            row["spend"] += seg["dcost"] * frac
            row["clicks"] += seg["dclicks"] * frac
            row["bid"] = max(row["bid"], seg["bid"])
            row["marginal_cpc"] = seg["dcost"] / seg["dclicks"]  # 이 키워드에서 마지막으로 산 구간의 한계 CPC
            left -= seg["dcost"] * frac
        out = pd.DataFrame(rows.values())
        out["cpc"] = np.where(out["clicks"] > 0, out["spend"] / out["clicks"].where(out["clicks"] > 0), np.nan)
        out["saturated"] = out["marginal_cpc"] > saturation_ratio * out["cpc"]
        return out

    def curve_table(self, n: int = 60) -> pd.DataFrame:
        s = np.linspace(0, self.capacity, n)
        return pd.DataFrame({"spend": s, "clicks": [self.clicks(x) for x in s]})


class MetaCurve:
    def __init__(self, base_cpc: float, saturation: float):
        self.base_cpc = float(base_cpc)
        self.saturation = float(saturation)
        self.capacity = float("inf")

    def cpc(self, spend: float) -> float:
        return self.base_cpc * (1 + self.saturation * max(spend, 0.0) / SAT_UNIT)

    def spendable(self, spend: float) -> float:
        return float(max(spend, 0.0))

    def clicks(self, spend: float) -> float:
        s = max(spend, 0.0)
        return 0.0 if s == 0 else s / self.cpc(s)

    def marginal_cpc(self, spend: float) -> float:
        return self.base_cpc * (1 + self.saturation * max(spend, 0.0) / SAT_UNIT) ** 2

    def curve_table(self, max_spend: float, n: int = 60) -> pd.DataFrame:
        s = np.linspace(0, max_spend, n)
        return pd.DataFrame({"spend": s, "clicks": [self.clicks(x) for x in s]})


class RevShareCurve:
    """과금 방식 '구매당'. 고객은 ④ 구매로 바로 들어오고(①② 매체 숫자는 캡처뿐), 비용은 매출에 비례한다.
    예산 배분 대상이 아니라 켜거나 끄는 채널이다 (budgeted = False)."""
    budgeted = False
    capacity = 0.0

    def __init__(self, rate: float, sales_per_campaign: float, campaigns_per_month: float = 1.0, upfront: float = 0.0,
                 fee_per_sale: float = 0.0):
        self.rate = float(rate)                          # 수수료형: 판매액 대비 수수료율 (0~1)
        self.fee_per_sale = float(fee_per_sale)          # 건당 고정형(구매 CPA): 판매 1건당 금액 (원)
        self.sales_per_campaign = float(sales_per_campaign)  # 1회 판매량 (= 상한)
        self.campaigns = float(campaigns_per_month)
        self.upfront = float(upfront)                    # 회당 착수금 (콘텐츠 제작비 등)

    def sales(self) -> float:
        return max(self.sales_per_campaign, 0.0) * max(self.campaigns, 0.0)

    def cost(self, sales: float, aov: float) -> float:
        """한 달 비용 = 수수료율 × 판매 매출 + 건당 금액 × 판매 수 + 착수금 × 횟수.
        수수료형: 구매당 비용 = 수수료율 × 객단가 + 착수금 ÷ 판매 수 / 건당 고정형: 건당 금액 + 착수금 ÷ 판매 수 (밸류체인 v3 4-1)"""
        return self.rate * sales * aov + self.fee_per_sale * sales + self.upfront * self.campaigns

    def cost_per_purchase(self, aov: float) -> float:
        s = self.sales()
        return self.cost(s, aov) / s if s > 0 else float("nan")

    # 예산 곡선 인터페이스 (예산을 받지 않음)
    def spendable(self, spend: float) -> float:
        return 0.0

    def clicks(self, spend: float) -> float:
        return 0.0

    def marginal_cpc(self, spend: float) -> float:
        return float("nan")


@dataclass
class Channel:
    key: str            # "naver", "meta", ...
    label: str          # 화면 표시 이름
    curve: object       # NaverCurve | MetaCurve (clicks(), spendable(), marginal_cpc())
    cvr_mult: float = 1.0        # 이 채널 클릭의 최종 전환율 배수 (구매 의도 차이)
    retention_mult: float = 1.0  # 이 채널 고객의 리텐션 배수
    billing: str = ""            # 과금 방식 키 (defaults.BILLING). 비우면 곡선 종류로 정함
    incr_mult: float = 1.0       # 증분 계수: 광고가 없었어도 왔을 고객을 뺀 비율 (기본 1, cvr_mult와 분리. 밸류체인 D6)

    def __post_init__(self):
        if not self.billing:
            self.billing = "click" if self.budgeted else "purchase"

    @property
    def budgeted(self) -> bool:
        """월 광고 예산을 나눠 받는 채널인가 (클릭당·노출당). 판매 수수료 채널은 False."""
        return getattr(self.curve, "budgeted", True)


# ── 메타 실무 보강 (명세 2장) ──────────────────────────────────
LEARNING_EVENTS_PER_WEEK = 50  # ✅ 머신 러닝 단계: 광고 세트당 마지막 큰 수정 뒤 7일 안에 결과 약 50개 (메타 도움말, 세팅 카드 meta-lrn-001). 샵 광고는 기준 다름


def cpc_from_cpm(cpm: float, ctr: float) -> float:
    """메타는 노출당 과금이 기본: CPC = CPM ÷ (1000 × CTR). CTR은 0~1."""
    return cpm / (1000 * ctr) if ctr > 0 else float("inf")


def learning_check(monthly_budget: float, ad_sets: int, cpa: float) -> dict:
    """머신 러닝 단계 예산 점검: 광고 세트 수 × 주 50건 × 예상 CPA > 주 예산이면 '제한된 머신 러닝' 경고.
    판정은 이 함수 하나 (코치 가이드 guide.meta_plan도 이걸 부름, 검수 A7). cpa는 메타만의 손님 1명 비용 (A3: ad_setup.channel_cpa)."""
    weekly = monthly_budget / D.WEEKS_PER_MONTH
    need = ad_sets * LEARNING_EVENTS_PER_WEEK * cpa
    return {"weekly_budget": weekly, "weekly_needed": need, "ok": weekly >= need,
            "events_per_set": weekly / cpa / max(ad_sets, 1) if cpa > 0 else float("inf")}
