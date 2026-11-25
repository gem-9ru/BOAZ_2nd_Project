"""5 다음 세팅: 판정과 진단 규칙으로 바꿀 칸 1개 + 3줄 요약 (희수 7장, 진단 규칙 rules.yaml).

한 사이클에 바꾸는 것은 하나. 결과는 챗봇(확장 프로그램)이 광고 관리자에서 그 칸을 짚는 데 쓴다.
"""
from typing import Dict, Optional

from .words import won, word

COPY = {"field_id": "meta.creative.copy", "label": "기본 문구 · 제목", "new": "새 문구로 바꿔 비교", "note": "이긴 세팅은 그대로 두고 소재 하나만 바꿔요"}


def run(verdict: Optional[Dict], diag: Dict, matrix_change: Optional[Dict] = None) -> Dict:
    out = _by_verdict(verdict, diag)
    if matrix_change:   # v4: 결론은 진단 매트릭스의 칸 1개 (판정은 그 칸의 확실도·'지켜보기'로)
        c = matrix_change
        out["change"] = dict(c, note=c["reason"])
        out["summary"][2] = f"다음에 테스트할 것: {c['path']} → {c.get('new_short') or c['new']}"
    return out


def _by_verdict(verdict: Optional[Dict], diag: Dict) -> Dict:
    rule_change = (diag.get("changes") or [None])[0]
    if verdict is None:   # 세트가 하나뿐이면 비교 대신 진단 규칙으로
        change = rule_change or {"field_id": "meta.adset.end_date", "label": "종료 날짜", "new": "7일 더 연장", "note": "숫자가 더 모이면 판단해요"}
        return {"action": "바꿔 보기", "change": change, "summary": [
            f"이번에 알게 된 것: {diag['finding']['title']}",
            "아직 모르는 것: 비교할 세트가 하나뿐이라 무엇이 더 나은지는 몰라요",
            f"다음에 바꿀 것: {change['label']} → {change['new']}"]}

    badge, mb = verdict["badge"], verdict.get("min_budget") or {}
    win = verdict["b"] if badge["better"] == "B" else verdict["a"]
    pct = round(badge["prob"] * 100)
    if badge["level"] == "채택":
        change = rule_change or COPY
        return {"action": "고정하고 새 변수", "change": change, "summary": [
            f"이번에 알게 된 것: {win}가 같은 돈으로 손님을 더 데려왔어요 (나을 확률 {pct}% · 확실해요)",
            "아직 모르는 것: 다른 칸을 바꾸면 더 나아질지",
            f"다음에 바꿀 것: {win} 세팅은 그대로, {change['label']}만 바꿔 보기"]}
    if badge["level"] == "유력":
        per = mb.get("per_group")
        change = {"field_id": "meta.adset.end_date", "label": "종료 날짜",
                  "new": f"세트당 총 {won(per)}이 쓰일 때까지 더 돌리기" if per else "기간을 늘려 더 돌리기",
                  "note": "확실히 고르려면 이만큼 더 필요해요"}
        return {"action": "한 번 더", "change": change, "summary": [
            f"이번에 알게 된 것: {win}가 나을 확률 {pct}% ({word('유력', badge['better'])})",
            "아직 모르는 것: 단정하기엔 도착 수가 적어요",
            f"다음에 바꿀 것: 같은 세팅으로 세트당 총 {won(per)}까지 더 돌려 확실히 고르기"]}
    change = rule_change or COPY
    return {"action": "다른 변수", "change": change, "summary": [
        f"이번에 알게 된 것: 두 세팅의 차이는 아직 몰라요 ({win}가 나을 확률 {pct}%)",
        "아직 모르는 것: 이 변수가 결과를 바꾸는지",
        f"다음에 바꿀 것: {change['label']} → {change['new']}"]}
