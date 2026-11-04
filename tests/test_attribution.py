"""M3 어트리뷰션 (명세 4장). GA4 샘플 기대값은 기획 세션 재계산 값 (자기 도메인 2개 제거, 11/5)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import attribution as A  # noqa: E402

RAW = A.load_ga4_paths()
CLEAN = A.clean_paths(RAW)
TAB = A.credit_table(CLEAN)


def toy():
    return A.clean_paths(pd.DataFrame({"path": ["a > b > c", "(none) > a", "b"], "source_path": ["x > y > z", "(direct) > x", "y"],
                                       "conversions": [10.0, 4.0, 6.0], "revenue": [0.0, 0.0, 0.0]}))


@pytest.mark.parametrize("model", list(A.MODELS))
def test_credit_sums_to_total(model):
    assert A.credit(toy(), model).sum() == pytest.approx(20.0)
    assert TAB[model].sum() == pytest.approx(100.0)


def test_model_rules():
    d = toy()
    assert A.credit(d, "first")["a"] == pytest.approx(10)
    assert A.credit(d, "last_non_direct")["a"] == pytest.approx(4)   # direct 건너뜀
    u = A.credit(d, "u_shape")
    assert u["a"] == pytest.approx(10 * 0.4 + 4 * 0.5) and u["b"] == pytest.approx(10 * 0.2 + 6)


def test_self_referral_removed():
    assert CLEAN["conversions"].sum() == pytest.approx(5692)
    domains = set(A.SELF_DOMAINS)
    for path, src, t in zip(CLEAN["path"], CLEAN["source_path"], CLEAN["touches"]):
        kept = [m for m, s in zip(path.split(A.SEP), src.split(A.SEP)) if not (m == "referral" and s in domains)]
        assert len(t) == max(len(kept), 1)
    assert A.self_ref_share(RAW) == pytest.approx(0.618, abs=1e-3)
    both = A.self_ref_share(RAW) + A.self_ref_share(RAW, domain=A.SELF_DOMAINS[1])
    assert both == pytest.approx(0.652, abs=1e-3)


EXPECTED = {  # 첫 클릭 / 마지막 클릭 / 마지막 비직접 / 선형 / U자형 (구매 가중 %)
    "organic": (45.5, 43.6, 45.2, 43.7, 44.2),
    "referral": (25.6, 26.2, 26.9, 25.4, 25.7),
    "direct": (16.7, 16.5, 12.8, 16.6, 16.6),
    A.UNKNOWN: (10.1, 11.8, 13.2, 12.3, 11.5),
    "cpc": (1.7, 1.3, 1.3, 1.5, 1.5),
    "email": (0.4, 0.5, 0.5, 0.4, 0.4),
}


def test_ga4_sample_matches_plan():
    assert A.single_touch_share(CLEAN) == pytest.approx(0.599, abs=1e-3)
    for ch, vals in EXPECTED.items():
        for model, v in zip(A.MODELS, vals):
            assert TAB.loc[ch, model] == pytest.approx(v, abs=0.051), (ch, model)
    raw_tab = A.credit_table(A.clean_paths(RAW, clean=False))
    assert raw_tab.loc["referral", "last"] == pytest.approx(51.4, abs=0.05)   # 정제 전 referral 절반
    assert "데이터 정제" in A.verdict(TAB)


def test_correction_preserves_total():
    k = A.correction_factors(TAB, "first")
    base = TAB.loc[k.index, "last"]
    assert (base * k).sum() == pytest.approx(base.sum())
    assert k["cpc"] > 1   # 마지막 클릭이 유료 검색을 과소평가
    assert A.correction_factors(TAB, "last").tolist() == pytest.approx([1.0] * len(k))


def test_upload_format():
    up = pd.DataFrame({"path": ["naver > meta", "meta", "myshop.com > naver"], "conversions": [3, 2, 5]})
    d = A.clean_paths(A.from_upload(up), self_domains=["myshop.com"])
    assert d["touches"].tolist() == [["naver", "meta"], ["meta"], ["naver"]]
