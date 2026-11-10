"""화면(app/main.py)을 실제로 한 번 돌려 보는 테스트 (Streamlit AppTest, 네이버·AI 키 없이 저장된 캐시만).

계산은 엔진 테스트가 지키고, 여기서는 '화면이 멈추지 않고 엔진 숫자를 그대로 보여 주는지'만 본다.
문구 전체를 고정하지 않음 (세팅 챗봇 등 화면 작업이 이어지므로 핵심 숫자만).
"""
import logging
import os
from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

BASE = {"q_category": "식품", "q_stores": ["스마트스토어"], "q_repurchase": "매달(정기)", "q_baseline": None}
EXAMPLES = {"coffee": dict(BASE, q_price=20_000, q_profit=7_000, q_budget=300_000, q_keyword="원두커피"),
            "protein": dict(BASE, q_price=79_000, q_profit=39_500, q_budget=500_000, q_keyword="프로틴쉐이크")}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    for k in list(os.environ):
        if k.startswith(("NAVER", "ANTHROPIC")):
            monkeypatch.delenv(k)
    logging.getLogger("streamlit").setLevel(logging.ERROR)


APP = str(Path(__file__).resolve().parents[1] / "app" / "main.py")


def _run(example: str, step: int = 1, **extra) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=90)
    for k, v in {**EXAMPLES[example], **extra}.items():
        at.session_state[k] = v
    at.session_state["coach_mode"], at.session_state["coach_step"], at.session_state["coach_seen"] = "example", step, 3
    at.run()
    assert not at.exception, at.exception
    return at


def _text(at: AppTest) -> str:
    return "\n".join([m.value for m in at.markdown] + [m.value for m in at.caption])


def _metric(at: AppTest, label: str) -> str:
    return next(m.value for m in at.metric if m.label == label)


@pytest.mark.parametrize("example, wins, cpc, pick", [("coffee", 3, "1,503원", "none"), ("protein", 84, "1,470원", "recommended")])
def test_answer_step_shows_engine_numbers(example, wins, cpc, pick):
    at = _run(example)
    assert f"aria-label='100번 중 {wins}번 남음'" in _text(at)
    assert _metric(at, "클릭 1번 비용 (평균)") == cpc
    assert at.session_state["q_budget_pick"] == pick          # 기본 선택: 100번 중 50번 미만이면 광고 안 함


def test_chosen_budget_resplits_on_screen():
    """B1: 사장님이 '작게 시작'을 고르면 배분·클릭 비용이 그 예산 기준."""
    at = _run("protein", q_budget_pick="small", _budget_touched=True)
    assert at.session_state["q_budget_pick"] == "small"
    assert _metric(at, "클릭 1번 비용 (평균)") != "1,470원"
    assert "시험 예산 39.5만 원" in _text(at)


def test_every_coach_step_opens():
    """v1.0: 단계 5개 (① 세팅 = 내 가게·답 보기·광고 세팅, ② 실행 준비, ③ 한 달 뒤) 모두 멈추지 않고 열림."""
    for step in range(5):
        at = _run("protein", step=step, coach_started="2026-10-01", coach_seen=4)
        assert at.session_state["coach_step"] == step


def test_result_before_start_shows_next_action():
    """광고를 시작하기 전에 ③을 누르면 빈 화면: 실행 준비로 가는 버튼 + 이미 돌린 사람의 시작일 칸."""
    at = _run("protein", step=4)
    assert any(b.label == "② 실행 준비로" for b in at.button)
    assert len(at.date_input) == 1


def test_first_screen_has_two_ways_in_and_report_only_skips_to_result():
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    labels = [b.label for b in at.button]
    assert "처음부터 시작" in labels and "리포트만 올리기" in labels
    # '리포트만 올리기'를 누른 뒤 상태 (가게 숫자 3개 입력): 내 가게 다음 버튼이 바로 결과 올리기로
    # (내 가게 화면의 pills는 AppTest에서 클릭 뒤 다시 돌릴 수 없어, 버튼 이름과 도착 화면을 따로 확인)
    at = _run("protein", step=0, coach_seen=0, report_only=True, q_idx=4)
    assert any(b.label.startswith("다음: 광고 결과 올리기") for b in at.button)
    at = _run("protein", step=4, coach_seen=0, report_only=True)
    assert any(b.label == "이 날짜로 결과 보기" for b in at.button)
    assert not any(b.label == "② 실행 준비로" for b in at.button)      # 리포트만 올리는 사람에게는 실행 안내를 띄우지 않음


def test_one_question_at_a_time_and_setup_phases():
    """v1.1 (시안 C): ① 세팅 질문 5개가 한 화면에 하나씩 열리고, 지난 답은 칩 버튼으로 보임. 광고 세팅은 예산 고르기 → 세팅 단계."""
    for qi in range(5):
        at = _run("protein", step=0, q_idx=qi)
        labels = [b.label for b in at.button]
        assert ("다음 →" in labels) == (qi < 4) and ("← 이전" in labels) == (qi > 0)
        if qi == 4:
            assert "맞아요, 계산해 주세요 →" in labels
    at = _run("protein", step=1)
    assert any(b.label.startswith("월 50.0만") for b in at.button)          # 결과 화면에도 지난 답 칩
    at = _run("protein", step=2)
    assert any(b.label == "이 예산으로 세팅 시작 →" for b in at.button)
    at = _run("protein", step=2, q_setup_phase=1)
    assert any(b.label.startswith("세팅 다 했어요") for b in at.button) and any(b.label == "예산 다시 고르기" for b in at.button)
