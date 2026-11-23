"""0 검증: 파일이 멀쩡한지, 광고가 안 나간 날이 있는지 (희수 5장 ①②, Kohavi 외 2020)."""
from server.engine.loop import check
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def test_reads_shape_of_the_ovenlog_file():
    r = check.run(read_export(OVEN))
    assert r["read"] == {"days": 4, "adsets": 2, "daily_rows": 8, "placement_rows": 11}


def test_totals_of_daily_and_placement_tables_match():
    r = check.run(read_export(OVEN))
    assert {t["metric"] for t in r["totals"]} == {"spend", "impressions", "link_clicks"}
    assert all(t["match"] for t in r["totals"])


def test_warns_about_the_day_nothing_ran():
    r = check.run(read_export(OVEN))
    zero = [w for w in r["warnings"] if w["kind"] == "no_delivery"]
    assert len(zero) == 1 and "11/17" in zero[0]["text"] and "두 세트 모두" in zero[0]["text"]


def test_missing_landing_page_column_is_named(tmp_path):
    from server.engine.meta_export import read_export as rx
    b = rx("server/tests/fixtures/meta_export_ko.csv")
    b.tables["meta_daily"].df = b.tables["meta_daily"].df.drop(columns=["landing_page_views"])
    r = check.run(b)
    assert any("랜딩 페이지 조회" in m for m in r["missing"])


def test_warns_when_auto_placements_pour_money_into_audience_network():
    b = read_export(OVEN)
    p = b.tables["meta_placement"].df
    a = p["adset"] == "A_자동노출위치"
    p.loc[a, "spend"] = 0.0
    p.loc[a & (p["placement"] == p.loc[a, "placement"].iloc[0]), "placement"] = "Audience Network an_classic"
    p.loc[a & (p["placement"] == "Audience Network an_classic"), "spend"] = 5308.0
    r = check.run(b)
    skew = [w for w in r["warnings"] if w["kind"] == "placement_skew"]
    assert len(skew) == 1 and "Audience Network" in skew[0]["text"] and "A_자동노출위치" in skew[0]["text"]


def test_safety_notes_attribution_and_same_audience():
    r = check.run(read_export(OVEN))
    texts = " ".join(s["text"] for s in r["safety"])
    assert "클릭 후 7일" in texts and "같은 사람" in texts
    assert {s["ok"] for s in r["safety"]} == {True, False}
