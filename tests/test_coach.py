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


def test_detail_page_verdict_pauses_and_restarts_at_minimum():
    # 판매 1건마다 손해라 절반으로 줄여도 손해 → 멈추고, 고친 뒤 첫 구매 손익분기 × 10건으로 재시험 (기획 수정 1)
    v = judge(spend=900_000, clicks=3_000)
    assert v.step == 3 and v.paused
    assert v.next_budget == pytest.approx(BE.first * C.MIN_SALES)
    assert "멈추" in v.title and f"{BE.first * C.MIN_SALES:,.0f}원" in v.detail
    assert not judge(spend=400_000).paused


@pytest.mark.parametrize("preset", list(C.REPURCHASE_PRESETS))
def test_retention_preset_passes_to_next_stage(preset):
    # 코치 프리셋 = 다음 단계 엔진에서 손님 1명의 12개월 재구매 횟수 (기획 수정 2)
    from src.engine import FunnelParams
    from src.engine import defaults as D
    r = C.REPURCHASE_PRESETS[preset]
    scale = C.retention_scale_for(r, D.RETENTION_FLOOR, D.RETENTION_DECAY, D.PURCHASE_FREQ)
    p = FunnelParams(retention_scale=scale)
    assert float(p.retention(12)[1:].sum()) * p.purchase_freq == pytest.approx(r)


# ── v0.9 UX 개편 ─────────────────────────────────────────────

def test_budget_options_three_with_recommended_middle():
    opts = C.budget_options(14_000, 1_000_000)
    assert [o["label"] for o in opts] == ["작게 시작", "권장", "최대"]
    assert [o["amount"] for o in opts] == [140_000, 420_000, 1_000_000]
    assert opts[1]["key"] == "recommended" and opts[1]["error"] == "±18%"


def test_budget_options_when_recommended_exceeds_max():
    opts = C.budget_options(14_000, 300_000)            # 권장 42만 > 최대 30만 → 최대로 맞춤, 작게 시작만 남김
    assert [o["key"] for o in opts] == ["small", "recommended"]
    assert opts[-1]["amount"] == 300_000
    only = C.budget_options(14_000, 100_000)             # 작게 시작 14만도 최대보다 큼 → 최대 하나
    assert len(only) == 1 and only[0]["amount"] == 100_000


def test_expected_and_realized_loss():
    sales, loss = C.expected_loss(420_000, 2_331, 14_000)
    assert sales == pytest.approx(420_000 / 2_331 * 0.0119)
    assert loss == pytest.approx(420_000 - sales * 14_000)
    assert C.expected_loss(140_000, 100, 14_000)[1] < 0      # 음수 = 이익 예상
    assert C.realized_loss(420_000, 12, 14_000) == 420_000 - 12 * 14_000


def test_biggest_drop_from_store_totals():
    labels = {"visits": "방문", "views": "상품 조회", "cart": "장바구니", "orders": "구매"}
    d = C.biggest_drop({"visits": 2000, "views": 1000, "cart": 100, "orders": 20}, labels, list(labels))
    assert d == ("상품 조회", "장바구니", pytest.approx(0.1))
    assert C.biggest_drop({"visits": 100}, labels, list(labels)) is None


def test_default_budget_pick_follows_signal():
    assert C.default_budget_pick("🔴") == "none"
    assert C.default_budget_pick("🟡") == "recommended"
    assert C.default_budget_pick("🟢") == "recommended"


def test_today_kst_uses_seoul_date():
    from datetime import datetime, timezone
    # UTC 11/5 15:30 = 한국 11/6 00:30
    assert C.today_kst(datetime(2026, 11, 5, 15, 30, tzinfo=timezone.utc)).isoformat() == "2026-11-06"
    assert C.today_kst(datetime(2026, 11, 5, 14, 59, tzinfo=timezone.utc)).isoformat() == "2026-11-05"


def test_naver_fallback_cpc_from_q1():
    from src.engine import defaults as D
    assert D.NAVER_FALLBACK_CPC == 1_300.0 > D.META_BASE_CPC


def test_retention_presets_include_uci():
    from src.engine import defaults as D
    floor, decay, _ = D.RETENTION_PRESETS["재구매 많은 업종 (UCI 선물·도매 예시)"]
    assert (floor, decay) == (0.176, 3.37)
    assert D.RETENTION_PRESETS["보통 (일반 쇼핑몰 가정)"][:2] == (D.RETENTION_FLOOR, D.RETENTION_DECAY)
