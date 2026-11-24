"""진단 매트릭스 (v4 3장): 신호 → 막힌 퍼널 단계 → 바꿀 칸 1개.

위에서부터(0 게재 → 1 노출 단가 → 2 클릭 → 3 도착 → 4 행동) 처음 막힌 단계의 칸을 고친다.
막힌 곳이 없으면 5 노출 위치 집중(그 자리에 맞는 소재)을 제안한다. 6 학습 단계는 '하지 말 것'의 근거.
판단은 이 코드가 하고, 광고 어시스턴트(LLM)는 결과를 쉬운 말로 풀기만 한다. 기준값은 rules.yaml loop.matrix.
"""
from typing import Dict, List, Optional

from ..specs import all_fields, fields as _fields
from ..specs import loop as _loop

PATH = {
    "meta.campaign.objective": "캠페인 › 목표",
    "meta.adset.performance_goal": "광고 세트 › 성과 목표",
    "meta.adset.placements": "광고 세트 › 노출 위치",
    "meta.adset.age_gender": "광고 세트 › 연령·성별",
    "meta.adset.location": "광고 세트 › 위치",
    "meta.adset.daily_budget": "광고 세트 › 예산",
    "meta.adset.end_date": "광고 세트 › 시작·종료 날짜",
    "meta.ad.media": "광고 › 형식·미디어",
    "meta.ad.format": "광고 › 형식·미디어",
    "meta.creative.copy": "광고 › 기본 문구·제목",
    "meta.creative.cta": "광고 › 버튼(행동 유도)",
    "meta.ad.website_url": "광고 › 웹사이트 URL",
}
LABEL_OF = {"채택": "확실", "유력": "유력", "보류": "보류"}

_NAME_HINTS = [
    (("노출위치", "노출 위치", "AN제외", "AN 제외", "피드만", "릴스만", "어드밴티지"), "meta.adset.placements"),
    (("연령", "20대", "30대", "40대", "50대", "여성", "남성"), "meta.adset.age_gender"),
    (("문구", "제목", "카피"), "meta.creative.copy"),
    (("소재", "이미지", "영상", "동영상", "세로"), "meta.ad.media"),
    (("예산",), "meta.adset.daily_budget"),
]


def tested_field(names: List[str]) -> Optional[str]:
    """세트 이름으로 무엇을 비교했는지 추정 (세팅값이 오면 그쪽이 우선)."""
    joined = " ".join(names)
    for words, field in _NAME_HINTS:
        if any(w in joined for w in words):
            return field
    return None


def _suffix(name: str) -> str:
    return name.split("_", 1)[1] if "_" in name else name


def _value(field: Optional[str], arm_name: str) -> str:
    s = _suffix(arm_name)
    if field == "meta.adset.placements":
        return "자동 (어드밴티지+)" if "자동" in s else f"수동 · {s}"
    return s


def _certainty(level: str, why: str) -> Dict:
    return {"level": level, "label": LABEL_OF[level], "why": why}


def _row(row: str, stage: str, signal: str, status: str, field: Optional[str] = None, detail: str = "") -> Dict:
    return {"row": row, "stage": stage, "signal": signal, "status": status, "field_id": field,
            "path": PATH.get(field or "", ""), "detail": detail}


def run(summary: Dict, check: Dict, verdict: Optional[Dict], alerts: List[Dict], settings: Optional[Dict] = None) -> Dict:
    cfg = _loop()["matrix"]
    settings = settings or {}
    arms = summary["arms"]
    tot = {k: sum(a[k] for a in arms) for k in ("spend", "impressions", "link_clicks", "landing_page_views")}
    days = check["read"]["days"]
    kinds = {a["kind"] for a in alerts}
    no_delivery = [a for a in alerts if a["kind"] == "no_delivery"]
    field = tested_field([a["name"] for a in arms])
    rows: List[Dict] = []
    keep: List[Dict] = []
    watch: List[Dict] = []
    proposals: Dict[str, Dict] = {}

    # 0 게재
    if "underspent" in kinds or (days and len(no_delivery) / days >= 0.5):
        rows.append(_row("0", "게재", "광고가 안 나간 날이 많거나 예산을 반도 못 썼어요", "blocked", "meta.adset.daily_budget"))
        proposals["0"] = {"field_id": "meta.adset.daily_budget", "new": "총예산을 하루 최소 × 기간 이상으로, 타깃이 좁으면 넓히기",
                          "reason": "광고가 충분히 나가지 않아 다른 숫자를 판단할 수 없어요.", "level": "유력", "grade": "A"}
    elif no_delivery:
        rows.append(_row("0", "게재", f"광고가 안 나간 날 {len(no_delivery)}일", "watch", "meta.adset.end_date"))
        watch.append({"field_id": "meta.adset.end_date", "path": PATH["meta.adset.end_date"],
                      "text": "첫날은 심사·학습으로 늦게 나갈 수 있어요. 다음엔 시작 시간에 여유를 두세요."})
    else:
        rows.append(_row("0", "게재", "매일 광고가 나갔어요", "ok"))

    # 1 노출 단가 (CPM)
    cpm = next((m for m in (verdict or {}).get("metrics", []) if m["key"] == "cpm"), None)
    if cpm and (cpm["word"] == "확실해요" or max(cpm["prob_b_better"], 1 - cpm["prob_b_better"]) >= 0.9):
        cheap = arms[1] if cpm["prob_b_better"] >= 0.5 else arms[0]
        dear = arms[0] if cheap is arms[1] else arms[1]
        pct = 1 - cheap["cpm"] / dear["cpm"]
        rows.append(_row("1", "노출 단가", f"{dear['name']}의 CPM이 {pct:.0%} 비쌈", "ok", field,
                         f"{_suffix(cheap['name'])} 쪽을 유지하면 해결돼요"))
        if field:
            keep.append({"field_id": field, "path": PATH.get(field, field), "value": _value(field, cheap["name"]),
                         "reason": f"같은 돈으로 더 많이 보여 줬어요 (CPM {pct:.0%} 저렴, 확실)"})
    elif len(arms) == 1 and arms[0].get("cpm") and arms[0]["cpm"] > cfg["cpm_high"]:
        rows.append(_row("1", "노출 단가", f"CPM ₩{arms[0]['cpm']:,.0f}이 기준보다 높아요", "blocked", "meta.adset.placements"))
        proposals["1"] = {"field_id": "meta.adset.placements", "new": "노출 위치 직접 고르기 (피드·릴스), 연령 '더 제한하기'로 고정",
                          "reason": "노출 단가가 높아 같은 돈으로 적게 보여 줘요.", "level": "유력", "grade": "D"}
    else:
        rows.append(_row("1", "노출 단가", "CPM 차이가 뚜렷하지 않아요", "ok"))

    # 2 클릭
    ctr = tot["link_clicks"] / tot["impressions"] if tot["impressions"] else None
    if ctr is not None and ctr < cfg["ctr_low"]:
        rows.append(_row("2", "클릭", f"클릭률 {ctr:.1%}가 기준 {cfg['ctr_low']:.0%}보다 낮아요", "blocked", "meta.ad.media"))
        proposals["2"] = {"field_id": "meta.ad.media", "new": "소재 바꾸기 (세로형 추가, 첫 장면에 상품)",
                          "reason": "보는 사람은 많은데 누르는 사람이 적어요. 소재·문구가 눈길을 못 끌어요.", "level": "유력", "grade": "A"}
    else:
        rows.append(_row("2", "클릭", f"클릭률 {ctr:.1%} 정상" if ctr is not None else "클릭 자료 없음", "ok" if ctr is not None else "skip"))

    # 2b 소재 피로
    if days < cfg["fatigue_days"] or "reach" not in check.get("columns", []):
        rows.append(_row("2b", "클릭 (피로)", f"기간 {days}일 · 도달 열 없음 → 해당 없음", "skip"))
    else:
        rows.append(_row("2b", "클릭 (피로)", "빈도·클릭률 변화 정상", "ok"))

    # 3 도착
    vr = tot["landing_page_views"] / tot["link_clicks"] if tot["link_clicks"] else None
    if vr is not None and tot["link_clicks"] >= 10 and vr < cfg["visit_rate_min"]:
        rows.append(_row("3", "도착", f"누른 사람 중 {vr:.0%}만 도착", "blocked", "meta.ad.website_url"))
        proposals["3"] = {"field_id": "meta.ad.website_url", "new": "페이지 속도·주소 점검, Audience Network 빼기",
                          "reason": "누르고도 페이지에 못 들어온 사람이 많아요.", "level": "유력", "grade": "A"}
    else:
        rows.append(_row("3", "도착", f"누른 사람 중 {vr:.0%} 도착 (정상)" if vr is not None else "도착 자료 없음", "ok" if vr is not None else "skip"))

    # 4 행동 (구매·문의 열이 있을 때만)
    rows.append(_row("4", "행동", "행동(구매·문의) 열이 없거나 표본이 적어요 → 보류", "skip"))

    # 5 노출 위치 집중
    places = summary.get("placements") or []
    top = max(places, key=lambda p: p["share"]) if places else None
    if top and top["share"] >= cfg["placement_share"]:
        vertical = any(w in top["label"] for w in ("릴스", "스토리"))
        new = f"{top['label'].split()[-1]}용 세로(9:16) 소재 추가" if vertical else "피드용 정사각(1:1)·세로(4:5) 소재 추가"
        rows.append(_row("5", "(전 단계)", f"{top['label']}에 지출 {top['share']:.0%}", "found", "meta.ad.media"))
        proposals["5"] = {"field_id": "meta.ad.media", "new": new,
                          "reason": f"돈의 {top['share']:.0%}가 {top['label']}에 쓰였어요. 그 자리에 맞는 모양의 소재가 있으면 더 잘 보여요.",
                          "level": "유력", "grade": "A", "meta_says": "메타 Opportunity Score도 릴스에는 9:16 소재를 권해요."}
    else:
        rows.append(_row("5", "(전 단계)", "한 자리에 몰리지 않았어요", "ok"))

    # 6 학습 단계
    per_week = (tot["link_clicks"] / max(1, len(arms))) * 7 / max(1, days)
    learning = per_week < cfg["learning_events"]
    rows.append(_row("6", "(구조)", f"세트당 주 {per_week:.0f}회 < {cfg['learning_events']}회 → 학습 완료 어려움" if learning else "학습에 충분해요",
                     "watch" if learning else "ok", "meta.adset.performance_goal" if learning else None))

    pick = next((r["row"] for r in rows if r["status"] == "blocked"), None) or ("5" if "5" in proposals else None)
    change = None
    if pick:
        p = proposals[pick]
        cert_level = p["level"]
        if verdict and verdict["badge"].get("capped") and cert_level == "채택":
            cert_level = "유력"
        checklist = [a["todo"] for a in alerts if a["level"] == "warn"]
        checklist.append("다음 테스트는 이 칸 1개만 바꾸고, 나머지는 그대로 둬요.")
        change = {"row": pick, "field_id": p["field_id"], "path": PATH[p["field_id"]],
                  "label": PATH[p["field_id"]].split(" › ")[-1],
                  "now": settings.get(p["field_id"]), "new": p["new"], "reason": p["reason"],
                  "certainty": _certainty(cert_level, "실측 + 진단 규칙" + (" + 메타 권장" if p.get("meta_says") else "")),
                  "grade": p["grade"], "meta_says": p.get("meta_says"), "checklist": checklist}

    if verdict and verdict["badge"]["level"] == "유력" and verdict.get("min_budget", {}).get("per_group"):
        watch.append({"field_id": "meta.adset.daily_budget", "path": PATH["meta.adset.daily_budget"],
                      "text": f"기간·예산: 지금 판정은 유력이에요. 세트당 ₩{verdict['min_budget']['per_group']:,}쯤 쓰면 확실히 고를 수 있어요."})

    dont = ["여러 칸을 한 번에 바꾸지 않기 — 무엇 때문에 달라졌는지 알 수 없게 돼요.",
            "평균만 보고 노출 위치·연령을 끄지 않기 — 메타는 다음 1건의 비용으로 돈을 나눠요(Breakdown effect). 끄고 싶으면 다음 5,000원 테스트로 확인해요."]
    if learning:
        dont.append("자주 고치지 않기 — 큰 수정은 학습을 처음부터 다시 시작시켜요.")

    return {"rows": rows, "change": change, "keep": keep, "watch": watch, "dont": dont, "tested_field": field,
            "settings": setting_rows(settings, change, keep, watch)}


def _spec_id(field_id: str) -> Optional[str]:
    """확장의 칸 id → 사양 id ('meta.creative.copy.text' → 'meta.creative.copy')."""
    known = all_fields()
    while field_id and field_id not in known:
        field_id = field_id.rsplit(".", 1)[0] if "." in field_id else ""
    return field_id or None


def setting_rows(settings: Dict, change: Optional[Dict], keep: List[Dict], watch: List[Dict]) -> List[Dict]:
    """AN-03 내 세팅 카드: 받은 세팅값 전부를 광고 관리자 순서로, 칸마다 변경·유지·검토·그대로 + 근거 한 줄."""
    if not settings:
        return []
    order = {f["id"]: i for i, f in enumerate(_fields("meta")["fields"])}
    known = all_fields()
    keep_by = {k["field_id"]: k for k in keep}
    watch_by = {w["field_id"]: w for w in watch}
    out = []
    for fid, value in settings.items():
        sid = _spec_id(fid)
        spec = known.get(sid or "", {})
        path = PATH.get(fid) or PATH.get(sid or "") or f"{spec.get('stage', '기타')} › {spec.get('label', fid)}"
        if change and sid and (_spec_id(change["field_id"]) == sid or path == change["path"]):   # 같은 자리(형식·미디어)면 같이
            kind, note = "변경", f"{change['new']} — {change['reason']}"
        elif sid in keep_by:
            kind, note = "유지", keep_by[sid]["reason"]
        elif sid in watch_by:
            kind, note = "검토", watch_by[sid]["text"]
        else:
            kind, note = "그대로", "이번 결과로는 바꿀 이유가 없어요."
        out.append({"field_id": fid, "path": path, "value": str(value), "kind": kind, "note": note,
                    "_order": order.get(sid or "", 999)})
    out.sort(key=lambda x: x.pop("_order"))
    return out
