"""v4: 판정 상한(표본 부족·지출 쏠림), Test & Roll, 백테스트."""
from server.engine.loop import backtest, simulate, summary, verdict
from server.engine.meta_export import read_export

OVEN = "server/data/demo/오븐로그_메타AB_20261117-20261120.csv"


def test_cap_small_sample_limits_to_likely():
    v = {"badge": {"level": "채택", "word": "확실해요", "better": "B", "prob": 0.95}, "metrics": []}
    out = verdict.apply_caps(v, small_sample=True, spend_gap=False)
    assert out["badge"]["level"] == "유력" and out["badge"]["word"] == "B 쪽이에요"
    assert out["badge"]["capped"]


def test_cap_spend_gap_lowers_one_level():
    v = {"badge": {"level": "유력", "word": "B 쪽이에요", "better": "B", "prob": 0.8}, "metrics": []}
    out = verdict.apply_caps(v, small_sample=False, spend_gap=True)
    assert out["badge"]["level"] == "보류" and out["badge"]["word"] == "아직 몰라요"


def test_test_and_roll_100k_is_6k_to_10k_per_set():
    t = simulate.next_test_budget(100_000)
    assert (t["per_set_lo"], t["per_set_hi"]) == (6000, 10000)   # 4,000원은 하루 1,000원으로 메타 하루 최소(1,336원)보다 적어 6,000원으로 올림 (감사 9)
    assert "Feit" in t["source"]


def test_backtest_predicts_last_day_from_earlier_days():
    bt = backtest.run(read_export(OVEN))
    assert bt["train_days"] == ["2026-11-18", "2026-11-19"] and bt["test_day"] == "2026-11-20"
    for arm in bt["arms"]:
        assert arm["link_clicks"]["lo"] <= arm["link_clicks"]["actual"] <= arm["link_clicks"]["hi"]
        assert arm["visits"]["inside"] is True
    assert "하루치" in bt["note"]
