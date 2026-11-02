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
    if step_name.endswith("완료"):
        return D.STEP_PRESCRIPTIONS["과업 완료"]
    return "이 단계 화면의 이탈 원인을 세션 녹화·사용자 인터뷰로 먼저 확인하기"


def biggest_drop(params) -> Tuple[str, float]:
    """전환율이 가장 낮은(이탈이 가장 큰) 단계 (Q3)."""
    name, rate = min(params.steps, key=lambda x: x[1])
    return name, rate


def warnings(res: SimResult, keyword_alloc: Optional[pd.DataFrame] = None) -> List[Tuple[str, str]]:
    """(수준, 문장). 수준: error / warning / info"""
    s, out = res.summary, []
    # PMF 경고 (기획안 결정 5): 현재 리텐션에서 12개월 LTV/CAC < 1
    if s["ltv_cac"] is not None and s["ltv_cac"] < D.PMF_LTV_CAC_THRESHOLD:
        out.append(("error", f"PMF 경고: 현재 리텐션에서 12개월 LTV/CAC가 {s['ltv_cac']:.2f}입니다. 광고로 데려온 고객 1명이 "
                             f"12개월 동안 남기는 이익({won(s['ltv_12m'])})이 데려오는 비용({won(s['paid_cac'])})보다 작습니다. "
                             "광고비 증액보다 리텐션·전환율 개선이 먼저입니다."))
    if s["paid_cac"] is not None and s["payback_month"] is None:
        out.append(("warning", "36개월 안에 고객 1명당 광고비(CAC)를 회수하지 못합니다."))
    if keyword_alloc is not None and len(keyword_alloc):
        sat = keyword_alloc[keyword_alloc["saturated"] & (keyword_alloc["spend"] > 0)]
        for _, row in sat.iterrows():
            out.append(("warning", f"포화 구간: '{row['keyword']}' 한계 CPC({won(row['marginal_cpc'])})가 평균 CPC({won(row['cpc'])})의 "
                                   f"{D.SATURATION_RATIO:.0f}배를 넘습니다. 세부 키워드를 추가하거나 다른 채널로 옮기세요."))
    for _, row in res.by_channel.iterrows():
        if row["unspent"] > 1:
            out.append(("info", f"{row['label']}: 선택한 키워드로는 월 {won(row['unspent'])}을 더 쓸 수 없습니다 "
                                "(최고 입찰가에서도 노출 한도). 키워드를 추가하거나 예산을 옮기세요."))
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
            out.append({"title": f"광고비를 더 쓰기 전에 퍼널을 보세요: '{top['lever']}' 개선이 광고비 증액보다 이익을 더 키웁니다.",
                        "evidence": f"+10% 시 12개월 이익 변화 — {top['lever']} {won(top['up'])}, 광고비 {won(spend_row.iloc[0]['up'])}",
                        "action": "아래 이탈 단계 실험부터 진행"})
        else:
            out.append({"title": "지금은 광고비 증액이 가장 효과가 큰 레버입니다.",
                        "evidence": f"광고비 +10% → 12개월 이익 {won(top['up'])}", "action": "예산 증액 후 한계 CPC 모니터링"})
    name, rate = biggest_drop(p)
    step = levers[levers["key"].str.startswith("step_")].sort_values("up", ascending=False)
    best = step.iloc[0]["lever"].replace("단계: ", "").replace(" (이탈 감소)", "") if len(step) else name
    best_gain = won(step.iloc[0]["up"]) if len(step) else "-"
    title = (f"가장 많이 빠지고 개선 효과도 가장 큰 단계는 '{name}'(통과율 {rate:.1%})입니다." if best == name else
             f"가장 많이 빠지는 단계는 '{name}'(통과율 {rate:.1%})이고, 개선 효과가 가장 큰 단계는 '{best}'입니다.")
    out.append({"title": title,
                "evidence": f"'{best}' 이탈 10% 감소 → 12개월 이익 {best_gain}",
                "action": f"A/B 테스트: {prescription(best)}"})
    budget = max(sum(opt_roas["spends"]) if opt_roas else 0.0, 1.0)
    no_ads = opt_profit is not None and sum(opt_profit["spends"]) < 0.05 * budget
    if no_ads:
        out.append({"title": "지금 퍼널·객단가·마진에서는 광고비를 쓸수록 12개월 이익이 줄어듭니다.",
                    "evidence": f"12개월 이익 최적 광고비 ≈ 0원 · 현재 LTV/CAC {s['ltv_cac'] or 0:.2f}",
                    "action": "광고 확대 전에 전환율·리텐션·객단가 레버부터 개선 (위 토네이도 참고)"})
    elif opt_profit is not None and opt_roas is not None:
        diff = max(abs(a - b) for a, b in zip(opt_profit["spends"], opt_roas["spends"]))
        if diff > 0.05 * budget:
            out.append({"title": "ROAS 기준 배분과 12개월 이익 기준 배분이 다릅니다 → ROAS만 보면 부분 최적화입니다.",
                        "evidence": "ROAS 최적 " + " / ".join(won(x) for x in opt_roas["spends"])
                                    + " vs 이익 최적 " + " / ".join(won(x) for x in opt_profit["spends"]) + " (채널 순서: 네이버 / 메타)",
                        "action": "④ 화면의 비교표에서 두 안의 12개월 이익 차이 확인"})
    if opt and not (no_ads and opt.get("omtm") == "profit"):
        gain = opt["value"] - opt["base_value"]
        if abs(gain) > 1e-6:
            out.append({"title": f"'{omtm_label}' 기준으로 채널 배분을 바꾸면 OMTM이 좋아집니다.",
                        "evidence": f"{_fmt_omtm(opt['base_value'], opt['omtm'])} → {_fmt_omtm(opt['value'], opt['omtm'])}",
                        "action": "최적안 배분으로 2~4주 집행 후 1단계 CSV로 재보정"})
    if scan is not None and len(scan) > 1:
        cur = scan[scan["multiplier"] == 1.0]
        up = scan[scan["multiplier"] == 1.25]
        if len(cur) and len(up):
            d = float(up.iloc[0]["profit_12m"] - cur.iloc[0]["profit_12m"])
            out.append({"title": "예산 증액 여지가 있습니다." if d > 0 else "지금은 예산 증액보다 배분·퍼널 개선이 먼저입니다.",
                        "evidence": f"예산 +25% → 12개월 이익 {'+' if d > 0 else '−'}{won(abs(d))}",
                        "action": "④ 예산 규모별 이익 곡선의 꼭짓점 확인"})
    if s["repeat_revenue"] > 0 and s["revenue"]:
        out.append({"title": "리텐션은 광고 효율의 바닥입니다: ROAS는 재구매를 빼고 계산하므로 고객 가치를 다 보여주지 못합니다.",
                    "evidence": f"12개월 매출 중 재구매 {s['repeat_revenue'] / s['revenue']:.0%}, ROAS(첫 구매 기준) {s['roas'] or 0:.2f}, "
                                f"회수 기간 {str(s['payback_month']) + '개월' if s['payback_month'] else '36개월+'}",
                    "action": "첫 구매 후 1~2개월 재구매 유도(쿠폰·리마인드) 실험"})
    if keyword_recs is not None and len(keyword_recs):
        kws = ", ".join(keyword_recs["keyword"].head(3))
        out.append({"title": "세부 키워드 기회: 경쟁이 낮거나 중간인 월 검색수 1천~3만 키워드가 있습니다.",
                    "evidence": f"추천: {kws}",
                    "action": "② 획득 설계에서 추가해 포화를 낮추기"})
    return out


def _fmt_omtm(v: float, omtm: str) -> str:
    if omtm == "profit":
        return won(v)
    if omtm == "roas":
        return f"{v:.2f}"
    return f"{v:,.0f}명"
