"""4 판정: 우위 확률 90/70% (희수 8장 ④) + 확률 계산·일자별 재현 (다정 M1·M3)."""
import pytest

from server.engine.loop import summary, verdict
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def ab():
    b = read_export(OVEN)
    return b, summary.run(b)["arms"]


def test_badge_is_visits_per_1000won_and_ovenlog_is_likely_b():
    _, (a, b) = ab()
    v = verdict.compare(a, b)
    assert v["badge"]["metric"] == "visits_per_1000won"
    assert v["badge"]["prob"] == pytest.approx(0.79, abs=0.01)      # 다정 79%
    assert (v["badge"]["level"], v["badge"]["better"]) == ("유력", "B")


def test_each_metric_has_prob_and_cpm_is_certain():
    _, (a, b) = ab()
    m = {x["key"]: x for x in verdict.compare(a, b)["metrics"]}
    assert set(m) == {"visits_per_1000won", "cpm", "cpc", "ctr"}
    assert m["cpm"]["prob_b_better"] > 0.99 and m["cpm"]["overlap"] is False
    assert m["ctr"]["prob_b_better"] == pytest.approx(0.61, abs=0.03)


def test_level_rules():
    assert verdict.level(0.95) == "채택" and verdict.level(0.79) == "유력" and verdict.level(0.6) == "보류"


def test_daily_replay_grows_toward_the_final_answer():
    bundle, (a, b) = ab()
    r = verdict.daily_replay(bundle, a["name"], b["name"])
    assert [x["date"] for x in r] == ["2026-11-18", "2026-11-19", "2026-11-20"]   # 아무것도 안 나간 날은 뺌
    assert r[-1]["prob"] == pytest.approx(0.79, abs=0.01)
    assert r[0]["prob"] < r[-1]["prob"]


def test_min_budget_is_more_than_what_was_spent():
    _, (a, _b) = ab()
    m = verdict.min_budget(a, lift=0.2, confidence=0.9, power=0.8, seed=0)
    assert m["per_group"] > a["spend"] and m["per_group"] % 1000 == 0
    assert m["power"] >= 0.8


def test_words_are_the_three_site_wide_phrases():
    assert verdict.word(0.95, overlap=True, better="B") == "확실해요"
    assert verdict.word(0.75, overlap=False, better="B") == "확실해요"      # 범위가 안 겹치면 확실
    assert verdict.word(0.79, overlap=True, better="B") == "B 쪽이에요"
    assert verdict.word(0.6, overlap=True, better="A") == "아직 몰라요"


def test_ovenlog_badge_word_and_cpm_word():
    _, (a, b) = ab()
    v = verdict.compare(a, b)
    assert v["badge"]["word"] == "B 쪽이에요"
    m = {x["key"]: x for x in v["metrics"]}
    assert m["cpm"]["word"] == "확실해요" and m["cpm"]["better"] == "B"
    assert m["ctr"]["word"] == "아직 몰라요"
