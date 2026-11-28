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
            body = {"brands": ["스탠리", "없는말"], "groups": [{"name": "재질", "words": ["스텐", "스탠리"]}, {"name": "크기", "words": ["대용량"]}]}
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(body, ensure_ascii=False))])

    monkeypatch.undo()   # conftest의 가짜 _ask를 풀고 진짜 _ask로
    monkeypatch.setattr(brands, "_known", {})
    monkeypatch.setattr(brands, "_groups", {})
    got, groups = brands.classify("텀블러", ["스탠리", "스텐", "대용량"], client=SimpleNamespace(messages=Msgs()))
    assert got == {"스탠리"}                       # 목록에 없는 말은 받지 않는다
    assert groups == {"스텐": "재질", "대용량": "크기"}   # 브랜드는 묶음에서 빠짐
    sent = json.loads(seen["messages"][0]["content"])
    assert sent == {"상품": "텀블러", "낱말": ["스탠리", "스텐", "대용량"]}   # 숫자(검색수)는 안 보낸다
    assert seen["output_config"]["format"]["type"] == "json_schema"


def test_memory_is_capped(monkeypatch):
    monkeypatch.setattr(brands, "MAX_KNOWN", 3)
    monkeypatch.setattr(brands, "_ask", lambda c, p, ws: (set(), {w: "기능" for w in ws}))
    brands.classify("텀블러", ["보온", "유리"], client=object())
    brands.classify("쿠키", ["버터", "초코"], client=object())
    assert len(brands._known) == 2   # 넘치면 비우고 새로 물은 2개만 남김


def test_known_brand_still_dropped_when_memory_is_emptied(monkeypatch):
    monkeypatch.setattr(brands, "MAX_KNOWN", 3)
    monkeypatch.setattr(brands, "_ask", lambda c, p, ws: ({"스탠리"} & set(ws), {w: "기능" for w in ws if w != "스탠리"}))
    brands.classify("텀블러", ["스탠리", "보온"], client=object())
    got, groups = brands.classify("텀블러", ["스탠리", "보온", "유리", "대용량"], client=object())   # 여기서 상한을 넘어 비움
    assert got == {"스탠리"} and groups == {"보온": "기능", "유리": "기능", "대용량": "기능"}


def test_remembers_words_and_asks_only_new_ones(monkeypatch):
    asked = []
    monkeypatch.setattr(brands, "_ask", lambda c, p, ws: (asked.append(list(ws)) or {"투썸"} & set(ws), {w: "기능" for w in ws if w != "투썸"}))
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
    monkeypatch.setattr(brands, "_ask", lambda c, p, ws: ({w for w in ws if w.startswith("브")}, {w: "기능" for w in ws}))
    monkeypatch.setattr(brands.copywriter, "make_client", lambda: object())
    words = [f"브랜드{i}" for i in range(5)] + [f"좋은점{i}" for i in range(20)]
    out = _good_points("텀블러", _mods(words))
    assert len(out) == 15 and not any(m["word"].startswith("브") for m in out)
    assert {m["group"] for m in out} == {"기능"}   # 묶음 이름은 Claude가 준 것으로


def test_offline_research_never_asks_claude(monkeypatch):
    monkeypatch.setenv("COACH_OFFLINE", "1")
    monkeypatch.setattr(brands, "_ask", lambda *a: (_ for _ in ()).throw(AssertionError("오프라인에서 묻지 않는다")))
    b = TestClient(app).post("/research", json={"product": "수제 쿠키"}).json()
    assert len(b["modifiers"]) <= 15


def test_other_product_words_are_dropped_per_product(monkeypatch):
    """처음 쓰는 사람 따라가기 7: 수제 쿠키의 '커터'(쿠키 틀)는 다른 상품이라 칩에서 뺀다. 상품마다 따로 판단한다."""
    class Msgs:
        def create(self, **kw):
            body = {"brands": [], "others": ["커터"], "groups": [{"name": "맛", "words": ["초코칩"]}]}
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(body, ensure_ascii=False))])

    monkeypatch.undo()
    monkeypatch.setattr(brands, "_known", {})
    monkeypatch.setattr(brands, "_groups", {})
    got, groups = brands.classify("수제 쿠키", ["커터", "초코칩"], client=SimpleNamespace(messages=Msgs()))
    assert got == {"커터"} and groups == {"초코칩": "맛"}
    assert brands.classify("쿠키 틀", ["커터"], client=False)[0] == set()   # 다른 상품에는 기억을 쓰지 않는다
