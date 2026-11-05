"""초보자 측정 키트: 광고 링크·쿠폰, 판매처 통계 파일 읽기."""
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.engine import measure as M  # noqa: E402


def q(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def test_smartstore_link_uses_nt_params():
    u = M.build_link("smartstore.naver.com/shop/products/123", "meta", "스마트스토어", "2611_coffee", detail="릴스A")
    assert u.startswith("https://")
    tags = q(u)
    assert tags["nt_source"] == "meta" and tags["nt_medium"] == "paid_social" and tags["nt_detail"] == "릴스A"
    assert "utm_source" not in tags


def test_own_mall_link_uses_utm_and_keeps_existing_params():
    u = M.build_link("https://myshop.com/p?id=7&utm_source=old", "influencer", "자사몰", "2611_coffee", detail="Reel A")
    tags = q(u)
    assert tags["id"] == "7" and tags["utm_source"] == "influencer"     # 기존 값은 덮어쓰고 다른 값은 유지
    assert tags["utm_medium"] == "social" and tags["utm_campaign"] == "2611_coffee" and tags["utm_content"] == "reel_a"


def test_coupang_has_no_link_and_coupon_format():
    assert M.build_link("https://coupang.com/vp/1", "meta", "쿠팡", "2611") is None
    assert M.coupon_code("meta", "2611", "coffee beans") == "MT2611COFF"
    assert M.campaign_name("2611", "Coffee Beans!") == "2611_coffee_beans"
    assert set(M.STORE_NOTES) >= {"스마트스토어", "자사몰", "쿠팡", "매장·예약"}


def test_detect_store_columns_and_totals():
    df = pd.DataFrame({"날짜": ["11-01", "11-02"], "유입수": ["1,200", "800"], "상품상세조회수": [600, 400],
                       "장바구니": [60, 40], "결제수": [12, 8], "결제금액": ["420,000원", "280,000원"]})
    m = M.detect_columns(list(df.columns))
    assert m == {"visits": "유입수", "views": "상품상세조회수", "cart": "장바구니", "orders": "결제수", "revenue": "결제금액"}
    t = M.store_totals(df, m)
    assert t["visits"] == 2000 and t["orders"] == 20 and t["revenue"] == 700_000
    f = M.store_funnel(t)
    assert list(f.columns) == ["방문 (유입)", "상품 조회", "장바구니", "구매 수"] and f.iloc[0, -1] == 20


def test_detect_does_not_reuse_revenue_as_orders():
    m = M.detect_columns(["주문금액", "주문건수", "방문자수"])
    assert m["revenue"] == "주문금액" and m["orders"] == "주문건수" and m["visits"] == "방문자수"
    assert M.store_funnel({"visits": 100, "orders": None}) is None
