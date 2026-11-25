"""5 다음 세팅: 바꿀 칸 1개 + 3줄 요약 (희수 7장 + 진단 규칙)."""
from server.engine.loop import run as loop
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def test_ovenlog_change_comes_from_the_matrix_and_budget_goes_to_watch():
    # v4 회의(2026-11-25): 결론은 '바꿀 칸 1개'(매트릭스). 유력 판정의 추가 예산은 '지켜보기'로.
    r = loop.run(read_export(OVEN))
    n = r["next"]
    assert n["action"] == "한 번 더"
    assert n["change"]["field_id"] == "meta.ad.media"
    assert len(n["summary"]) == 3 and "형식·미디어" in n["summary"][2]
    # v4.2: 추가 예산 숫자는 화면 글이 아니라 값으로만 (🔎 안에서 보여 줌)
    per = r["verdict"]["min_budget"]["per_group"]
    assert any(w.get("need_per_set") == per for w in r["matrix"]["watch"])


def test_run_has_all_blocks_and_one_change():
    r = loop.run(read_export(OVEN))
    assert set(r) >= {"check", "summary", "verdict", "replay", "next", "placements"}
    assert isinstance(r["next"]["change"], dict)


def test_single_adset_file_still_gives_a_next_step():
    r = loop.run(read_export("server/tests/fixtures/meta_export_ko.csv"))
    assert r["verdict"] is None and r["next"]["change"]["field_id"]
