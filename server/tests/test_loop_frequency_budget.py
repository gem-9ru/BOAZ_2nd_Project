"""ALT-16 반복 노출 · 매트릭스 2b 소재 피로 · ALT-12 예산 덜 씀 — 메타 내보내기(일 × 노출 위치) 그대로 올렸을 때."""
import pandas as pd

from server.engine.loop import alerts, check, matrix, summary
from server.engine.loop.run import run
from server.engine.meta_export import read_export

FIXTURE = "server/tests/fixtures/meta_export_2sets_no_actions.csv"


def _csv(days=8, reach=200, ctr_drop=0.0, budget="캠페인 예산 사용", budget_kind="0", spend=2000):
    """세트 2개 × 노출 위치 2개 × days일. reach = 행마다 도달, ctr_drop = 뒤 절반 클릭이 줄어드는 비율."""
    rows = []
    for d in range(days):
        date = f"2026-11-{10 + d:02d}"
        clicks = 10 if d < days // 2 else round(10 * (1 - ctr_drop))
        for aset in ("A_자동노출위치", "B_수동노출위치"):
            for place in ("Instagram 릴스", "피드"):
                rows.append({"보고 시작": date, "보고 종료": date, "광고 세트 이름": aset, "플랫폼": "Instagram", "노출 위치": place,
                             "도달": reach, "광고 세트 예산": budget, "광고 세트 예산 유형": budget_kind,
                             "지출 금액 (KRW)": spend, "노출": 500, "링크 클릭": clicks, "랜딩 페이지 조회": clicks})
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def _alerts(b, settings=None):
    return alerts.run(b, check.run(b), summary.run(b), settings=settings)


def test_reach_survives_the_placement_export_and_gives_a_frequency_floor():
    b = read_export(_csv(reach=100))
    assert "reach_daily" in b.tables["meta_daily"].df.columns
    arm = summary.run(b)["arms"][0]
    # 하루 노출 1,000 (500 × 2자리) ÷ 도달 합 200 → 적어도 5번
    assert arm["frequency_min"] == 5.0


def test_high_frequency_alert_fires_from_a_real_export():
    out = _alerts(read_export(_csv(reach=100)))
    hf = next(a for a in out if a["kind"] == "high_frequency")
    assert hf["level"] == "warn" and "적어도 5.0번" in hf["text"] and "소재를 바꿀 때예요" in hf["text"]


def test_no_frequency_alert_when_people_saw_it_once_or_twice():
    assert "high_frequency" not in [a["kind"] for a in _alerts(read_export(_csv(reach=400)))]


def test_existing_fixture_with_reach_column_now_has_a_frequency():
    arms = summary.run(read_export(FIXTURE))["arms"]
    assert all(a["frequency_min"] is not None for a in arms)


def test_fatigue_row_blocks_when_frequency_high_and_clicks_drop():
    r = run(read_export(_csv(days=8, reach=100, ctr_drop=0.3)))
    row = next(x for x in r["matrix"]["rows"] if x["row"] == "2b")
    assert row["status"] == "blocked" and row["field_id"] == "meta.ad.media"
    assert r["matrix"]["change"]["row"] == "2b" and r["matrix"]["change"]["tag"] == "테스트 제안"


def test_fatigue_row_is_ok_when_clicks_hold_up():
    r = run(read_export(_csv(days=8, reach=100, ctr_drop=0.0)))
    assert next(x for x in r["matrix"]["rows"] if x["row"] == "2b")["status"] == "ok"


def test_fatigue_row_skips_short_tests():
    r = run(read_export(_csv(days=4, reach=100, ctr_drop=0.3)))
    row = next(x for x in r["matrix"]["rows"] if x["row"] == "2b")
    assert row["status"] == "skip" and "4일" in row["signal"]


def test_underspent_reads_the_budget_from_the_export_itself():
    # 하루 예산 10,000원 × 4일 × 2세트 = 80,000원 설정 · 실제 쓴 돈 2,000원 × 2자리 × 4일 × 2세트 = 32,000원 (40%)
    b = read_export(_csv(days=4, budget="10,000", budget_kind="일일"))
    assert b.budget == {"total": 80000.0, "level": "adset", "kinds": ["daily"]}
    us = next(a for a in _alerts(b) if a["kind"] == "underspent")
    assert "8만 원" in us["text"] and "32,000원" in us["text"]


def test_lifetime_budget_is_not_multiplied_by_days():
    b = read_export(_csv(days=4, budget="20000", budget_kind="총 예산"))
    assert b.budget["total"] == 40000.0   # 세트당 총 20,000원 × 2세트


def test_campaign_budget_or_unknown_type_does_not_guess():
    assert read_export(FIXTURE).budget is None                                    # '캠페인 예산 사용'
    assert read_export(_csv(budget="10000", budget_kind="알 수 없음")).budget is None


def test_settings_budget_still_works_when_the_file_has_none():
    out = _alerts(read_export(_csv(days=4)), settings={"meta.adset.daily_budget": "10,000원"})
    assert "underspent" in [a["kind"] for a in out]


def test_file_budget_wins_over_settings():
    # 파일: 하루 4,000원 × 4일 × 2세트 = 32,000원 (다 씀) · 세팅값 10,000원이면 절반도 못 쓴 셈 → 파일을 믿는다
    out = _alerts(read_export(_csv(days=4, budget="4000", budget_kind="일일")), settings={"meta.adset.daily_budget": "10000"})
    assert "underspent" not in [a["kind"] for a in out]


def test_extension_lifetime_budget_answer_is_per_set_total():
    # 확장 ② 세팅 답 '3만 원' = 세트마다 기간 총예산 → 2세트 6만 원 설정 · 쓴 돈 2,000 × 2자리 × 4일 × 2세트 = 32,000원 (53%) → 알림 없음
    b = read_export(_csv(days=4))
    assert "underspent" not in [a["kind"] for a in _alerts(b, settings={"meta.adset.lifetime_budget": "3만 원"})]
    # '10만 원'이면 20만 원 중 32,000원 → 절반도 못 씀
    us = next(a for a in _alerts(b, settings={"meta.adset.lifetime_budget": "10만 원"}) if a["kind"] == "underspent")
    assert "20만 원" in us["text"]


def test_parse_won():
    assert alerts.parse_won("3만 원") == 30000 and alerts.parse_won("25,000원") == 25000 and alerts.parse_won("x") == 0
