"""네이버 검색광고 API 호출 안정화 (검수 A2·A4·A5·A6·A10·A11·A12). 실제 네이버를 부르지 않고 가짜 응답으로."""
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import naver_source as ns  # noqa: E402

KW_OK = {"keywordList": [{"relKeyword": "마카롱", "monthlyPcQcCnt": 100, "monthlyMobileQcCnt": "< 10",
                          "monthlyAveMobileClkCnt": 3, "monthlyAveMobileCtr": 1.2, "compIdx": "중간"}]}
EST_OK = {"estimate": [{"bid": b, "impressions": b, "clicks": b / 100, "cost": b * 10} for b in (70, 100, 200)]}


class Clock:
    def __init__(self):
        self.t, self.slept = 1_000_000.0, []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


@pytest.fixture
def env(tmp_path, monkeypatch):
    """캐시 폴더를 임시로, 시계·잠자기를 가짜로, 호출 상태 초기화."""
    clock = Clock()
    monkeypatch.setattr(ns, "CACHE_DIR", tmp_path / "interim")
    monkeypatch.setattr(ns, "EXAMPLE_CACHE_DIR", tmp_path / "examples")
    monkeypatch.setattr(ns, "_now", clock.now)
    monkeypatch.setattr(ns, "_sleep", clock.sleep)
    monkeypatch.setattr(ns, "_STATE", {"rate_hits": [], "paused_until": 0.0, "last_kw": 0.0})
    return clock


def fake(responses, monkeypatch):
    """순서대로 돌려줄 응답 목록. 예외 객체면 그걸 던짐."""
    seq = list(responses)
    calls = []

    def call(method, uri, params=None, body=None):
        calls.append((method, uri, params, body))
        r = seq.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(ns, "_api_call", lambda: call)
    return calls


def test_a2_error_responses_are_not_cached(env, monkeypatch):
    fake([{"code": 403, "title": "Forbidden", "status": 403}], monkeypatch)
    with pytest.raises(ns.NaverUnavailable) as e:
        ns.keyword_tool(["마카롱"])
    assert "권한" in e.value.message
    assert not ns.CACHE_DIR.exists() or not list(ns.CACHE_DIR.glob("*.json"))          # 오류는 캐시에 안 남음
    fake(["<html>깨진 응답</html>"], monkeypatch)                                       # JSON이 아닌 응답
    with pytest.raises(ns.NaverUnavailable):
        ns.bid_estimate("마카롱")
    fake([KW_OK], monkeypatch)                                                           # 다음에 다시 시도하면 정상 → 캐시
    assert ns.keyword_tool(["마카롱"]).iloc[0]["keyword"] == "마카롱"
    assert len(list(ns.CACHE_DIR.glob("keywordstool_*.json"))) == 1


def test_a4_429_waits_long_and_retries_once(env, monkeypatch):
    calls = fake([{"code": 429, "status": 429}, KW_OK], monkeypatch)
    assert ns.keyword_tool(["마카롱"]) is not None and len(calls) == 2
    assert ns.RETRY_WAIT["keywordstool"] in env.slept                                    # 키워드 도구는 길게 쉼
    assert ns.RETRY_WAIT["keywordstool"] >= 5 * ns.RETRY_WAIT["estimate"]


def test_a4_repeated_429_pauses_five_minutes(env, monkeypatch):
    calls = fake([{"code": 1016}, {"code": 1016}], monkeypatch)
    with pytest.raises(ns.NaverUnavailable) as e:
        ns.keyword_tool(["마카롱"])
    assert e.value.code == "paused" and "5분" in e.value.message
    n = len(calls)
    with pytest.raises(ns.NaverUnavailable):                                             # 멈춘 동안은 부르지 않음
        ns.bid_estimate("마카롱")
    assert len(calls) == n
    env.t += ns.PAUSE_SECONDS + 1                                                        # 5분 뒤 다시
    fake([EST_OK], monkeypatch)
    assert ns.bid_estimate("마카롱") is not None


def test_a4_keyword_tool_calls_are_spaced(env, monkeypatch):
    fake([KW_OK, KW_OK], monkeypatch)
    ns.keyword_tool(["마카롱"])
    ns.keyword_tool(["쿠키"])
    assert any(abs(s - ns.KW_GAP) < 1e-6 for s in env.slept)


def test_a10_same_hints_same_cache(env, monkeypatch):
    calls = fake([KW_OK], monkeypatch)
    ns.keyword_tool(["쿠키", "마카롱", "쿠키"])
    ns.keyword_tool(["마카롱", "쿠키"])                       # 순서·중복이 달라도 같은 캐시 → 다시 안 부름
    assert len(calls) == 1 and calls[0][2]["hintKeywords"] == "마카롱,쿠키"


def test_a6_bids_in_key_and_seven_day_refresh(env, monkeypatch):
    calls = fake([EST_OK], monkeypatch)
    ns.bid_estimate("마카롱")
    path = next(ns.CACHE_DIR.glob("estimate_*.json"))
    assert path == ns._cache_path("estimate", f"마카롱|MOBILE|{ns._bids_tag()}")
    env.t = time.time() + 8 * 86_400                                                       # 8일 뒤
    fake([EST_OK], monkeypatch)
    ns.bid_estimate("마카롱")
    assert len(calls) == 1                                                                 # 첫 가짜는 그대로, 새 가짜로 다시 받음
    # 오프라인이면 오래된 캐시를 그대로 쓰고 받은 날짜를 알려 줌
    df = ns.bid_estimate("마카롱", online=False)
    assert df.attrs["source"] == "저장본" and df.attrs["fetched_at"]
    # 다시 받기가 실패하면 지난 저장본
    env.t += 8 * 86_400
    fake([{"code": 503, "status": 503}], monkeypatch)
    assert ns.bid_estimate("마카롱").attrs["source"] == "지난 저장본"


def test_a6_legacy_cache_only_with_same_bids(env, monkeypatch):
    ns.CACHE_DIR.mkdir(parents=True)
    legacy = ns._cache_path("estimate", "마카롱|MOBILE")
    legacy.write_text(json.dumps({"request": {"bids": [70, 100]}, "fetched_at": "2026-11-09 00:00:00", "response": EST_OK}))
    assert ns.bid_estimate("마카롱", online=False) is None                                # 입찰가 목록이 다르면 안 씀
    legacy.write_text(json.dumps({"request": {"bids": list(ns.BIDS)}, "fetched_at": "2026-11-09 00:00:00", "response": EST_OK}))
    assert ns.bid_estimate("마카롱", online=False) is not None


def test_a12_broken_cache_is_ignored(env, monkeypatch):
    ns.CACHE_DIR.mkdir(parents=True)
    ns._cache_path("keywordstool", "마카롱").write_text("{깨짐")
    assert ns.keyword_tool(["마카롱"], online=False) is None
    fake([KW_OK], monkeypatch)
    assert ns.keyword_tool(["마카롱"]) is not None


def test_a5_examples_are_pinned_and_not_refreshed(monkeypatch):
    """예시 1·2 캐시는 data/examples/naver_cache에 고정: 오래돼도, 온라인이어도 다시 받지 않음 (숫자 고정)."""
    calls = fake([], monkeypatch)
    for kw in ("원두커피", "프로틴쉐이크", ns.SAMPLE_KEYWORD):
        df = ns.bid_estimate(kw)
        assert df is not None and df.attrs["source"] == "예시 저장본"
    assert ns.keyword_tool(["원두커피"]).attrs["source"] == "예시 저장본" and calls == []
    root = Path(__file__).resolve().parents[1]
    assert "data/interim/naver_cache/" in (root / ".gitignore").read_text(encoding="utf-8")


@pytest.mark.parametrize("code,word", [("7001", "5개"), ("7002", "두 번"), ("7003", "특수문자"), ("1016", "너무 많아"),
                                       ("429", "너무 많아"), ("403", "권한"), (None, "대략값")])
def test_a11_error_sentences(code, word):
    assert word in ns.error_text(code)
