"""v4 6장 이상 알림: ■ 차단 · ▲ 주의 · ● 참고. 기준값은 rules.yaml loop.alerts."""
import pandas as pd

from server.engine.loop import alerts, check, summary
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def _run(b, settings=None):
    return alerts.run(b, check.run(b), summary.run(b), settings=settings)


def kinds(out, level=None):
    return [a["kind"] for a in out if level is None or a["level"] == level]


def test_ovenlog_shows_the_three_alerts_the_meeting_listed():
    out = _run(read_export(OVEN))
    assert set(kinds(out)) == {"no_delivery", "small_sample", "meta_vs_measured"}
    nd = next(a for a in out if a["kind"] == "no_delivery")
    assert nd["level"] == "warn" and "11/17" in nd["text"] and nd["screen"] == "AN-01"
    assert next(a for a in out if a["kind"] == "small_sample")["level"] == "warn"
    mvm = next(a for a in out if a["kind"] == "meta_vs_measured")
    assert mvm["level"] == "info" and "자동" in mvm["text"] and "CPM" in mvm["text"]


def test_every_alert_has_shape_level_text_and_fix():
    for a in _run(read_export(OVEN)):
        assert a["level"] in ("block", "warn", "info")
        assert a["mark"] == {"block": "■", "warn": "▲", "info": "●"}[a["level"]]
        assert a["text"] and a["todo"]


def test_alerts_sorted_block_first():
    b = read_export(OVEN)
    b.tables["meta_placement"].df = b.tables["meta_placement"].df.assign(spend=lambda d: d["spend"] * 1.5)
    out = _run(b)
    assert out[0]["level"] == "block" and out[0]["kind"] == "sum_mismatch"


def test_missing_landing_column_blocks():
    b = read_export(OVEN)
    b.tables["meta_daily"].df = b.tables["meta_daily"].df.drop(columns=["landing_page_views"])
    out = _run(b)
    assert "missing_column" in kinds(out, "block")


def test_spend_gap_over_30pp_warns():
    b = read_export(OVEN)
    df = b.tables["meta_daily"].df
    df.loc[df["adset"].str.startswith("A"), "spend"] *= 0.4   # 약 29 : 71
    b.tables["meta_placement"].df = b.tables["meta_placement"].df  # 합계 경고와는 따로 본다
    assert "spend_gap" in kinds(_run(b), "warn")


def test_low_visit_rate_warns():
    b = read_export(OVEN)
    df = b.tables["meta_daily"].df
    df["landing_page_views"] = (df["link_clicks"] * 0.5).round()
    assert "low_visit_rate" in kinds(_run(b), "warn")


def test_budget_underspent_needs_the_setting_value():
    b = read_export(OVEN)
    assert "underspent" not in kinds(_run(b))
    out = _run(b, settings={"meta.adset.daily_budget": "10000"})   # 4일 × 2세트 × 1만 원 = 8만, 1만 원 씀
    assert "underspent" in kinds(out, "warn")
