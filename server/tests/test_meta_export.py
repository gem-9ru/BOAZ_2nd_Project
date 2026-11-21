import io

from server.engine.meta_export import read_export

DEMO = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def test_ovenlog_splits_into_two_tables():
    b = read_export(DEMO)
    assert {"meta_daily", "meta_placement"} <= set(b.tables)


def test_ovenlog_totals_match_notion():
    d = read_export(DEMO).tables["meta_daily"].df
    by_set = d.groupby("adset")[["spend", "impressions", "link_clicks", "landing_page_views"]].sum()
    assert sorted(by_set["spend"].round()) == [5308, 5308]
    assert sorted(by_set["impressions"]) == [837, 985]
    assert sorted(by_set["link_clicks"]) == [13, 17]
    assert sorted(by_set["landing_page_views"]) == [10, 14]
    assert set(d["campaign_objective"]) == {"트래픽"}


def test_ovenlog_daily_rows_and_short_adset_names():
    d = read_export(DEMO).tables["meta_daily"].df
    assert sorted(d["adset"].unique()) == ["A_자동노출위치", "B_피드만노출(AN제외)"]
    assert sorted(d["date"].dt.strftime("%m-%d").unique()) == ["11-17", "11-18", "11-19", "11-20"]


def test_ovenlog_placements_are_named_for_metrics():
    p = read_export(DEMO).tables["meta_placement"].df
    assert "Instagram instagram_reels" in set(p["placement"])
    a = p[p["adset"] == "A_자동노출위치"]
    assert a["spend"].sum() == 5308 and a["link_clicks"].sum() == 13


def test_empty_file_is_a_problem_not_a_crash():
    b = read_export(io.BytesIO(b""))
    assert not b.tables and b.problems


def test_unknown_columns_are_a_friendly_problem():
    b = read_export(io.BytesIO("이름,나이\n철수,3\n".encode("utf-8")))
    assert not b.tables and "열이 없어요" in " ".join(b.problems)


META_EXPORT = (
    "보고 시작,광고 세트 이름,노출 위치,지출 금액 (KRW),노출,링크 클릭,랜딩 페이지 조회\n"
    "2026-11-18,세트A,Instagram 릴스,1000,200,4,3\n"
    "2026-11-18,세트A,Audience Network 네이티브,500,300,6,1\n"
    "2026-11-19,세트A,Instagram 릴스,800,150,2,2\n"
    "합계,,,2300,650,12,6\n"
)


def test_meta_day_by_placement_export():
    b = read_export(io.BytesIO(META_EXPORT.encode("utf-8")))
    d = b.tables["meta_daily"].df
    assert len(d) == 2 and d["spend"].sum() == 2300 and d["link_clicks"].sum() == 12
    assert set(d["campaign_objective"]) == {"트래픽"}
    p = b.tables["meta_placement"].df
    assert len(p) == 3 and p["placement"].str.contains("Audience Network").sum() == 1
