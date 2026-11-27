"""이상 알림 3단계 (v4 6장, 문구는 v4.2 AN-ALT·AN-TXT): ■ 차단 · ▲ 주의 · ● 참고.

이상한 데이터로 잘못된 결론을 내지 않게, 결론보다 먼저 계산한다. 기준값은 rules.yaml loop.alerts.
색만으로 구분하지 않게 모양(mark)을 같이 준다 (WCAG 1.4.1). ▲는 주의 전용.
문구는 사장님 말로: 금액은 '원', 판정은 '확실해요 / ○ 쪽이에요 / 아직 몰라요', CPM 같은 약어는 쓰지 않는다.
"""
from typing import Dict, List, Optional

from ..specs import loop as _loop
from .words import won as _won

MARK = {"block": "■", "warn": "▲", "info": "●"}
ORDER = {"block": 0, "warn": 1, "info": 2}
REQUIRED = {"spend": "지출 금액", "impressions": "노출", "link_clicks": "링크 클릭", "landing_page_views": "랜딩 페이지 조회"}


def parse_won(text) -> float:
    """'3만 원' · '25,000원' · '10000' → 원. 못 읽으면 0."""
    t = str(text or "").replace(",", "").replace(" ", "").replace("원", "")
    try:
        return float(t[:-1]) * 10000 if t.endswith("만") else float(t)
    except ValueError:
        return 0.0


def _a(level: str, kind: str, text: str, todo: str, screen: str, **extra) -> Dict:
    return dict({"level": level, "mark": MARK[level], "kind": kind, "text": text, "todo": todo, "screen": screen}, **extra)


def run(bundle, check: Dict, summary: Dict, settings: Optional[Dict] = None) -> List[Dict]:
    cfg = _loop()["alerts"]
    daily = bundle.tables["meta_daily"].df
    out: List[Dict] = []

    # ■ 차단: 필수 열 · 합계 불일치
    missing = [k for k in REQUIRED if k not in daily.columns]
    no_visits = "landing_page_views" not in daily.columns or float(daily["landing_page_views"].sum()) == 0
    if "meta_placement" not in bundle.tables:
        missing.append("placement")
    for k in missing:
        name = "노출 위치(분석 데이터)" if k == "placement" else REQUIRED[k]
        text = "노출 위치별로 나눠서 다시 내보내 주세요." if k == "placement" else f"'{name}' 열이 없어요."
        out.append(_a("block", "missing_column", text,
                      f"광고 관리자 › 광고 세트 탭 › 표 위 '분석 데이터'에서 '일 · 노출 위치'에 체크하고 '{name}' 열이 보이게 해서 다시 내보내 주세요.", "AN-00"))
    if no_visits and "landing_page_views" in daily.columns:
        # 열은 있는데 칸이 다 비었으면 다시 내보내도 같다: 웹사이트에 픽셀이 없거나 성과 목표가 랜딩 페이지 조회가 아닌 경우
        out.append(_a("block", "missing_column", "'랜딩 페이지 조회' 칸이 다 비어 있어요.",
                      "웹사이트에 메타 픽셀을 연결하고, 성과 목표를 '랜딩 페이지 조회 수 극대화'로 둔 광고의 결과를 올려 주세요.", "AN-00"))
    # 같은 날 같이 돌린 두 세트만 비교할 수 있어요 (다른 날이면 날짜·경쟁 차이가 섞임)
    if len(summary["arms"]) >= 2 and "spend" in daily.columns:
        names = [a["name"] for a in summary["arms"][:2]]
        on = [set(daily[(daily["adset"] == n) & (daily["spend"] > 0)]["date"]) for n in names]
        both = on[0] & on[1]
        # 두 세트 모두 돈의 절반 이상을 같이 돌린 날에 써야 비교할 수 있다 (하루만 살짝 겹친 건 같이 돌린 게 아님)
        share = [daily[(daily["adset"] == n) & daily["date"].isin(both)]["spend"].sum() / max(1e-9, daily[daily["adset"] == n]["spend"].sum())
                 for n in names]
        if min(share) < 0.5:
            out.append(_a("block", "not_same_days", "두 세트를 같은 날 같이 돌리지 않아서 비교할 수 없어요.",
                          "비교할 두 세트를 같은 날 같이 시작해 돌린 기간만 골라 다시 내보내 주세요.", "AN-00"))
    for t in check.get("totals", []):
        d, p = t["daily"], t["placement"]
        if abs(d - p) > max(1.0, cfg["sum_mismatch"] * abs(d)):
            out.append(_a("block", "sum_mismatch", "기간이 겹치거나 빠진 날이 있어요.",
                          f"같은 기간·같은 캠페인으로 다시 내보내 주세요. (날짜별 합 {d:,.0f} · 노출 위치별 합 {p:,.0f})", "AN-00"))

    # ▲ 주의
    for w in check.get("warnings", []):
        if w["kind"] == "no_delivery":
            extra = {"date": w.get("date")}
            if w.get("later"):
                extra["later"] = w["later"]   # 다음 화면 알림 바: '11/17은 광고가 안 나가서 비교에서 뺐어요'
            out.append(_a("warn", "no_delivery", w["text"], "첫날은 심사로 늦게 나갈 수 있어요. 다음엔 시작 시간을 하루 여유 있게 잡아 주세요. 이 날은 비교에서 뺐어요.", "AN-01", **extra))
        elif w["kind"] == "placement_skew":
            out.append(_a("warn", "an_skew", w["text"], "노출 위치를 직접 고르기(수동)로 바꿔 Audience Network를 빼 보세요.", "AN-04"))

    arms = summary["arms"]
    spend = sum(a["spend"] for a in arms)
    # ALT-12 예산 덜 씀: 설정 예산은 결과 파일의 예산 열(광고 세트 예산·유형)이 먼저, 없으면 세팅값의 하루 예산 × 기간 × 세트 수
    # (확장 ② 세팅의 '광고 세트 총예산' 답이 오면 그 금액 × 세트 수)
    expected = float((getattr(bundle, "budget", None) or {}).get("total") or 0)
    s = settings or {}
    if not expected and parse_won(s.get("meta.adset.lifetime_budget")):
        expected = parse_won(s["meta.adset.lifetime_budget"]) * len(arms)
    if not expected and parse_won(s.get("meta.adset.daily_budget")):
        expected = parse_won(s["meta.adset.daily_budget"]) * daily["date"].nunique() * len(arms)
    if expected:
        if spend / expected < cfg["spend_used_min"]:
            out.append(_a("warn", "underspent", f"예산의 절반도 못 썼어요 (쓴 돈 {_won(spend)} / 설정 {_won(expected)}) → 타깃 범위가 너무 좁을 수 있어요.",
                          "타깃을 넓히거나 총예산을 '하루 최소 × 기간'보다 넉넉하게 잡아 주세요.", "AN-01"))
    pair = arms[:2]   # 판정은 A·B 두 세트만 비교한다 → 쏠림·표본도 두 세트로 본다 (세트가 3개면 셋째가 섞였다, 감사 15)
    pair_spend = sum(a["spend"] for a in pair)
    if len(pair) >= 2 and pair_spend > 0:
        shares = sorted(a["spend"] / pair_spend for a in pair)
        if shares[-1] - shares[0] > cfg["spend_gap_pp"]:
            out.append(_a("warn", "spend_gap", f"한쪽에 돈이 몰렸어요 ({shares[0]:.0%} : {shares[-1]:.0%}) → 비교 결과를 조심해서 보세요.",
                          "그래서 판정을 한 단계 낮춰 보여 드려요. 다음엔 두 세트 예산을 똑같이 나눠 주세요.", "AN-04"))
    # ALT-14 표본 부족: 링크 클릭 < 30 (세트 합) 또는 행동(알림 신청 등) < 5 (세트 합, 파일에 있을 때)
    clicks = sum(a["link_clicks"] for a in pair)
    acts = [a.get("actions") for a in pair]
    actions = sum(acts) if acts and all(x is not None for x in acts) else None
    if clicks < cfg["min_clicks"]:
        names = " · ".join(f"{'AB'[i] if i < 2 else a['name']} {int(a['link_clicks'])}번" for i, a in enumerate(arms))
        out.append(_a("warn", "small_sample", f"클릭이 적어서 아직 몰라요 ({names}) · 클릭이 {cfg['min_clicks']}번 넘게 모이면 알 수 있어요.",
                      f"그래서 화면 판정은 'B 쪽이에요'까지만 보여 드려요. 클릭이 {cfg['min_clicks']}번 넘게 모일 때까지 그대로 두세요.", "AN-02"))
    elif actions is not None and actions < cfg["min_actions"]:
        label = summary.get("action_label") or "행동"
        out.append(_a("warn", "small_sample", f"{label}이 {int(actions)}건뿐이라 ④단계는 아직 몰라요.",
                      f"{label}이 {cfg['min_actions']}건 넘게 모이면 알 수 있어요. 그래서 화면 판정은 'B 쪽이에요'까지만 보여 드려요.", "AN-02", actions=actions))
    for a in arms if not no_visits else []:   # 도착 칸이 비었으면 0명으로 세지 않는다 (위 차단 알림)
        r = a.get("click_to_visit")
        if r is not None and a["link_clicks"] > 0 and r < cfg["visit_rate_min"]:
            out.append(_a("warn", "low_visit_rate", f"{a['name']}: 누른 {int(a['link_clicks'])}명 중 {int(a['landing_page_views'])}명만 페이지에 들어왔어요 → 링크 주소 · 페이지 속도",
                          "휴대폰으로 광고 주소를 열어 주소가 맞는지, 빨리 열리는지 확인해 주세요.", "AN-02"))
    # ALT-16 반복 노출: 세트마다 빈도의 최솟값(노출 ÷ 도달 합)이 기준을 넘으면 → 실제 빈도도 넘는다
    freqs = [(a, a["frequency_min"]) for a in arms if a.get("frequency_min") is not None]
    if freqs:
        top, freq = max(freqs, key=lambda x: x[1])
        if freq > cfg["frequency_max"]:
            who = f"{top['name']}: " if len(arms) > 1 else ""
            out.append(_a("warn", "high_frequency", f"{who}한 사람이 평균 {cfg['frequency_max']:g}번 넘게 봤어요 (적어도 {freq:.1f}번) → 소재를 바꿀 때예요.",
                          "새 소재를 준비하거나 타깃을 넓혀 보세요.", "AN-02", frequency=freq))

    from .matrix import differing_fields
    differ = differing_fields(arms)
    # ● 참고: 메타 추천 ≠ 실측 (메타는 자동 노출 위치를 권장)
    auto = [a for a in arms if "자동" in a["name"]]
    manual = [a for a in arms if "자동" not in a["name"]]
    if len(arms) >= 2 and auto and manual and auto[0].get("cpm") and manual[0].get("cpm") and manual[0]["cpm"] < auto[0]["cpm"]:
        pct = 1 - manual[0]["cpm"] / auto[0]["cpm"]
        if len(differ) >= 2:
            out.append(_a("info", "meta_vs_measured", f"메타는 '노출 위치 자동'을 권해요. 우리 결과에선 '직접 고르기(수동)' 세트가 광고비가 {pct:.0%} 쌌지만, "
                          f"{' · '.join(differ[:3])}이 같이 달라서 어느 칸 덕인지는 몰라요.",
                          "지금 세트는 그대로 두고, 노출 위치만 다르게 한 비교로 확인해 보세요.", "AN-03", saving=pct))
        else:
            out.append(_a("info", "meta_vs_measured", f"메타는 '노출 위치 자동'을 권하지만, 우리가 돌려 본 결과에선 '직접 고르기(수동)'가 광고비가 {pct:.0%} 쌌어요.",
                          "지금은 수동을 유지하세요. 메타 추천은 참고로만 봐요.", "AN-03", saving=pct))

    # ● 참고: 여러 칸이 함께 다름 (ALT-23) — 세트 이름으로 보면 두 칸 이상이 다르게 설정됨
    if len(arms) >= 2:
        if len(differ) >= 2:
            out.append(_a("info", "many_fields", f"{' · '.join(differ[:3])}이 같이 달라서 어느 칸 덕인지는 몰라요.",
                          "다음엔 칸 1개만 다르게 두 세트를 만들어 주세요.", "AN-04", fields=differ))

    # ● 참고: 세트가 3개 이상이면 이름 순 앞 두 세트만 A·B로 비교
    if len(arms) > 2:
        out.append(_a("info", "extra_sets", f"세트가 {len(arms)}개예요. 이름 순으로 앞 두 세트(A {arms[0]['name']} · B {arms[1]['name']})만 비교했어요. "
                      f"빠진 세트: {', '.join(a['name'] for a in arms[2:])}",
                      "다른 세트끼리 보려면 비교할 두 세트만 골라 다시 내보내 주세요.", "AN-01"))

    # ● 참고: 써 본 적 없는 금액 (AN-05 예산 슬라이더) — 그보다 큰 금액은 가설
    if arms and spend > 0:
        most = max(a["spend"] for a in arms)
        out.append(_a("info", "untried_budget", f"세트당 {_won(most)}까지만 써 봤어요. 그 이상은 가설이라 범위가 넓어요.",
                      "써 본 적 없는 금액은 점선으로 보여 드려요.", "AN-05", spent=most, shown_from="AN-05"))

    return sorted(out, key=lambda x: ORDER[x["level"]])


def blocked(alerts: List[Dict]) -> bool:
    return any(a["level"] == "block" for a in alerts)
