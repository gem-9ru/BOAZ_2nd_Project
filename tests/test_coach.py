"""초보자 코치 (초보자_코치_설계안.md 8장 확정 값)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import coach as C  # noqa: E402

BE = C.breakeven(14_000, C.REPURCHASE_PRESETS["가끔"])   # 첫 구매 1.4만 원, 1년 2.1만 원


def test_breakeven_first_and_year():
    assert BE.first == 14_000 and BE.year == pytest.approx(21_000)
    assert C.breakeven(14_000, 0).year == 14_000
    assert C.REPURCHASE_PRESETS == {"거의 안 삼": 0.0, "가끔": 0.5, "자주": 2.0}


@pytest.mark.parametrize("cpc,light", [(140, "🟢"), (141, "🟡"), (420, "🟡"), (421, "🔴")])
def test_signal_thresholds_on_first_purchase(cpc, light):
    # 필요한 구매 비율 = 클릭 비용 ÷ 첫 구매 손익분기 → 🟢 ≤1% / 🟡 1~3% / 🔴 >3%
    assert C.signal(C.required_rate(cpc, BE.first))[0] == light


def test_first_channel_follows_store():
    assert C.first_channel(["스마트스토어"])[0] == "네이버 쇼핑검색광고"
    assert C.first_channel(["쿠팡"])[0].startswith("쿠팡 광고")
    assert C.first_channel(["자사몰"], monthly_search=1_000)[0] == "네이버 검색광고"
    assert C.first_channel(["자사몰"], monthly_search=999)[0].startswith("메타")
    assert C.first_channel(["매장·예약"])[0] == "네이버 플레이스 광고"
    assert C.first_channel(["자사몰", "스마트스토어"])[0] == "네이버 쇼핑검색광고"   # 여러 곳이면 우선순위


def test_test_budget_and_warning():
    b, w = C.test_budget(3_000_000, 14_000)
    assert b == 14_000 * 30 and w is None
    b, w = C.test_budget(100_000, 14_000)          # 14만 원 미만 → 경고
    assert b == 100_000 and "판단할 만큼" in w


def test_ad_sales_priority():
    s = C.ad_sales(coupon=12, report=20, total=50, baseline=30)
    assert s.value == 12 and s.side_by_side == (12, 20)
    assert C.ad_sales(report=20, total=50).value == 20
    assert C.ad_sales(total=50, baseline=30).value == 20
    s = C.ad_sales(total=50)
    assert s.value == 50 and s.conservative and "광고 외 판매" in s.warning


def judge(days=30, spend=400_000, clicks=1_000, sales=None, cpc=300.0, channel="네이버 쇼핑검색광고"):
    return C.judge(days, spend, clicks, sales or C.ad_sales(coupon=30), BE, cpc, channel)


def test_judge_order():
    assert judge(days=10).step == 0                                     # 14일 미만 보류
    assert judge(sales=C.ad_sales(coupon=9)).step == 0                  # 10건 미만 보류
    assert judge(spend=400_000, sales=C.ad_sales(coupon=30)).step == 1  # CPA 1.33만 ≤ 1.4만 → 계속
    assert judge(spend=400_000).next_budget == pytest.approx(480_000)
    assert judge(spend=600_000).step == 2                               # CPA 2만 ≤ 1년 2.1만 → 유지+재구매
    # CPA 3만 > 2.1만, 구매 비율 30/1000 = 3% > 필요 300/14000 = 2.1% → 클릭이 비쌈
    assert judge(spend=900_000).step == 4
    # 같은 CPA인데 구매 비율 30/3000 = 1% < 2.1% → 상세페이지
    assert judge(spend=900_000, clicks=3_000).step == 3


def test_judge_conservative_when_total_only():
    v = judge(spend=400_000, sales=C.ad_sales(total=30))
    assert v.step == 2 and "늘리지는 않음" in v.title


def test_learning_period_hint_for_meta():
    v = judge(days=5, channel="메타 광고 (인스타그램·페이스북)")
    assert v.step == 0 and "학습" in v.detail
