"""2 보정: 숫자 하나 대신 가능한 범위 (베타·감마), 작은 칸은 전체 평균 쪽으로 (Efron & Morris 1975)."""
import numpy as np

from server.engine.loop import posterior, summary
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def arms():
    return summary.run(read_export(OVEN))["arms"]


def test_cpm_95_interval_matches_team_numbers():
    a, b = arms()
    lo, hi = posterior.interval(a, "cpm", level=0.95)
    assert 5850 < lo < 6000 and 6700 < hi < 6850          # 팀 계산 A ₩5,926~6,786
    lo_b, hi_b = posterior.interval(b, "cpm", level=0.95)
    assert hi_b < lo                                       # 안 겹침 → 확실


def test_draws_are_reproducible_and_shaped():
    a, _ = arms()
    d1 = posterior.draws(a, n=1000, seed=1)
    d2 = posterior.draws(a, n=1000, seed=1)
    assert set(d1) == {"cpm", "ctr", "cpc", "click_to_visit", "visits_per_1000won"}
    assert np.array_equal(d1["ctr"], d2["ctr"])


def test_small_placements_are_pulled_to_the_average_and_marked_reference_only():
    rows = [{"placement": "big", "impressions": 5000, "link_clicks": 75},
            {"placement": "tiny", "impressions": 9, "link_clicks": 2}]
    out = {r["placement"]: r for r in posterior.shrink(rows)}
    assert out["tiny"]["reference_only"] is True and out["big"]["reference_only"] is False
    assert 0.015 < out["tiny"]["ctr_adjusted"] < 2 / 9      # 22%가 평균 쪽으로
    assert abs(out["big"]["ctr_adjusted"] - 0.015) < 0.002  # 큰 칸은 거의 그대로
