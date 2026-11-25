"""Task 4: 꾸밈말(좋은 점 후보). 네트워크 없이."""
import pandas as pd

from server.engine import market
from server.tests.test_market import SEEDS, classified, isolated  # noqa: F401  (픽스처 재사용)


def _table(keywords, qcs):
    """_frame 열 형식의 작은 표."""
    n = len(keywords)
    return pd.DataFrame({"keyword": keywords, "total_qc": qcs, "mobile_qc": qcs, "pc_qc": [0] * n,
                         "mobile_clicks": [0.0] * n, "mobile_ctr": [0.0] * n, "comp": ["낮음"] * n,
                         "tier": [market.tier_of(q) for q in qcs]})


def test_modifiers_from_small_table():
    kw = market.classify(_table(["개별포장쿠키", "쿠키개별포장", "버터쿠키", "수제쿠키추천", "쿠키선물"],
                                [700, 500, 900, 300, 2000]), ["쿠키"])
    out = market.modifiers(kw, ["쿠키"])
    words = {m["word"]: m for m in out}
    assert words["개별포장"]["total_qc"] == 1200 and words["개별포장"]["group"] == "포장"
    assert sorted(words["개별포장"]["examples"]) == ["개별포장쿠키", "쿠키개별포장"]
    assert words["버터"]["group"] == "맛·재료"
    assert words["수제"]["total_qc"] == 300
    assert "추천" not in words and "선물" not in words
    assert [m["total_qc"] for m in out] == sorted((m["total_qc"] for m in out), reverse=True)


def test_modifiers_edge_cases():
    kw = market.classify(_table(["쿠키", "쿠키100", "쿠키가격", "쿠키일곱글자넘는꾸밈말", "독특쿠키", "크리스마스쿠키"],
                                [9000, 800, 700, 600, 500, 400]), ["쿠키"])
    out = market.modifiers(kw, ["쿠키"])
    assert [(m["word"], m["group"]) for m in out] == [("독특", "그 밖")]
    assert len(market.modifiers(kw, ["쿠키"], limit=0)) == 0


def test_modifiers_on_cached_real_data_are_15_or_less(classified):  # noqa: F811
    out = market.modifiers(classified, market.product_words("쿠키", SEEDS))
    assert 0 < len(out) <= 15 and all(2 <= len(m["word"]) <= 6 and len(m["examples"]) <= 3 for m in out)


def test_cached_real_data_has_no_noise_chips(classified):  # noqa: F811
    out = market.modifiers(classified, market.product_words("쿠키", SEEDS))
    words = {m["word"] for m in out}
    assert out and not words & {"전문점", "종류", "쇼핑몰", "생지", "세트", "포장"}


def test_bare_packaging_skipped_but_compound_kept():
    kw = market.classify(_table(["쿠키포장", "개별포장쿠키", "선물포장쿠키"], [900, 500, 400]), ["쿠키"])
    assert {m["word"] for m in market.modifiers(kw, ["쿠키"])} == {"개별포장"}
