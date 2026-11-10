"""MVP 7e 3단계: 상태 키 선언 하나 + 계획 파일(Plan) + 단계 이동 함수.

키 목록 세 벌(_KEEP·PLAN_INPUT_KEYS·초기화 목록)이 선언 하나에서 나오는지, 계획 파일이 모든 키를 왕복하는지,
단계 이동·초기화·열림 규칙이 화면이 하던 그대로인지.
"""
import json

import pytest

from src.engine import session_schema as S

# 리팩토링 전 main.py·report.py에 있던 목록 (그대로 나와야 함)
OLD_KEEP = ["q_category", "q_stores", "q_price", "q_profit", "q_repurchase", "q_budget", "q_baseline", "q_keyword",
            "q_cpc", "q_budget_pick", "q_spent", "q_clicks", "q_coupon", "q_report", "q_total",
            "prep_1", "prep_2", "prep_3", "link_store", "link_ch", "link_url", "link_product", "link_detail"]
OLD_PLAN = ["q_category", "q_stores", "q_price", "q_profit", "q_repurchase", "q_budget", "q_baseline", "q_keyword",
            "q_cpc", "q_budget_pick", "repurchase_measured"]
MONTH_LATER = ["q_spent", "q_clicks", "q_coupon", "q_report", "q_total"]
MEASURED = {"customers": 120, "orders": 260, "observed_months": 4.0, "repeat_share": 0.4, "repeats_observed": 1.1,
            "repeats_year": 2.6, "extended": True}


# 7d 세팅 도우미 매체 고르기: 고른 매체는 단계 이동 때 남기고, '내 숫자로 시작'에서 진행·결과와 함께 지움
SETUP_PERSIST = ["setup_media"]
SETUP_RESET = {"setup_media", "_setup_media_touched", "setup_phase", "setup_last"}


def test_key_lists_come_from_one_declaration():
    assert S.PERSIST == OLD_KEEP + SETUP_PERSIST
    assert set(S.PLAN) == set(OLD_PLAN) | set(MONTH_LATER)          # 한 달 뒤 입력도 계획 파일에 (7e 3단계)
    assert set(S.RESET) == set(OLD_KEEP) | {"coach_started", "coach_prev_rate", "coach_seen", "_budget_touched", "report_only"} | SETUP_RESET
    assert "repurchase_measured" not in S.RESET                     # '내 숫자로 시작'해도 주문 내역 실측은 남김 (지금과 같음)


def _full_plan():
    inputs = {"q_category": "식품", "q_stores": ["스마트스토어", "쿠팡"], "q_price": 20_000, "q_profit": 7_000,
              "q_repurchase": "실측", "q_budget": 300_000, "q_baseline": 3, "q_keyword": "원두커피", "q_cpc": 900,
              "q_budget_pick": "small", "repurchase_measured": MEASURED,
              "q_spent": 120_000, "q_clicks": 90, "q_coupon": 4, "q_report": 6, "q_total": 11}
    pred = {"budget": 210_000, "naver": 68_000, "meta": 142_000, "clicks": 140.0, "cpc": 1_500.0, "new": 1.4,
            "cvr": 0.0126, "wins": 3, "p10": -170_000.0, "p90": -60_000.0}
    return S.Plan(inputs=inputs, prediction=pred, started="2026-11-09", settings={"naver_daily": 10_000, "objective": "트래픽"})


def test_plan_roundtrip_keeps_every_key():
    plan = _full_plan()
    back = S.Plan.from_json(plan.to_json())
    assert set(back.inputs) == set(S.PLAN)
    assert back.inputs == plan.inputs and back.started == plan.started and back.settings == plan.settings
    assert back.prediction == pytest.approx(plan.prediction)
    assert json.loads(plan.to_json())["version"] == S.PLAN_VERSION


def test_plan_from_session_takes_only_declared_keys():
    ss = dict(_full_plan().inputs, coach_step=2, chat_hist=["개인 대화"], link_url="https://x")
    plan = S.Plan.from_session(ss, {"budget": 1.0}, "2026-11-09")
    assert set(plan.inputs) == set(S.PLAN) and "link_url" not in plan.inputs and "chat_hist" not in plan.inputs


def test_plan_rejects_bad_month_later_and_settings():
    for bad in ({"q_spent": -1}, {"q_clicks": True}, {"q_total": float("inf")}):
        with pytest.raises(ValueError):
            S.Plan.from_json(json.dumps({"version": S.PLAN_VERSION, "inputs": bad}))
    with pytest.raises(ValueError):
        S.Plan.from_json(json.dumps({"version": S.PLAN_VERSION, "inputs": {}, "settings": {"x": {"nested": 1}}}))


def test_apply_plan_opens_month_later_when_started():
    ss = {"coach_step": 0}
    S.apply_plan(ss, _full_plan())
    assert ss["q_price"] == 20_000 and ss["q_spent"] == 120_000 and ss["repurchase_measured"] == MEASURED
    assert ss["_budget_touched"] is True and ss["plan_pred"]["budget"] == 210_000
    assert (ss["coach_mode"], ss["coach_started"], ss["coach_step"], ss["coach_seen"]) == ("mine", "2026-11-09", S.RESULT, S.RESULT)
    ss2 = {"coach_step": 1}
    S.apply_plan(ss2, S.Plan(inputs={"q_price": 1}, prediction={}, started=None))
    assert ss2["coach_step"] == 1 and "_budget_touched" not in ss2 and ss2["coach_mode"] == "mine"


def test_go_to_reset_and_unlock_rules():
    ss = {"coach_step": 0, "coach_seen": 2}
    S.go_to(ss, 1)
    assert ss["coach_step"] == 1 and ss["coach_seen"] == 2          # 본 단계는 줄지 않음
    S.begin(ss, "example", 1)
    assert (ss["coach_mode"], ss["coach_step"], ss["coach_seen"]) == ("example", 1, 1)
    full = dict(_full_plan().inputs, coach_started="2026-11-09", coach_prev_rate=0.01, coach_seen=3, _budget_touched=True,
                prep_1=True, link_ch="meta", coach_mode="example", coach_step=3, chat_hist=[])
    S.reset(full)
    assert not set(S.RESET) & set(full)
    assert full["coach_mode"] == "mine" and full["coach_step"] == 0 and "chat_hist" in full
    assert full["repurchase_measured"] == MEASURED
    # 열림 (v1.0): 답이 없으면 내 가게만, 답이 있으면 최적화까지 모두 (광고 시작 전이면 최적화 화면이 빈 화면 안내)
    ss = {"coach_step": S.RESULT}
    assert S.clamp_step(ss, has_answer=False) == (0, 0) and ss["coach_step"] == 0
    ss = {"coach_step": S.RESULT}
    assert S.clamp_step(ss, has_answer=True) == (S.RESULT, S.RESULT)
    ss = {"coach_step": S.SETUP}
    assert S.clamp_step(ss, has_answer=True) == (S.SETUP, S.RESULT)


def test_three_stages_cover_five_steps_once():
    """화면 묶음 3개(세팅·실행·최적화)가 단계 5개를 빠짐없이 한 번씩 덮음."""
    assert [s for _, steps in S.STAGES for s in steps] == list(range(len(S.STEP_NAMES)))
    assert [S.stage_of(s) for s in range(5)] == [0, 0, 0, 1, 2]


def test_plan_rejects_non_dict_sections():
    for body in ({"version": 2, "inputs": ["q_price"]}, {"version": 2, "inputs": {}, "prediction": [1, 2]}):
        with pytest.raises(ValueError):
            S.Plan.from_json(json.dumps(body))


# ── 1단계에서 옮겨 옴 (report.plan_to_json·plan_from_json → Plan, 검사 규칙은 그대로) ──
MEASURED_B3 = {"customers": 103, "orders": 180, "observed_months": 3.0, "repeat_share": 0.46, "repeats_observed": 0.67,
               "repeats_year": 7.5, "extended": True}


def _write(inputs, prediction, started):
    return S.Plan(inputs, prediction, started).to_json()


def _read(text):
    p = S.Plan.from_json(text)
    return p.inputs, p.prediction, p.started


def test_plan_roundtrip_and_rejects_bad_values():
    inputs = {"q_price": 20_000, "q_profit": 7_000, "q_stores": ["스마트스토어"], "q_keyword": "원두커피", "q_repurchase": "가끔",
              "q_budget": 300_000, "secret": "x"}
    text = _write(inputs, {"budget": 210_000, "naver": 68_000, "meta": 142_000, "clicks": 140, "new": 1.4}, "2026-11-09")
    got_in, got_pred, started = _read(text)
    assert "secret" not in got_in and got_in["q_price"] == 20_000 and started == "2026-11-09"
    assert got_pred["naver"] == 68_000
    with pytest.raises(ValueError):
        _read('{"version": 1, "inputs": {"q_price": "abc"}}')
    with pytest.raises(ValueError):
        _read('{"version": 9}')


def test_b3_plan_keeps_measured_repurchase():
    """재구매 실측값을 계획 파일에 저장·불러오기 → 불러온 뒤에도 '실측'이 그대로 (화면이 '가끔'으로 바꾸지 않게)."""
    inputs = {"q_price": 20_000, "q_profit": 7_000, "q_repurchase": "실측", "q_budget": 300_000,
              "repurchase_measured": MEASURED_B3}
    text = _write(inputs, {"budget": 210_000}, "2026-11-09")
    assert json.loads(text)["version"] == 2
    got, _, _ = _read(text)
    assert got["q_repurchase"] == "실측" and got["repurchase_measured"] == MEASURED_B3


def test_b3_version1_plan_still_reads():
    v1 = json.dumps({"version": 1, "started": "2026-10-01",
                     "inputs": {"q_price": 20_000, "q_profit": 7_000, "q_repurchase": "매달(정기)", "q_budget": 300_000,
                                "q_budget_pick": "recommended"},
                     "prediction": {"budget": 210_000.0, "wins": 0.0}})
    got, pred, started = _read(v1)
    assert got["q_repurchase"] == "매달(정기)" and "repurchase_measured" not in got
    assert pred["budget"] == 210_000 and started == "2026-10-01"


def test_b3_measured_without_numbers_is_rejected():
    bad = dict(MEASURED_B3, repeats_year="많이")
    with pytest.raises(ValueError):
        _read(json.dumps({"version": 2, "inputs": {"q_repurchase": "실측", "repurchase_measured": bad}}))
    with pytest.raises(ValueError):
        _read(json.dumps({"version": 2, "inputs": {"repurchase_measured": dict(MEASURED_B3, repeats_year=float("nan"))}}))


@pytest.mark.parametrize("inputs", [
    {"q_price": True},                       # bool은 숫자가 아님
    {"q_budget": float("nan")},
    {"q_budget": float("inf")},
    {"q_repurchase": "아무거나"},
    {"q_budget_pick": "전부"},
    {"q_category": "우주선"},
])
def test_b4_plan_rejects_bad_inputs(inputs):
    with pytest.raises(ValueError):
        _read(json.dumps({"version": S.PLAN_VERSION, "inputs": inputs}))


@pytest.mark.parametrize("started", ["2026-02-30", "2026-13-01", "0000-00-00"])
def test_b4_plan_rejects_impossible_dates(started):
    with pytest.raises(ValueError):
        _read(json.dumps({"version": S.PLAN_VERSION, "started": started, "inputs": {}}))


def test_b4_plan_rejects_bad_prediction_numbers():
    with pytest.raises(ValueError):
        _read(json.dumps({"version": S.PLAN_VERSION, "inputs": {}, "prediction": {"wins": float("nan")}}))


def test_b4_allowed_choices_pass():
    got, _, _ = _read(json.dumps({"version": S.PLAN_VERSION, "inputs": {
        "q_category": "식품", "q_repurchase": "가끔", "q_budget_pick": "none", "q_stores": ["스마트스토어"]}}))
    assert got == {"q_category": "식품", "q_repurchase": "가끔", "q_budget_pick": "none", "q_stores": ["스마트스토어"]}
