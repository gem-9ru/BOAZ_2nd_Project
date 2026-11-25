"""1 실측 요약: 세트별 지표 (희수 4장 지표 정의)."""
import pytest

from server.engine.loop import summary
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def test_arm_totals_and_rates():
    s = summary.run(read_export(OVEN))
    a, b = s["arms"]
    assert (a["name"], a["spend"], a["impressions"], a["link_clicks"], a["landing_page_views"]) == ("A_자동노출위치", 5308, 837, 13, 10)
    assert (b["impressions"], b["link_clicks"], b["landing_page_views"]) == (985, 17, 14)
    assert a["cpm"] == pytest.approx(6342, abs=1)
    assert b["cpm"] == pytest.approx(5389, abs=1)
    assert a["visits_per_1000won"] == pytest.approx(1.88, abs=0.01)
    assert b["visits_per_1000won"] == pytest.approx(2.64, abs=0.01)
    assert a["click_to_visit"] == pytest.approx(10 / 13)


def test_placements_have_spend_share():
    s = summary.run(read_export(OVEN))
    shares = [p["share"] for p in s["placements"]]
    assert sum(shares) == pytest.approx(1.0)
    assert s["placements"][0]["spend"] >= s["placements"][-1]["spend"]   # 지출 큰 순
