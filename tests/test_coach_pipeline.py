"""MVP 7e 1단계: 화면(main.py)의 코치 계산 흐름에서 확인된 버그를 고정하는 테스트 (B1·B2·B8)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import coach as C  # noqa: E402
from src.engine import defaults as D  # noqa: E402


def _naver_curve():
    import pandas as pd
    from src.engine import NaverCurve
    df = pd.DataFrame({"bid": [100, 300, 600, 1000], "cost": [20_000, 60_000, 120_000, 200_000],
                       "clicks": [80, 180, 290, 400], "impressions": [0, 0, 0, 0]})
    return NaverCurve({"원두커피": df})


def test_b1_rates_follow_the_split_actually_used():
    """고른 예산으로 다시 나누면 평균 클릭 비용·필요 구매율도 그 split 기준이어야 함 (권장 예산 값이 남으면 안 됨)."""
    params = C.coach_params(20_000, 7_000, 6)
    be = C.breakeven(7_000, 6)
    rec = C.split_budget(210_000, _naver_curve(), 1_300.0, params)
    small = C.split_budget(70_000, _naver_curve(), 1_300.0, params)
    assert small.cpc != pytest.approx(rec.cpc)               # 예산이 다르면 평균 클릭 비용이 다름
    cpc, need, need_year = C.rates_for(small, be)
    assert cpc == pytest.approx(small.cpc)
    assert need == pytest.approx(C.required_rate(small.cpc, be.first))
    assert need_year == pytest.approx(C.required_rate(small.cpc, be.year))


def test_b2_next_month_keeps_measured_repurchase_grade():
    """한 달 뒤 다시 계산할 때 재구매 등급은 처음 계산 등급을 그대로 (실측이면 C, 프리셋이면 D)."""
    first = C.mc_grades(False)
    first_measured = dict(first, retention="C")
    g = C.next_month_grades(first_measured, naver_measured=True, meta_measured=True, cvr_measured=True)
    assert g["retention"] == "C"
    assert C.next_month_grades(first, True, True, True)["retention"] == "D"
    # 나머지 규칙은 지금과 같음
    assert g["cpc_naver"] == "A" and g["cpc_meta"] == "A" and g["cvr"] == "A"
    g0 = C.next_month_grades(first, naver_measured=False, meta_measured=False, cvr_measured=False)
    assert g0["cpc_naver"] == "B" and g0["cpc_meta"] == first["cpc_meta"] and g0["cvr"] == "C"


def test_b8_meta_fallback_cpc_is_its_own_constant():
    assert D.META_FALLBACK_CPC == 1_300.0                     # 숫자는 그대로 (사용자 결정 Q2)
    assert "META_FALLBACK_CPC" in D.INPUT_GRADES
    # 계산은 CO.solve로 옮겨짐 (7e 2단계): 메타 클릭 비용을 안 넣으면 메타 기본값 상수를 씀
    a = C.solve(C.CoachInputs(20_000, 7_000, 300_000), None, C.repurchase_source("가끔"))
    assert a.split.meta.cpc == D.META_FALLBACK_CPC and a.grades["cpc_meta"] == "D"
    main = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    assert "NAVER_FALLBACK_CPC" not in main                    # 화면이 메타 기본값에 네이버 상수를 쓰지 않음


def test_meta_fallback_cpc_grade_is_read_from_one_place():
    """사용자 결정 (11/10): 메타 기본 클릭 비용 등급은 D 하나. 등급표(INPUT_GRADES)와 몬테카를로가 같은 값을 읽음."""
    assert D.INPUT_GRADES["META_FALLBACK_CPC"][0] == "D"
    assert C.mc_grades(False)["cpc_meta"] == D.INPUT_GRADES["META_FALLBACK_CPC"][0]
    assert C.mc_grades(True)["cpc_meta"] == "A"


# ── 배포 앱 점검 D3·D4 (11/10) ──
def _protein():
    from src.engine import NaverCurve, naver_source as ns
    est = ns.bid_estimate("프로틴쉐이크", device=D.NAVER_DEVICE, online=False)
    inp = C.CoachInputs(79_000, 39_500, 500_000, "프로틴쉐이크")
    return inp, NaverCurve({"프로틴쉐이크": est}), C.repurchase_source("매달(정기)")


def test_d3_orders_default_is_coupon_only():
    """판매처 전체 판매(광고 외 포함)는 기본값으로 쓰지 않음: 쿠폰 없으면 빈칸."""
    assert C.report_orders_default(None) is None          # 판매처 61건만 있고 쿠폰 없음 → 빈칸
    assert C.report_orders_default(16) == 16 and C.report_orders_default(0) == 0


def test_d3_unknown_orders_keep_assumed_rate():
    inp, curve, rep = _protein()
    a = C.solve(inp, curve, rep)
    unknown = C.solve(inp, curve, rep, pick=a.pick, actuals=C.Actuals(92, 133_400, 280, 364_000, None))
    assert unknown.params.cvr == pytest.approx(a.params.cvr) and unknown.grades["cvr"] == "C"   # 가정 그대로 (등급 C)
    coupon = C.solve(inp, curve, rep, pick=a.pick, actuals=C.Actuals(92, 133_400, 280, 364_000, 16))
    assert coupon.params.cvr == pytest.approx(16 / 372) and coupon.grades["cvr"] == "A"
    zero = C.solve(inp, curve, rep, pick=a.pick, actuals=C.Actuals(92, 133_400, 280, 364_000, 0))
    assert zero.params.cvr == 0 and zero.grades["cvr"] == "A"                                      # 직접 0 → 0건으로 계산


def test_d4_next_month_split_uses_verdict_budget():
    inp, curve, rep = _protein()
    a = C.solve(inp, curve, rep)
    up = C.Verdict(step=1, level="success", title="늘리기", detail="", next_budget=596_880.0)
    amount, label = C.next_month_budget(up, a.budget)
    assert amount == 596_880.0 and "판정대로" in label
    nxt = C.solve(inp, curve, rep, pick=a.pick, budget=amount, actuals=C.Actuals(92, 133_400, 280, 364_000, 16))
    assert nxt.split.total == pytest.approx(596_880.0)                    # 다시 나눈 합계 = 판정의 다음 달 예산
    amount, label = C.next_month_budget(None, a.budget)
    assert amount == a.budget and "이번 달 예산" in label
    same = C.solve(inp, curve, rep, pick=a.pick, budget=amount, actuals=C.Actuals(92, 133_400, 280, 364_000, 16))
    assert same.split.total == pytest.approx(a.budget)
    # 판정은 인자로 넘김 (상태 키에 숨기지 않음)
    main = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    assert "report_section(a, v)" in main and "def report_section(a: dict, verdict=None)" in main
