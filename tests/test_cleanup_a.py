"""검수 A16·A17·A20·A23 작은 정리 (숫자 변화 없음)."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import attribution as A  # noqa: E402
from src.engine import chat_intake as CI  # noqa: E402
from src.engine import data_loader as dl  # noqa: E402
from src.engine import optimize as O  # noqa: E402


def test_a16_other_sdk_errors_become_unavailable():
    import anthropic

    class Boom:
        messages = None

        def __init__(self):
            self.messages = self

        def create(self, **kw):
            raise anthropic.APIError("이상한 오류", request=SimpleNamespace(), body=None)
    with pytest.raises(CI.IntakeUnavailable):
        CI.call_json(Boom(), "s", [{"role": "user", "content": "x"}], {"type": "object"})


def test_a17_all_failed_gives_zero_split(monkeypatch):
    ch = [SimpleNamespace(budgeted=True), SimpleNamespace(budgeted=True)]
    monkeypatch.setattr(O, "omtm_value", lambda channels, spends, params, omtm: float("nan") if sum(spends) else 0.0)
    out = O.optimize_allocation(ch, 100_000, None, "new_customers")
    assert out["spends"] == [0.0, 0.0]


def test_a20_segment_named_total_and_blank_rows():
    df = pd.DataFrame({"seg": ["전체", "검색", None, ""], "a": [100, 50, 30, 20], "b": [10, 5, 3, 2]})
    out = dl.segment_rates(df, "seg", ["a", "b"])
    assert dl.GA4_ALL in out.index and f"{dl.GA4_ALL} (묶음 값)" in out.index and "nan" not in out.index
    assert out.loc[dl.GA4_ALL, "visitors"] == 150                         # 합계 행 = 빈 묶음 뺀 합
    assert out.loc[f"{dl.GA4_ALL} (묶음 값)", "visitors"] == 100


def test_a23_zero_conversions_do_not_divide_by_zero():
    df = A.clean_paths(pd.DataFrame({"path": ["cpc"], "source_path": ["google"], "conversions": [0]}))
    tab = A.credit_table(df)
    assert np.isfinite(tab.to_numpy()).all()
    t = pd.DataFrame({"last": [0.0, 0.0], "first": [1.0, 0.0]}, index=["a", "b"])
    assert A.correction_factors(t, "first").empty or np.isfinite(A.correction_factors(t, "first")).all()
    import inspect
    assert "lookback_days" not in inspect.signature(A.clean_paths).parameters


def test_a9_keyword_axis_caption_from_tiers():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
    import charts
    assert charts.tier_caption() == "300 미만 롱테일 · 300~1만 세부 · 1만 이상 대표"
    src = (Path(__file__).resolve().parents[1] / "app" / "charts.py").read_text(encoding="utf-8")
    assert "1천~3만" not in src


def test_a18_masked_medium_not_offered():
    from src.engine import defaults as D
    ms = dl.ga4_mediums()
    assert D.GA4_MASKED_MEDIUM not in ms and (not ms or ms[0] == dl.GA4_ALL)


@pytest.mark.parametrize("wins,lvl,word", [(84, "success", "해 볼 만해요"), (60, "warning", "작게 시험"), (3, "error", "준비가 먼저")])
def test_q3_one_verdict_follows_coach(wins, lvl, word):
    from src.engine import insights as I
    got_lvl, text = I.coach_verdict_line(wins)
    assert got_lvl == lvl and word in text and f"100번 해 보면 {wins}번" in text


def test_q3_more_tab_passes_coach_wins():
    main = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    assert "verdict(res.summary, opt_profit[\"spends\"], coach_wins)" in main
    assert "warnings(res, alloc, coach_wins)" in main and "recs, coach_wins)" in main
