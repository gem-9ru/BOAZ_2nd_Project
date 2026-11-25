"""Task 1: 분야·상품을 입력한 낱말의 실제 검색 결과로 판정 (분야별 낱말 목록 없음). 네트워크 없이."""
from pathlib import Path

import pytest

from server.engine import market, naver_api as api
from server.tests.test_market import Resp, fake_keys, isolated  # noqa: F401  (autouse 픽스처 재사용)


def test_twelve_categories_in_order():
    codes = [c["code"] for c in market.CATEGORIES]
    assert codes[:3] == ["50000000", "50000001", "50000002"] and codes[-1] == "50005542" and len(codes) == 12


FIXTURES = Path(__file__).parent / "fixtures" / "category"


def flat(n):
    """달 n개가 모두 100인 가짜 응답 비율 (추정 최고 검색수 1 → 동점 만들기 쉬움)."""
    return [100.0] * n if n else None


def test_guess_category_picks_category_with_most_monthly_points(monkeypatch):
    pts = {"50000002": 12, "50000000": 2, "50000006": 1}
    monkeypatch.setattr(api, "category_keyword_ratios", lambda c, k, online=True: flat(pts.get(c, 0)))
    assert market.guess_category("립 밤") == "50000002"


def test_guess_category_none_when_tied_or_thin(monkeypatch):
    monkeypatch.setattr(api, "category_keyword_ratios", lambda c, k, online=True: flat(12) if c in ("50000006", "50000008") else None)
    assert market.guess_category("홍삼") is None
    monkeypatch.setattr(api, "category_keyword_ratios", lambda c, k, online=True: flat(3))
    assert market.guess_category("zz상품") is None


def test_peak_count_from_rounded_ratios():
    assert market.peak_count([100.0, 50.0]) == 2
    assert market.peak_count([40, 100, 33.33333, 6.66667, 53.33333]) == 15
    assert market.peak_count([9.09091, 100, 63.63636]) == 11
    assert market.peak_count([89.05505, 95.71884, 100, 84.3506]) is None    # 50 안에서 정수로 안 떨어짐 = 검색이 많음
    assert market.peak_count([]) is None


def test_more_searches_breaks_a_points_tie(monkeypatch):
    """달 수가 같으면 추정 최고 검색수가 큰 분야 (실제 텀블러: 생활/건강 12달 vs 도서 12달·최고 15번)."""
    data = {"50000008": [89.05505, 95.71884, 100, 84.3506] * 3, "50005542": [40, 100, 33.33333, 6.66667] * 3}
    monkeypatch.setattr(api, "category_keyword_ratios", lambda c, k, online=True: data.get(c))
    code, cands = market.category_guess("텀블러")
    assert code == "50000008" and cands == ["50000008", "50005542"]


@pytest.mark.parametrize("product, expected", [("텀블러", "50000008"), ("캠핑의자", "50000007"), ("립밤", "50000002")])
def test_category_guess_on_real_saved_responses(monkeypatch, product, expected):
    """실제 네이버 응답(2026-11-25 저장본, 분야 12개)을 고정해 둔 것으로 추정. 네트워크 없음."""
    monkeypatch.setattr(api, "CACHE_DIR", FIXTURES)
    monkeypatch.setattr(api, "EXAMPLES_DIR", FIXTURES / "none")
    code, _ = market.category_guess(product, online=False)
    assert code == expected


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
    # 맞추기(상품 판정·추천): 이름 전체 + 마지막 조각(머리 명사) + seeds. 앞 조각(캠핑)은 넣지 않는다
    assert market.product_words("캠핑 의자", ["캠핑의자", "접이식 의자"]) == ["캠핑의자", "의자", "접이식의자"]
    assert market.product_words("립밤", []) == ["립밤"]
    # 지우기(꾸밈말): 모든 조각
    assert market.strip_words("캠핑 의자", ["캠핑의자", "접이식 의자"]) == ["캠핑의자", "캠핑", "의자", "접이식의자"]


def test_front_piece_alone_is_not_my_product():
    words = market.product_words("캠핑 의자", [])
    assert market.intent_of("캠핑카대여", words) != "상품"
    assert market.intent_of("캠핑텐트", words) != "상품"
    assert market.intent_of("경량캠핑의자", words) == "상품"
    knit = market.product_words("니트 가디건", [])
    assert market.intent_of("반팔니트", knit) != "상품"
    assert market.intent_of("캐시미어가디건", knit) == "상품"


def test_modifiers_strip_every_piece_but_match_only_head(monkeypatch):
    from server.tests.test_modifiers import _table
    kw = market.classify(_table(["캠핑카대여", "경량캠핑의자", "캠핑텐트", "캠핑접이식의자"], [9000, 800, 5000, 400]),
                         market.product_words("캠핑 의자", []))
    out = market.modifiers(kw, market.product_words("캠핑 의자", []), strip=market.strip_words("캠핑 의자", []))
    words = [m["word"] for m in out]
    assert words == ["경량", "접이식"]
    assert "카대여" not in words and "텐트" not in words
    assert market.recommend(kw, seeds=market.product_words("캠핑 의자", [])) == ["경량캠핑의자", "캠핑접이식의자"]


def test_no_product_words_constant_and_common_words_from_specs():
    assert not hasattr(market, "PRODUCT_WORDS")
    assert "선물" in market.GIFT_WORDS and "만들기" in market.MAKING_WORDS
    assert set(market.MODIFIER_GROUPS) == {"포장", "맛·재료", "배송", "양"}


def test_category_candidates_tie_returns_both_in_order(monkeypatch):
    """동점(달 수·최고 검색수 모두 같음)이면 묻는다: 후보는 맨 윗줄(달 수가 가장 많은) 분야만, 최대 3개."""
    pts = {"50000006": 12, "50000008": 12, "50000002": 7, "50000000": 5}
    monkeypatch.setattr(api, "category_keyword_ratios", lambda c, k, online=True: flat(pts.get(c, 0)))
    got = market.category_candidates("캠핑의자")
    assert got == ["50000006", "50000008"] and market.guess_category("캠핑의자") is None
    many = {c["code"]: flat(12) for c in market.CATEGORIES[:5]}
    monkeypatch.setattr(api, "category_keyword_ratios", lambda c, k, online=True: many.get(c))
    assert market.category_candidates("zz") == [c["code"] for c in market.CATEGORIES[:3]]
    monkeypatch.setattr(api, "category_keyword_ratios", lambda c, k, online=True: flat(2))
    assert market.category_candidates("zz") == []


def test_ratios_and_points_read_same_response(monkeypatch):
    fake_keys(monkeypatch)
    body = {"results": [{"data": [{"period": "2025-11-01", "ratio": 50}, {"period": "2025-12-01", "ratio": 100}]}]}
    monkeypatch.setattr(api, "_http_hub", lambda keys, path, b: Resp(200, body))
    assert api.category_keyword_ratios("50000002", "립밤") == [50.0, 100.0]
    assert api.category_keyword_points("50000002", "립밤") == 2
