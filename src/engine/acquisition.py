"""획득 단계: 광고비 → 클릭 (포화 곡선).

- 네이버: 키워드별 '입찰가 → (비용, 클릭)' 예상 실적 점들로 곡선을 만든다.
  예상 실적은 계단 모양이라 점들의 위쪽 볼록 껍질(concave hull)을 쓰고,
  여러 키워드는 한계 CPC가 낮은 구간부터 채우는 방식으로 합친다 (= 네이버 안에서의 최적 배분).
  일 예산 상한으로 한 입찰가의 일부만 쓰는 것이 가능하므로 점 사이 선형 보간을 허용한다.
- 메타: CPC(s) = base_cpc × (1 + saturation × s / 100만 원). 클릭 = s / CPC(s).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

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

    def allocation(self, spend: float) -> pd.DataFrame:
        """주어진 네이버 예산에서 키워드별 광고비·클릭·권장 입찰가."""
        left = self.spendable(spend)
        rows: Dict[str, dict] = {kw: {"keyword": kw, "spend": 0.0, "clicks": 0.0, "bid": 0.0} for kw in self.points}
        for seg in self.segments:
            if left <= 0:
                break
            frac = min(1.0, left / seg["dcost"])
            row = rows[seg["keyword"]]
            row["spend"] += seg["dcost"] * frac
            row["clicks"] += seg["dclicks"] * frac
            row["bid"] = max(row["bid"], seg["bid"])
            left -= seg["dcost"] * frac
        out = pd.DataFrame(rows.values())
        out["cpc"] = np.where(out["clicks"] > 0, out["spend"] / out["clicks"].where(out["clicks"] > 0), np.nan)
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


@dataclass
class Channel:
    key: str            # "naver", "meta", ...
    label: str          # 화면 표시 이름
    curve: object       # NaverCurve | MetaCurve (clicks(), spendable(), marginal_cpc())
    cvr_mult: float = 1.0        # 이 채널 클릭의 최종 전환율 배수 (구매 의도 차이)
    retention_mult: float = 1.0  # 이 채널 고객의 리텐션 배수
