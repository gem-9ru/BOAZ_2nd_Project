"""Task 2: 데이터랩 검색어 트렌드 호출 (저장본·오류 처리). 네트워크 없이."""
import pytest

from server.engine import naver_api as api


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """내 저장본 폴더는 임시 폴더로, 대기는 건너뛰고, 진짜 HTTP는 막는다."""
    monkeypatch.setattr(api, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(api, "_sleep", lambda s: None)
    monkeypatch.setitem(api._STATE, "paused_until", 0.0)
    monkeypatch.setitem(api._STATE, "last_kw", 0.0)
    monkeypatch.setitem(api._STATE, "rate_hits", [])

    class NetworkUsed(BaseException):      # Exception이 아니라서 앱쪽의 넓은 except에도 삼켜지지 않음
        pass

    def boom(*a, **k):
        raise NetworkUsed("테스트에서 네트워크를 쓰면 안 돼요")
    monkeypatch.setattr(api, "_http_ad", boom)
    monkeypatch.setattr(api, "_http_hub", boom)


def no_keys(monkeypatch):
    monkeypatch.setattr(api, "read_keys", lambda names, env_file=None: None)


def fake_keys(monkeypatch):
    monkeypatch.setattr(api, "read_keys", lambda names, env_file=None: {n: "x" for n in names})


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


def test_trend_body_and_cache(monkeypatch):
    fake_keys(monkeypatch)
    seen = []

    def hub(keys, path, body):
        seen.append((path, body))
        return Resp(200, {"results": [{"title": "선물·답례", "data": [{"period": "2025-12-01", "ratio": 100}]}]})
    monkeypatch.setattr(api, "_http_hub", hub)
    g = {"선물·답례": ["답례품쿠키", "쿠키선물세트", "a", "b", "c", "d"]}
    assert api.search_trend(g)["results"][0]["title"] == "선물·답례"
    assert seen[0][0] == "/search-trend/v1/search"
    assert seen[0][1]["keywordGroups"][0]["keywords"] == ["답례품쿠키", "쿠키선물세트", "a", "b", "c"]
    api.search_trend(g)                      # 두 번째는 저장본
    assert len(seen) == 1


def test_trend_without_keys_is_none(monkeypatch):
    no_keys(monkeypatch)
    assert api.search_trend({"상품": ["수제쿠키"]}) is None


def test_trend_error_does_not_escape(monkeypatch):
    fake_keys(monkeypatch)
    monkeypatch.setattr(api, "_http_hub", lambda *a: Resp(500, {}))
    assert api.search_trend({"상품": ["수제쿠키"]}) is None and api.last_error()
