"""분석 페이지 점검(2026-11-26) 1~10번: 빈 랜딩 페이지 열 · 다른 날 돌린 세트 · 여러 칸이 함께 다름 · 하루 최소 예산 · 쉬운 말."""
import pandas as pd

from server.engine.loop import alerts, check, summary
from server.engine.loop.run import run
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"
HEESU = "server/data/demo/모닝빈_메타AB_20261117-20261120.csv"


def _csv(sets=(("A_자동노출위치", range(4)), ("B_수동노출위치", range(4))), lpv="same"):
    """세트마다 돌린 날(0부터) · lpv: 'same'(클릭과 같음) / 'empty'(열은 있는데 빈칸) / 'none'(열 없음)."""
    rows = []
    for name, days in sets:
        for d in days:
            date = f"2026-11-{10 + d:02d}"
            for place in ("Instagram 릴스", "피드"):
                row = {"보고 시작": date, "보고 종료": date, "광고 세트 이름": name, "플랫폼": "Instagram", "노출 위치": place,
                       "지출 금액 (KRW)": 2000, "노출": 500, "링크 클릭": 10}
                if lpv != "none":
                    row["랜딩 페이지 조회"] = 8 if lpv == "same" else None
                rows.append(row)
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def _alerts(b):
    return alerts.run(b, check.run(b), summary.run(b))


# 3 · 4: 열은 있는데 칸이 비었으면 '없어요'가 아니라 '비어 있어요', 그리고 0명으로 세지 않는다
def test_empty_landing_column_says_empty_not_missing():
    out = _alerts(read_export(_csv(lpv="empty")))
    block = next(a for a in out if a["kind"] == "missing_column")
    assert "비어 있어요" in block["text"] and "픽셀" in block["todo"]
    assert "비어 있어요" in check.run(read_export(_csv(lpv="empty")))["missing"][0]


def test_missing_landing_column_still_says_missing():
    out = _alerts(read_export(_csv(lpv="none")))
    assert any(a["kind"] == "missing_column" and "열이 없어요" in a["text"] for a in out)


def test_empty_landing_column_gives_no_low_visit_alerts():
    assert not any(a["kind"] == "low_visit_rate" for a in _alerts(read_export(_csv(lpv="empty"))))


def test_low_visit_alert_uses_real_counts():
    csv = _csv(lpv="same").decode().replace(",8\n", ",1\n").encode()   # 클릭 10 중 도착 1
    lv = next(a for a in _alerts(read_export(csv)) if a["kind"] == "low_visit_rate")
    assert "누른 80명 중 8명만" in lv["text"] and "10명 중" not in lv["text"]


# 5: 같은 날 같이 돌리지 않은 두 세트는 비교하지 않는다 · 세트가 3개 이상이면 앞 두 개만 비교했다고 알린다
def test_sets_run_on_different_days_are_blocked():
    b = read_export(_csv(sets=(("A_자동노출위치", range(0, 3)), ("B_수동노출위치", range(5, 8)))))
    nd = next(a for a in _alerts(b) if a["kind"] == "not_same_days")
    assert nd["level"] == "block" and "같은 날" in nd["text"]


def test_sets_that_share_only_a_sliver_of_spend_are_blocked():
    # 실제 내보내기: 한 세트는 6/13~15, 다른 세트는 6/15 하루 → 겹친 날 1일이지만 A 돈은 거의 다 다른 날
    b = read_export(_csv(sets=(("A_자동노출위치", range(0, 5)), ("B_수동노출위치", range(4, 6)))))
    assert any(a["kind"] == "not_same_days" for a in _alerts(b))


def test_three_sets_say_only_two_were_compared():
    b = read_export(_csv(sets=(("A_자동노출위치", range(4)), ("B_수동노출위치", range(4)), ("C_소재", range(4)))))
    extra = next(a for a in _alerts(b) if a["kind"] == "extra_sets")
    assert "3개" in extra["text"] and "C_소재" in extra["text"]


def test_overlapping_sets_are_not_blocked():
    assert not any(a["kind"] == "not_same_days" for a in _alerts(read_export(OVEN)))


# 6: 희수 실험은 노출 위치와 연령을 함께 바꿨다 → '노출 위치 덕분'이라고 하지 않는다
def test_heesu_keep_card_does_not_credit_placement_alone():
    r = run(read_export(HEESU))
    keep = r["matrix"]["keep"][0]
    assert not keep["reason"].startswith("↓")   # 점검 N: ↓는 퍼널 '비교보다 나쁨' 전용
    assert keep["title"] == keep["value"] and "노출 위치" in keep["value"] and "연령" in keep["value"] and "어느 칸 덕인지는 몰라요" in keep["reason"]
    mvm = next(a for a in r["alerts"] if a["kind"] == "meta_vs_measured")
    assert "연령" in mvm["text"] and "어느 칸 덕인지는 몰라요" in mvm["text"]


def test_ovenlog_keep_card_still_credits_placement():
    keep = run(read_export(OVEN))["matrix"]["keep"][0]
    assert keep["value"].startswith("직접 고르기(수동)") and keep["reason"] == "광고비 15% 싸요 · 확실해요"


# 7: 날짜별 판정도 같은 이유(돈 쏠림)로 낮춘다 → 마지막 날 판정 = 큰 판정
def test_heesu_replay_last_day_matches_capped_badge():
    r = run(read_export(HEESU))
    assert r["verdict"]["badge"]["word"] == "아직 몰라요"
    assert r["replay"][-1]["word"] == r["verdict"]["badge"]["word"]


# 8 · 9: '④단계' 대신 단계 이름, 지켜보기 이유는 기간·예산과 이어지게
def test_small_sample_names_the_stage_and_watch_says_what_to_do():
    r = run(read_export(OVEN))
    ss = next(a for a in r["alerts"] if a["kind"] == "small_sample")
    # 점검 O: 화면설계서 v4.2 AN-02·AN-01 문구 그대로
    assert ss["text"] == "알림 신청이 1건뿐이라 ④단계는 아직 몰라요."
    assert r["matrix"]["watch"][0]["text"] == "알림 신청이 1건뿐이라 아직 몰라요"


# 1: 다음 테스트 금액은 메타 하루 최소보다 많이 (하루 = 세트당 총액 ÷ 기간)
def test_next_test_budget_clears_meta_daily_minimum():
    for path in (OVEN, HEESU):
        c = run(read_export(path))["matrix"]["change"]
        assert c["days"] == 4 and c["per_set"] / c["days"] >= 1336
        assert c["per_set"] == 6000 and "6,000원" in c["test"]


# 점검 A: 노출은 사람 수가 아니라 보여진 횟수
def test_click_rate_is_told_in_times_not_people():
    r = run(read_export(OVEN))
    row2 = next(x for x in r["matrix"]["rows"] if x["row"] == "2")
    assert row2["signal"].startswith("1,000번 보이면 약 16번 눌려요") and "명" not in row2["signal"]


# 점검 L: 화면설계서 v4.2 AN-06 ② — 끝이 있는 '그대로 두기'
def test_checklist_wait_item_has_an_end_like_the_spec():
    c = run(read_export(OVEN))["matrix"]["change"]
    assert "클릭 30번 미만이면 딱 하루만 연장, 그래도 모자라면 \"아직 몰라요\"로 마무리" in c["checklist"]
    assert not any("모일 때까지" in t for t in c["checklist"])


# 점검 M: 화면설계서 v4.2 AN-TXT 용어표 — 랜딩 페이지 조회 = '방문자' ('손님'은 구매로 들려서 안 씀)
def test_analysis_result_says_visitor_not_customer():
    import json
    from server.engine.loop import assistant
    for path in (OVEN, HEESU):
        r = run(read_export(path))
        assert "손님" not in json.dumps(r, ensure_ascii=False)
        for step in ("AN-01", "AN-02", "AN-03", "AN-04", "AN-05", "AN-06"):
            assert "손님" not in json.dumps(assistant.opening(r, step), ensure_ascii=False)


# 점검 S: 화면설계서 v4.2 AN-06 '세트당 총 5,000원, 4일 (Test & Roll 권장 범위 안)'
def test_next_test_says_whether_it_is_inside_test_and_roll():
    assert run(read_export(OVEN))["matrix"]["change"]["test_roll"] is True   # 6,000원 ∈ 10만 원 기준 4,000~10,000원


# 점검 Q: 화면설계서 v4.2 AN-00 '허용: .csv / .xlsx'
def test_excel_export_reads_like_csv(tmp_path):
    df = pd.read_csv(OVEN)
    path = tmp_path / "x.xlsx"
    df.to_excel(path, index=False)
    a, b = read_export(OVEN), read_export(path.read_bytes())
    assert not b.problems and b.tables["meta_daily"].df["spend"].sum() == a.tables["meta_daily"].df["spend"].sum()
