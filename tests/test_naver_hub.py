"""NAVER API HUB 연결 (네트워크 없이 응답 형식만 검사)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import naver_hub as H  # noqa: E402


def fake_response(values, start="2023-11-01"):
    periods = pd.date_range(start, periods=len(values), freq="MS").strftime("%Y-%m-%d")
    return {"startDate": periods[0], "endDate": periods[-1], "timeUnit": "month",
            "results": [{"title": "원두", "keywords": ["원두"], "data": [{"period": p, "ratio": v} for p, v in zip(periods, values)]}]}


def test_results_frame_shape():
    df = H._results_frame(fake_response([10, 20, 30]))
    assert list(df.columns) == ["원두"] and df["원두"].tolist() == [10, 20, 30]


def test_seasonality_index_mean_one_and_removes_trend(monkeypatch):
    # 해마다 전체 검색량이 2배씩 늘어도, 12월이 다른 달의 2배라는 계절성만 남아야 함
    vals = []
    for y, scale in zip(range(3), (1, 2, 4)):
        vals += [scale * (2 if m == 12 else 1) for m in range(1, 13)]
    monkeypatch.setattr(H, "post", lambda path, body, online=True: fake_response(vals, "2023-01-01"))
    idx = H.seasonality("원두", years=3, end="2025-12-31")
    assert idx.mean() == pytest.approx(1.0)
    assert idx[12] / idx[1] == pytest.approx(2.0)
    assert idx[3] == pytest.approx(idx[7])


def test_no_key_offline_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(H, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(H, "_keys", lambda: None)
    assert H.search_trend({"원두": ["원두"]}, "2025-01-01", "2025-12-31") is None


def test_request_body_limits(monkeypatch):
    seen = {}
    monkeypatch.setattr(H, "post", lambda path, body, online=True: seen.update(path=path, body=body) or {"results": []})
    H.search_trend({f"g{i}": [f"k{j}" for j in range(7)] for i in range(7)}, "2025-01-01", "2025-12-31", gender="f")
    assert seen["path"] == H.SEARCH_TREND
    assert len(seen["body"]["keywordGroups"]) == 5 and all(len(g["keywords"]) == 5 for g in seen["body"]["keywordGroups"])
    assert seen["body"]["gender"] == "f"
