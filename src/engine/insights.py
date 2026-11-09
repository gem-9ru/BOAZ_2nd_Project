"""경고와 인사이트 문장 (규칙 기반)."""
from typing import Dict, List, Optional, Tuple

import pandas as pd

from . import defaults as D
from .model import SimResult


def won(x: Optional[float]) -> str:
    if x is None:
        return "-"
    if abs(x) >= 1e8:
        return f"{x / 1e8:,.2f}억 원"
    if abs(x) >= 1e6:
        return f"{x / 1e4:,.0f}만 원"
    if abs(x) >= 1e4:
        return f"{x / 1e4:,.1f}만 원"
    return f"{x:,.0f}원"


def prescription(step_name: str) -> str:
    if step_name in D.STEP_PRESCRIPTIONS:
        return D.STEP_PRESCRIPTIONS[step_name]
    if step_name.startswith("④"):
        return D.STEP_PRESCRIPTIONS["④ 구매"]
    return "이 단계 화면의 이탈 원인을 세션 녹화·사용자 인터뷰로 먼저 확인하기"


def biggest_drop(params) -> Tuple[str, float]:
    """전환율이 가장 낮은(이탈이 가장 큰) 단계 (Q3). '더 보기' 시뮬레이션 단계용 (그냥 최솟값: 기준 대비는 늘 1.0이라 쓰지 않음).
    판매처 실측 진단(코치·퍼널 카드)은 measure.lowest_step·diagnose_funnel (기준 대비 비율, B5)."""
    name, rate = min(params.steps, key=lambda x: x[1])
    return name, rate


def warnings(res: SimResult, keyword_alloc: Optional[pd.DataFrame] = None) -> List[Tuple[str, str]]:
    """(수준, 문장). 수준: error / warning / info"""
    s, out = res.summary, []
    # PMF 경고 (기획안 결정 5): 현재 리텐션에서 12개월 LTV/CAC < 1
    if s["ltv_cac"] is not None and s["ltv_cac"] < D.PMF_LTV_CAC_THRESHOLD:
        out.append(("error", f"광고할수록 손해인 상태입니다 (PMF 경고). 광고로 데려온 손님 1명이 1년 동안 남겨 주는 돈({won(s['ltv_12m'])})이 "
                             f"데려오는 데 든 광고비({won(s['paid_cac'])})보다 작습니다 (LTV/CAC {s['ltv_cac']:.2f}). "
                             "광고비를 늘리기 전에 재구매·구매 비율을 먼저 올려야 합니다."))
    if s["paid_cac"] is not None and s["payback_month"] is None:
        out.append(("warning", "손님 1명을 데려오는 데 쓴 광고비를 3년 안에 되찾지 못합니다 (회수 기간 36개월 넘음)."))
    if keyword_alloc is not None and len(keyword_alloc):
        sat = keyword_alloc[keyword_alloc["saturated"] & (keyword_alloc["spend"] > 0)]
        for _, row in sat.iterrows():
            out.append(("warning", f"'{row['keyword']}' 검색어는 돈을 더 넣어도 효과가 작습니다 (포화). 클릭 1번을 더 얻는 데 {won(row['marginal_cpc'])}이 들어 "
                                   f"평균({won(row['cpc'])})의 {D.SATURATION_RATIO:.0f}배가 넘습니다. 다른 검색어를 추가하거나 예산을 메타로 옮기세요."))
    for _, row in res.by_channel.iterrows():
        if row["unspent"] > 1:
            out.append(("info", f"{row['label']}: 고른 검색어를 찾는 사람이 적어 한 달 {won(row['unspent'])}은 쓰지 못합니다. "
                                "검색어를 더 추가하거나 남는 예산을 다른 채널로 옮기세요."))
    return out


def insights(res: SimResult, levers: pd.DataFrame, opt: Dict, omtm_label: str,
             scan: Optional[pd.DataFrame] = None, opt_profit: Optional[Dict] = None, opt_roas: Optional[Dict] = None,
             keyword_recs: Optional[pd.DataFrame] = None) -> List[Dict[str, str]]:
    """인사이트 카드: {"title": 문장, "evidence": 근거 숫자, "action": 다음 실험}."""
    s, p, out = res.summary, res.params, []
    core = levers[levers["core"]].sort_values("up", ascending=False)
    spend_row = core[core["key"] == "spend"]
    if len(core):
        top = core.iloc[0]
        if top["key"] != "spend" and len(spend_row):
            sp = spend_row.iloc[0]
            out.append({"title": f"'{top['lever']}' 10% 개선은 비용을 모르지만, 1년 동안 최대 {won(top['up'])}까지 써도 이득입니다.",
                        "evidence": f"광고비 10% 증액은 {won(sp['extra_spend'])}을 더 쓰고 남는 돈 {_signed(sp['up'])} · "
                                    f"'{top['lever']}' 10% 개선은 남는 돈 {_signed(top['up'])} (개선 비용을 빼기 전)",
                        "action": "이 금액보다 싸게 개선할 방법이 있으면 광고비 증액보다 먼저. 아래 실험 카드로 효과부터 확인"})
        else:
            out.append({"title": "지금은 광고비를 늘리는 것이 이익을 가장 많이 키웁니다 (증액분을 뺀 뒤에도).",
                        "evidence": f"광고비 10% 증액 ({won(top['extra_spend'])}) → 1년 동안 남는 돈 {_signed(top['up'])}",
                        "action": "예산을 조금씩 늘리면서 클릭당 비용이 너무 오르지 않는지 지켜보기"})
    name, rate = biggest_drop(p)
    step = levers[levers["key"].str.startswith("step_")].sort_values("up", ascending=False)
    best = step.iloc[0]["lever"].replace("단계: ", "").replace(" (이탈 감소)", "") if len(step) else name
    best_gain = won(step.iloc[0]["up"]) if len(step) else "-"
    title = (f"손님이 가장 많이 그만두는 곳은 '{name}' 단계입니다 (100명 중 {rate * 100:.0f}명만 통과). 여기를 고치는 효과가 가장 큽니다." if best == name else
             f"손님이 가장 많이 그만두는 곳은 '{name}' 단계(100명 중 {rate * 100:.0f}명 통과)지만, 고쳤을 때 효과는 '{best}' 단계가 가장 큽니다.")
    out.append({"title": title,
                "evidence": f"'{best}'에서 그만두는 사람 10% 감소 → 1년 동안 남는 돈 {best_gain} 증가",
                "action": f"두 버전 비교 실험(A/B 테스트): {prescription(best)}"})
    budget = max(sum(opt_roas["spends"]) if opt_roas else 0.0, 1.0)
    no_ads = opt_profit is not None and sum(opt_profit["spends"]) < 0.05 * budget
    if no_ads:
        out.append({"title": "지금 숫자로는 광고비를 쓸수록 1년 동안 남는 돈이 줄어듭니다.",
                    "evidence": f"남는 돈이 가장 큰 광고비 ≈ 0원 · 손님이 남기는 돈은 데려오는 비용의 {s['ltv_cac'] or 0:.2f}배",
                    "action": "광고를 늘리기 전에 구매 비율·재구매·결제 금액부터 올리기 ('결과·우선순위' 탭의 4가지 선택지 비교 참고)"})
    elif opt_profit is not None and opt_roas is not None:
        diff = max(abs(a - b) for a, b in zip(opt_profit["spends"], opt_roas["spends"]))
        if diff > 0.05 * budget:
            out.append({"title": "광고 매체 숫자(ROAS)만 보고 짠 예산과 실제로 남는 돈이 가장 큰 예산이 다릅니다.",
                        "evidence": "ROAS 기준 네이버 " + " · 메타 ".join(won(x) for x in opt_roas["spends"])
                                    + " vs 남는 돈 기준 네이버 " + " · 메타 ".join(won(x) for x in opt_profit["spends"]) + " (한 달)",
                        "action": "'결과·우선순위' 탭의 '계획별 비교와 그래프'에서 두 계획의 남는 돈 차이 확인"})
    if opt and not (no_ads and opt.get("omtm") == "profit"):
        gain = opt["value"] - opt["base_value"]
        if abs(gain) > 1e-6:
            out.append({"title": f"네이버·메타 예산 비율을 바꾸면 '{omtm_label}' 목표가 더 좋아집니다.",
                        "evidence": f"{_fmt_omtm(opt['base_value'], opt['omtm'])} → {_fmt_omtm(opt['value'], opt['omtm'])}",
                        "action": "추천 계획으로 2~4주 광고해 보고, 시작에서 실제 광고 성과 파일을 올려 다시 계산"})
    if scan is not None and len(scan) > 1:
        cur = scan[scan["multiplier"] == 1.0]
        up = scan[scan["multiplier"] == 1.25]
        if len(cur) and len(up):
            d = float(up.iloc[0]["profit_12m"] - cur.iloc[0]["profit_12m"])
            out.append({"title": "광고비를 더 늘려도 이익이 늘어납니다." if d > 0 else "지금은 광고비를 늘리기보다 예산 배분과 가게 개선이 먼저입니다.",
                        "evidence": f"광고비 25% 증액 → 1년 동안 남는 돈 {'+' if d > 0 else '−'}{won(abs(d))}",
                        "action": "'결과·우선순위' 탭의 '계획별 비교와 그래프'에서 예산 규모별 그래프에서 가장 높은 지점 확인"})
    if s["repeat_revenue"] > 0 and s["revenue"]:
        out.append({"title": "다시 오는 손님이 광고 효과를 받쳐 줍니다. ROAS는 첫 구매만 세서 이 부분을 보여주지 못합니다.",
                    "evidence": f"1년 매출 중 재구매 {s['repeat_revenue'] / s['revenue']:.0%} · ROAS(첫 구매만) {s['roas'] or 0:.2f} · "
                                f"광고비 본전 {str(s['payback_month']) + '개월' if s['payback_month'] else '36개월 넘음'}",
                    "action": "자동화의 '첫 구매 후 재구매' 시나리오로 손익분기 반응률 확인"})
    if keyword_recs is not None and len(keyword_recs):
        kws = ", ".join(keyword_recs["keyword"].head(3))
        out.append({"title": "경쟁이 덜한 알짜 검색어가 있습니다 (세부 키워드).",
                    "evidence": f"추천: {kws}",
                    "action": "광고 관리자에서 추가해 클릭을 더 싸게 얻기"})
    return out


def _signed(v: float) -> str:
    return ("+" if v >= 0 else "−") + won(abs(v))


def _fmt_omtm(v: float, omtm: str) -> str:
    if omtm == "profit":
        return won(v)
    if omtm == "roas":
        return f"{v:.2f}원"
    return f"{v:,.0f}명"
