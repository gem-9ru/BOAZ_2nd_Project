"""메타 광고 관련성 진단 (품질·참여율·전환율 순위): 있으면 퍼널 진단의 보조 신호, 없거나 '-'면 건너뜀 (v4 2장)."""
import pandas as pd

from server.engine.loop.run import run
from server.engine.meta_export import _rank, read_export

FIXTURE = "server/tests/fixtures/meta_export_2sets_no_actions.csv"


def _csv(quality=("평균 이하 - 하위 35%", "평균"), engagement=("평균", "평균 이상"), conversion=("-", "-"), with_cols=True):
    rows = []
    for d in range(4):
        date = f"2026-11-{17 + d}"
        for i, aset in enumerate(("A_자동노출위치", "B_수동노출위치")):
            row = {"보고 시작": date, "보고 종료": date, "광고 세트 이름": aset, "플랫폼": "Instagram", "노출 위치": "Instagram 릴스",
                   "지출 금액 (KRW)": 1300, "노출": 250, "링크 클릭": 5, "랜딩 페이지 조회": 4}
            if with_cols:
                row.update({"품질 순위": quality[i], "참여율 순위": engagement[i], "전환율 순위": conversion[i]})
            rows.append(row)
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def test_rank_words():
    assert _rank("평균 이하 - 하위 10%") == "below" and _rank("Below average - Bottom 35% of ads") == "below"
    assert _rank("평균 이상") == "above" and _rank("Above average") == "above"
    assert _rank("평균") == "average" and _rank("Average") == "average"
    assert _rank("-") is None and _rank("") is None and _rank(float("nan")) is None


def test_rankings_are_read_per_ad_set():
    b = read_export(_csv())
    assert b.rankings == {"A_자동노출위치": {"quality": "below", "engagement": "average"},
                          "B_수동노출위치": {"quality": "average", "engagement": "above"}}   # 전환율 '-'는 건너뜀


def test_below_average_becomes_a_side_signal_on_its_funnel_row():
    m = run(read_export(_csv()))["matrix"]
    assert m["rankings"] is True
    assert m["meta_signals"] == [{"row": "1", "key": "quality",
                                  "text": "메타 품질 순위: A(자동) 평균 이하 — 같은 손님을 두고 경쟁하는 광고보다 소재 품질이 낮게 보여요 → 소재 · 형식"}]
    assert "메타 품질 순위" in next(r for r in m["rows"] if r["row"] == "1")["detail"]


def test_side_signal_does_not_change_the_conclusion():
    with_rank = run(read_export(_csv(quality=("평균 이하 - 하위 10%",) * 2, engagement=("평균 이하 - 하위 10%",) * 2)))["matrix"]
    without = run(read_export(_csv(with_cols=False)))["matrix"]
    assert with_rank["change"]["field_id"] == without["change"]["field_id"]
    assert [r["status"] for r in with_rank["rows"]] == [r["status"] for r in without["rows"]]
    assert {s["row"] for s in with_rank["meta_signals"]} == {"1", "2"}


def test_no_ranking_columns_or_all_dashes_means_skip():
    for csv in (_csv(with_cols=False), _csv(quality=("-", "-"), engagement=("-", "-"))):
        m = run(read_export(csv))["matrix"]
        assert m["rankings"] is False and m["meta_signals"] == []
    assert read_export(FIXTURE).rankings == {}
