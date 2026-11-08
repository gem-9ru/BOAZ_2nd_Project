"""Phase 6: 시연용 가상 데이터가 앱 입력 형식과 맞는지, 개인정보가 없는지."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import measure as MS  # noqa: E402
from src.engine import report as R  # noqa: E402

DEMO = ROOT / "data" / "examples" / "demo_store"


def test_demo_files_feed_the_coach():
    inputs, pred, started = R.plan_from_json((DEMO / "plan.json").read_text(encoding="utf-8"))
    assert inputs["q_price"] == 20_000 and inputs["q_profit"] == 7_000 and started == "2026-10-01" and pred["naver"] == 68_000
    for f, platform in (("naver_report.csv", "naver"), ("meta_report.csv", "meta")):
        df = pd.read_csv(DEMO / f)
        assert R.detect_platform(list(df.columns)) == platform
        t = R.totals(df, R.map_columns(list(df.columns), platform), platform)
        assert t["cost"] > 0 and t["clicks"] > 0
    stats = pd.read_csv(DEMO / "store_stats.csv")
    assert all(MS.detect_columns(list(stats.columns))[k] for k in ("visits", "orders"))


def test_demo_orders_have_no_personal_data():
    orders = pd.read_csv(DEMO / "orders.csv", dtype=str)
    # 커머스API 개인정보 항목 (커머스API_주문데이터_매핑.md 3장)
    banned = ("ordererName", "ordererTel", "ordererId", "shippingAddress", "pickupLocationContent", "entryMethodContent")
    assert not [c for c in orders.columns if any(b.lower() in c.lower() for b in banned)]
    assert orders["order.ordererNo"].str.startswith("DEMO").all()
