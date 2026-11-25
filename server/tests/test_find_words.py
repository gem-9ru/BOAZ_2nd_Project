"""Task 1: 분야·상품을 입력한 낱말의 실제 검색 결과로 판정 (분야별 낱말 목록 없음). 네트워크 없이."""
import pytest

from server.engine import market, naver_api as api
from server.tests.test_market import Resp, fake_keys, isolated  # noqa: F401  (autouse 픽스처 재사용)


def test_twelve_categories_in_order():
    codes = [c["code"] for c in market.CATEGORIES]
    assert codes[:3] == ["50000000", "50000001", "50000002"] and codes[-1] == "50005542" and len(codes) == 12


def test_guess_category_picks_category_with_most_monthly_points(monkeypatch):
    pts = {"50000002": 12, "50000000": 2, "50000006": 1}
    monkeypatch.setattr(api, "category_keyword_points", lambda c, k, online=True: pts.get(c, 0))
    assert market.guess_category("립 밤") == "50000002"


def test_guess_category_none_when_tied_or_thin(monkeypatch):
    monkeypatch.setattr(api, "category_keyword_points", lambda c, k, online=True: 12 if c in ("50000006", "50000008") else 0)
    assert market.guess_category("홍삼") is None
    monkeypatch.setattr(api, "category_keyword_points", lambda c, k, online=True: 3)
    assert market.guess_category("zz상품") is None


def test_points_request_body(monkeypatch):
    fake_keys(monkeypatch)
    seen = []
    monkeypatch.setattr(api, "_http_hub", lambda keys, path, body: seen.append((path, body)) or Resp(200, {"results": [{"data": [{"period": "2025-11-01", "ratio": 1}] * 12}]}))
    assert api.category_keyword_points("50000002", "립밤") == 12
    assert seen[0][0] == "/shopping/v1/category/keywords" and seen[0][1]["keyword"] == [{"name": "립밤", "param": ["립밤"]}]
    assert seen[0][1]["category"] == "50000002" and seen[0][1]["timeUnit"] == "month"


def test_points_none_without_keys_or_data(monkeypatch):
    monkeypatch.setattr(api, "read_keys", lambda names, env_file=None: None)
    assert api.category_keyword_points("50000002", "립밤") is None


def test_product_detected_from_typed_words_not_bakery_list():
    seeds = market.product_words("캠핑 의자", [])
    assert market.intent_of("캠핑의자추천", seeds) == "상품"
    assert market.intent_of("휘낭시에", seeds) == "관련 낮음"          # 빵 낱말이 들어가지 않음
    assert market.intent_of("립밤만들기", market.product_words("립밤", [])) == "제외: 만들기"


def test_product_words_dedup_and_pieces():
    assert market.product_words("캠핑 의자", ["캠핑의자", "접이식 의자"]) == ["캠핑의자", "캠핑", "의자", "접이식의자"]


def test_no_product_words_constant_and_common_words_from_specs():
    assert not hasattr(market, "PRODUCT_WORDS")
    assert "선물" in market.GIFT_WORDS and "만들기" in market.MAKING_WORDS
    assert set(market.MODIFIER_GROUPS) == {"포장", "맛·재료", "배송", "양"}
