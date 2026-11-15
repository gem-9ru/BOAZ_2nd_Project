"""기존 모듈(specs·ingest·effect) 테스트 (P1)."""
import io

import pandas as pd
import pytest

from v2.engine import effect, ingest, metrics, specs

CTX = metrics.Context(start=pd.Timestamp("2026-11-16"), end=pd.Timestamp("2026-12-15"))


@pytest.fixture(scope="module")
def bundle():
    return ingest.demo()


def _csv(df: pd.DataFrame, name: str):
    f = io.BytesIO(df.to_csv(index=False).encode("utf-8-sig"))
    f.name = name
    return f


def _real_meta_export() -> pd.DataFrame:
    """메타 광고 관리자 화면 이름 머리글 (영문 열 이름이 아님)."""
    days = pd.date_range("2026-11-16", periods=3)
    return pd.DataFrame({
        "일": [d.strftime("%Y-%m-%d") for d in days],
        "광고 세트 이름": ["소연베이크_넓게"] * 3,
        "캠페인 목표": ["트래픽"] * 3,
        "지출 금액 (KRW)": ["10,000", "12,000", "9,500"],
        "노출": ["5,000", "6,000", "4,800"],
        "링크 클릭": [60, 75, 50],
        "CPM(1,000회 노출당 비용)": [2000, 2000, 1979],
    })


# ── 사양 ──
def test_specs_check_all_clean():
    assert specs.check_all() == []


def test_rules_have_required_keys():
    for r in specs.rules():
        assert {"id", "title", "funnel", "when", "says"} <= set(r)


# ── 데모 엑셀 ──
def test_demo_reads_five_tables_without_problems(bundle):
    assert bundle.problems == []
    assert set(bundle.tables) == {"meta_daily", "meta_placement", "naver_daily", "store_daily", "survey"}
    assert all(len(t.df) > 0 for t in bundle.tables.values())


def test_demo_cases_and_modes(bundle):
    assert {"C1", "C2", "C3", "C4", "C0", "C1b"} <= set(bundle.cases())
    assert set(bundle.modes()) == {"forecast", "sim"}


def test_demo_select_keeps_one_case_and_mode(bundle):
    one = bundle.select("C2", "sim")
    for t in one.tables.values():
        if "case" in t.df:
            assert set(t.df["case"]) <= {"C2"}       # 설문처럼 그 케이스 행이 없는 표는 비어 있을 수 있음
        if "mode" in t.df:
            assert set(t.df["mode"]) <= {"sim"}
    assert len(one.get("meta_daily")) > 0 and set(one.get("meta_daily")["case"]) == {"C2"}


# ── 머리글 별칭 (실제 메타 내보내기) ──
def test_real_meta_csv_headers_are_recognised():
    b = ingest.read_csvs([_csv(_real_meta_export(), "meta.csv")])
    assert b.problems == []
    df = b.get("meta_daily")
    assert df is not None and len(df) == 3
    assert {"adset", "campaign_objective", "date", "spend", "impressions", "link_clicks"} <= set(df.columns)
    assert df["spend"].tolist() == [10000, 12000, 9500]       # 쉼표 숫자를 읽음
    assert df["date"].iloc[0] == pd.Timestamp("2026-11-16")
    assert set(df["mode"]) == {"real"}


def test_real_meta_csv_english_headers_also_work():
    df = _real_meta_export().rename(columns={
        "일": "Day", "광고 세트 이름": "Ad set name", "캠페인 목표": "Objective",
        "지출 금액 (KRW)": "Amount spent (KRW)", "노출": "Impressions", "링크 클릭": "Link clicks"})
    b = ingest.read_csvs([_csv(df, "meta_en.csv")])
    assert b.problems == [] and len(b.get("meta_daily")) == 3


def test_summary_row_without_date_is_dropped():
    df = _real_meta_export()
    df.loc[len(df)] = ["", "", "", "31,500", "15,800", 185, 2000]
    t, problems = ingest.clean(df, "meta_daily", "meta.csv")
    assert len(t.df) == 3
    assert any("날짜가 없는 행" in p for p in problems)


# ── 필수 열이 없을 때 ──
def test_missing_required_column_message_tells_how_to_fix():
    df = _real_meta_export().drop(columns=["지출 금액 (KRW)"])
    t, problems = ingest.clean(df, "meta_daily", "meta.csv")
    assert t is None
    assert len(problems) == 1
    msg = problems[0]
    assert "meta.csv" in msg
    assert "지출" in msg                                     # 어떤 열이 없는지
    assert "열이 없어요" in msg
    assert "광고 관리자" in msg and "다시 내보내" in msg       # 어디서 어떻게 고치는지


def test_unknown_csv_gives_friendly_problem():
    f = _csv(pd.DataFrame({"가": [1], "나": [2]}), "엉뚱.csv")
    b = ingest.read_csvs([f])
    assert b.tables == {}
    assert b.problems and "엉뚱.csv" in b.problems[0] and "내보내" in b.problems[0]


# ── 효과 (C0 시뮬·정답 비교) ──
def _effect(bundle, case):
    return metrics.case_metrics(bundle.select(case, "sim"), CTX)["effect"]


def test_c0_naive_lift_about_31_percent_and_corrected_near_zero(bundle):
    e = _effect(bundle, "C0")
    assert e.naive_lift == pytest.approx(0.31, abs=0.03)
    assert 0.0 <= e.corrected_lift <= 0.05
    assert e.truth_brand_orders == 0


@pytest.mark.parametrize("case", ["C1", "C2", "C3"])
def test_estimate_within_25_percent_of_truth(bundle, case):
    e = _effect(bundle, case)
    assert e.truth_brand_orders and e.truth_brand_orders > 0
    assert e.extra_brand_orders == pytest.approx(e.truth_brand_orders, rel=0.25)


def test_c4_no_ad_effect_estimated(bundle):
    e = _effect(bundle, "C4")
    assert e.extra_brand_orders == 0


def test_estimate_without_search_columns_is_safe():
    store = pd.DataFrame({"date": pd.date_range("2026-11-01", periods=20), "orders_meta": 1.0, "orders_naver_ad": 1.0})
    e = effect.estimate(store, pd.Timestamp("2026-11-10"), pd.Timestamp("2026-11-15"))
    assert e.naive_lift is None and e.extra_brand_orders == 0.0 and e.truth_brand_orders is None


def test_ad_period_matches_demo(bundle):
    start, end = effect.ad_period(bundle.select("C1", "sim"))
    assert start == pd.Timestamp("2026-11-16") and end == pd.Timestamp("2026-12-15")
