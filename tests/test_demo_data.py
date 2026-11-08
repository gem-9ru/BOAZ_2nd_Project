"""Phase 6: 시연용 가상 데이터가 앱 입력 형식과 맞는지, 개인정보가 없는지."""
import sys
from pathlib import Path

import json

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import measure as MS  # noqa: E402
from src.engine import report as R  # noqa: E402

BASE = ROOT / "data" / "examples" / "demo_store"


@pytest.mark.parametrize("ex,price", [("coffee", 20_000), ("protein", 79_000)])
def test_demo_files_feed_the_coach(ex, price):
    DEMO = BASE / ex
    inputs, pred, started = R.plan_from_json((DEMO / "plan.json").read_text(encoding="utf-8"))
    assert inputs["q_price"] == price and inputs["q_repurchase"] == "매달(정기)" and started == "2026-10-01"
    for f, platform in (("naver_report.csv", "naver"), ("meta_report.csv", "meta")):
        df = pd.read_csv(DEMO / f)
        assert R.detect_platform(list(df.columns)) == platform
        t = R.totals(df, R.map_columns(list(df.columns), platform), platform)
        assert t["cost"] > 0 and t["clicks"] > 0
    stats = pd.read_csv(DEMO / "store_stats.csv")
    assert all(MS.detect_columns(list(stats.columns))[k] for k in ("visits", "orders"))


@pytest.mark.parametrize("ex", ["coffee", "protein"])
def test_demo_orders_have_no_personal_data(ex):
    orders = pd.read_csv(BASE / ex / "orders.csv", dtype=str)
    # 커머스API 개인정보 항목 (커머스API_주문데이터_매핑.md 3장)
    banned = ("ordererName", "ordererTel", "ordererId", "shippingAddress", "pickupLocationContent", "entryMethodContent")
    assert not [c for c in orders.columns if any(b.lower() in c.lower() for b in banned)]
    assert orders["order.ordererNo"].str.startswith("DEMO").all()


def test_demo_verdicts_match_the_story():
    """예시 1은 광고 판매가 거의 없어 판단 보류, 예시 2는 쿠폰 판매로 '계속'."""
    from src.engine import coach as C
    for ex, profit, step in (("coffee", 7_000, 0), ("protein", 39_500, 1)):
        s = json.loads((BASE / ex / "summary.json").read_text(encoding="utf-8"))
        basis = C.ad_sales(s["coupon_orders"], s["report_conversions"], None, None)
        v = C.judge(31, s["spend"], s["clicks"], basis, C.breakeven(profit, 6.0), s["spend"] / s["clicks"], "메타 광고")
        assert v.step == step, (ex, v.title)
        assert s["report_conversions"] > s["ad_orders"]          # 리포트가 실제보다 많이 셈 (과대 집계 시연)


def test_demo_over_count_is_realistic():
    """플랫폼 과대 집계율 = (리포트 전환 − 실제 광고 주문) ÷ 실제 광고 주문이 +30~100% 범위."""
    for ex in ("coffee", "protein"):
        s = json.loads((BASE / ex / "summary.json").read_text(encoding="utf-8"))
        assert s["ad_orders"] > 0
        rate = R.over_count_rate(s["report_conversions"], s["ad_orders"])
        assert 0.3 <= rate <= 1.0, (ex, rate)


def test_demo_ad_or_store_line_differs():
    """예시 1은 광고 클릭률이 낮아 '광고 쪽부터', 예시 2는 클릭률은 정상인데 가게 안에서 빠져 '가게 쪽' (7a)."""
    from src.engine import measure as MS
    lines = {}
    for ex in ("coffee", "protein"):
        reps = []
        for f, pf in (("naver_report.csv", "naver"), ("meta_report.csv", "meta")):
            d = pd.read_csv(BASE / ex / f)
            reps.append(R.totals(d, R.map_columns(list(d.columns), pf), pf))
        ctr = sum(r["clicks"] for r in reps) / sum(r["impressions"] for r in reps)
        s = pd.read_csv(BASE / ex / "store_stats.csv")
        lines[ex] = MS.ad_or_store(ctr, MS.diagnose_funnel(MS.store_totals(s, MS.detect_columns(list(s.columns)))))
    assert "광고 쪽부터" in lines["coffee"] and "가게 쪽" in lines["protein"] and "담고 삼" in lines["protein"]
