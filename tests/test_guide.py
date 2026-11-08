"""Phase 5: 광고 관리자 가이드."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import NaverCurve  # noqa: E402
from src.engine import guide as G  # noqa: E402


def test_meta_objective_rules():
    assert G.meta_plan(0, 50_000, True)["objective"] is None
    assert G.meta_plan(142_000, 100_000, pixel_ready=False)["objective"] == "트래픽"
    p = G.meta_plan(142_000, 100_000, pixel_ready=True)
    assert p["objective"] == "판매" and not p["learning_ok"] and "학습" in p["why"]
    assert G.meta_plan(10_000_000, 10_000, True)["learning_ok"]      # 주 약 230건
    assert {o[0] for o in G.META_OBJECTIVES} == {"인지도", "트래픽", "참여", "잠재 고객", "앱 홍보", "판매"}
    assert all(o[3] in ("✅", "△") for o in G.META_OBJECTIVES)


def test_naver_bid_and_checklist():
    df = pd.DataFrame({"bid": [100, 300, 600, 1000], "cost": [20_000, 60_000, 120_000, 200_000],
                       "clicks": [80, 180, 290, 400], "impressions": [0] * 4})
    c = NaverCurve({"원두커피": df})
    assert G.naver_bid_at(c, 10_000) == 100 and G.naver_bid_at(c, 50_000) == 300 and G.naver_bid_at(c, 10**9) == 1000
    assert G.naver_bid_at(None, 50_000) is None
    items = G.naver_checklist(68_000, 300, "원두커피", ["스마트스토어"])
    assert any("쇼핑검색광고" in i["step"] for i in items)
    assert any(i["step"] == f"하루 예산: {68_000 / 30.4:,.0f}원" for i in items)
    assert all(i["check"] in ("✅", "△", "🧮") for i in items)
    assert any("파워링크" in i["step"] for i in G.naver_checklist(68_000, None, "x", ["자사몰"]))
