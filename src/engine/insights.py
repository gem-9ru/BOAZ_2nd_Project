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


def warnings(res: SimResult, pmf_threshold: float = D.PMF_FLOOR_THRESHOLD) -> List[Tuple[str, str]]:
    """(수준, 문장). 수준: error / warning / info"""
    s, p, out = res.summary, res.params, []
    if p.retention_floor < pmf_threshold:
        out.append(("error", f"PMF 경고: 리텐션 바닥값 {p.retention_floor:.1%}가 기준({pmf_threshold:.0%})보다 낮습니다. "
                             "고객이 계속 남지 않는 상태라 광고비 증액보다 리텐션(제품·재구매 경험) 개선이 먼저입니다."))
    if s["ltv_cac"] is not None and s["ltv_cac"] < 1:
        out.append(("warning", f"LTV/CAC가 {s['ltv_cac']:.2f}입니다. 광고로 데려온 고객이 12개월 동안 광고비({won(s['paid_cac'])})만큼 "
                               f"이익({won(s['ltv_12m'])})을 내지 못합니다."))
    if s["paid_cac"] is not None and s["payback_month"] is None:
        out.append(("warning", "36개월 안에 고객 1명당 광고비(CAC)를 회수하지 못합니다."))
    for _, row in res.by_channel.iterrows():
        if row["channel"] == "naver" and row["spend"] > 0 and row["cpc"] > 0 \
                and row["marginal_cpc"] > D.SATURATION_RATIO * row["cpc"]:
            out.append(("warning", f"포화 구간: 네이버 한계 CPC({won(row['marginal_cpc'])})가 평균 CPC({won(row['cpc'])})의 "
                                   f"{D.SATURATION_RATIO:.0f}배를 넘습니다. 키워드를 늘리거나 다른 채널로 옮기세요."))
        if row["unspent"] > 1:
            out.append(("info", f"{row['label']}: 선택한 키워드로는 월 {won(row['unspent'])}을 더 쓸 수 없습니다 "
                                "(최고 입찰가에서도 노출 한도). 키워드를 추가하거나 예산을 옮기세요."))
    return out


def sentences(res: SimResult, levers: pd.DataFrame, opt: Dict, omtm_label: str,
              scan: Optional[pd.DataFrame] = None) -> List[str]:
    s, out = res.summary, []
    core = levers[levers["core"]].sort_values("up", ascending=False)
    if len(core):
        top = core.iloc[0]
        spend_row = core[core["key"] == "spend"]
        if top["key"] != "spend" and len(spend_row):
            out.append(f"광고비 +10%(12개월 이익 {won(spend_row.iloc[0]['up'])})보다 **'{top['lever']}' +10%**"
                       f"(12개월 이익 {won(top['up'])})가 더 효과적입니다.")
        else:
            out.append(f"지금은 **광고비 증액**이 가장 효과가 큰 레버입니다 (+10% → 12개월 이익 {won(top['up'])}).")
    step = levers[levers["key"].str.startswith("step_")].sort_values("up", ascending=False)
    if len(step):
        out.append(f"퍼널 단계 중에서는 **{step.iloc[0]['lever'].replace('단계: ', '').replace(' (이탈 감소)', '')}** 단계 개선 효과가 가장 큽니다 "
                   f"(이탈 10% 감소 → {won(step.iloc[0]['up'])}). 이 단계부터 A/B 테스트를 제안합니다.")
    if opt:
        gain = opt["value"] - opt["base_value"]
        if abs(gain) > 1e-6:
            out.append(f"'{omtm_label}' 기준 최적 배분으로 바꾸면: "
                       f"{_fmt_omtm(opt['base_value'], opt['omtm'])} → **{_fmt_omtm(opt['value'], opt['omtm'])}**")
    if scan is not None and len(scan) > 1:
        cur = scan[scan["multiplier"] == 1.0]
        up = scan[scan["multiplier"] == 1.25]
        if len(cur) and len(up):
            d = float(up.iloc[0]["profit_12m"] - cur.iloc[0]["profit_12m"])
            if d > 0:
                out.append(f"예산을 25% 늘리면 12개월 이익이 {won(d)} 늘어납니다 → **증액 여지**가 있습니다.")
            else:
                out.append(f"예산을 25% 늘리면 12개월 이익이 {won(-d)} 줄어듭니다 → 증액보다 **배분·퍼널 개선**이 먼저입니다.")
    if s["repeat_revenue"] > 0:
        share = s["repeat_revenue"] / s["revenue"] if s["revenue"] else 0
        out.append(f"12개월 매출 중 재구매 비중은 {share:.0%}입니다. ROAS(첫 구매 기준 {s['roas'] or 0:.2f})만 보면 이 부분이 빠집니다.")
    return out


def _fmt_omtm(v: float, omtm: str) -> str:
    if omtm == "profit":
        return won(v)
    if omtm == "roas":
        return f"{v:.2f}"
    return f"{v:,.0f}명"
