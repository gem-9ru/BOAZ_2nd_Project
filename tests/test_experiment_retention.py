import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import data_loader as dl  # noqa: E402
from src.engine import naver_source as ns  # noqa: E402
from src.engine.experiment import days_needed, sample_size  # noqa: E402


def test_sample_size_textbook_case():
    # 기준 5% → 5.5% (상대 10%), α 0.05, 검정력 0.8 → 그룹당 약 3.1만 명
    out = sample_size(0.05, 0.10)
    assert out["n_per_group"] == pytest.approx(31_234, rel=0.01)
    assert sample_size(0.05, 0.20)["n_per_group"] < out["n_per_group"]


def test_days_needed():
    assert days_needed(3000, 3000) == 31            # 한 달 = 30.4일 (예전 30일이면 30)
    assert days_needed(1000, 30_400) == 1
    assert days_needed(100, 0) == float("inf")


def test_fit_retention_recovers_parameters():
    t = np.arange(1, 13)
    r = 0.08 + 0.92 * np.exp(-1.3 * t)
    table = dl.retention_curve_table(pd.DataFrame({"months_since": t, "retention": r, "customers": 100}))
    fit = dl.fit_retention(table, fit_months=6)
    assert fit["floor"] == pytest.approx(0.08, abs=1e-3)
    assert fit["decay"] == pytest.approx(1.3, abs=1e-2)
    assert fit["holdout_mae"] < 1e-3


def test_secret_keys_from_env(monkeypatch):
    for k in ns.KEY_NAMES:
        monkeypatch.setenv(k, "x")
    assert ns._secret_keys() == {k: "x" for k in ns.KEY_NAMES}
