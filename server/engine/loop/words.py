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
    n = int(x + 0.5)   # 0.5는 올림 (분석 페이지 화면의 Math.round와 같게, 감사 19)
    if n >= 10_000 and n % 10_000 == 0:
        return f"{n // 10_000:,}만 원"
    return f"{n:,}원"


def word(level: str, better: str = "B") -> str:
    """개발 판정(채택·유력·보류) → 사장님 판정 3단어."""
    return {"채택": "확실해요", "유력": f"{better} 쪽이에요", "보류": "아직 몰라요"}[level]


def word_of(p: float, better: str = "B") -> str:
    """나은 쪽 확률 p(0.5 이상)를 3단어로: 90% 이상 / 70~90% / 70% 미만."""
    return "확실해요" if p >= ADOPT else f"{better} 쪽이에요" if p >= LIKELY else "아직 몰라요"


def per_people(rate: Optional[float], base: int = 1000, unit: str = "명") -> str:
    """1.73% → '약 17명' (base명 중). 100명 기준으로 차이가 안 보이면 1,000명 기준을 쓴다.
    노출 대비 클릭처럼 사람 수가 아닌 비율은 unit='번'."""
    if rate is None:
        return "?"
    n = rate * base
    return f"약 {int(n + 0.5)}{unit}" if n >= 1 else f"약 {n:.1f}{unit}"


def josa(word: str, pair: str = "이가") -> str:
    """받침에 맞는 조사: josa('세로 소재', '이가') → '세로 소재가', josa('새 문구', '이가') → '새 문구가'."""
    last = word.rstrip()[-1:] if word else ""
    has = "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28 != 0
    return word + (pair[0] if has else pair[1])


def arm_short(name: str, index: int) -> str:
    """세트 이름 → 'A(자동)' · 'B(수동)'. 노출 위치를 비교한 이름이 아니면 글자만."""
    letter = "AB"[index] if index < 2 else str(index + 1)
    if "자동" in name:
        return f"{letter}(자동)"
    if any(w in name for w in ("수동", "피드만", "AN제외", "AN 제외", "릴스만")):
        return f"{letter}(수동)"
    return letter


_PLATFORM_KO = {"Facebook": "페이스북", "Instagram": "인스타그램", "Messenger": "메신저"}
_POSITION_KO = {
    "feed": "피드", "instagram_reels": "릴스", "facebook_reels": "릴스", "instagram_stories": "스토리",
    "facebook_stories": "스토리", "instream_video": "인스트림 동영상", "instagram_explore": "탐색 탭",
    "instagram_explore_grid_home": "탐색 홈", "marketplace": "마켓플레이스", "right_hand_column": "오른쪽 칼럼",
    "search": "검색 결과", "video_feeds": "동영상 피드", "facebook_profile_feed": "프로필 피드",
    "instagram_profile_feed": "프로필 피드", "an_classic": "네이티브·배너·전면", "rewarded_video": "보상형 동영상",
    "messenger_inbox": "받은 메시지함", "messenger_stories": "스토리",
    "네이티브, 배너 및 전면 광고": "네이티브·배너·전면",   # 한국어 내보내기의 Audience Network 자리
}
_PLATFORMS = ("Audience Network", "Facebook", "Instagram", "Messenger", "Threads")


def placement_label(name: str) -> str:
    """'Instagram instagram_reels' → '인스타그램 릴스'. 모르는 이름은 그대로 둔다 (보고서 표시용)."""
    name = str(name)
    plat = next((p for p in _PLATFORMS if name.startswith(p + " ")), None)
    if plat:
        rest = name[len(plat) + 1:]
        if rest.lower().startswith(plat.lower() + " "):   # 'Instagram Instagram 릴스' 같은 겹침
            rest = rest[len(plat) + 1:]
        return f"{_PLATFORM_KO.get(plat, plat)} {_POSITION_KO.get(rest, rest)}"
    head, _, pos = name.rpartition(" ")
    if not head:
        return name
    return f"{_PLATFORM_KO.get(head, head)} {_POSITION_KO.get(pos, pos)}"
