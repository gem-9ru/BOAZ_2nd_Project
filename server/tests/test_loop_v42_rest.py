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
