"""세트가 1개일 때: A/B 비교 대신 기준값(rules.yaml)과 비교한 신호 (분석 페이지 축소안 v5 ①b).

표시는 ✓ 괜찮아요(ok) / ↓ 기준보다 낮아요(low) / – 아직 몰라요(unknown) 셋뿐이고 판정 배지(확실해요·○ 쪽이에요)는 쓰지 않는다.
링크 클릭이 판정 최소(min_clicks, 30번)보다 적으면 숫자가 좋아 보여도 무조건 '아직 몰라요' (③ '30번은 있어야 판단'과 같은 기준).
범위는 비율의 베타 사후 분포 90% 구간 (예: 클릭 17 중 도착 14 → 82%, 62~92%).
"""
from typing import Dict, List

from ..specs import loop as _loop
from ..uncertainty import beta_interval


def run(arms: List[Dict]) -> List[Dict]:
    if len(arms) != 1:
        return []
    a = arms[0]
    cfg = _loop()
    min_clicks = cfg["alerts"]["min_clicks"]
    few = a["link_clicks"] < min_clicks
    why = f"클릭 {int(a['link_clicks'])}번이라 {min_clicks}번이 안 돼요 → 판정 안 함" if few else None
    out: List[Dict] = []

    def add(key, label, value, rng, standard, good, text):
        out.append({"key": key, "label": label, "value": value, "range": rng, "standard": standard,
                    "signal": "unknown" if few else ("ok" if good else "low"), "text": text, "why": why})

    if a["impressions"] > 0:
        ctr = a["link_clicks"] / a["impressions"]
        lo, hi = beta_interval(a["link_clicks"], a["impressions"])
        low = cfg["matrix"]["ctr_low"]
        add("ctr", "본 사람이 누르는 정도", ctr, [lo, hi], f"1,000번 보이면 {round(low * 1000)}번 이상",
            ctr >= low, f"1,000번 보이면 {ctr * 1000:.0f}번 (범위 {lo * 1000:.0f}~{hi * 1000:.0f}번)")
    if a["link_clicks"] > 0:
        vr = min(a["landing_page_views"] / a["link_clicks"], 1.0)
        lo, hi = beta_interval(min(a["landing_page_views"], a["link_clicks"]), a["link_clicks"])
        need = cfg["alerts"]["visit_rate_min"]
        add("visit_rate", "누른 뒤 페이지 도착", vr, [lo, hi], f"{need:.0%}",
            vr >= need, f"{vr:.0%} (범위 {lo:.0%}~{hi:.0%})")
    if a.get("frequency_min"):
        fmax = cfg["alerts"]["frequency_max"]
        # frequency_min = 노출 ÷ 날마다 본 사람 수의 합 → 실제 평균보다 작거나 같다 (아래쪽 값). 그래서 '적어도'로 말하고,
        # 기준 이하여도 '✓ 괜찮아요'라고 단정하지 않는다 (넘으면 확실히 ↓)
        f = a["frequency_min"]
        out.append({"key": "frequency", "label": "한 사람이 본 횟수", "value": f, "range": None, "standard": f"{fmax}번 이하",
                    "signal": "unknown" if few or f <= fmax else "low", "text": f"적어도 {f:.1f}번", "why": why})
    return out
