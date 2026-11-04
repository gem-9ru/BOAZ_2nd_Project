"""M3 어트리뷰션 (명세 4장). GA4 샘플 기대값은 기획 세션 수치 기준, 정제 규칙 차이로 ±2.5%p 허용."""
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
        kept = [s for s in src.split(A.SEP) if s not in domains]
        assert len(t) == max(len(kept), 1)
    assert A.self_ref_share(RAW) == pytest.approx(0.618, abs=1e-3)


def test_ga4_sample_matches_plan():
    assert A.single_touch_share(CLEAN) == pytest.approx(0.585, abs=0.025)
    for ch, first, last in [("organic", 45.1, 43.2), ("referral", 27.8, 28.4), ("direct", 15.1, 15.0), ("cpc", 1.7, 1.3)]:
        assert TAB.loc[ch, "first"] == pytest.approx(first, abs=2.5)
        assert TAB.loc[ch, "last"] == pytest.approx(last, abs=2.5)
    raw_tab = A.credit_table(A.clean_paths(RAW, clean=False))
    assert raw_tab.loc["referral", "last"] == pytest.approx(51.4, abs=0.5)   # 정제 전 referral 절반
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
