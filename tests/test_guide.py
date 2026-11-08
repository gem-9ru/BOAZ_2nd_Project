"""광고 관리자 가이드: 세팅 카드(공식 문서)와 맞춘 15곳 (MVP 7번)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import NaverCurve  # noqa: E402
from src.engine import guide as G  # noqa: E402
from src.engine import setup_rag as SR  # noqa: E402


def test_meta_objective_rules():
    assert G.meta_plan(0, 50_000, True)["objective"] is None
    assert G.meta_plan(142_000, 100_000, pixel_ready=False, stores=["자사몰"])["objective"] == "트래픽"
    p = G.meta_plan(142_000, 100_000, pixel_ready=True, stores=["자사몰"])
    assert p["objective"] == "판매" and not p["learning_ok"]
    assert "머신 러닝" in p["why"] and "제한된 머신 러닝" in p["why"] and "학습 기준" not in p["why"]
    assert G.meta_plan(10_000_000, 10_000, True, ["자사몰"])["learning_ok"]
    assert len(G.META_OBJECTIVES) == 6 and all(o[3] == "✅" for o in G.META_OBJECTIVES)


def test_smartstore_meta_defaults_to_traffic_and_says_unconfirmed():
    p = G.meta_plan(142_000, 100_000, pixel_ready=True, stores=["스마트스토어"], click_cost=1_300)
    assert p["objective"] == "트래픽" and "공식 확인 못 함" in p["why"]


def test_meta_daily_budget_rules():
    p = G.meta_plan(304_000, 100_000, pixel_ready=False, stores=["자사몰"], click_cost=1_300)
    assert p["daily"] == pytest.approx(10_000) and p["recommended_daily"] == pytest.approx(13_000)   # 링크 클릭 1,300원 × 10
    assert not p["daily_ok"] and p["daily_max"] == pytest.approx(17_500)                             # 최대 75% 더
    names = " ".join(a[1] + a[2] for a in G.AUTO_VS_MANUAL)
    assert "최고 볼륨" in names and "단계적으로 없어지는" in names
    assert any("참여한 조회 후 1일" in n for n, _, _ in G.META_NOTES)


def _curve():
    df = pd.DataFrame({"bid": [100, 300, 600, 1000], "cost": [20_000, 60_000, 120_000, 200_000],
                       "clicks": [80, 180, 290, 400], "impressions": [0] * 4})
    return NaverCurve({"원두커피": df})


def test_naver_bid_and_checklist():
    c = _curve()
    assert G.naver_bid_at(c, 10_000) == 100 and G.naver_bid_at(c, 50_000) == 300 and G.naver_bid_at(c, 10**9) == 1000
    assert G.naver_bid_at(None, 50_000) is None
    items = G.naver_checklist(68_000, 300, "원두커피", ["스마트스토어"])
    text = " ".join(i["step"] + i["detail"] for i in items)
    assert any("쇼핑검색광고" in i["step"] for i in items)
    assert any(i["step"] == f"하루 예산: {68_000 / 30.4:,.0f}원" for i in items)
    assert "최소 50원" in text and "키워드를 넣지 않고" in text            # 쇼핑검색 기준 입찰 설명
    assert "입찰가 × 품질지수" not in text and "광고 연관지수" in text       # 공식 표현
    assert "전환 추적 관리" in text and "캠페인 설정에서" in text           # 신청 + 캠페인에서 고르기
    assert "ADVoost" in text
    assert all(i["check"] in ("✅", "△", "❓", "🧮") for i in items)
    assert all(SR.by_id(i["card"]) is not None for i in items if i.get("card"))   # 근거 카드가 실제로 있음
    assert any("파워링크" in i["step"] for i in G.naver_checklist(68_000, None, "x", ["자사몰"]))


def test_keywordplus_removed():
    src = (Path(__file__).resolve().parents[1] / "src" / "engine" / "naver_source.py").read_text(encoding="utf-8")
    assert '"keywordplus": True' not in src
