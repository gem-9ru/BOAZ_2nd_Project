"""계절성 (네이버 데이터랩 검색어 트렌드 → 월별 클릭 배수)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import Channel, FunnelParams, MetaCurve, simulate  # noqa: E402
from src.engine import naver_hub as H  # noqa: E402
from src.engine import seasonal as S  # noqa: E402

IDX = [1.30, 1.03, 1.19, 1.00, 0.87, 0.75, 0.76, 0.85, 0.97, 1.00, 1.00, 1.29]


def test_index_keeps_mean_one():
    assert S.normalize(IDX).mean() == pytest.approx(1.0)
    for start in (1, 6, 11):   # 12개월 연속이면 어디서 시작해도 평균 1
        assert np.mean(S.monthly_multipliers(IDX, start, 12)) == pytest.approx(1.0)
    assert S.monthly_multipliers(IDX, 11, 3)[0] == pytest.approx(S.normalize(IDX)[10])
    assert S.peak_low(IDX) == (1, 6)


def test_simulate_clicks_follow_index_at_same_spend():
    ch = [Channel("meta", "메타", MetaCurve(1000.0, 0.0))]
    base = simulate(ch, [1_000_000], FunnelParams())
    mult = S.monthly_multipliers(IDX, 11, 12)
    seas = simulate(ch, [1_000_000], FunnelParams(season=mult))
    assert seas.monthly["spend"].tolist() == pytest.approx(base.monthly["spend"].tolist())      # 광고비 같음
    assert seas.monthly["clicks"].values == pytest.approx(base.monthly["clicks"].values * np.array(mult))
    assert seas.summary["clicks_total"] == pytest.approx(base.summary["clicks_total"])          # 1년 합 같음
    assert seas.monthly["paid_new"].values == pytest.approx(base.monthly["paid_new"].values * np.array(mult))
    # 지수 없으면 지금과 같음
    assert simulate(ch, [1_000_000], FunnelParams(season=())).summary == base.summary


def test_season_note_boundaries():
    assert S.season_note(None) is None
    assert S.season_note(0.85) is None and S.season_note(1.15) is None and S.season_note(1.0) is None
    assert "비수기" in S.season_note(0.849)
    assert "성수기" in S.season_note(1.151)


def test_seasonality_fallback_without_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(H, "EXAMPLE_DIR", tmp_path / "examples")
    monkeypatch.setattr(H, "_keys", lambda: None)
    idx, src = H.seasonality_safe("원두커피")
    assert idx is None and "계절성 미반영" in src
    assert "검색어 없음" in H.seasonality_safe("")[1]
    # 연결 실패도 앱을 멈추지 않음
    def boom(*a, **k):
        raise RuntimeError("HTTP 500")
    monkeypatch.setattr(H, "seasonality", boom)
    idx, src = H.seasonality_safe("원두커피", online=True)
    assert idx is None and "미반영" in src
    # 예시 지수 파일이 있으면 그걸 씀 (평균 1로)
    (tmp_path / "examples").mkdir()
    pd.DataFrame({"month": range(1, 13), "index": [2.0] * 12}).to_csv(tmp_path / "examples" / "원두커피.csv", index=False)
    idx, src = H.seasonality_safe("원두커피", online=False)
    assert idx.mean() == pytest.approx(1.0) and "예시 지수 파일" in src
