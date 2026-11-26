"""진단 매트릭스 (v4 3장): 신호 → 막힌 퍼널 단계 → 바꿀 칸 1개.

위에서부터(0 게재 → 1 노출 단가 → 2 클릭 → 3 도착 → 4 행동) 처음 막힌 단계의 칸을 고친다.
막힌 곳이 없으면 5 노출 위치 집중(그 자리에 맞는 소재)을 제안한다. 6 학습 단계는 '하지 말 것'의 근거.
판단은 이 코드가 하고, 광고 어시스턴트(LLM)는 결과를 쉬운 말로 풀기만 한다. 기준값은 rules.yaml loop.matrix.
"""
from typing import Dict, List, Optional

from ..specs import all_fields, fields as _fields
from ..specs import loop as _loop
from .words import arm_short, josa, per_people, won

PATH = {
    "meta.campaign.objective": "캠페인 › 목표",
    "meta.adset.performance_goal": "광고 세트 › 성과 목표",
    "meta.adset.placements": "광고 세트 › 노출 위치",
    "meta.adset.age_gender": "광고 세트 › 연령·성별",
    "meta.adset.location": "광고 세트 › 위치",
    "meta.adset.daily_budget": "광고 세트 › 예산",
    "meta.adset.lifetime_budget": "광고 세트 › 예산",
    "meta.adset.end_date": "광고 세트 › 시작·종료 날짜",
    "meta.adset.start_date": "광고 세트 › 시작·종료 날짜",
    "meta.ad.media": "광고 › 형식·미디어",
    "meta.ad.format": "광고 › 형식·미디어",
    "meta.creative.copy": "광고 › 기본 문구·제목",
    "meta.creative.cta": "광고 › 버튼(행동 유도)",
    "meta.ad.website_url": "광고 › 웹사이트 URL",
}
# 사장님 화면 판정 3단어 (근거 탭·개발 문서의 level 값은 채택·유력·보류 그대로)
LABEL_OF = {"채택": "확실해요", "유력": "쪽이에요", "보류": "아직 몰라요"}
# AN-03 상태 배지 (v4.2: 변경/검토/유지 → 테스트/다시 보기/그대로)
TEST, RECHECK, SAME = "테스트", "다시 보기", "그대로"

_NAME_HINTS = [
    (("노출위치", "노출 위치", "AN제외", "AN 제외", "피드만", "릴스만", "어드밴티지"), "meta.adset.placements"),
    (("연령", "20대", "30대", "40대", "50대", "여성", "남성"), "meta.adset.age_gender"),
    (("문구", "제목", "카피"), "meta.creative.copy"),
    (("소재", "이미지", "영상", "동영상", "세로"), "meta.ad.media"),
    (("예산",), "meta.adset.daily_budget"),
]


NAME_LABELS = {"meta.adset.placements": "노출 위치", "meta.adset.age_gender": "연령·성별", "meta.creative.copy": "문구",
               "meta.ad.media": "소재", "meta.adset.daily_budget": "예산"}


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
        if "자동" in s:
            return "자동 (Advantage+)"
        return "직접 고르기(수동)" + (", Audience Network 제외" if any(w in s for w in ("AN제외", "AN 제외")) else "")
    return s


def _certainty(level: str, why: str, better: str = "B") -> Dict:
    label = f"{better} 쪽이에요" if level == "유력" else LABEL_OF[level]
    return {"level": level, "label": label, "why": why}


def _row(row: str, stage: str, signal: str, status: str, field: Optional[str] = None, detail: str = "") -> Dict:
    return {"row": row, "stage": stage, "signal": signal, "status": status, "field_id": field,
            "path": PATH.get(field or "", ""), "detail": detail}


def _has_vertical(settings: Dict) -> Optional[bool]:
    """내 광고 설정에 세로 소재가 있는지 (모르면 None)."""
    vals = [str(v) for k, v in settings.items() if k.startswith(("meta.ad.media", "meta.ad.format"))]
    if not vals:
        return None
    return any(w in " ".join(vals) for w in ("세로", "9:16", "릴스", "동영상", "영상"))


def _checklist(alerts: List[Dict], label: str) -> List[str]:
    """남은 주의 알림 → 할 일 + '칸 1개만' + '같은 날 같이 시작' (v4.2 AN-06 · EX-03, ALT 번호는 숨김)."""
    cfg = _loop()
    words = cfg.get("checklist", {})
    out: List[str] = []
    for a in alerts:
        t = words.get(a["kind"]) if a["level"] == "warn" else None
        if t:
            t = t.format(min_clicks=cfg["alerts"]["min_clicks"], label=label)
            if t not in out:
                out.append(t)
    out.append(words.get("one_field", "바꾸는 칸은 {label} 1개만").format(label=label))
    out.append(words.get("same_day", "두 세트는 같은 날 같이 시작"))
    return out


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
        proposals["0"] = {"field_id": "meta.adset.daily_budget", "new": "총예산을 '하루 최소 × 기간'보다 넉넉하게, 타깃이 좁으면 넓히기",
                          "short": "총예산 넉넉하게", "what": "넉넉한 총예산",
                          "reason": "광고가 충분히 나가지 않아서 다른 숫자를 판단할 수 없어요.", "level": "유력", "grade": "A"}
    elif no_delivery:
        rows.append(_row("0", "게재", f"광고가 안 나간 날 {len(no_delivery)}일", "watch", "meta.adset.end_date"))
        watch.append({"field_id": "meta.adset.end_date", "path": PATH["meta.adset.end_date"], "title": "시작 시간",
                      "text": "첫날 안 보여졌어요 → 다음엔 시작 시간을 하루 여유 있게"})
    else:
        rows.append(_row("0", "게재", "매일 광고가 나갔어요", "ok"))

    # 1 광고가 보이는 값 (CPM)
    cpm = next((m for m in (verdict or {}).get("metrics", []) if m["key"] == "cpm"), None)
    if cpm and (cpm["word"] == "확실해요" or max(cpm["prob_b_better"], 1 - cpm["prob_b_better"]) >= 0.9):
        ci = 1 if cpm["prob_b_better"] >= 0.5 else 0
        cheap, dear = arms[ci], arms[1 - ci]
        pct = 1 - cheap["cpm"] / dear["cpm"]
        rows.append(_row("1", "광고가 보이는 값", f"{arm_short(cheap['name'], ci)}가 {pct:.0%} 싸요 · 확실해요", "ok", field,
                         f"{arm_short(cheap['name'], ci)} 쪽을 유지하면 돼요"))
        if field:
            keep.append({"field_id": field, "path": PATH.get(field, field), "value": _value(field, cheap["name"]),
                         "reason": f"↓ 광고비 {pct:.0%} 싸요 · 확실해요", "saving": pct, "arm": cheap["name"]})
    elif len(arms) == 1 and arms[0].get("cpm") and arms[0]["cpm"] > cfg["cpm_high"]:
        rows.append(_row("1", "광고가 보이는 값", f"광고 1,000번 보여주는 데 {won(arms[0]['cpm'])} 들어서 기준보다 비싸요", "blocked", "meta.adset.placements"))
        proposals["1"] = {"field_id": "meta.adset.placements", "new": "노출 위치 직접 고르기(수동: 피드·릴스), 연령 '더 제한하기'로 고정",
                          "short": "노출 위치 직접 고르기(수동)", "what": "직접 고른 노출 위치",
                          "reason": "광고를 보여주는 값이 비싸서 같은 돈으로 적게 보여요.", "level": "유력", "grade": "D"}
    else:
        rows.append(_row("1", "광고가 보이는 값", "두 세트 광고비 차이가 뚜렷하지 않아요" if len(arms) > 1
                         else "비교할 세트가 하나라 광고비 비교는 없어요", "ok" if len(arms) > 1 else "skip"))

    # 2 본 사람이 누르는 정도
    ctr = tot["link_clicks"] / tot["impressions"] if tot["impressions"] else None
    if ctr is not None and ctr < cfg["ctr_low"]:
        rows.append(_row("2", "누르는 정도", f"1,000명이 보면 {per_people(ctr)}이 눌러요 · 기준({per_people(cfg['ctr_low'])})보다 적어요", "blocked", "meta.ad.media"))
        proposals["2"] = {"field_id": "meta.ad.media", "new": "소재 바꾸기 (세로형 추가, 첫 장면에 상품)", "short": "+ 새 소재 1개", "what": "새 소재",
                          "reason": "보는 사람은 많은데 누르는 사람이 적어요. 소재·문구가 눈길을 못 끌어요.", "level": "유력", "grade": "A"}
    else:
        rows.append(_row("2", "누르는 정도", f"1,000명이 보면 {per_people(ctr)}이 눌러요 → 괜찮아요" if ctr is not None else "클릭 자료가 없어요",
                         "ok" if ctr is not None else "skip"))

    # 2b 소재 피로
    # 빈도↑(적어도 기준 넘게 봄) + 클릭률↓(기간 뒤 절반이 앞 절반보다 기준 넘게 떨어짐), 기간이 짧거나 도달 열이 없으면 건너뜀
    freq_max = _loop()["alerts"]["frequency_max"]
    tired = [a for a in arms if (a.get("frequency_min") or 0) > freq_max and a.get("ctr_first") and a.get("ctr_last") is not None
             and a["ctr_last"] <= a["ctr_first"] * (1 - cfg["fatigue_ctr_drop"])]
    if days < cfg["fatigue_days"] or not any(a.get("frequency_min") is not None for a in arms):
        why = f"기간 {days}일이라 아직 해당 없음 ({cfg['fatigue_days']}일 이상일 때 봐요)" if days < cfg["fatigue_days"] else "본 사람 수(도달) 열이 없어 해당 없음"
        rows.append(_row("2b", "누르는 정도 (같은 소재 피로)", why, "skip"))
    elif tired:
        a = tired[0]
        drop = 1 - a["ctr_last"] / a["ctr_first"]
        rows.append(_row("2b", "누르는 정도 (같은 소재 피로)",
                         f"한 사람이 적어도 {a['frequency_min']:.1f}번 봤고, 뒤 절반에 누르는 사람이 {drop:.0%} 줄었어요", "blocked", "meta.ad.media"))
        proposals["2b"] = {"field_id": "meta.ad.media", "new": "새 소재로 바꾼 세트를 하나 더 만들어 보세요", "short": "+ 새 소재 1개",
                           "what": "새 소재", "reason": "같은 사람이 같은 광고를 여러 번 봐서 누르는 사람이 줄었어요.", "level": "유력", "grade": "A"}
    else:
        rows.append(_row("2b", "누르는 정도 (같은 소재 피로)", "같은 사람에게 너무 자주 보이지 않았어요", "ok"))

    # 3 누른 뒤 페이지에 들어오는 정도
    vr = tot["landing_page_views"] / tot["link_clicks"] if tot["link_clicks"] else None
    if vr is not None and tot["link_clicks"] >= 10 and vr < cfg["visit_rate_min"]:
        rows.append(_row("3", "페이지 도착", f"누른 100명 중 {vr * 100:.0f}명만 페이지에 들어왔어요", "blocked", "meta.ad.website_url"))
        proposals["3"] = {"field_id": "meta.ad.website_url", "new": "페이지 속도·주소 점검, Audience Network 빼기", "short": "주소·속도 점검", "what": "주소·속도를 고친 페이지",
                          "reason": "누르고도 페이지에 못 들어온 사람이 많아요.", "level": "유력", "grade": "A"}
    else:
        rows.append(_row("3", "페이지 도착", f"누른 100명 중 {vr * 100:.0f}명이 들어왔어요 → 괜찮아요" if vr is not None else "도착 자료가 없어요",
                         "ok" if vr is not None else "skip"))

    # 4 들어온 뒤 행동 (알림 신청 등, 파일에 있을 때만)
    acts = [a.get("actions") for a in arms]
    act_label = summary.get("action_label") or "행동"
    if acts and all(x is not None for x in acts):
        n = sum(acts)
        counts = " · ".join(f"{'AB'[i] if len(arms) > 1 else ''} {int(x)}건".strip() for i, x in enumerate(acts))
        if n < _loop()["alerts"]["min_actions"]:
            rows.append(_row("4", "행동", f"{act_label} {counts} → 아직 몰라요", "skip"))
        else:
            rows.append(_row("4", "행동", f"{act_label} {counts}", "ok"))
    else:
        rows.append(_row("4", "행동", "구매·알림 신청 같은 행동 숫자가 파일에 없어요 → 아직 몰라요", "skip"))

    # 5 노출 위치 집중 → 그 자리에 맞는 소재 (돌려 본 적 없는 선택지라 '테스트 제안')
    places = summary.get("placements") or []
    top = max(places, key=lambda p: p["share"]) if places else None
    if top and top["share"] >= cfg["placement_share"]:
        vertical = any(w in top["label"] for w in ("릴스", "스토리"))
        spot = top["label"].replace("인스타그램", "인스타").replace("페이스북", "페북")
        has_v = _has_vertical(settings)
        if vertical:
            new, short = "세로(9:16) 소재를 넣은 세트를 하나 더 만들어 보세요", "+ 세로(9:16) 1개"
            what = "세로 소재"
            why = (f"돈의 {top['share']:.0%}가 {spot}(세로 화면)에서 나갔는데, 세로 소재가 없었어요." if has_v is False
                   else f"돈의 {top['share']:.0%}가 {spot}(세로 화면)에서 나갔어요. 그 자리에 꽉 차는 세로 소재로 비교해 봐요.")
        else:
            new, short = "피드용 정사각(1:1)·세로(4:5) 소재를 넣은 세트를 하나 더 만들어 보세요", "+ 피드용 소재 1개"
            what = "피드용 소재"
            why = f"돈의 {top['share']:.0%}가 {spot}에서 나갔어요. 그 자리에 맞는 모양의 소재로 비교해 봐요."
        rows.append(_row("5", "(전 단계)", f"{spot}에 돈의 {top['share']:.0%}", "found", "meta.ad.media"))
        proposals["5"] = {"field_id": "meta.ad.media", "new": new, "short": short, "what": what,
                          "reason": why, "level": "유력", "grade": "A",
                          "meta_says": "메타 Opportunity Score도 릴스에는 9:16 소재를 권해요." if vertical else None}
    else:
        rows.append(_row("5", "(전 단계)", "한 자리에 돈이 몰리지 않았어요", "ok"))

    # 6 학습 단계
    per_week = (tot["link_clicks"] / max(1, len(arms))) * 7 / max(1, days)
    learning = per_week < cfg["learning_events"]
    rows.append(_row("6", "(구조)", f"세트당 일주일에 클릭 약 {per_week:.0f}번 < {cfg['learning_events']}번 → 메타가 배우기엔 적어요" if learning else "메타가 배우기에 충분해요",
                     "watch" if learning else "ok", "meta.adset.performance_goal" if learning else None))

    # 막힌 곳도, 돈이 몰린 자리도 없으면: 이긴 세팅은 그대로 두고 문구 하나만 바꿔 비교 (v4.2: 결론은 언제나 테스트 제안 1개)
    if not any(r["status"] == "blocked" for r in rows) and "5" not in proposals:
        proposals["-"] = {"field_id": "meta.creative.copy", "new": "기본 문구를 바꾼 세트를 하나 더 만들어 보세요", "short": "+ 새 문구 1개",
                          "what": "새 문구", "reason": "크게 막힌 곳이 없어요. 지금 세팅은 그대로 두고 문구 하나만 바꿔 비교해 봐요.",
                          "level": "보류", "grade": "D"}
    pick = next((r["row"] for r in rows if r["status"] == "blocked"), None) or ("5" if "5" in proposals else "-" if "-" in proposals else None)
    change = None
    if pick:
        p = proposals[pick]
        label = PATH[p["field_id"]].split(" › ")[-1]
        # 써 본 금액 안에서 천 원 단위로 내림 (올리면 '써 본 적 없는 금액'이 돼요)
        per_set = max(5000, int(tot["spend"] / max(1, len(arms)) // 1000 * 1000)) if arms else 5000
        what = p.get("what", f"{label} 변경")
        change = {"row": pick, "field_id": p["field_id"], "path": PATH[p["field_id"]], "label": label,
                  "now": settings.get(p["field_id"]), "new": p["new"], "new_short": p["short"], "reason": p["reason"],
                  # v4.2: 결론은 돌려 본 적 없는 선택지 → 판정 배지 대신 '테스트 제안' (효과는 아직 몰라요)
                  "tag": "테스트 제안", "tested": False, "per_set": per_set, "what": what,
                  "test": f"지금 세트와 {won(per_set)}씩 같이 돌려서 직접 비교해요.",
                  "unknown": f"{josa(what)} 손님을 더 데려올지는 아직 몰라요. 돌려 봐야 알 수 있어요.",
                  "certainty": _certainty("보류", "돌려 본 적 없는 값이라 이번 테스트로 확인해요"),
                  # 근거 탭·개발 문서용: 진단 규칙 자체의 신뢰도 (확실/유력/보류 그대로)
                  "rule": {"row": pick, "level": p["level"], "why": "실측 + 진단 규칙" + (" + 메타 권장" if p.get("meta_says") else "")},
                  "grade": p["grade"], "meta_says": p.get("meta_says"), "checklist": _checklist(alerts, label)}

    if verdict and verdict["badge"]["level"] != "채택":
        mb = (verdict.get("min_budget") or {}).get("per_group")
        ss = next((a for a in alerts if a["kind"] == "small_sample"), None)
        why = (f"{act_label}이 {int(ss['actions'])}건뿐이라 아직 몰라요" if ss and ss.get("actions") is not None
               else f"클릭이 {_loop()['alerts']['min_clicks']}번이 안 모여서 아직 몰라요" if ss
               else f"지금은 '{verdict['badge']['word']}' 단계라 더 모아야 확실해요")
        watch.insert(0, {"field_id": "meta.adset.daily_budget", "path": PATH["meta.adset.daily_budget"], "title": "기간 · 예산",
                         "text": why, "need_per_set": mb})

    dont = ["여러 칸 한 번에 변경 — 무엇 덕분인지 모르게 돼요.",
            "평균만 보고 노출 위치·연령 끄기 — 메타는 '다음 손님 1명에 드는 돈'을 보고 돈을 나눠요. 끄고 싶으면 다음 5,000원 테스트로 확인해요."]
    if learning:
        dont.append("자주 고치기 — 큰 수정은 메타가 처음부터 다시 배우게 해요.")

    return {"rows": rows, "change": change, "keep": keep, "watch": watch, "dont": dont, "tested_field": field,
            "settings": setting_rows(settings, change, keep, watch)}


def _spec_id(field_id: str) -> Optional[str]:
    """확장의 칸 id → 사양 id ('meta.creative.copy.text' → 'meta.creative.copy')."""
    known = all_fields()
    while field_id and field_id not in known:
        field_id = field_id.rsplit(".", 1)[0] if "." in field_id else ""
    return field_id or None


def setting_rows(settings: Dict, change: Optional[Dict], keep: List[Dict], watch: List[Dict]) -> List[Dict]:
    """AN-03 내 세팅 카드: 받은 세팅값 전부를 광고 관리자 순서로, 칸마다 테스트·다시 보기·그대로 + 근거 한 줄 (사장님 말)."""
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
            kind, note = TEST, change["reason"]
        elif sid in keep_by:
            kind, note = SAME, keep_by[sid]["reason"]
        elif sid in watch_by:
            kind, note = RECHECK, watch_by[sid]["text"]
        else:
            kind, note = SAME, "—"
        out.append({"field_id": fid, "path": path, "value": str(value), "kind": kind, "note": note,
                    "_order": order.get(sid or "", 999)})
    out.sort(key=lambda x: x.pop("_order"))
    return out
