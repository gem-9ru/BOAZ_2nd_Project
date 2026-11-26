"""② 세팅·준비물 질문 말: 처음 하는 사장님이 답할 수 있게 (어려운 말·답할 수 없는 질문 없음)."""
from server.engine import specs


def _field(fid):
    return next(f for f in specs.fields("meta")["fields"] if f["id"] == fid)


def test_instagram_says_it_can_be_left_empty():
    assert "비워" in _field("meta.pre.ig_account")["why"]


def test_click_destination_has_no_objective_jargon():
    why = _field("meta.adset.conversion_location")["why"]
    assert "트래픽" not in why and "참여 목표" not in why


def test_language_asks_about_facebook_not_ads_manager():
    ask = _field("meta.pre.language")["ask"]
    assert "광고 관리자" not in ask and "페이스북" in ask
