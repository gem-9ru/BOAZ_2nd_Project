"""Phase 4: 계획 파일, 리포트 매핑, 진단·과대 집계·예측 오차."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import report as R  # noqa: E402

# 메타 광고 관리자 한국어 내보내기 실제 열 이름 (값은 가짜)
META_COLS = ['보고 시작', '보고 종료', '캠페인 이름', '캠페인 게재', '기여 설정', '결과', '결과 표시 도구', '도달', '빈도',
             '결과당 비용', '광고 세트 예산', '광고 세트 예산 유형', '지출 금액 (KRW)', '종료', '노출',
             'CPM(1,000회 노출당 비용) (KRW)', '링크 클릭', 'shop_clicks', 'CPC(링크 클릭당 비용) (KRW)', 'CTR(링크 클릭률)',
             '클릭(전체)', 'CTR(전체)', 'CPC(전체) (KRW)', '랜딩 페이지 조회', '랜딩 페이지 조회당 비용 (KRW)', '결과(초기)', '결과(초기) 표시 도구']
NAVER_COLS = ["캠페인", "키워드", "노출수", "클릭수", "클릭률(%)", "평균클릭비용(VAT포함,원)", "총비용(VAT포함,원)", "전환수", "전환율(%)", "전환매출액(원)"]


def meta_df(result_kind="actions:offsite_conversion.fb_pixel_purchase", results=(3, 2)):
    rows = []
    for i, r in enumerate(results):
        row = {c: 0 for c in META_COLS}
        row.update({"캠페인 이름": f"c{i}", "결과": r, "결과 표시 도구": result_kind, "도달": 2_000, "노출": 8_000,
                    "지출 금액 (KRW)": "70,000", "링크 클릭": 100, "결과당 비용": 99_999, "CTR(링크 클릭률)": 1.25})
        rows.append(row)
    return pd.DataFrame(rows, columns=META_COLS)


def naver_df():
    return pd.DataFrame([["c", "원두커피", 5_000, 60, 1.2, 1_100, "66,000", 2, 3.3, 40_000],
                         ["c", "원두", 3_000, 30, 1.0, 1_200, "36,000", 1, 3.3, 20_000]], columns=NAVER_COLS)


def test_meta_export_mapping_and_totals():
    assert R.detect_platform(META_COLS) == "meta"
    m = R.map_columns(META_COLS, "meta")
    assert m["cost"] == "지출 금액 (KRW)" and m["clicks"] == "링크 클릭" and m["impressions"] == "노출"
    assert m["conversions"] == "결과" and m["reach"] == "도달" and m["objective"] == "결과 표시 도구"
    t = R.totals(meta_df(), m, "meta")
    assert t["cost"] == 140_000 and t["clicks"] == 200 and t["conversions"] == 5 and t["frequency"] == pytest.approx(4.0)
    # 결과가 구매가 아니면 전환으로 세지 않음
    t2 = R.totals(meta_df("actions:link_click"), m, "meta")
    assert t2["conversions"] == 0 and "구매가 아니라" in t2["conversions_note"] and not t2["objective_is_purchase"]


def test_naver_report_mapping_skips_derived_columns():
    assert R.detect_platform(NAVER_COLS) == "naver"
    m = R.map_columns(NAVER_COLS, "naver")
    assert m["clicks"] == "클릭수" and m["cost"] == "총비용(VAT포함,원)" and m["conversions"] == "전환수"
    assert m["revenue"] == "전환매출액(원)"
    t = R.totals(naver_df(), m, "naver")
    assert t["cost"] == 102_000 and t["conversions"] == 3 and t["impressions"] == 8_000


def test_diagnosis_rules():
    m = R.map_columns(META_COLS, "meta")
    # 목적이 구매가 아님
    titles = [d["title"] for d in R.diagnose(R.totals(meta_df("actions:link_click"), m, "meta"), 0.0126)]
    assert any("목적" in x for x in titles)
    # 클릭률 높고(200/16,000 = 1.25%) 산 비율 낮음(5/200 = 2.5% vs 예측 10%) → 상세페이지
    titles = [d["title"] for d in R.diagnose(R.totals(meta_df(), m, "meta"), 0.10)]
    assert any("상세페이지" in x for x in titles)
    # 빈도 4, 클릭률 낮음 → 소재 피로
    df = meta_df(); df["노출"] = 40_000; df["도달"] = 8_000
    titles = [d["title"] for d in R.diagnose(R.totals(df, m, "meta"), 0.0126)]
    assert any("소재 피로" in x for x in titles)
    # 전환 0 → 측정 확인
    titles = [d["title"] for d in R.diagnose(R.totals(meta_df(results=(0, 0)), m, "meta"), 0.0126)]
    assert any("측정" in x for x in titles)


def test_over_count_and_prediction_error():
    assert R.over_count_rate(5 + 3, 6) == pytest.approx(2 / 6)
    assert R.over_count_rate(5, 0) is None
    assert R.prediction_error(10, 8) == pytest.approx(0.25) and R.prediction_error(None, 8) is None


def test_scaled_curve():
    from src.engine import MetaCurve
    c = R.ScaledCurve(MetaCurve(1_000, 0.0), 0.5)
    assert c.clicks(100_000) == pytest.approx(50) and c.marginal_cpc(0) == pytest.approx(2_000)


def test_bom_meta_export_fixture():
    """실제 메타 내보내기 열 이름 + 가상 숫자, BOM 포함 (원본 파일은 커밋하지 않음)."""
    path = Path(__file__).parent / "fixtures" / "meta_export_fake.csv"
    assert path.read_bytes()[:3] == b"\xef\xbb\xbf"
    assert R.detect_platform(["\ufeff보고 시작", "지출 금액 (KRW)", "링크 클릭"]) == "meta"   # BOM이 열 이름에 남는 읽기 도구 대비
    assert R.map_columns(["\ufeff노출", "링크 클릭"], "meta")["impressions"] == "\ufeff노출"
    df = R.read_report(path)
    assert df.columns[0] == "보고 시작"
    t = R.totals(df, R.map_columns(list(df.columns), "meta"), "meta")
    assert t["cost"] == 140_000 and t["conversions"] == 5


# ── MVP 7e 1단계 (B7). 계획 파일(B3·B4) 테스트는 test_session_schema.py로 ──
def test_b7_naver_average_cost_is_not_cost():
    """'평균클릭비용'만 있고 '총비용'이 없으면 비용 열을 비워 둠 (평균을 합치면 엉뚱한 광고비)."""
    m = R.map_columns(["캠페인", "노출수", "클릭수", "평균클릭비용(VAT포함,원)", "전환수"], "naver")
    assert m["cost"] is None


def test_b7_total_rows_are_dropped():
    df = pd.DataFrame({"캠페인": ["원두", "드립백", "합계"], "노출수": [1_000, 500, 1_500], "클릭수": [10, 5, 15],
                       "총비용(VAT포함,원)": [13_000, 6_500, 19_500], "전환수": [1, 0, 1]})
    t = R.totals(df, R.map_columns(list(df.columns), "naver"), "naver")
    assert t["clicks"] == 15 and t["cost"] == 19_500 and t["conversions"] == 1
    df.loc[2, "캠페인"] = "총계"
    assert R.totals(df, R.map_columns(list(df.columns), "naver"), "naver")["impressions"] == 1_500
