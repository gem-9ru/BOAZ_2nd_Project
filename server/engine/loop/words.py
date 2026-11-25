"""사장님 화면 표현 (설계서 v4.2 AN-TXT): 금액은 '원', 판정은 3단어, 비율은 사람 수로.

개발 문서·근거 탭은 확실 / 유력 / 보류(코드 값 '채택·유력·보류')를 그대로 쓰고,
사장님이 보는 글은 여기 함수로만 바꾼다.
"""
from typing import Optional

ADOPT, LIKELY = 0.9, 0.7


def won(x: Optional[float]) -> str:
    """6,342원 · 10만 원 ('₩' 대신 '원'). 만 원 단위로 딱 떨어지면 '10만 원'."""
    if x is None:
        return "?"
    n = int(round(x))
    if n >= 10_000 and n % 10_000 == 0:
        return f"{n // 10_000:,}만 원"
    return f"{n:,}원"


def word(level: str, better: str = "B") -> str:
    """개발 판정(채택·유력·보류) → 사장님 판정 3단어."""
    return {"채택": "확실해요", "유력": f"{better} 쪽이에요", "보류": "아직 몰라요"}[level]


def word_of(p: float, better: str = "B") -> str:
    """나은 쪽 확률 p(0.5 이상)를 3단어로: 90% 이상 / 70~90% / 70% 미만."""
    return "확실해요" if p >= ADOPT else f"{better} 쪽이에요" if p >= LIKELY else "아직 몰라요"


def per_people(rate: Optional[float], base: int = 1000) -> str:
    """1.73% → '약 17명' (base명 중). 100명 기준으로 차이가 안 보이면 1,000명 기준을 쓴다."""
    if rate is None:
        return "?"
    n = rate * base
    return f"약 {n:.0f}명" if n >= 1 else f"약 {n:.1f}명"


def arm_short(name: str, index: int) -> str:
    """세트 이름 → 'A(자동)' · 'B(수동)'. 노출 위치를 비교한 이름이 아니면 글자만."""
    letter = "AB"[index] if index < 2 else str(index + 1)
    if "자동" in name:
        return f"{letter}(자동)"
    if any(w in name for w in ("수동", "피드만", "AN제외", "AN 제외", "릴스만")):
        return f"{letter}(수동)"
    return letter


def set_budget(per_set: Optional[float], days: Optional[int] = None) -> str:
    """예산은 총예산인지 하루 예산인지 분명히: '세트당 총 5,000원 (4일)'."""
    s = f"세트당 총 {won(per_set)}"
    return f"{s} ({days}일)" if days else s
