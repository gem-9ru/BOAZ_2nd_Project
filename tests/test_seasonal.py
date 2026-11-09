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
        raise H.HubError("HTTP 500")
    monkeypatch.setattr(H, "seasonality", boom)
    idx, src = H.seasonality_safe("원두커피", online=True)
    assert idx is None and "미반영" in src
    # 연결·HTTP 오류만 잡음: 코드 버그는 숨기지 않음 (검수 A15)
    def bug(*a, **k):
        raise KeyError("코드 버그")
    monkeypatch.setattr(H, "seasonality", bug)
    with pytest.raises(KeyError):
        H.seasonality_safe("원두커피", online=True)
    # 예시 지수 파일이 있으면 그걸 씀 (평균 1로)
    (tmp_path / "examples").mkdir()
    pd.DataFrame({"month": range(1, 13), "index": [2.0] * 12}).to_csv(tmp_path / "examples" / "원두커피.csv", index=False)
    idx, src = H.seasonality_safe("원두커피", online=False)
    assert idx.mean() == pytest.approx(1.0) and "예시 지수 파일" in src


def test_a1_partial_years_do_not_flatten_season():
    """검수 A1: 2023-11~2026-10처럼 첫해·끝해가 몇 달뿐이어도 꽉 찬 해만 써서 12월/1월 = 2.0 (예전 방식은 1.77)."""
    months = pd.date_range("2023-11-01", "2026-10-01", freq="MS")
    s = pd.Series([100.0 if m.month == 12 else 50.0 for m in months], index=months.strftime("%Y-%m-%d"))
    idx = H.index_from_series(s)
    assert idx[12] / idx[1] == pytest.approx(2.0) and not idx.attrs["partial"]
    assert idx.mean() == pytest.approx(1.0)
    # 꽉 찬 해가 하나도 없으면 예전처럼 + 화면 안내
    short = s.iloc[-8:]
    idx2 = H.index_from_series(short)
    assert idx2.attrs["partial"]


def test_a1_partial_note_on_screen(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(H, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(H, "EXAMPLE_DIR", tmp_path / "examples")
    (tmp_path / "cache").mkdir()
    data = [{"period": f"2026-{m:02d}-01", "ratio": 50.0 + m} for m in range(3, 11)]
    saved = {"request": {"timeUnit": "month", "keywordGroups": [{"groupName": "마카롱", "keywords": ["마카롱"]}]},
             "fetched_at": "2026-11-10 00:00:00", "response": {"results": [{"title": "마카롱", "data": data}]}}
    (tmp_path / "cache" / "search-trend_v1_search_x.json").write_text(json.dumps(saved, ensure_ascii=False))
    idx, src = H.seasonality_safe("마카롱", online=False)
    assert idx is not None and H.PARTIAL_NOTE in src


def test_a1_example_files_follow_full_year_rule():
    for kw in ("원두커피", "프로틴쉐이크", "필라테스"):
        idx = H._from_example(kw)
        assert idx is not None and idx.mean() == pytest.approx(1.0, abs=1e-3)
