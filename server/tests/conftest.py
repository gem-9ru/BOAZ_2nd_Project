import pytest


@pytest.fixture(autouse=True)
def _no_real_brand_check(monkeypatch):
    """테스트에서 브랜드 거르기가 진짜 Claude를 부르지 않게 (부르면 '브랜드 없음'). 기억도 테스트마다 비운다."""
    from server.engine import brands
    monkeypatch.setattr(brands, "_ask", lambda client, product, words: set())
    monkeypatch.setattr(brands, "_known", {})
