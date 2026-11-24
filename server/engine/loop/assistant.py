"""광고 어시스턴트: 분석 페이지 오른쪽에 늘 떠 있는 설명 창구 (v4 5장 공통 레이아웃 · 8장).

- 단계에 들어오면 첫 말풍선 + 추천 질문 2개 → 코드로 만든다 (LLM 없이도 항상 나옴).
- 사장님이 물으면 그 단계 결과 JSON만 LLM에 넘겨 쉬운 말로 풀게 한다. 숫자·결론은 만들지 않는다.
- 같은 알림은 처음 나오는 화면에서만 말풍선으로 설명한다 (알림의 screen 값).
"""
import json
from typing import Dict, List, Optional

from ..copywriter import MODEL

KEYS = {
    "AN-01": ("matrix", "next", "check"),
    "AN-02": ("funnel", "intervals", "matrix_rows"),
    "AN-03": ("matrix",),
    "AN-04": ("verdict", "replay", "placements"),
    "AN-05": ("summary", "backtest"),
    "AN-06": ("next", "matrix"),
    "EX-03": ("next", "matrix"),   # 확장 프로그램 챗봇이 변경안을 이어받음
}
SYSTEM = ("너는 광고를 처음 하는 1인 가게 사장님을 돕는 '광고 어시스턴트'야. 쉬운 한국어 존댓말로 3문장 이내로 답해.\n"
          "판단(바꿀 칸·확률·알림)은 이미 코드가 정했어. 너는 그걸 풀어 설명만 한다. 결론을 바꾸거나 새 제안을 만들지 마.\n"
          "숫자는 아래 JSON에 있는 숫자만 써. JSON에 없는 숫자는 만들지 말고 '이 화면 자료에는 없어요'라고 말해.\n"
          "전문 용어는 처음 쓸 때 괄호로 쉬운 말을 붙여.")


def _won(x) -> str:
    return f"₩{round(x):,}" if x is not None else "?"


def context(result: Dict, step: str) -> Dict:
    out = {}
    for k in KEYS.get(step, ()):
        if k == "matrix_rows":
            out["matrix_rows"] = (result.get("matrix") or {}).get("rows", [])
        elif k in result:
            out[k] = result[k]
    out["alerts"] = [a for a in result.get("alerts", []) if a["screen"] == step]
    return out


def opening(result: Dict, step: str) -> Dict:
    m = result.get("matrix") or {}
    c = m.get("change") or (result.get("next") or {}).get("change") or {}
    v = result.get("verdict") or {}
    badge = v.get("badge") or {}
    alerts = [a for a in result.get("alerts", []) if a["screen"] == step]
    msg: str
    sug: List[str]
    if step == "AN-01":
        msg = f"이번에 바꿀 칸은 '{c.get('path', c.get('label', ''))}' 하나예요. 바꿀 값: {c.get('new', '')}."
        sug = ["왜 이 칸이에요?", "나머지 칸은 그대로 둬도 돼요?"]
    elif step == "AN-02":
        blocked = next((r for r in m.get("rows", []) if r["status"] == "blocked"), None)
        msg = (f"'{blocked['stage']}' 단계에서 막혔어요. {blocked['signal']}." if blocked
               else "보여 주기 → 누르기 → 들어오기까지 크게 막힌 곳은 없었어요. 그래서 소재 모양을 손보는 쪽을 권해요.")
        sug = ["CPM이 뭐예요?", "도착률은 얼마면 괜찮아요?"]
    elif step == "AN-03":
        keep = m.get("keep") or []
        msg = ("지금 세팅에서 바꿀 칸은 하나, " + (f"그대로 둘 칸은 '{keep[0]['path']}'예요." if keep else "나머지는 그대로 두세요."))
        sug = ["메타 추천이랑 왜 달라요?", "유지할 칸을 바꾸면 어떻게 돼요?"]
    elif step == "AN-04":
        msg = (f"{badge.get('label', '')} 기준으로 {badge.get('better', '')}가 나을 확률은 {round(badge.get('prob', 0) * 100)}%예요 ({badge.get('level', '')})."
               if badge else "비교할 세트가 하나뿐이라 값 비교는 없어요.")
        sug = ["79%면 믿어도 돼요?", "노출 위치별 숫자는 왜 회색이에요?"]
    elif step == "AN-05":
        bt = result.get("backtest") or {}
        msg = ("예산을 움직이면 예상 방문 범위가 바뀌어요. "
               + ("앞 날짜로 마지막 날을 맞혀 봤더니 범위 안에 들어왔어요." if bt.get("ok") and all(a["visits"]["inside"] for a in bt["arms"]) else "써 본 적 없는 금액은 '가설'로 봐 주세요."))
        sug = ["범위가 왜 이렇게 넓어요?", "다음 테스트엔 얼마를 써요?"]
    elif step == "EX-03":
        keep = m.get("keep") or []
        msg = (f"광고 관리자에서 '{c.get('path', '')}' 칸만 짚어 드릴게요. 나머지 칸은 그대로 두세요"
               + (f" (특히 '{keep[0]['path']}'는 유지)." if keep else "."))
        sug = ["이 칸을 왜 바꿔요?", "바꾸고 나서 언제 다시 봐요?"]
    else:
        msg = f"바꿀 칸을 확장 프로그램으로 보내면 광고 관리자에서 '{c.get('path', '')}' 칸을 짚어 드려요."
        sug = ["보내면 자동으로 바뀌어요?", "체크리스트는 언제 확인해요?"]
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
