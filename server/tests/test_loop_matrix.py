"""v4 3장 진단 매트릭스: 위에서부터 처음 막힌 단계의 칸 1개 (+ 유지·지켜보기·하지 말기)."""
from server.engine.loop import run as loop_run
from server.engine.loop import matrix
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def oven():
    return loop_run.run(read_export(OVEN))


def test_ovenlog_change_is_vertical_creative_in_ad_media():
    m = oven()["matrix"]
    c = m["change"]
    assert c["field_id"] == "meta.ad.media"
    assert c["path"] == "광고 › 형식·미디어"
    assert "9:16" in c["new"]
    # v4.2: 돌려 본 적 없는 선택지 → 판정 배지 대신 '테스트 제안', 효과는 '아직 몰라요'. 규칙 신뢰도(유력)는 근거 탭용
    assert c["tag"] == "테스트 제안" and c["tested"] is False
    assert c["certainty"]["level"] == "보류" and c["certainty"]["label"] == "아직 몰라요"
    assert c["rule"]["level"] == "유력"
    assert "6,000원씩" in c["test"]   # 5,000원 ÷ 4일은 메타 하루 최소보다 적어서 올림
    assert c["row"] == "5" and "릴스" in c["reason"]
    assert c["checklist"] == ["두 세트를 같은 날 같이 시작, 시작은 하루 여유 있게", "바꾸는 칸은 형식·미디어 1개만", "4일 동안 그대로 두기",
                              "클릭 30번 미만이면 딱 하루만 연장, 그래도 모자라면 '아직 몰라요'로 마무리"]   # 최종안 ③
    assert len(c["checklist"]) == 4 and not any("ALT" in t for t in c["checklist"])


def test_owner_words_on_rows_and_keep():
    m = oven()["matrix"]
    row1 = next(r for r in m["rows"] if r["row"] == "1")
    assert row1["signal"] == "B(수동)가 15% 싸요 · 확실해요" and "CPM" not in row1["signal"]
    assert m["keep"][0]["reason"].startswith("광고비 15% 싸요")   # ↓는 퍼널 전용 (설계서 AN-03 ③)
    assert m["keep"][0]["value"].startswith("직접 고르기(수동)")
    assert not any("₩" in w["text"] or "유력" in w["text"] for w in m["watch"])


def test_ovenlog_keeps_manual_placement_and_lists_dont():
    m = oven()["matrix"]
    keep = {k["field_id"]: k for k in m["keep"]}
    assert "meta.adset.placements" in keep and "수동" in keep["meta.adset.placements"]["value"]
    assert any("한 번에" in d or "여러 칸" in d for d in m["dont"])
    assert any(w["field_id"] in ("meta.adset.end_date", "meta.adset.daily_budget") for w in m["watch"])


def test_rows_are_checked_top_down_with_status():
    rows = oven()["matrix"]["rows"]
    assert [r["row"] for r in rows] == ["0", "1", "2", "2b", "3", "4", "5", "6"]
    st = {r["row"]: r["status"] for r in rows}
    assert st["2"] == "ok" and st["3"] == "ok"
    assert st["2b"] == "skip" and st["4"] == "skip"
    assert st["5"] == "found"


def test_low_ctr_blocks_before_placement_row():
    b = read_export(OVEN)
    df = b.tables["meta_daily"].df
    df["link_clicks"] = (df["link_clicks"] * 0.2).round()
    df["landing_page_views"] = (df["link_clicks"] * 0.8).round()
    c = loop_run.run(b)["matrix"]["change"]
    assert c["row"] == "2" and c["field_id"] in ("meta.ad.media", "meta.creative.copy")


def test_low_visit_rate_points_at_website_url():
    b = read_export(OVEN)
    df = b.tables["meta_daily"].df
    df["landing_page_views"] = (df["link_clicks"] * 0.4).round()
    c = loop_run.run(b)["matrix"]["change"]
    assert c["row"] == "3" and c["field_id"] == "meta.ad.website_url"


def test_tested_field_is_read_from_set_names():
    assert matrix.tested_field(["A_자동노출위치", "B_피드만노출(AN제외)"]) == "meta.adset.placements"
    assert matrix.tested_field(["A_20대", "B_30대"]) == "meta.adset.age_gender"
    assert matrix.tested_field(["A_문구1", "B_문구2"]) == "meta.creative.copy"
    assert matrix.tested_field(["세트1", "세트2"]) is None
