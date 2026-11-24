"""이상 알림 3단계 (v4 6장): ■ 차단 · ▲ 주의 · ● 참고.

이상한 데이터로 잘못된 결론을 내지 않게, 결론보다 먼저 계산한다. 기준값은 rules.yaml loop.alerts.
색만으로 구분하지 않게 모양(mark)을 같이 준다 (WCAG 1.4.1).
"""
from typing import Dict, List, Optional

from ..specs import loop as _loop

MARK = {"block": "■", "warn": "▲", "info": "●"}
ORDER = {"block": 0, "warn": 1, "info": 2}
REQUIRED = {"spend": "지출 금액", "impressions": "노출", "link_clicks": "링크 클릭", "landing_page_views": "랜딩 페이지 조회"}


def _a(level: str, kind: str, text: str, todo: str, screen: str, **extra) -> Dict:
    return dict({"level": level, "mark": MARK[level], "kind": kind, "text": text, "todo": todo, "screen": screen}, **extra)


def _won(x: float) -> str:
    return f"₩{round(x):,}"


def run(bundle, check: Dict, summary: Dict, settings: Optional[Dict] = None) -> List[Dict]:
    cfg = _loop()["alerts"]
    daily = bundle.tables["meta_daily"].df
    out: List[Dict] = []

    # ■ 차단: 필수 열 · 합계 불일치
    missing = [k for k, name in REQUIRED.items() if k not in daily.columns or (k == "landing_page_views" and float(daily[k].sum()) == 0)]
    if "meta_placement" not in bundle.tables:
        missing.append("placement")
    for k in missing:
        name = "노출 위치(분석 기준)" if k == "placement" else REQUIRED[k]
        out.append(_a("block", "missing_column", f"'{name}' 열이 없어요.",
                      f"광고 관리자에서 내보낼 때 분석 기준을 '일 · 노출 위치'로 고르고 '{name}' 열을 넣어 다시 받아 주세요.", "AN-00"))
    for t in check.get("totals", []):
        d, p = t["daily"], t["placement"]
        if abs(d - p) > max(1.0, cfg["sum_mismatch"] * abs(d)):
            out.append(_a("block", "sum_mismatch", f"일자별 합과 노출 위치별 합이 달라요 ({t['metric']}: {d:,.0f} vs {p:,.0f}).",
                          "같은 기간·같은 캠페인으로 두 표를 다시 내보내 주세요.", "AN-00"))

    # ▲ 주의
    for w in check.get("warnings", []):
        if w["kind"] == "no_delivery":
            out.append(_a("warn", "no_delivery", w["text"], "첫날은 심사·학습으로 늦게 나갈 수 있어요. 다음엔 시작 시간에 여유를 두세요.", "AN-01", date=w.get("date")))
        elif w["kind"] == "placement_skew":
            out.append(_a("warn", "an_skew", w["text"], "노출 위치를 직접 골라 Audience Network를 빼 보세요.", "AN-04"))

    arms = summary["arms"]
    spend = sum(a["spend"] for a in arms)
    budget = (settings or {}).get("meta.adset.daily_budget")
    if budget:
        try:
            expected = float(str(budget).replace(",", "").replace("원", "")) * daily["date"].nunique() * len(arms)
        except ValueError:
            expected = 0
        if expected and spend / expected < cfg["spend_used_min"]:
            out.append(_a("warn", "underspent", f"설정 예산의 {spend / expected:.0%}만 썼어요 ({_won(spend)} / {_won(expected)}).",
                          "타깃이 너무 좁거나 입찰이 낮을 수 있어요. 타깃을 넓히거나 총예산을 하루 최소 × 기간 이상으로 두세요.", "AN-01"))
    if len(arms) >= 2 and spend > 0:
        shares = sorted(a["spend"] / spend for a in arms)
        if shares[-1] - shares[0] > cfg["spend_gap_pp"]:
            out.append(_a("warn", "spend_gap", f"두 세트 지출이 {shares[0]:.0%} : {shares[-1]:.0%}로 쏠렸어요. 확실도를 한 단계 낮춰서 봐요.",
                          "다음엔 메타 'A/B 테스트'로 만들어 예산을 똑같이 나눠 주세요.", "AN-04"))
    low = [a for a in arms if a["link_clicks"] < cfg["min_clicks"]]
    if low:
        names = ", ".join(f"{a['name']} {int(a['link_clicks'])}번" for a in low)
        out.append(_a("warn", "small_sample", f"링크 클릭이 적어요 ({names}). 판정은 최대 '유력'까지만 해요.",
                      f"세트마다 클릭이 {cfg['min_clicks']}번 넘게 모이도록 기간이나 예산을 늘려 보세요.", "AN-02"))
    for a in arms:
        r = a.get("click_to_visit")
        if r is not None and a["link_clicks"] > 0 and r < cfg["visit_rate_min"]:
            out.append(_a("warn", "low_visit_rate", f"{a['name']}: 누른 사람 중 {r:.0%}만 페이지에 들어왔어요.",
                          "페이지가 느리거나 주소가 틀렸을 수 있어요. 휴대폰으로 광고 주소를 열어 확인해 주세요.", "AN-02"))
    if "reach" in daily.columns and float(daily["reach"].sum()) > 0:
        freq = float(daily["impressions"].sum()) / float(daily["reach"].sum())
        if freq > cfg["frequency_max"]:
            out.append(_a("warn", "high_frequency", f"한 사람에게 평균 {freq:.1f}번 보였어요.", "소재를 새로 바꾸거나 타깃을 넓혀 보세요.", "AN-02"))

    # ● 참고: 메타 추천 ≠ 실측 (메타는 자동 노출 위치를 권장)
    auto = [a for a in arms if "자동" in a["name"]]
    manual = [a for a in arms if "자동" not in a["name"]]
    if len(arms) >= 2 and auto and manual and auto[0].get("cpm") and manual[0].get("cpm") and manual[0]["cpm"] < auto[0]["cpm"]:
        pct = 1 - manual[0]["cpm"] / auto[0]["cpm"]
        out.append(_a("info", "meta_vs_measured", f"메타는 자동 노출 위치를 권하지만, 이번 실측은 수동이 CPM {pct:.0%} 저렴했어요.",
                      "실측을 우선해요. 메타 추천은 참고로만 봐요.", "AN-03"))

    return sorted(out, key=lambda x: ORDER[x["level"]])


def blocked(alerts: List[Dict]) -> bool:
    return any(a["level"] == "block" for a in alerts)
