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


def test_default_budget_pick_follows_action():
    assert C.default_budget_pick("prep") == "none"
    assert C.default_budget_pick("small") == "recommended"
    assert C.default_budget_pick("go") == "recommended"


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


# ── 서비스 진단 6-1 수정 ──
def test_coupang_coupon_prefix():
    from src.engine import measure as MS
    assert MS.coupon_code("coupang", "2611", "coffee").startswith("CP")


def test_short_budget_warning_for_banner():
    _, warn = C.test_budget(max_budget=100_000, be_first=14_000)    # 14,000 × 10 = 140,000 > 100,000
    assert warn and "판매 10건" in warn
    assert C.test_budget(max_budget=1_000_000, be_first=14_000)[1] is None


def test_naver_connection_error_raises_unavailable(monkeypatch):
    import requests
    from src.engine import naver_source as ns

    def broken(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(ns, "_read_cache", lambda *a, **k: None)
    monkeypatch.setattr(ns, "_api_call", lambda: broken)
    with pytest.raises(ns.NaverUnavailable):
        ns.bid_estimate("테스트검색어", online=True)
    with pytest.raises(ns.NaverUnavailable):
        ns.keyword_tool(["테스트검색어"], online=True)


def test_reference_rate_matches_engine_funnel():
    from src.engine import data_loader as dl
    import numpy as np
    steps, _ = dl.funnel_steps()
    visit_to_purchase = float(np.prod([r for _, r in steps[1:]]))
    assert C.REFERENCE_RATES["GA4 공개 샘플 전체"] == pytest.approx(visit_to_purchase, abs=5e-4)


# ── Phase 1: 네이버·메타 배분 ──
def _naver_curve(cap_cost=200_000.0, cap_clicks=400.0):
    import pandas as pd
    from src.engine import NaverCurve
    # 입찰가가 오를수록 클릭당 비용이 오르는 꺾은선 (포화)
    df = pd.DataFrame({"bid": [100, 300, 600, 1000], "cost": [20_000, 60_000, 120_000, cap_cost],
                       "clicks": [80, 180, 290, cap_clicks], "impressions": [0, 0, 0, 0]})
    return NaverCurve({"원두커피": df})


def test_split_budget_fills_naver_before_saturation():
    params = C.coach_params(20_000, 7_000, 0.5)
    small = C.split_budget(20_000, _naver_curve(), 1_300.0, params)       # 네이버 첫 구간 CPC 250원 < 메타 1,300원
    assert small["naver"] == pytest.approx(20_000, rel=0.05) and small["naver"] + small["meta"] == pytest.approx(20_000)
    big = C.split_budget(1_000_000, _naver_curve(), 1_300.0, params)      # 네이버 상한 20만 원 → 나머지는 메타
    assert big["naver"] <= 200_000 + 1 and big["meta"] >= 800_000 - 1
    assert big["naver"] + big["meta"] == pytest.approx(1_000_000)
    assert [r["share"] for r in big["table"]] == list(C.SPLIT_SHARES)


def test_split_budget_without_naver_goes_all_meta():
    params = C.coach_params(20_000, 7_000, 0.5)
    s = C.split_budget(210_000, None, 1_300.0, params)
    assert s["naver"] == 0 and s["meta"] == pytest.approx(210_000) and not s["has_naver"] and s["table"] == []
