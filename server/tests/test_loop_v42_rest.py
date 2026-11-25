"""설계서 v4.2 후속: 행동(알림 신청) 숫자 · ALT-14 '세트 합' 기준 · ALT-23 여러 칸 · 날짜별 판정의 표본 부족."""
from server.engine.loop import alerts, check, summary
from server.engine.loop import run as loop_run
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def oven():
    return loop_run.run(read_export(OVEN))


def test_lead_column_is_read_as_actions():
    s = summary.run(read_export(OVEN))
    assert [a["actions"] for a in s["arms"]] == [0.0, 1.0] and s["action_label"] == "알림 신청"


def test_alt14_uses_set_sum_clicks_or_actions_like_the_spec():
    r = oven()
    ss = next(a for a in r["alerts"] if a["kind"] == "small_sample")
    assert ss["text"] == "알림 신청이 1건뿐이라 ④단계는 아직 몰라요."   # 클릭은 세트 합 30이라 기준(30 미만) 밖
    row4 = next(x for x in r["matrix"]["rows"] if x["row"] == "4")
    assert row4["signal"] == "알림 신청 A 0건 · B 1건 → 아직 몰라요"
    assert r["matrix"]["watch"][0]["text"] == "알림 신청이 1건뿐이라 아직 몰라요"
    assert r["verdict"]["badge"]["word"] == "B 쪽이에요"   # 표본 부족이라도 79%는 그대로 'B 쪽이에요'


def test_replay_day_with_too_few_customers_is_still_unknown():
    words = [d["word"] for d in oven()["replay"]]
    assert words == ["아직 몰라요", "아직 몰라요", "B 쪽이에요"]   # 설계서 11/18 26% · 11/19 65% · 11/20 79%


def test_alt23_two_fields_differ_by_set_names():
    b = read_export(OVEN)
    d = b.tables["meta_daily"].df
    d["adset"] = d["adset"].map({"A_자동노출위치": "A_20대_정사각", "B_피드만노출(AN제외)": "B_30대_세로영상"})
    p = b.tables["meta_placement"].df
    p["adset"] = p["adset"].map({"A_자동노출위치": "A_20대_정사각", "B_피드만노출(AN제외)": "B_30대_세로영상"})
    out = alerts.run(b, check.run(b), summary.run(b))
    many = next(a for a in out if a["kind"] == "many_fields")
    assert many["level"] == "info" and many["screen"] == "AN-04" and "어느 칸 덕인지는 몰라요" in many["text"]
    assert "many_fields" not in [a["kind"] for a in oven()["alerts"]]   # 오븐로그는 노출 위치 한 칸만 다름


# ── 예외 파일 (화면 확인 2026-11-25) ──
TWO = "server/tests/fixtures/meta_export_2sets_no_actions.csv"   # 광고 관리자 내보내기, 행동 열 없음, A(자동)가 이김
ONE = "server/tests/fixtures/meta_export_ko.csv"                  # 세트 1개


def test_two_sets_without_actions_still_give_one_test_proposal_not_the_kept_field():
    r = loop_run.run(read_export(TWO))
    assert all(a.get("actions") is None for a in r["summary"]["arms"])
    assert "small_sample" not in [a["kind"] for a in r["alerts"]] and not r["blocked"]
    row4 = next(x for x in r["matrix"]["rows"] if x["row"] == "4")
    assert "파일에 없어요" in row4["signal"]
    keep = r["matrix"]["keep"][0]
    assert keep["field_id"] == "meta.adset.placements" and keep["value"].startswith("자동")
    c = r["matrix"]["change"]   # 막힌 곳이 없으면 문구 하나만 바꿔 비교 (유지할 노출 위치를 바꾸라고 하지 않음)
    assert c["field_id"] == "meta.creative.copy" and c["tag"] == "테스트 제안" and c["what"] == "새 문구"
    assert c["unknown"].startswith("새 문구가 ") and c["per_set"] <= r["summary"]["arms"][0]["spend"]
    assert "A(자동)가" in r["next"]["summary"][0] and "_" not in r["next"]["summary"][0]


def test_single_set_has_no_ad_cost_comparison_and_a_test_proposal():
    r = loop_run.run(read_export(ONE))
    assert r["verdict"] is None
    row1 = next(x for x in r["matrix"]["rows"] if x["row"] == "1")
    assert row1["status"] == "skip" and "세트가 하나" in row1["signal"]
    c = r["matrix"]["change"]
    assert c["field_id"] == "meta.ad.website_url" and c["unknown"].startswith("주소·속도를 고친 페이지가 ")
    assert c["per_set"] == 6000   # 6,660원 쓴 세트 → 내림 (써 본 금액 안)
