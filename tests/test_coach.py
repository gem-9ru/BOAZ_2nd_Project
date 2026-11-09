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
    assert C.REPURCHASE_PRESETS == {"거의 안 삼": 0.0, "가끔": 0.5, "자주": 2.0, "매달(정기)": 6.0}


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
    d = C.biggest_drop({"visits": 2000, "views": 1000, "cart": 100, "orders": 20}, labels)
    assert d == ("상품 조회", "장바구니", pytest.approx(0.1))
    assert C.biggest_drop({"visits": 100}, labels) is None


def test_biggest_drop_uses_funnel_diagnosis_rule():
    """B5: '가장 많이 빠지는 단계'는 퍼널 진단 하나(기준 대비 비율)로. 단계마다 원래 비율이 달라 그냥 최솟값은 늘 같은 곳을 짚음."""
    from src.engine import measure as MS
    labels = {"visits": "방문", "views": "상품 조회", "cart": "장바구니", "orders": "구매"}
    # 단계 비율: 조회 25% (기준 22.2%), 담기 24% (기준 19.9%), 사기 30% (기준 33.7%) → 그냥 최솟값은 담기, 기준 대비로는 사기
    totals = {"visits": 1000, "views": 250, "cart": 60, "orders": 18}
    assert MS.diagnose_funnel(totals)["worst"]["key"] == "orders"
    assert C.biggest_drop(totals, labels) == ("장바구니", "구매", pytest.approx(0.3))
    # 판매처 파일에 '방문' 열이 없어도 있는 단계끼리는 짚음 (퍼널 카드는 100명 기준이 없어 안 그림)
    no_visits = {"views": 250, "cart": 60, "orders": 18}
    assert MS.diagnose_funnel(no_visits) is None
    assert C.biggest_drop(no_visits, labels) == ("장바구니", "구매", pytest.approx(0.3))


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
    monkeypatch.setattr(ns, "_read_cache", lambda *a, **k: (None, False))
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
    assert small.naver_spend == pytest.approx(20_000, rel=0.05) and small.naver_spend + small.meta.spend == pytest.approx(20_000)
    big = C.split_budget(1_000_000, _naver_curve(), 1_300.0, params)      # 네이버 상한 20만 원 → 나머지는 메타
    assert big.naver_spend <= 200_000 + 1 and big.meta.spend >= 800_000 - 1
    assert big.naver_spend + big.meta.spend == pytest.approx(1_000_000)
    assert [r["share"] for r in big.table] == list(C.SPLIT_SHARES)


def test_split_budget_without_naver_goes_all_meta():
    params = C.coach_params(20_000, 7_000, 0.5)
    s = C.split_budget(210_000, None, 1_300.0, params)
    assert s.naver_spend == 0 and s.meta.spend == pytest.approx(210_000) and not s.has_naver and s.table == []


def test_breakeven_grid_boundary_matches_formula():
    import numpy as np
    g = C.breakeven_grid(20_000, 0.35, 21_000, 0.5)
    # 본전 선 위(재구매 = 경계)에서 손님 1명 이익 = 0, 손익분기식(breakeven().year = CPA)과 같음
    for p, r in zip(g["prices"], g["boundary"]):
        assert C.breakeven(p * 0.35, r).year == pytest.approx(21_000) or r == 0
    assert g["need_here"] == pytest.approx(21_000 / 7_000 - 1)
    i_lo = np.searchsorted(g["reps"], 1.0)          # 재구매 1번이면 지금 판매가에서 7,000 × 2 = 14,000 < 21,000 → 손해
    j = int(np.argmin(abs(g["prices"] - 20_000)))
    assert g["profit"][i_lo, j] < 0 and g["profit"][-1, j] > 0


def test_split_table_uses_one_month_cohort():
    from src.engine import montecarlo as MC
    params = C.coach_params(20_000, 7_000, 0.5)
    sp = C.split_budget(210_000, _naver_curve(), 1_300.0, params)
    row = next(r for r in sp.table if r["share"] == 0.5)
    det = MC.one_month(sp.channels, [row["naver"], row["meta"]], params)
    assert row["profit_cohort"] == pytest.approx(det["profit"]) and row["profit_first"] <= row["profit_cohort"]
    assert row["profit_cohort"] > -210_000 - 1      # 한 달 광고비보다 크게 잃지 않음 (12개월 집행 기준이 아님)


@pytest.mark.parametrize("rep", [0.5, 2.0, 6.0])
def test_retention_scale_hits_preset_even_with_clipping(rep):
    from src.engine import defaults as D
    from src.engine.model import FunnelParams
    s = C.retention_scale_for(rep, D.RETENTION_FLOOR, D.RETENTION_DECAY, D.PURCHASE_FREQ)
    got = FunnelParams(retention_scale=s).retention(12)[1:].sum() * D.PURCHASE_FREQ
    assert got == pytest.approx(rep, rel=1e-3)


def test_store_stats_one_month():
    import pandas as pd
    from src.engine import measure as MS
    df = pd.DataFrame({"날짜": ["2026.09.30.", "2026.10.01.", "2026-10-02", "20261101"], "유입수": [10, 20, 30, 40], "결제수": [1, 2, 3, 4]})
    col = MS.detect_date_column(df)
    assert col == "날짜" and MS.months_in(df, col) == ["2026-09", "2026-10", "2026-11"]
    oct_ = MS.only_month(df, col, "2026-10")
    assert oct_["결제수"].sum() == 5
    assert MS.detect_date_column(pd.DataFrame({"유입수": [1], "결제수": [1]})) is None


def test_funnel_diagnosis_on_both_demo_examples():
    import pandas as pd
    from pathlib import Path
    from src.engine import measure as MS
    base = Path(__file__).resolve().parents[1] / "data" / "examples" / "demo_store"
    got = {}
    for ex in ("coffee", "protein"):
        df = pd.read_csv(base / ex / "store_stats.csv")
        d = MS.diagnose_funnel(MS.store_totals(df, MS.detect_columns(list(df.columns))))
        assert not d["hold"] and d["per100"][0] == ("들어온", 100.0) and len(d["per100"]) == 4
        got[ex] = d["worst"]["key"]
    assert got == {"coffee": "cart", "protein": "orders"}          # 예시마다 다른 단계가 짚힘


def test_funnel_hold_and_ad_or_store():
    from src.engine import measure as MS
    small = MS.diagnose_funnel({"visits": 50, "views": 20, "cart": 2, "orders": 1})
    assert small["hold"] and small["worst"] is None and MS.ad_or_store(0.02, small) is None
    d = MS.diagnose_funnel({"visits": 1000, "views": 220, "cart": 10, "orders": 4})
    assert d["worst"]["key"] == "cart" and "상세페이지" in d["worst"]["action"]
    assert "가게 쪽" in MS.ad_or_store(0.015, d) and "광고 쪽부터" in MS.ad_or_store(0.004, d)
    assert MS.funnel_baseline()["orders"] == pytest.approx(0.769 * 0.438, abs=1e-3)
    assert MS.diagnose_funnel({"visits": None}) is None
