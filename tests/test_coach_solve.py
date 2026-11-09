"""MVP 7e 2단계: 코치 '풀기'를 엔진 하나로 (CO.solve → Answer, Split).

화면(app/main.py)은 입력을 모아 solve를 한 번 부르고, Answer만 읽는다. 네이버 곡선은 화면이 불러와 넘김(바깥 일).
"""
import pandas as pd
import pytest

from src.engine import NaverCurve
from src.engine import coach as C


def _naver_curve(cap_cost=200_000.0, cap_clicks=400.0):
    df = pd.DataFrame({"bid": [100, 300, 600, 1000], "cost": [20_000, 60_000, 120_000, cap_cost],
                       "clicks": [80, 180, 290, cap_clicks], "impressions": [0, 0, 0, 0]})
    return NaverCurve({"원두커피": df})


# ── Split: 배분 결과 (dict → 데이터클래스) ──
def test_split_has_naver_and_meta_legs():
    params = C.coach_params(20_000, 7_000, 0.5)
    sp = C.split_budget(1_000_000, _naver_curve(), 1_300.0, params)
    assert sp.has_naver and sp.naver.spend + sp.meta.spend == pytest.approx(1_000_000)
    assert sp.naver.spend <= sp.naver_capacity + 1 and sp.meta.cpc == 1_300.0
    # 네이버 클릭 비용 = 네이버에 쓴 돈 ÷ 그 돈으로 받는 클릭 (등급표에 보이는 값)
    assert sp.naver.cpc == pytest.approx(sp.naver.spend / sp.naver.curve.clicks(sp.naver.spend))
    assert sp.spends == [sp.naver.spend, sp.meta.spend] and [c.key for c in sp.channels] == ["naver", "meta"]
    assert sp.total == pytest.approx(1_000_000)


def test_split_without_naver_has_no_naver_leg():
    params = C.coach_params(20_000, 7_000, 0.5)
    sp = C.split_budget(210_000, None, 1_300.0, params)
    assert sp.naver is None and not sp.has_naver and sp.spends == [210_000] and sp.meta.cpc == 1_300.0
    assert sp.cpc > 1_300.0          # 평균 클릭 비용은 메타 포화 곡선 때문에 입력값보다 조금 높음


def test_split_still_reads_like_the_old_dict():
    """이전 단계 동안 화면 코드가 그대로 돌도록 예전 키도 읽힘 (main.py 호출부를 옮긴 뒤 지움)."""
    params = C.coach_params(20_000, 7_000, 0.5)
    sp = C.split_budget(1_000_000, _naver_curve(), 1_300.0, params)
    assert sp["naver"] == sp.naver.spend and sp["meta"] == sp.meta.spend and sp["meta_cpc"] == 1_300.0
    assert sp["has_naver"] and sp["spends"] == sp.spends and sp["channels"] == sp.channels
    assert sp["table"] is sp.table and sp["cpc"] == sp.cpc and sp["clicks"] == sp.clicks
    assert sp["naver_capacity"] == sp.naver_capacity and sp["naver_marginal_cpc"] == sp.naver_marginal_cpc
    none = C.split_budget(210_000, None, 1_300.0, params)
    assert none["naver"] == 0.0 and none["naver_marginal_cpc"] is None
