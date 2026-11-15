"""P7 app 테스트: 페이지별 렌더링, 예시(소연베이크) 3분 경로, 한 번에 한 질문, 올린 파일 읽기.

네트워크·API 키를 쓰지 않는다 (시장 조사는 저장본, 문구는 문장 틀).
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from v2.app import data, state
from v2.engine import ingest, market, naver_api, plan_io

MAIN = str(Path(__file__).resolve().parents[1] / "app" / "main.py")
SETUP, RUN, DIAG = "setup.py", "run.py", "diagnose.py"


def fresh() -> AppTest:
    at = AppTest.from_file(MAIN, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    return at


def into(at: AppTest, key: str, page: str) -> AppTest:
    """st.switch_page를 부르는 버튼을 누른다. AppTest는 쪽 이동을 기억하지 못해서 같은 쪽으로 다시 맞춰 준다."""
    at.button(key=key).click().run()
    at.switch_page(page)
    return at


def titles(at):
    return [t.value for t in at.title]


def texts(at) -> str:
    """화면의 글 전체 (설명·캡션·경고 포함)."""
    parts = []
    for coll in (at.markdown, at.caption, at.success, at.info, at.warning, at.error):
        parts += [str(e.value) for e in coll]
    return "\n".join(parts)


def demo_to_sheet(at: AppTest) -> AppTest:
    into(at, "home_demo", SETUP)
    at.button(key="market_find").click().run()
    at.button(key="market_next").click().run()
    at.button(key="budget_next").click().run()
    at.button(key="q_skip_rest").click().run()
    assert not at.exception, at.exception
    return at


# ── 페이지마다 예외 없이 그려진다 ───────────────────────────

def test_home_renders():
    at = fresh()
    assert titles(at) == ["광고 코치"]
    assert any("예시로 해 보기" in b.label for b in at.button)
    assert "근거 등급" in texts(at)


def test_setup_first_page_renders_and_validates():
    at = fresh()
    into(at, "home_mine", SETUP)
    assert titles(at) == ["① 세팅"]
    at.button(key="store_next").click().run()          # 아무것도 안 적고 다음
    assert "가게 이름을 적어 주세요" in "".join(e.value for e in at.error)
    assert at.session_state["setup_step"] == 0
    at.text_input(key="w_name").set_value("소연베이크")
    at.text_input(key="w_product").set_value("수제 구움과자")
    at.button(key="store_next").click().run()
    assert at.session_state["setup_step"] == 1
    assert at.session_state["store"]["name"] == "소연베이크"


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


# ── 예시 3분 경로 ─────────────────────────────────────────

def test_demo_path_market_card():
    at = fresh()
    into(at, "home_demo", SETUP)
    assert at.session_state["setup_step"] == 1 and at.session_state["store"]["name"] == "소연베이크"
    at.button(key="market_find").click().run()
    assert not at.exception, at.exception
    assert any("찾는 사람은" in s.value for s in at.success)     # 한 줄 요약(헤드라인)
    assert at.session_state["store"]["keywords"] and at.session_state["store"]["negatives"]
    assert "근거 B" in texts(at)


def test_market_not_found_gives_one_next_action():
    at = fresh()
    into(at, "home_demo", SETUP)
    at.text_input(key="w_seeds").set_value("존재하지않는상품단어xyz")
    at.button(key="market_find").click().run()
    assert not at.exception
    assert "더 넓은 단어" in "".join(w.value for w in at.warning)
    assert any(b.key == "market_demo_seeds" for b in at.button)


FRIENDLY = "네이버 키가 맞지 않는 것 같아요. 키를 다시 확인해 주세요."


def _live_find(monkeypatch, fake_build):
    """실시간 토글을 켜고 '내 손님 찾기'. 네트워크 없이 market.build를 바꿔 끼운다."""
    monkeypatch.setattr(market, "build", fake_build)
    at = fresh()
    into(at, "home_demo", SETUP)
    at.toggle(key="use_live").set_value(True)
    at.button(key="market_find").click().run()
    assert not at.exception, at.exception
    return at


def test_live_failure_shows_friendly_message_and_next_action(monkeypatch):
    def fail(seeds, online=True):
        naver_api._set_error(FRIENDLY)
        return None
    at = _live_find(monkeypatch, fail)
    assert FRIENDLY in "".join(w.value for w in at.warning)
    assert any(b.key == "market_use_saved" for b in at.button)
    assert "다시" in texts(at)
    at.button(key="market_use_saved").click().run()                 # 다음 행동: 저장된 예시로 계속하기
    assert not at.exception, at.exception
    assert at.session_state["market"] is not None and not at.session_state["use_live"]
    assert FRIENDLY not in "".join(w.value for w in at.warning)


def test_live_error_warning_persists_on_later_reruns(monkeypatch):
    def fail(seeds, online=True):
        naver_api._set_error(FRIENDLY)
        return None
    at = _live_find(monkeypatch, fail)
    at.text_input(key="w_seeds").set_value("휘낭시에, 수제쿠키").run()     # 찾기 버튼은 누르지 않은 다시 그리기
    assert not at.exception, at.exception
    assert FRIENDLY in "".join(w.value for w in at.warning)
    assert any(b.key == "market_use_saved" for b in at.button)
    at.toggle(key="use_live").set_value(False).run()                 # 실시간을 끄면 안내도 사라진다
    assert at.session_state["market_error"] is None
    assert FRIENDLY not in "".join(w.value for w in at.warning)


def test_live_failure_then_successful_retry_clears_warning(monkeypatch):
    real = market.build
    state_ = {"fail": True}

    def flaky(seeds, online=True):
        if state_["fail"]:
            naver_api._set_error(FRIENDLY)
            return None
        naver_api._set_error(None)
        return real(seeds, online=False)
    at = _live_find(monkeypatch, flaky)
    assert FRIENDLY in "".join(w.value for w in at.warning)
    state_["fail"] = False
    at.button(key="market_find").click().run()                       # 다시 찾기: 이번엔 성공
    assert not at.exception, at.exception
    assert not at.warning and at.session_state["market_error"] is None
    assert any("찾는 사람은" in s.value for s in at.success)
    at.text_input(key="w_seeds").set_value("휘낭시에, 수제쿠키").run()     # 이후 다시 그리기에도 안 돌아온다
    assert not at.exception, at.exception
    assert not at.warning and at.session_state["market_error"] is None


def test_demo_path_offline_shows_no_warning(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network must not be used on the demo path")
    for name in ("_http_ad", "_http_hub"):                          # raising=True: 이름이 틀리면 바로 실패
        monkeypatch.setattr(naver_api, name, boom)
    monkeypatch.setattr(naver_api.requests, "get", boom)
    monkeypatch.setattr(naver_api.requests, "post", boom)
    real = market.build
    online_args = []

    def spy(seeds, online=True):
        online_args.append(online)
        return real(seeds, online=online)
    monkeypatch.setattr(market, "build", spy)
    naver_api._set_error(None)
    at = fresh()
    into(at, "home_demo", SETUP)
    at.button(key="market_find").click().run()
    assert not at.exception, at.exception
    assert online_args and all(o is False for o in online_args), online_args
    assert not at.warning
    assert at.session_state["market_error"] is None
    assert naver_api.last_error() is None
    assert any("찾는 사람은" in s.value for s in at.success)


def test_live_fallback_to_saved_data_still_warns(monkeypatch):
    real = market.build

    def fallback(seeds, online=True):
        rep = real(seeds, online=False)
        naver_api._set_error(FRIENDLY)
        return rep
    at = _live_find(monkeypatch, fallback)
    assert FRIENDLY in "".join(w.value for w in at.warning)
    assert any("찾는 사람은" in s.value for s in at.success)       # 저장된 값으로 결과는 보인다


def test_live_success_shows_no_warning(monkeypatch):
    real = market.build

    def ok(seeds, online=True):
        naver_api._set_error(None)
        return real(seeds, online=False)
    at = _live_find(monkeypatch, ok)
    assert not at.warning
    assert any("찾는 사람은" in s.value for s in at.success)


def test_budget_step_has_metrics_and_grades():
    at = fresh()
    into(at, "home_demo", SETUP)
    at.button(key="market_find").click().run()
    at.button(key="market_next").click().run()
    assert at.session_state["setup_step"] == 2
    labels = [m.label for m in at.metric]
    assert "한 달 광고비" in labels and "네이버 하루 예산" in labels and "메타 하루 예산" in labels
    assert "근거 C" in texts(at) or "근거 D" in texts(at)
    at.button(key="budget_next").click().run()
    bp = at.session_state["budget_plan"]
    assert at.session_state["setup_step"] == 3 and bp["naver_daily"] > 0 and bp["meta_daily"] > 0
    assert at.session_state["answers"]["meta.adset.end_date"] == "14일"


def test_questions_one_at_a_time_then_sheet():
    at = fresh()
    into(at, "home_demo", SETUP)
    at.button(key="market_find").click().run()
    at.button(key="market_next").click().run()
    at.button(key="budget_next").click().run()
    first = at.session_state["q_index"]
    assert "질문 1/" in "".join(m.value for m in at.markdown)
    at.button(key="q_ok").click().run()                 # 첫 질문(선택형)은 권장 답으로
    assert at.session_state["q_index"] == first + 1
    assert not at.exception, at.exception
    at.button(key="q_skip_rest").click().run()          # 나머지는 예시 답으로
    assert at.session_state["setup_step"] == state.LAST_STEP
    a = at.session_state["answers"]
    assert isinstance(a["meta.creative.copy"], dict) and isinstance(a["naver.ad.copy"], dict)
    assert len(a["naver.ad.copy"]["headline"]) <= 15
    assert a["meta.ad.website_url"].startswith("https://")


def test_text_question_rejects_bad_url_inline():
    at = fresh()
    into(at, "home_demo", SETUP)
    at.button(key="market_find").click().run()
    at.button(key="market_next").click().run()
    at.button(key="budget_next").click().run()
    qs = state.asked_questions(["meta", "naver"])
    url_idx = [q["id"] for q in qs].index("meta.ad.website_url")
    at.session_state["q_index"] = url_idx
    at.run()
    at.chat_input[0].set_value("smartstore").run()
    assert "http" in "".join(e.value for e in at.error)
    assert at.session_state["q_index"] == url_idx       # 넘어가지 않음


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


def test_fill_demo_seeds_sets_state_before_widget_exists():
    """'예시 단어로 채우기' 뒤에도 입력칸 값이 예시 단어로 바뀌고 예외가 없다."""
    at = fresh()
    into(at, "home_mine", SETUP)
    at.text_input(key="w_name").set_value("가게")
    at.text_input(key="w_product").set_value("쿠키")
    at.button(key="store_next").click().run()
    at.button(key="market_demo_seeds").click().run()
    assert not at.exception, at.exception
    assert at.text_input(key="w_seeds").value == ", ".join(state.DEMO_SEEDS)


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


def test_demo_entry_prefilled_with_market_card_ready():
    at = fresh()
    into(at, "home_demo", SETUP)
    assert not at.exception, at.exception
    assert at.session_state["setup_step"] == 1
    assert at.text_input(key="w_seeds").value == ", ".join(state.DEMO_SEEDS)
    assert any("찾는 사람은" in s.value for s in at.success)       # 누르지 않아도 결과 카드가 이미 있음
    assert at.session_state["store"]["keywords"]
    at.button(key="market_next").click().run()                      # 다음만 누르면 예산 단계
    assert at.session_state["setup_step"] == 2 and not at.exception


def test_demo_entry_after_a_previous_visit_still_prefilled():
    at = fresh()
    into(at, "home_mine", SETUP)
    at.switch_page("home.py").run()
    into(at, "home_demo", SETUP)
    assert at.text_input(key="w_seeds").value == ", ".join(state.DEMO_SEEDS)


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
