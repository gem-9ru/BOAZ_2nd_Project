"""감사 5·9·15·16·19·20 (2026-11-26): 분석 엔진의 숫자·오류."""
from fastapi.testclient import TestClient

from server.app import app
from server.engine.loop import funnel, next_step, simulate, words

HEAD = "보고 시작,보고 종료,광고 세트 이름,지출 금액 (KRW),노출,링크 클릭,랜딩 페이지 조회\n"


def _csv(rows):
    return (HEAD + "".join(f"2026-11-{d},2026-11-{d},{n},{s},{i},{c},{v}\n" for d, n, s, i, c, v in rows)).encode()


def test_a_set_that_never_ran_gives_no_verdict_and_no_500(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    rows = [(d, "A", 0, 0, 0, 0) for d in (18, 19, 20)] + [(d, "B", 1700, 60000, 1300, 1000) for d in (18, 19, 20)]
    r = TestClient(app).post("/analysis", files={"file": ("x.csv", _csv(rows), "text/csv")})
    assert r.status_code == 200
    assert r.json()["verdict"] is None


def test_next_test_budget_never_below_meta_daily_minimum_and_rounds_half_up():
    floor = simulate._loop()["meta_daily_min"]
    least = -(-int(floor * 4) // 1000) * 1000
    for total in (10_000, 50_000, 100_000):
        t = simulate.next_test_budget(total)
        assert t["per_set_lo"] >= least and t["per_set_hi"] >= t["per_set_lo"]
    assert simulate._thousand(2500) == 3000   # round()는 2,000


def test_spend_gap_looks_only_at_the_two_compared_sets():
    from types import SimpleNamespace
    import pandas as pd
    from server.engine.loop import alerts
    arms = [{"name": n, "spend": s, "impressions": 10000, "link_clicks": 100, "landing_page_views": 80, "actions": None, "frequency_min": None}
            for n, s in (("A", 4500), ("B", 4500), ("C", 1000))]
    daily = pd.DataFrame({"date": pd.to_datetime(["2026-11-18"] * 3), "adset": ["A", "B", "C"], "spend": [4500, 4500, 1000], "impressions": [1] * 3})
    bundle = SimpleNamespace(tables={"meta_daily": SimpleNamespace(df=daily)}, budget=None)
    out = alerts.run(bundle, {"warnings": [], "missing": [], "totals": []}, {"arms": arms, "placements": []})
    assert "spend_gap" not in {a["kind"] for a in out}


def test_likely_without_a_reachable_budget_does_not_print_a_question_mark():
    v = {"badge": {"level": "유력", "better": "B", "prob": 0.8}, "a": "A", "b": "B", "min_budget": {"per_group": None}}
    out = next_step.run(v, {"status": "normal", "finding": {"title": "x"}, "changes": []})
    assert "?" not in " ".join(out["summary"])


def test_half_rounds_up_like_the_page_and_rates_never_exceed_100():
    assert words.won(1234.5) == "1,235원"
    assert words.per_people(0.0025, base=1000, unit="번") == "약 3번"
    f = funnel.run([{"name": "A", "impressions": 1000, "link_clicks": 3, "landing_page_views": 4}])
    visit = [s for s in f["arms"][0]["stages"] if s.get("rate") is not None][-1]
    assert visit["rate"] <= 1.0
