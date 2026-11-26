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


def test_dated_summary_row_without_adset_is_dropped():
    csv = ("보고 시작,광고 세트 이름,지출 금액 (KRW),노출,링크 클릭\n"
           "2026-11-18,A,100,500,5\n2026-11-19,A,100,500,5\n2026-11-18,,200,1000,10\n")
    d = read_export(io.BytesIO(csv.encode("utf-8"))).tables["meta_daily"].df
    assert d["impressions"].sum() == 1000


def test_long_format_without_date_is_a_problem_not_a_crash():
    csv = "section,ad_set,metric,value\n5_부록_일자별,A,노출,10\n"
    b = read_export(io.BytesIO(csv.encode("utf-8")))
    assert "meta_daily" not in b.tables and b.problems


KO_EXPORT = "server/tests/fixtures/meta_export_ko.csv"   # 실제 한국어 광고 관리자 내보내기와 같은 머리글 (이름만 바꿈)


def test_real_korean_export_names_placements_with_their_platform():
    p = read_export(KO_EXPORT).tables["meta_placement"].df
    names = set(p["placement"])
    assert "Instagram 릴스" in names                                  # 이미 플랫폼이 붙은 이름은 그대로
    assert {"Instagram 피드", "Facebook 피드"} <= names               # 같은 '피드'라도 플랫폼별로 나뉜다
    assert "Audience Network 네이티브, 배너 및 전면 광고" in names    # 노출 위치 쏠림 진단이 찾는 글자


def test_real_korean_export_daily_and_audience_network_share():
    from server.engine import metrics
    b = read_export(KO_EXPORT)
    d = b.tables["meta_daily"].df
    assert sorted(d["date"].dt.strftime("%m-%d")) == ["11-17", "11-18"]
    assert d["link_clicks"].sum() == 23                                # 합계 행은 빠진다
    m = metrics.case_metrics(b)
    assert m["an_click_share"] > 0.3                                   # 23번 중 8번이 Audience Network


def test_export_with_no_data_says_so(tmp_path):
    """결과가 없는 기간을 내보내면 메타는 머리글 + 'No data available.' 한 줄을 준다 (2026-11-25 실제 파일).
    '합계 행을 뺐어요' 대신 이 기간에 결과가 없다고 알려야 사장님이 기간을 다시 고른다."""
    p = tmp_path / "empty.csv"
    p.write_text('"보고 시작","보고 종료","광고 세트 이름","노출 위치","지출 금액 (KRW)",노출,"링크 클릭"\n"No data available."\n', encoding="utf-8")
    b = read_export(str(p))
    assert "meta_daily" not in b.tables
    assert b.problems and "결과가 없어요" in b.problems[0] and "합계" not in " ".join(b.problems)
