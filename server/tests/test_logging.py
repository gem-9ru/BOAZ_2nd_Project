"""Task 11: 서버 로그. 네트워크 없이 (HTTP 층·Claude는 가짜), caplog로 확인."""
import logging

import pytest
from fastapi.testclient import TestClient

from server.app import app
from server.engine import copywriter, market, naver_api as api
from server.tests.test_api import CACHED_SEEDS
from server.tests.test_market import Resp, isolated  # noqa: F401  (autouse 픽스처 재사용)

SECRET = "SECRET123"
HUB_BODY = {"results": [{"data": [{"period": "2025-11-01", "ratio": 1}]}]}


@pytest.fixture(autouse=True)
def coach_logs_reach_caplog(monkeypatch):
    """앱은 coach 로거를 propagate=False로 두므로, caplog(루트 핸들러)가 받도록 테스트 동안만 켠다."""
    monkeypatch.setattr(logging.getLogger("coach"), "propagate", True)


def secret_keys(monkeypatch):
    monkeypatch.setattr(api, "read_keys", lambda names, env_file=None: {n: SECRET for n in names})


def records(caplog, phrase):
    return [r for r in caplog.records if r.getMessage().startswith(phrase)]


def test_naver_call_logged_with_status_and_ms(monkeypatch, caplog):
    secret_keys(monkeypatch)
    monkeypatch.setattr(api, "_http_hub", lambda keys, path, body: Resp(200, HUB_BODY))
    with caplog.at_level(logging.INFO, logger="coach"):
        api.hub_raw("/shopping/v1/category/keywords", {})
        api.hub_raw(api.SEARCH_TREND, {})
    msgs = [r.getMessage() for r in records(caplog, "naver call")]
    assert "kind=hub" in msgs[0] and "status=200" in msgs[0] and "ms=" in msgs[0]
    assert "kind=trend" in msgs[1]
    assert SECRET not in caplog.text


def test_naver_call_exception_is_warning(monkeypatch, caplog):
    secret_keys(monkeypatch)

    def boom(keys, path, body):
        raise ConnectionError(f"failed with {SECRET}")
    monkeypatch.setattr(api, "_http_hub", boom)
    with caplog.at_level(logging.INFO, logger="coach"):
        try:
            api.hub_raw("/shopping/v1/category/keywords", {})
        except api.NaverError:
            pass
    rec = records(caplog, "naver call")[0]
    assert rec.levelno == logging.WARNING and "status=error" in rec.getMessage() and "err=ConnectionError" in rec.getMessage()
    assert SECRET not in caplog.text


def test_naver_degraded_on_500_without_secrets(monkeypatch, caplog):
    secret_keys(monkeypatch)
    monkeypatch.setattr(api, "_http_hub", lambda keys, path, body: Resp(500, {}))
    with caplog.at_level(logging.DEBUG, logger="coach"):
        assert api.category_keyword_points("50000002", "립밤") is None
    rec = records(caplog, "naver degraded")[0]
    assert rec.levelno == logging.WARNING and "kind=hub" in rec.getMessage()
    assert SECRET not in caplog.text and "X-NCP" not in caplog.text


def test_naver_source_logged_at_debug(caplog):
    with caplog.at_level(logging.DEBUG, logger="coach"):
        api.fetch_cached("hub", "없는키", False, lambda: None)
    assert "naver source kind=hub source=none" in caplog.text


def test_naver_paused_logged(monkeypatch, caplog):
    with caplog.at_level(logging.INFO, logger="coach"):
        api._note_429()
        api._note_429()
    assert records(caplog, "naver paused until=")[0].levelno == logging.WARNING


def test_research_done_logged(monkeypatch, caplog):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    with caplog.at_level(logging.INFO, logger="coach"):
        TestClient(app).post("/research", json={"product": "수제 쿠키", "seeds": CACHED_SEEDS})
    done = records(caplog, "research done")
    assert len(done) == 1
    msg = done[0].getMessage()
    assert "segments=" in msg and "source=" in msg and "ms=" in msg
    assert records(caplog, "segments done") or "segments=0" in msg


def test_category_guess_logged(monkeypatch, caplog):
    monkeypatch.setattr(api, "category_keyword_ratios", lambda c, k, online=True: [100.0] * 12 if c == "50000002" else None)
    with caplog.at_level(logging.INFO, logger="coach"):
        market.category_guess("립밤", False)
    msg = records(caplog, "category guess")[0].getMessage()
    assert "code=50000002" in msg and "top=" in msg


def test_copies_done_template(monkeypatch, caplog):
    monkeypatch.setenv("COACH_NO_LLM", "1")
    with caplog.at_level(logging.INFO, logger="coach"):
        TestClient(app).post("/copies", json={"product": "수제 쿠키", "strengths": ["버터"], "keywords": []})
    assert "copies done source=template" in caplog.text


def test_claude_degraded_logged_without_message(caplog):
    class Boom:
        class messages:
            @staticmethod
            def create(**kw):
                raise RuntimeError(f"leak {SECRET}")
    with caplog.at_level(logging.INFO, logger="coach"):
        assert copywriter._ask_claude(Boom, "meta", "쿠키", ["버터"], 3) == []
    rec = records(caplog, "claude degraded")[0]
    assert rec.levelno == logging.WARNING and "err=RuntimeError" in rec.getMessage()
    assert SECRET not in caplog.text


def test_log_level_falls_back_to_info_when_invalid():
    from server.app import _log_level
    assert _log_level("debug") == "DEBUG" and _log_level("WARNING") == "WARNING"
    assert _log_level("loud") == "INFO" and _log_level(None) == "INFO" and _log_level("") == "INFO"
