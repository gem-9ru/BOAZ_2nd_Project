"""P7 app 테스트: 페이지별 렌더링, 챗봇 세팅 대화(예시 소연베이크 경로), 올린 파일 읽기, 다음 달 이어 하기.

네트워크·API 키를 쓰지 않는다 (시장 조사는 저장본, 문구는 문장 틀, 도움말은 미리 쓴 답).
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from v2.app import data, state
from v2.engine import conversation, copywriter, ingest, intake, plan_io, specs

MAIN = str(Path(__file__).resolve().parents[1] / "app" / "main.py")
SETUP, RUN, DIAG = "setup.py", "run.py", "diagnose.py"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Claude 키가 있어도 쓰지 않는다 (도움말 LLM·문구 모두 키 없는 경로)."""
    monkeypatch.setattr(conversation, "_client", lambda: None)
    monkeypatch.setattr(copywriter, "_read_key", lambda: None)
    state.set_services(None)
    yield
    state.set_services(None)


def fresh() -> AppTest:
    at = AppTest.from_file(MAIN, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def into(at: AppTest, key: str, page: str) -> AppTest:
    """st.switch_page를 부르는 버튼을 누른다. AppTest는 쪽 이동을 기억하지 못해서 같은 쪽으로 다시 맞춰 준다."""
    at.button(key=key).click().run()
    at.switch_page(page)
    at.run()
    return at


def titles(at):
    return [t.value for t in at.title]


def texts(at) -> str:
    """화면의 글 전체 (설명·캡션·경고 포함)."""
    parts = []
    for coll in (at.markdown, at.caption, at.success, at.info, at.warning, at.error):
        parts += [str(e.value) for e in coll]
    return "\n".join(parts)


def chip(at: AppTest, label: str) -> AppTest:
    """대화 칩(버튼)을 글자로 찾아 누른다."""
    hits = [b for b in at.button if b.label == label]
    assert hits, "칩 없음: {} (있는 버튼: {})".format(label, [b.label for b in at.button])
    hits[0].click().run()
    assert not at.exception, at.exception
    return at


def say(at: AppTest, text: str) -> AppTest:
    at.chat_input[0].set_value(text).run()
    assert not at.exception, at.exception
    return at


def phase(at: AppTest) -> tuple:
    c = at.session_state["chat"]
    return c["phase"], c["step"]


def demo_to_budget(at: AppTest) -> AppTest:
    """예시 → 확인(맞아요) → 내 손님 카드 → 목표·기간 → 예산 카드 → 세팅 질문 시작."""
    into(at, "home_demo", SETUP)
    chip(at, "맞아요")
    say(at, ", ".join(state.DEMO_SEEDS))
    chip(at, "이대로 쓸게요")
    chip(at, "스토어 방문 늘리기")
    chip(at, "14일")
    chip(at, "이대로 할게요")
    return at


def demo_to_sheet(at: AppTest) -> AppTest:
    demo_to_budget(at)
    chip(at, "있어요")                                  # 페이스북 페이지
    say(at, "soyeonbake")                               # 인스타그램 계정
    chip(at, "남은 질문은 권장 답으로")
    return at


def test_home_renders():
    at = fresh()
    assert titles(at) == ["광고 코치"]
    assert any("예시로 해 보기" in b.label for b in at.button)
    assert "근거 등급" in texts(at)


def test_run_and_diag_are_locked_without_plan():
    at = fresh()
    at.switch_page(RUN).run()
    assert not at.exception and "아직 열 수 없어요" in texts(at)
    at.switch_page(DIAG).run()
    assert not at.exception and "아직 진단할 계획이 없어요" in texts(at)
    assert any(b.key == "diag_demo_plan" for b in at.button)


def test_diag_demo_plan_button_opens_the_page():
    at = fresh()
    at.switch_page(DIAG).run()
    at.button(key="diag_demo_plan").click().run()
    assert not at.exception, at.exception
    assert at.session_state["month_index"] == 1 and state.LAST_STEP == at.session_state["setup_step"]
    assert any("진단: 고쳐 볼 곳" in m.value for m in at.markdown)


# ── 챗봇 세팅 ────────────────────────────────────────────

def test_home_demo_opens_chat_at_confirm_card_with_filled_store_card():
    at = fresh()
    into(at, "home_demo", SETUP)
    assert titles(at) == ["① 세팅"] and len(at.chat_input) == 1
    assert phase(at) == ("confirm", "ok")
    assert at.session_state["is_demo"] and at.session_state["store"]["name"] == "소연베이크"
    body = texts(at)
    assert "이렇게 이해했어요" in body and "소연베이크" in body and "26,000원" in body
    assert {b.label for b in at.button} >= {"맞아요", "고칠래요"}


def test_own_store_start_asks_name_first_and_invalid_money_shows_inline_error():
    at = fresh()
    into(at, "home_mine", SETUP)
    assert phase(at) == ("store", "name") and "가게 이름이 뭐예요" in texts(at)
    say(at, "소연베이크")
    say(at, "수제 구움과자")
    assert phase(at) == ("store", "price")
    say(at, "얼마였더라")                                # 못 읽는 금액
    assert phase(at) == ("store", "price")              # 단계 그대로
    assert any("금액으로 읽지 못했어요" in e.value for e in at.error)
    say(at, "2만 6천원")
    assert phase(at) == ("store", "margin") and "26,000원으로 이해했어요" in texts(at)
    assert at.session_state["setup_step"] == 0


def test_budget_too_small_shows_inline_error_and_keeps_step():
    at = fresh()
    into(at, "home_mine", SETUP)
    for text in ("가게", "쿠키", "20000", "7000"):
        say(at, text)
    say(at, "500원")
    assert phase(at) == ("store", "budget") and any("광고비" in e.value for e in at.error)


def test_demo_chat_path_cards_help_source_and_skip_to_sheet():
    at = fresh()
    into(at, "home_demo", SETUP)
    chip(at, "맞아요")
    assert phase(at) == ("market", "seeds") and at.session_state["setup_step"] == 2
    assert any(b.label == "예시 단어로 찾기" for b in at.button)
    say(at, ", ".join(state.DEMO_SEEDS))
    assert phase(at) == ("market", "pick")
    assert any("찾는 사람은" in m.value for m in at.markdown)           # 손님 카드: 한 줄 요약
    assert at.session_state["chat"]["market"]["recommended"] and at.session_state["chat"]["market"]["negatives"]
    chip(at, "이대로 쓸게요")
    chip(at, "스토어 방문 늘리기")
    chip(at, "14일")
    assert phase(at) == ("budget", "ok")
    labels = [m.label for m in at.metric]
    assert "한 달 광고비" in labels and "네이버 하루 예산" in labels and "메타 하루 예산" in labels
    assert "근거 D" in texts(at) or "근거 C" in texts(at)
    chip(at, "이대로 할게요")
    assert phase(at)[0] == "ask" and at.session_state["setup_step"] == 4
    assert "세팅 보드" in texts(at)
    chip(at, "있어요")                                  # 페이스북 페이지 (사전 점검)
    say(at, "soyeonbake")                               # 인스타 계정은 글로 답
    assert at.session_state["chat"]["answers"]["meta.pre.ig_account"] == "soyeonbake"
    # 도움말 질문: 같은 질문을 다시 묻고, 미리 쓴 답에 출처(확인 표시 + 링크)가 붙는다
    step = phase(at)[1]
    n_before = len(at.session_state["chat"]["turns"])
    say(at, "특별 광고 카테고리가 뭐예요?")
    helps = [t for t in at.session_state["chat"]["turns"][n_before:] if t["kind"] == "help"]
    assert helps and helps[0]["data"]["sources"], helps
    assert phase(at)[1] == step                          # 답이 아니라 질문이었으니 단계 그대로
    shown = "\n".join(c.value for c in at.caption)
    assert "출처" in shown and "http" in shown and any(x in shown for x in ("✅", "△", "❓"))
    chip(at, "아니요")
    assert phase(at)[1] != step
    chip(at, "남은 질문은 권장 답으로")                    # 나머지는 권장 답
    assert not at.exception, at.exception
    assert at.session_state["setup_step"] == state.LAST_STEP and phase(at)[0] == "done"
    a = at.session_state["answers"]
    assert isinstance(a["meta.creative.copy"], dict) and isinstance(a["naver.ad.copy"], dict)
    assert len(a["naver.ad.copy"]["headline"]) <= 15
    assert at.session_state["budget_plan"]["naver_daily"] > 0 and at.session_state["budget_plan"]["meta_daily"] > 0
    assert a["meta.adset.end_date"] == "14일"
    # 세팅값 시트: 광고 관리자 칸 전부
    ctx = state.make_ctx(at.session_state["store"], at.session_state["media"], at.session_state["budget_plan"])
    assert len(intake.build_sheet(a, ctx)) == len(specs.all_fields()) == 62
    assert "준비가 끝났어요" in texts(at) and len(at.get("arrow_data_frame")) >= 1


def test_edit_past_answer_goes_back_and_returns_to_sheet():
    at = demo_to_sheet(fresh())
    assert phase(at)[0] == "done"
    at.button(key="edit_price").click().run()
    assert not at.exception, at.exception
    assert phase(at) == ("store", "price") and at.session_state["setup_step"] < state.LAST_STEP
    say(at, "30,000원")
    assert phase(at) == ("confirm", "ok")
    chip(at, "맞아요")
    assert phase(at)[0] == "done" and at.session_state["store"]["price"] == 30000


def test_streamed_llm_help_is_written_and_saved(monkeypatch):
    """kind=="llm" 답은 st.write_stream으로 흘리고, 끝나면 대화 기록에 글이 남는다."""
    from types import SimpleNamespace
    real = conversation.make_services(online=True)

    def help_(question, step_id, ctx):
        if "스트림" in question:
            return SimpleNamespace(kind="llm", text="", field_id=step_id, stream=iter(["안녕", "하세요"]),
                                   sources=[{"title": "공식 도움말", "url": "https://example.com/x", "check": "✅"}])
        return real.help(question, step_id, ctx)

    real.help = help_
    state.set_services(real)
    at = fresh()
    into(at, "home_demo", SETUP)
    say(at, "스트림 질문이에요?")
    helps = [t for t in at.session_state["chat"]["turns"] if t["kind"] == "help"]
    assert helps and helps[-1]["text"] == "안녕하세요" and helps[-1]["data"]["stream"] is False
    assert "AI가 도움말을 바탕으로" in texts(at) and "example.com" in texts(at)


def test_sheet_page_has_table_downloads_and_next_link():
    at = demo_to_sheet(fresh())
    assert titles(at) == ["① 세팅"] and "준비가 끝났어요" in texts(at)
    assert len(at.get("arrow_data_frame")) >= 1                    # data_editor 시트
    assert at.session_state["answers"]["meta.pre.ig_account"] == "soyeonbake"
    names = [e.proto.label for e in at.get("download_button")]
    assert any("계획 파일" in n for n in names) and any("CSV" in n for n in names) and any("엑셀" in n for n in names)


def test_run_page_after_setup():
    at = demo_to_sheet(fresh())
    at.switch_page(RUN).run()
    assert not at.exception, at.exception
    assert titles(at) == ["② 실행"]
    assert len(at.checkbox) >= 3
    at.checkbox[0].check().run()
    assert at.session_state["run_checks"]["baseline"] is True
    assert "결과 파일을 올려" in texts(at)


def test_full_demo_flow_c2_to_next_month():
    at = demo_to_sheet(fresh())
    at.switch_page(DIAG).run()
    assert not at.exception, at.exception
    assert at.selectbox(key="diag_case").value == "C2"
    body = texts(at)
    assert "다른 앱" in body or "Audience Network" in body        # placement_quality 진단 문장
    labels = [m.label for m in at.metric]
    assert labels[0].startswith("손님 1명에게 쓸 수 있는 한도")        # 첫 숫자 = 한도
    assert "근거: 한도 A" in texts(at)
    assert any("효과 확인" in m.value for m in at.markdown)
    assert "시즌을 뺀 진짜 변화" in "".join(m.label for m in at.metric)
    into(at, "next_month", SETUP)
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["month_index"] == 2 and at.session_state["setup_step"] == state.LAST_STEP
    assert "수동 노출 위치: Instagram 피드·스토리·릴스" in str(at.session_state["answers"]["meta.adset.placements"])
    assert "2개월 차" in texts(at)
    assert at.session_state["history"][-1]["month"] == 1
    changes = at.session_state["history"][-1]["changes"]
    assert changes and all(str(c["before"]) != str(c["after"]) for c in changes), changes
    shown = [df.value for df in at.get("arrow_data_frame")]
    assert shown, "changed-fields table missing"


def test_c4_shows_search_cap_and_changes_naver_budget():
    at = demo_to_sheet(fresh())
    at.switch_page(DIAG).run()
    at.selectbox(key="diag_case").select("C4").run()
    assert not at.exception, at.exception
    before = at.session_state["budget_plan"]["naver_daily"]
    into(at, "next_month", SETUP)
    at.run()
    assert at.session_state["budget_plan"]["naver_daily"] != before


def test_c0_changes_nothing_and_every_case_renders():
    at = demo_to_sheet(fresh())
    at.switch_page(DIAG).run()
    for case in ("C1", "C3", "C0", "C1b"):
        at.selectbox(key="diag_case").select(case).run()
        assert not at.exception, (case, at.exception)
        if case == "C0":
            assert "고칠 곳이 보이지 않아요" in texts(at)
    at.radio(key="diag_mode").set_value("forecast").run()
    assert not at.exception, at.exception


# ── 올린 파일 ─────────────────────────────────────────────

def test_read_upload_demo_excel_and_bad_file():
    raw = ingest.DEMO_XLSX.read_bytes()
    bundle = data.read_upload((("소연베이크.xlsx", raw),))
    assert len(bundle.tables) == 5 and not bundle.problems
    bad = data.read_upload((("메모.csv", "a,b\n1,2\n".encode("utf-8")),))
    assert not bad.tables and bad.problems and "어떤 리포트" in bad.problems[0]


def test_plan_json_round_trip_through_state():
    at = demo_to_sheet(fresh())
    at.run()
    plan = plan_io.from_json(plan_io.to_json(plan_io.Plan(
        store=dict(at.session_state["store"]), media=list(at.session_state["media"]),
        answers=dict(at.session_state["answers"]), budget_plan=dict(at.session_state["budget_plan"]))))
    assert plan.store["name"] == "소연베이크" and plan.month_index == 1


def test_one_media_only_flow_has_fewer_questions():
    assert len(state.asked_questions(["meta"])) < len(state.asked_questions(["meta", "naver"]))
    assert "meta.campaign.objective" not in [q["id"] for q in state.asked_questions(["meta", "naver"])]


# ── 입력칸 패턴 · 조사 · 시연 진입 · 근거 등급 · 바뀐 칸 ─────────────────

def test_keyed_widgets_never_pass_default_values():
    """key가 있는 입력칸에 value=/index=/default=(또는 슬라이더 값 자리 인자)를 함께 주면 Streamlit이 경고를 띄운다.
    AppTest는 그 경고를 보여 주지 않아서 소스를 직접 훑는다."""
    import ast
    app_dir = Path(__file__).resolve().parents[1] / "app"
    widgets = {"text_input", "number_input", "radio", "selectbox", "multiselect", "checkbox", "toggle", "pills",
               "slider", "date_input", "text_area", "segmented_control", "select_slider"}
    bad = []
    for path in sorted(app_dir.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in widgets):
                continue
            kws = {k.arg for k in node.keywords}
            if "key" not in kws:
                continue
            if kws & {"value", "index", "default"}:
                bad.append("{}:{} {}".format(path.name, node.lineno, node.func.attr))
            if node.func.attr == "slider" and len(node.args) > 3:
                bad.append("{}:{} slider 값 자리 인자".format(path.name, node.lineno))
    assert not bad, bad


def test_josa_helper():
    from v2.app import ui
    assert ui.josa("10,529원", "이에요") == "10,529원이에요"
    assert ui.josa("18,716원", "으로") == "18,716원으로"
    assert ui.josa("+31%", "으로") == "+31%로"
    assert ui.josa("+3%", "이에요") == "+3%예요"
    assert ui.josa("3건", "은") == "3건은" and ui.josa("5명", "이") == "5명이"
    assert ui.josa("2", "이에요") == "2예요" and ui.josa("10", "이에요") == "10이에요"
    assert ui.josa("7", "으로") == "7로"       # 칠: ㄹ 받침은 '로'
    assert ui.josa("쿠키", "을") == "쿠키를"


def test_no_wrong_particle_after_won_in_source():
    """'{}원' 값 뒤에 예요/로를 바로 붙인 문장 틀이 남아 있지 않다 (받침 있는 말 뒤에 쓰면 어색함)."""
    import re
    app_dir = Path(__file__).resolve().parents[1] / "app"
    pat = re.compile(r"\{[^}]*\}원(예요|로[ ,.])")
    for path in app_dir.glob("*.py"):
        assert not pat.search(path.read_text(encoding="utf-8")), path.name


def test_calc_grade_text_and_unknown_grade_fallback():
    from v2.app import diagnose as app_diag
    assert "계산" in app_diag.rule_grade_text("calc") and "확인됨" not in app_diag.rule_grade_text("calc")
    assert app_diag.rule_grade_text("hypothesis").startswith("가설")
    assert app_diag.rule_grade_text("앞으로생길등급")        # 예외 없이 글이 나옴
    assert app_diag.rule_grade_text(None)


def test_cac_over_margin_card_says_calc_not_checked():
    at = demo_to_sheet(fresh())
    at.switch_page(DIAG).run()
    body = texts(at)
    assert not at.exception, at.exception
    if "첫 구매로는 손해" in body:
        assert "계산: 사장님 숫자로 바로 계산한 결과예요" in body
    assert "10,529원예요" not in body and "원로 보이지만" not in body


def test_month_two_sheet_lists_changed_cells_in_their_own_table():
    at = demo_to_sheet(fresh())
    at.switch_page(DIAG).run()
    into(at, "next_month", SETUP)
    at.run()
    assert not at.exception, at.exception
    body = texts(at)
    assert "이번 달에 바뀐 칸" in body and "노란색" not in body
    assert len(at.get("arrow_data_frame")) >= 2                     # 바뀐 칸 표 + 시트


def _run_links(at) -> int:
    return len([e for e in at.get("page_link") if "실행으로 가기" in str(e.proto.label)])


def _next_month_with(at, case: str):
    at.switch_page(DIAG).run()
    at.selectbox(key="diag_case").select(case).run()
    assert not at.exception, at.exception
    into(at, "next_month", SETUP)
    at.run()
    assert not at.exception, at.exception
    return at


def test_month_two_shows_two_changed_rows_in_info_and_sheet():
    at = _next_month_with(demo_to_sheet(fresh()), "C2")
    assert at.session_state["month_index"] == 2
    assert "바뀐 칸이 2개" in texts(at)
    assert _run_links(at) == 1
    assert len(at.session_state["history"][-1]["changes"]) == 2


def test_month_three_without_changes_shows_message_and_no_stale_panel():
    at = _next_month_with(demo_to_sheet(fresh()), "C2")
    at = _next_month_with(at, "C2")
    assert at.session_state["month_index"] == 3
    assert at.session_state["history"][-1]["changes"] == []
    body = texts(at)
    assert "3개월 차예요. 이번 진단에서는 새로 바꿀 칸이 없어요" in body
    assert "바뀐 칸이" not in body and "이번 달에 바뀐 칸" not in body
    assert len(at.get("arrow_data_frame")) == 1                    # 시트 하나뿐 (바뀐 칸 표 없음)
    assert not at.session_state["answers"].get("_changed")
    assert _run_links(at) == 1


def test_c2_then_c4_chain_shows_only_c4_change():
    at = _next_month_with(demo_to_sheet(fresh()), "C2")
    at = _next_month_with(at, "C4")
    assert at.session_state["month_index"] == 3
    changes = at.session_state["history"][-1]["changes"]
    ids = {c["field_id"] for c in changes}
    assert "naver.campaign.daily_budget" in ids and all("daily_budget" in i for i in ids), ids
    assert at.session_state["answers"]["_changed"] == [c["field_id"] for c in changes]
    assert "바뀐 칸이 {}개".format(len(ids)) in texts(at)
    panel = str(at.get("arrow_data_frame")[0].value.to_dict())
    assert "Instagram" not in panel
    assert _run_links(at) == 1


def test_month_one_sheet_has_exactly_one_run_link():
    at = demo_to_sheet(fresh())
    assert _run_links(at) == 1


def test_loaded_plan_shows_sheet_only_and_can_open_chat_to_edit():
    at = _next_month_with(demo_to_sheet(fresh()), "C2")
    assert at.session_state["chat"] is None and len(at.chat_input) == 0      # 이어 하기: 시트만
    at.button(key="sheet_redo").click().run()
    assert not at.exception, at.exception
    assert phase(at) == ("done", "done") and len(at.chat_input) == 1
    at.button(key="edit_margin").click().run()
    assert phase(at) == ("store", "margin") and not at.exception
    say(at, "9,000원")
    chip(at, "맞아요")
    assert phase(at)[0] == "done" and at.session_state["store"]["margin_per_order"] == 9000
    assert at.session_state["month_index"] == 2 and at.session_state["history"]


def _edit_margin_in_month_two(at):
    at.button(key="sheet_redo").click().run()
    at.button(key="edit_margin").click().run()
    say(at, "9,000원")
    chip(at, "맞아요")
    assert not at.exception, at.exception
    return at


def test_month_two_c4_margin_edit_keeps_diagnosis_budget():
    at = _next_month_with(demo_to_sheet(fresh()), "C4")
    before = dict(at.session_state["budget_plan"])
    _edit_margin_in_month_two(at)
    bp = at.session_state["budget_plan"]
    assert at.session_state["store"]["margin_per_order"] == 9000
    assert bp["naver_daily"] == before["naver_daily"] and bp["meta_daily"] == before["meta_daily"]
    assert bp["naver_daily"] == at.session_state["answers"]["naver.campaign.daily_budget"]
    assert "아직 고르지 않아서" not in "".join(t["text"] for t in at.session_state["chat"]["turns"])


def test_month_two_c2_margin_edit_keeps_cap_and_notes():
    at = _next_month_with(demo_to_sheet(fresh()), "C2")
    before = dict(at.session_state["budget_plan"])
    _edit_margin_in_month_two(at)
    bp = at.session_state["budget_plan"]
    assert bp["naver_cap_month"] == before["naver_cap_month"] and bp["notes"] == before["notes"]


def test_month_two_budget_edit_replans_without_false_keyword_note():
    at = _next_month_with(demo_to_sheet(fresh()), "C4")
    at.button(key="sheet_redo").click().run()
    at.button(key="edit_budget").click().run()
    say(at, "40만원")
    chip(at, "맞아요")
    assert not at.exception, at.exception
    bp = at.session_state["budget_plan"]
    assert bp["budget"] == 400000
    assert "아직 고르지 않아서" not in " ".join(bp["notes"])


def test_setup_layout_puts_chat_first_on_narrow_screens_and_has_guide_toggle():
    at = demo_to_budget(fresh())
    assert at.toggle(key="w_guide").value is True
    from v2.app import chat
    assert "order:-1" in chat.GUIDE_CSS and "prefers-reduced-motion" in chat.GUIDE_CSS
    cs = at.session_state["chat"]
    assert chat.focus_id(cs) in ("budget", "market") or cs["phase"] == "ask"
    html = " ".join(str(m.value) for m in at.markdown)
    assert '<span class="coach-bubble">' in html
    at.toggle(key="w_guide").set_value(False).run()
    assert '<span class="coach-bubble">' not in " ".join(str(m.value) for m in at.markdown)
