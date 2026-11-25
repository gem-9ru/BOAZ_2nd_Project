"""손님 무리(segments) 테스트: 네트워크 없이 search_trend·audience를 가짜로."""
import pandas as pd
import pytest

from server.engine import market, naver_api as api
from server.tests.test_market import isolated, fake_keys, Resp  # noqa: F401

ROWS = [("답례품쿠키", "선물·답례", 2100), ("쿠키선물세트", "선물·답례", 1500),
        ("수제쿠키", "상품", 9300), ("크리스마스쿠키", "시즌", 800)]
KW = pd.DataFrame([{"keyword": k, "intent": i, "total_qc": q} for k, i, q in ROWS])
REC = [r[0] for r in ROWS]
AUD = {"female": 0.7, "ages": {"30": 0.5, "20": 0.2, "40": 0.2, "50": 0.05, "10": 0.03, "60": 0.02},
       "index": {"30": 2.8}, "monthly": {"2025-12": 100, "2025-11": 40}, "peak_month": 12}


def fake_trend(monkeypatch, result, calls=None):
    def f(groups, online=True, start=None, end=None):
        if calls is not None:
            calls.append(groups)
        return result
    monkeypatch.setattr(api, "search_trend", f)


def test_segments_group_by_intent_and_lead_is_top_volume(monkeypatch):
    fake_trend(monkeypatch, None)
    monkeypatch.setattr(market, "audience", lambda k, c, o=True: dict(AUD))
    segs = market.segments(KW, REC, "50000006", online=False)
    assert [s["intent"] for s in segs] == ["상품", "선물·답례", "시즌"]
    assert segs[1]["lead"] == "답례품쿠키"
    assert segs[1]["label"] == "선물로 찾는 손님"
    assert segs[1]["total_qc"] == 3600


def test_one_trend_call_for_all_groups(monkeypatch):
    calls = []
    fake_trend(monkeypatch, None, calls)
    monkeypatch.setattr(market, "audience", lambda k, c, o=True: None)
    market.segments(KW, REC, "50000006", online=False)
    assert len(calls) == 1 and set(calls[0]) == {"상품", "선물·답례", "시즌"}


def test_trend_failure_falls_back_to_shopping_monthly(monkeypatch):
    fake_trend(monkeypatch, None)
    monkeypatch.setattr(market, "audience", lambda k, c, o=True: dict(AUD))
    segs = market.segments(KW, REC, "50000006", online=False)
    assert segs[0]["trend_source"] == "shopping" and segs[0]["trend"]["peak_month"] == 12


def test_search_trend_overrides_audience_monthly(monkeypatch):
    data = {"results": [{"title": "상품", "keywords": [], "data": [
        {"period": "2025-03-01", "ratio": 50.0}, {"period": "2025-04-01", "ratio": 10.0}]}]}
    fake_trend(monkeypatch, data)
    monkeypatch.setattr(market, "audience", lambda k, c, o=True: dict(AUD))
    s = market.segments(KW, REC, "50000006", online=False)[0]
    assert s["trend_source"] == "search" and s["trend"]["peak_month"] == 3
    assert s["trend"]["monthly"]["2025-03"] == 100 and "3월" in s["line"]


def test_keep_filters_and_no_category_skips_audience(monkeypatch):
    fake_trend(monkeypatch, None)
    n = []
    monkeypatch.setattr(market, "audience", lambda *a, **k: n.append(1))
    segs = market.segments(KW, REC, None, online=False, keep=["수제쿠키"])
    assert len(segs) == 1 and segs[0]["intent"] == "상품" and not n
    assert segs[0]["audience"] is None and segs[0]["trend"] is None
    assert segs[0]["line"] == "누가 찾는지 자료가 아직 없어요"


def test_hub_calls_within_15(monkeypatch, isolated):  # noqa: F811
    fake_keys(monkeypatch)
    n = []
    monkeypatch.setattr(api, "_http_hub", lambda keys, path, body: (n.append(1), Resp(200, {"results": []}))[1])
    market.segments(KW, REC, "50000006", online=True)
    assert len(n) <= 15
