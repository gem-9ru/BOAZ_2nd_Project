"""감사 3·4 (2026-11-26): 서버는 공개 주소(Cloudflare 터널)로 누구나 부를 수 있다.
- 3: 터널로 온 요청(cf-connecting-ip)은 주소마다 분당 횟수 제한, 입력 길이 제한 (Claude·네이버 비용)
- 4: 큰 값·망가진 파일로 메모리를 다 쓰거나 500이 나지 않게
사장님 컴퓨터에서 바로 부르는 요청(헤더 없음)은 제한하지 않는다."""
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from server import app as app_module
from server.app import app


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    monkeypatch.setenv("COACH_NO_LLM", "1")
    app_module._HITS.clear()


def test_public_callers_are_rate_limited_but_local_owner_is_not():
    c = TestClient(app)
    body = {"product": "쿠키", "strengths": ["바삭"]}
    public = {"cf-connecting-ip": "203.0.113.9"}
    codes = [c.post("/copies", json=body, headers=public).status_code for _ in range(app_module.RATE_PER_MIN + 1)]
    assert codes[:-1] == [200] * app_module.RATE_PER_MIN and codes[-1] == 429
    assert "많아요" in c.post("/copies", json=body, headers=public).json()["error"]
    assert c.post("/copies", json=body, headers={"cf-connecting-ip": "198.51.100.1"}).status_code == 200   # 다른 주소는 따로 센다
    assert all(c.post("/copies", json=body).status_code == 200 for _ in range(app_module.RATE_PER_MIN + 1))   # 내 컴퓨터


def test_inputs_sent_to_claude_have_length_caps():
    c = TestClient(app)
    assert c.post("/copies", json={"product": "쿠키", "strengths": ["a"] * 20000}).status_code in (413, 422)   # 본문 크기에서 먼저 막힘
    assert c.post("/copies", json={"product": "쿠키", "strengths": ["a"] * 11}).status_code == 422
    assert c.post("/copies", json={"product": "쿠" * 500, "strengths": []}).status_code == 422
    assert c.post("/research", json={"product": "쿠" * 500}).status_code == 422
    assert c.post("/assistant", json={"code": "ABCD", "step": "x" * 500}).status_code == 422


def test_settings_size_is_capped():
    c = TestClient(app)
    assert c.post("/settings", json={"settings": {"meta.adset.lifetime_budget": "3만 원"}}).status_code == 200
    assert c.post("/settings", json={"settings": {"k": "x" * 5_000_000}}).status_code in (400, 413)
    assert c.post("/settings", json={"settings": {f"k{i}": "v" for i in range(500)}}).status_code == 400


def test_bad_numbers_are_400s_not_500s():
    c = TestClient(app)
    code = c.get("/analysis/example").json()["code"]
    arm = c.get("/analysis/example").json()["summary"]["arms"][0]["name"]
    r = c.post("/simulate", content=f'{{"code":"{code}","arm":"{arm}","budget":Infinity}}', headers={"content-type": "application/json"})
    assert r.status_code == 422
    assert c.post("/audience/split", json={"keyword": "쿠키", "category": "50000006", "ages": {"20": "abc"}}).status_code == 422


def test_broken_or_huge_files_get_a_friendly_400():
    c = TestClient(app)
    r = c.post("/analysis", files={"file": ("x.xlsx", b"PK\x03\x04garbage", "application/octet-stream")})
    assert r.status_code == 400 and "읽지 못했어요" in r.json()["error"]
    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/worksheets/sheet1.xml", "0" * (60 * 1024 * 1024))   # 압축하면 작지만 풀면 60MB
    r = c.post("/analysis", files={"file": ("bomb.xlsx", bomb.getvalue(), "application/octet-stream")})
    assert r.status_code == 400 and "너무 커요" in r.json()["error"]
    r = c.post("/settings", content=b"{" + b" " * (200 * 1024) + b"}", headers={"content-type": "application/json"})
    assert r.status_code == 413


def test_api_docs_are_not_published():
    c = TestClient(app)
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


def test_examples_do_not_push_out_the_owners_result():
    """감사 10: 예시를 몇 번 눌러도 사장님 결과 코드는 그대로 (예시는 정해진 코드 EX01·EX02)."""
    c = TestClient(app)
    before = len(app_module._PLANS)
    codes = {c.get("/analysis/example").json()["code"] for _ in range(5)}
    assert codes == {"EX02"} or codes == {"EX01"}
    assert len(app_module._PLANS) == before
    assert c.get(f"/plan/{codes.pop()}").status_code == 200


def test_public_code_lookups_are_counted():
    c = TestClient(app)
    public = {"cf-connecting-ip": "203.0.113.7"}
    codes = [c.get("/plan/ZZZZ", headers=public).status_code for _ in range(app_module.RATE_PER_MIN + 1)]
    assert codes[-1] == 429


def test_naver_wait_is_bounded(monkeypatch):
    """감사 11: 앞 요청이 끝나지 않으면 끝없이 줄 서지 않고 '잠시 뒤' (503)."""
    monkeypatch.setattr(app_module, "NAVER_WAIT", 0.05)
    app_module._NAVER_LOCK.acquire()
    try:
        r = TestClient(app).post("/research", json={"product": "쿠키"})
    finally:
        app_module._NAVER_LOCK.release()
    assert r.status_code == 503 and "잠시 뒤" in r.json()["detail"]


def test_cache_files_are_capped(tmp_path, monkeypatch):
    from server.engine import naver_api
    monkeypatch.setattr(naver_api, "MAX_CACHE_FILES", 5)
    for i in range(9):
        naver_api.save("hub", f"k{i}", {"i": i}, directory=tmp_path)
    assert len(list(tmp_path.glob("*.json"))) == 5
