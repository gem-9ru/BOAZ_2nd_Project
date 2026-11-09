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
    for step in (0, 2, 3):
        _run("protein", step=step, coach_started="2026-10-01")
