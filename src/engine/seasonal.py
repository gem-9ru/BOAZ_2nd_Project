"""계절성: 네이버 데이터랩 검색어 트렌드로 만든 월별 계절 지수(1~12월, 평균 1)를 시뮬레이션·코치 문장에 붙인다.

지수 출처: naver_hub.seasonality (최근 3년 월간 검색량을 해마다 평균 1로 맞춘 뒤 같은 달끼리 평균).
가정: 검색량이 평소의 x배인 달은 같은 광고비로 클릭도 x배 (입찰 경쟁·단가 변화는 반영 안 함).
"""
from typing import Optional, Sequence, Tuple

import numpy as np

LOW, HIGH = 0.85, 1.15      # 판정 참고 문장 경계: 지수 < 0.85 비수기, > 1.15 성수기
MONTH_NAMES = [f"{m}월" for m in range(1, 13)]


def normalize(index: Sequence[float]) -> np.ndarray:
    """12개 값을 평균 1로."""
    a = np.asarray(index, dtype=float)
    return a / a.mean() if a.size and a.mean() > 0 else np.ones(12)


def monthly_multipliers(index: Sequence[float], start_month: int, months: int = 12) -> Tuple[float, ...]:
    """1~12월 지수 → 시뮬레이션 1달째(start_month)부터 months개월 배수. 12개월 연속이면 평균이 정확히 1."""
    a = normalize(index)
    return tuple(float(a[(start_month - 1 + i) % 12]) for i in range(months))


def peak_low(index: Sequence[float]) -> Tuple[int, int]:
    """가장 많이·적게 검색되는 달 (1~12)."""
    a = normalize(index)
    return int(np.argmax(a)) + 1, int(np.argmin(a)) + 1


def season_note(value: Optional[float]) -> Optional[str]:
    """한 달 뒤 판정 아래 참고 문장. 판정 기준은 바꾸지 않는다."""
    if value is None:
        return None
    if value < LOW:
        return f"비수기라 클릭이 평소보다 적었을 수 있어요 (이 검색어의 그달 검색량은 평소의 {value:.0%})."
    if value > HIGH:
        return f"성수기라 클릭이 평소보다 많았을 수 있어요. 다음 달엔 줄 수 있어요 (그달 검색량은 평소의 {value:.0%})."
    return None
