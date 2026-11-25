"""광고 어시스턴트: 분석 페이지 오른쪽에 늘 떠 있는 설명 창구 (v4 5장 공통 레이아웃 · 8장, 말 규칙은 v4.2 AN-TXT).

- 단계에 들어오면 첫 말풍선 + 추천 질문 2개 → 코드로 만든다 (LLM 없이도 항상 나옴).
- 사장님이 물으면 그 단계 결과 JSON만 LLM에 넘겨 쉬운 말로 풀게 한다. 숫자·결론은 만들지 않는다.
- 같은 알림은 처음 나오는 화면에서만 말풍선으로 설명한다 (알림의 screen 값).
"""
import json
from typing import Dict, List, Optional

from ..copywriter import MODEL
from .words import arm_short, won

KEYS = {
    "AN-01": ("matrix", "next", "check"),
    "AN-02": ("funnel", "intervals", "matrix_rows"),
    "AN-03": ("matrix",),
    "AN-04": ("verdict", "replay", "placements"),
    "AN-05": ("summary", "backtest"),
    "AN-06": ("next", "matrix"),
    "EX-03": ("next", "matrix"),   # 확장 프로그램 챗봇이 변경안을 이어받음
}
# 말 규칙 (설계서 v4.2 AN-TXT): 분석 페이지 어시스턴트와 확장 프로그램 챗봇(EX-03)이 같은 규칙을 쓴다.
SPEECH_RULES = (
    "말 규칙 5가지:\n"
    "① 판정은 '확실해요 / ○ 쪽이에요 / 아직 몰라요' 세 가지로만 말해 (90% 이상 / 70~90% / 70% 미만·표본 부족). "
    "'유의미하다', '우세하다', '유력', '보류' 같은 말은 쓰지 마.\n"
    "② 숫자는 아래 결과 JSON에 있는 것만 써. 예측은 항상 범위나 확률과 함께 말해 (예: '보통 13명 (적게 7명 ~ 많이 20명)', 'B가 나을 확률 79%'). "
    "JSON에 없는 숫자는 만들지 말고 '이 화면 자료에는 없어요'라고 말해.\n"
    "③ 광고 전후를 비교해서 '광고 덕분에 늘었어요'라고 단정하지 마. 효과는 같은 기간에 동시에 돌린 A/B 비교로만 말해.\n"
    "④ 돌려 본 적 없는 선택지(예: 세로 영상)는 결과를 예상하지 말고 '5,000원씩 두 세트로 돌려서 직접 비교해 보세요'라고 안내해.\n"
    "⑤ 용어는 사장님 말을 먼저, 영어 약어는 괄호로 (예: '광고 1,000번 보여주는 데 드는 돈 (CPM)', '클릭 1번에 드는 돈 (CPC)', "
    "'본 사람 중 누른 비율 (CTR)'). 금액은 '6,342원'처럼 '원'으로 쓰고 '₩'는 쓰지 마. 너 자신은 '광고 어시스턴트'라고 불러."
)
SYSTEM = ("너는 광고를 처음 하는 1인 가게 사장님을 돕는 '광고 어시스턴트'야. 쉬운 한국어 존댓말로 3문장 이내로 답해.\n"
          "판단(바꿀 칸·확률·알림)은 이미 코드가 정했어. 너는 그걸 풀어 설명만 한다. 결론을 바꾸거나 새 제안을 만들지 마.\n"
          "숫자는 아래 JSON에 있는 숫자만 써. 경고(알림)가 있으면 결론보다 먼저 말해.\n"
          + SPEECH_RULES)


def context(result: Dict, step: str) -> Dict:
    out = {}
    for k in KEYS.get(step, ()):
        if k == "matrix_rows":
            out["matrix_rows"] = (result.get("matrix") or {}).get("rows", [])
        elif k in result:
            out[k] = result[k]
    out["alerts"] = [a for a in result.get("alerts", []) if a["screen"] == step]
    return out


def _same_money(result: Dict) -> Optional[Dict]:
    """같은 돈으로 온 손님 수 (AN-01 유지 카드 · AN-04): 두 세트 중 적게 쓴 돈 기준."""
    arms = (result.get("summary") or {}).get("arms") or []
    if len(arms) < 2:
        return None
    base = min(a["spend"] for a in arms[:2])
    return {"base": base, "counts": [round((a.get("visits_per_1000won") or 0) * base / 1000) for a in arms[:2]]}


def _forecast(result: Dict) -> Optional[Dict]:
    """AN-05 첫 말: 지금 세팅(나은 쪽)으로 세트당 예산을 쓰면 손님 수 범위 (80%)."""
    from . import simulate
    arms = (result.get("summary") or {}).get("arms") or []
    if not arms:
        return None
    badge = (result.get("verdict") or {}).get("badge") or {}
    i = 0 if badge.get("better") == "A" or len(arms) == 1 else 1
    budget = ((result.get("matrix") or {}).get("change") or {}).get("per_set") or 5000
    v = simulate.run(arms[i], budget, runs=20_000)["visits"]
    return {"arm": arm_short(arms[i]["name"], i).replace("(", " ").rstrip(")"), "budget": budget,
            "median": round(v["median"]), "lo": round(v["lo"]), "hi": round(v["hi"])}


def opening(result: Dict, step: str) -> Dict:
    """단계 첫 말풍선 (v4.2): 알림 말풍선이 먼저(alerts), 그다음 이 단계 요약(message)."""
    m = result.get("matrix") or {}
    c = m.get("change") or (result.get("next") or {}).get("change") or {}
    v = result.get("verdict") or {}
    badge = v.get("badge") or {}
    alerts = [a for a in result.get("alerts", []) if a["screen"] == step]
    label = c.get("label", "")
    what = (c.get("unknown") or "").split("가 손님을")[0] or f"{label} 칸"
    msg: str
    sug: List[str]
    if step == "AN-01":
        msg = (f"이번엔 {what} 하나만 바꿔서 테스트해 보세요. 나머지는 그대로 두세요. "
               f"({c.get('path', label)})")
        sug = ["왜 이 칸이에요?", "테스트는 어떻게 해요?"]
    elif step == "AN-02":
        blocked = next((r for r in m.get("rows", []) if r["status"] == "blocked"), None)
        row1 = next((r for r in m.get("rows", []) if r["row"] == "1" and r.get("detail")), None)
        if blocked:
            msg = f"'{blocked['stage']}' 단계에서 처음 막혔어요. {blocked['signal']}."
        elif row1:
            msg = (f"광고가 보이는 값에서만 차이가 났고, 그 아래 단계는 괜찮아요. {row1['signal']}."
                   + (" → 노출 위치는 지금처럼 직접 고르는(수동) 게 좋아요." if "수동" in row1["signal"] else ""))
        else:
            msg = "보여지고 → 눌리고 → 페이지에 오기까지 크게 막힌 곳은 없었어요."
        sug = ["CPM이 뭐예요?", "④는 왜 회색이에요?"]
    elif step == "AN-03":
        msg = f"이번에 테스트할 칸은 {label} 하나예요. 나머지는 그대로 두세요."
        sug = ["다시 보기는 뭐예요?", "메타 추천을 따를까요?"]
    elif step == "AN-04":
        if badge:
            same = _same_money(result)
            who = "B" if badge.get("better") == "B" else "A"
            msg = (f"같은 돈으로 {who}가 손님을 더 데려왔어요"
                   + (f" (A {same['counts'][0]}명 · B {same['counts'][1]}명)" if same else "")
                   + f". {who}가 나을 확률 {round(badge.get('prob', 0) * 100)}% · '{badge.get('word', '')}'"
                   + (" 단계라 같은 조건으로 한 번 더 돌리면 확실해질 수 있어요." if badge.get("word") != "확실해요" else "예요."))
            cpm = next((x for x in v.get("metrics", []) if x["key"] == "cpm"), None)
            if cpm and cpm.get("word") == "확실해요":
                msg += f" 광고비 자체는 {cpm['better']}가 확실히 쌌어요. 범위가 겹치지 않아요."
        else:
            msg = "비교할 세트가 하나뿐이라 값 비교는 없어요."
        sug = ["70%·90% 선이 뭐예요?", "노출 위치별로 보여줘요"]
    elif step == "AN-05":
        f = _forecast(result)
        msg = (f"지금 세팅({f['arm']})으로 {won(f['budget'])}을 쓰면 보통 {f['median']}명 (적게 {f['lo']}명 ~ 많이 {f['hi']}명) 와요. "
               if f else "예산을 움직이면 예상 손님 수 범위가 바뀌어요. ")
        if c.get("tested") is False:
            msg += f"{what} 효과는 이 숫자에 없어요. {won(c.get('per_set') or 5000)}씩 두 세트로 돌려 직접 비교해 보세요."
        sug = ["왜 범위가 넓어요?", "얼마 더 써야 확실해요?"]
    elif step == "EX-03":
        msg = (f"{c.get('reason', '')} 지금 세트는 그대로 두고, 복제한 세트에서 '{c.get('path', label)}' 칸만 바꾸세요. "
               "두 세트를 같은 날 같이 돌려야 비교할 수 있어요.")
        sug = ["세로 소재는 어떻게 만들어요?" if "세로" in c.get("new", "") else "이 칸을 왜 바꿔요?", "바꾸고 나서 언제 다시 봐요?"]
    else:
        n = len(c.get("checklist") or [])
        msg = ("[확장 프로그램으로 보내기]를 누르면 확장 프로그램이 광고 관리자에서 그 칸을 바로 가리켜 드려요. "
               + (f"체크리스트 {n}개만 지키면 다음 결과로 {what} 효과를 잴 수 있어요." if n else ""))
        sug = ["지금 바로 준비해요?", "근거 더 보여줘요"]
    return {"step": step, "message": msg, "suggestions": sug, "alerts": alerts}


def _fallback(result: Dict, step: str, question: str) -> str:
    c = (result.get("matrix") or {}).get("change") or {}
    base = opening(result, step)["message"]
    if c.get("reason"):
        base += f" 이유: {c['reason']}"
    return base + " (지금은 설명 도우미에 연결하지 못해서 정해진 설명으로 답했어요.)"


def answer(result: Dict, step: str, question: str, client=None) -> Dict:
    question = (question or "").strip()[:300]
    if client is not None and question:
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=2000, system=SYSTEM,   # 생각 + 3문장
                messages=[{"role": "user", "content": json.dumps({"화면": step, "결과": context(result, step), "질문": question},
                                                                 ensure_ascii=False, default=str)}])
            text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "").strip()
            if text:
                return {"message": text, "source": "llm"}
        except Exception:  # noqa: BLE001 (키·네트워크 문제 → 정해진 설명)
            pass
    return {"message": _fallback(result, step, question), "source": "rules"}
