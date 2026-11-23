"""5 다음 세팅: 바꿀 칸 1개 + 3줄 요약 (희수 7장 + 진단 규칙)."""
from server.engine.loop import run as loop
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def test_ovenlog_likely_b_means_run_once_more_with_a_budget():
    r = loop.run(read_export(OVEN))
    n = r["next"]
    assert n["action"] == "한 번 더"
    assert n["change"]["field_id"] == "meta.adset.end_date"
    assert len(n["summary"]) == 3
    assert f"{r['verdict']['min_budget']['per_group']:,}" in n["summary"][2]


def test_run_has_all_blocks_and_one_change():
    r = loop.run(read_export(OVEN))
    assert set(r) >= {"check", "summary", "verdict", "replay", "next", "placements"}
    assert isinstance(r["next"]["change"], dict)


def test_single_adset_file_still_gives_a_next_step():
    r = loop.run(read_export("server/tests/fixtures/meta_export_ko.csv"))
    assert r["verdict"] is None and r["next"]["change"]["field_id"]
