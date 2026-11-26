"""좋은 점 칩에서 브랜드·가게 이름 거르기 (Claude, 낱말만)."""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from server.app import _good_points, app
from server.engine import brands


def _mods(words):
    return [{"word": w, "group": "그 밖", "total_qc": 100 - i, "examples": [w + "텀블러"]} for i, w in enumerate(words)]


def test_sends_only_words_and_parses_the_answer(monkeypatch):
    seen = {}

    class Msgs:
        def create(self, **kw):
            seen.update(kw)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"brands": ["스탠리", "없는말"]}))])

    monkeypatch.undo()   # conftest의 가짜 _ask를 풀고 진짜 _ask로
    monkeypatch.setattr(brands, "_known", {})
    got = brands.brand_words("텀블러", ["스탠리", "스텐", "대용량"], client=SimpleNamespace(messages=Msgs()))
    assert got == {"스탠리"}                       # 목록에 없는 말은 받지 않는다
    sent = json.loads(seen["messages"][0]["content"])
    assert sent == {"상품": "텀블러", "낱말": ["스탠리", "스텐", "대용량"]}   # 숫자(검색수)는 안 보낸다
    assert seen["output_config"]["format"]["type"] == "json_schema"


def test_remembers_words_and_asks_only_new_ones(monkeypatch):
    asked = []
    monkeypatch.setattr(brands, "_ask", lambda c, p, ws: asked.append(list(ws)) or {"투썸"} & set(ws))
    assert brands.brand_words("텀블러", ["투썸", "보온"], client=object()) == {"투썸"}
    assert brands.brand_words("텀블러", ["투썸", "보온", "유리"], client=object()) == {"투썸"}
    assert asked == [["투썸", "보온"], ["유리"]]


def test_failure_or_no_key_filters_nothing(monkeypatch):
    def boom(*a):
        raise RuntimeError("x")
    monkeypatch.setattr(brands, "_ask", boom)
    assert brands.brand_words("텀블러", ["스탠리"], client=object()) == set()
    assert brands.brand_words("텀블러", ["스탠리"], client=False) == set()


def test_good_points_drop_brands_then_keep_15(monkeypatch):
    monkeypatch.delenv("COACH_OFFLINE", raising=False)
    monkeypatch.delenv("COACH_NO_LLM", raising=False)
    monkeypatch.setattr(brands, "_ask", lambda c, p, ws: {w for w in ws if w.startswith("브")})
    monkeypatch.setattr(brands.copywriter, "make_client", lambda: object())
    words = [f"브랜드{i}" for i in range(5)] + [f"좋은점{i}" for i in range(20)]
    out = _good_points("텀블러", _mods(words))
    assert len(out) == 15 and not any(m["word"].startswith("브") for m in out)


def test_offline_research_never_asks_claude(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    monkeypatch.setattr(brands, "_ask", lambda *a: (_ for _ in ()).throw(AssertionError("오프라인에서 묻지 않는다")))
    b = TestClient(app).post("/research", json={"product": "수제 쿠키"}).json()
    assert len(b["modifiers"]) <= 15
