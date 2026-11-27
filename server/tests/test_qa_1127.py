"""QA 2026-11-27: 분석 페이지 새로고침 복원(N-06), 빠진 열 오류 문장(N-01)."""
import pytest
from fastapi.testclient import TestClient

from server import app as app_module
from server.app import app


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    monkeypatch.setenv("COACH_NO_LLM", "1")
    app_module._HITS.clear()


def test_result_can_be_fetched_again_by_code():
    c = TestClient(app)
    first = c.get("/analysis/example").json()
    again = c.get(f"/analysis/result/{first['code'].lower()}")
    assert again.status_code == 200 and again.json()["code"] == first["code"]
    assert again.json()["verdict"] == first["verdict"]
    gone = c.get("/analysis/result/ZZZZ")
    assert gone.status_code == 404 and "다시 올려" in gone.json()["detail"]


def test_result_lookup_is_rate_limited_for_public_callers():
    c = TestClient(app)
    public = {"cf-connecting-ip": "203.0.113.11"}
    codes = [c.get("/analysis/result/ZZZZ", headers=public).status_code for _ in range(app_module.RATE_PER_MIN + 1)]
    assert codes[-1] == 429


def test_missing_column_message_has_one_todo():
    r = TestClient(app).post("/analysis", files={"file": ("x.csv", "광고 이름,값\n가,1\n".encode(), "text/csv")})
    assert r.status_code == 400
    msg = r.json()["error"]
    assert "열이 없어요 → 이 열을 넣어 다시 내보내 주세요. (받는 곳:" in msg
