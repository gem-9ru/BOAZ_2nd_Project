"""플로팅 도움말 챗봇 (규칙 기반)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import helpbot as H  # noqa: E402
from src.engine.insights import won  # noqa: E402

CTX = {"profit": -25_830_000, "ltv": 43_000, "cac": 124_000, "ltv_cac": 0.35, "roas": 0.53, "payback": None,
       "cvr": 0.0141, "aov": 60_000, "margin": 0.35, "pmf": True, "verdict": "🔴 지금 조건이면 광고를 할수록 손해입니다",
       "top_option": ("퍼널 개선", 3_940_000, "ceiling", 3_940_000), "best_step": ("③ 장바구니", 3_940_000, "버튼을 위로"),
       "attribution": "모델보다 데이터 정제가 중요합니다."}


def ask(q, screen="결과·우선순위"):
    return H.answer(q, CTX, screen, won)


def test_every_screen_term_is_in_glossary_and_findable():
    for screen, (terms, _) in H.SCREEN_HELP.items():
        assert screen in H.SUGGESTIONS
        for t in terms:
            assert t in H.GLOSSARY
            assert t in H.find_terms(t)


def test_longest_alias_wins():
    assert H.find_terms("LTV/CAC가 뭐야?") == ["LTV/CAC"]
    assert H.find_terms("ltv랑 cac 차이") == ["LTV (고객 생애 가치)", "CAC (고객 획득 비용)"]
    assert H.find_terms("클릭당 비용이 뭐예요") == ["CPC (클릭당 비용)"]


def test_definition_and_personal_number():
    a = ask("ROAS가 뭐야?")
    assert "광고비 1원당 매출" in a and "0.53원" in a
    assert ask("내 LTV/CAC는 얼마야?").startswith("지금 계획의 LTV/CAC: **0.35배**")


def test_intents():
    assert "퍼널 개선" in ask("뭐부터 해야 해?") and "보류" in ask("뭐부터 해야 해?")
    assert "손해" in ask("왜 손해라고 나와?")
    assert "③ 장바구니" in ask("손님이 어디서 제일 많이 새?")
    assert "데이터 정제" in ask("어트리뷰션 결과 믿어도 돼?")
    assert "GA4 샘플 구매" in ask("이 숫자 어디서 나와?", "어트리뷰션")
    assert "네이버 검색광고 API" in ask("포화는 어디서 나온 숫자야?", "시작")   # 용어가 속한 화면의 출처


def test_every_suggestion_gets_a_real_answer():
    for screen, qs in H.SUGGESTIONS.items():
        for q in qs:
            assert "잘 모르겠어요" not in H.answer(q, CTX, screen, won), q
    assert "잘 모르겠어요" in ask("날씨 어때?")


def test_new_customer_is_not_leak():
    assert "③ 장바구니" not in ask("새 손님이 뭐야?")


def test_profit_sign_wording():
    assert "손해" in ask("1년 동안 얼마 남아?") and "-" not in ask("1년 동안 얼마 남아?")
