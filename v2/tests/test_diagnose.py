"""진단 (P1) 테스트: 골든 케이스(규칙 8개) + 규칙 동작 + 다음 달 변경."""
import pandas as pd
import pytest

from v2.engine import diagnose, ingest, metrics, specs
from v2.engine.diagnose import Change, Finding

CTX = metrics.Context(start=pd.Timestamp("2026-11-16"), end=pd.Timestamp("2026-12-15"))

DAJEONG_RULES = [
    "rule.weekly_freq_high", "rule.awareness_freq_low", "rule.creative_fatigue", "rule.placement_quality",
    "rule.ig_share_low", "rule.search_demand_cap", "rule.target_saturation", "rule.awareness_hidden",
]
# 다정 규칙 8개가 가상 데이터(sim)에서 걸리는 케이스 (계약 2장 P1)
GOLDEN = {
    "rule.weekly_freq_high": set(),
    "rule.awareness_freq_low": {"C1", "C3"},
    "rule.creative_fatigue": set(),
    "rule.placement_quality": {"C2"},
    "rule.ig_share_low": {"C2"},
    "rule.search_demand_cap": {"C4"},
    "rule.target_saturation": {"C3"},
    "rule.awareness_hidden": {"C1", "C2", "C3", "C1b"},
}


@pytest.fixture(scope="module")
def sim_findings():
    bundle = ingest.demo()
    out = {}
    for case in bundle.cases():
        m = metrics.case_metrics(bundle.select(case, "sim"), CTX)
        out[case] = (m, diagnose.evaluate(m))
    return out


def test_golden_eight_rules_exact_case_sets(sim_findings):
    got = {rid: set() for rid in DAJEONG_RULES}
    for case, (_, findings) in sim_findings.items():
        for f in diagnose.fired(findings):
            if f.id in got:
                got[f.id].add(case)
    assert got == GOLDEN


def test_c0_fires_nothing(sim_findings):
    assert diagnose.fired(sim_findings["C0"][1]) == []


def test_fired_findings_have_message_and_evidence(sim_findings):
    for _, findings in sim_findings.values():
        for f in diagnose.fired(findings):
            assert f.message and "{" not in f.message
            assert f.evidence
            assert f.grade in ("hypothesis", "checked", "calc")


def test_message_uses_formatted_numbers(sim_findings):
    f = {x.id: x for x in sim_findings["C4"][1]}["rule.search_demand_cap"]
    assert metrics.fmt("budget_use", sim_findings["C4"][0]["budget_use"]) in f.message
    assert f.evidence["budget_use"] in f.message


def test_one_finding_per_rule_in_spec_order(sim_findings):
    ids = [f.id for f in sim_findings["C2"][1]]
    assert ids == [r["id"] for r in specs.rules()]


def test_missing_metric_is_no_data():
    findings = {f.id: f for f in diagnose.evaluate({})}
    assert all(f.status == "no_data" for f in findings.values())
    assert diagnose.fired(list(findings.values())) == []


def test_none_value_is_no_data():
    f = diagnose.evaluate({"weekly_freq_max": None})[0]
    assert f.id == "rule.weekly_freq_high" and f.status == "no_data"


def test_passed_when_condition_false():
    f = {x.id: x for x in diagnose.evaluate({"weekly_freq_max": 2.0})}["rule.weekly_freq_high"]
    assert f.status == "passed" and f.message == ""


def test_boundary_ops():
    # creative_fatigue는 >= 0.30, weekly_freq_high는 > 3
    ids = lambda m: {f.id for f in diagnose.fired(diagnose.evaluate(m))}
    assert "rule.creative_fatigue" in ids({"ctr_drop_max": 0.30})
    assert "rule.creative_fatigue" not in ids({"ctr_drop_max": 0.29})
    assert "rule.weekly_freq_high" not in ids({"weekly_freq_max": 3})
    assert "rule.weekly_freq_high" in ids({"weekly_freq_max": 3.01})


def test_all_conditions_must_hold():
    # search_demand_cap: budget_use < 0.9 이고 naver_spend > 0
    ids = lambda m: {f.id for f in diagnose.fired(diagnose.evaluate(m))}
    assert "rule.search_demand_cap" in ids({"budget_use": 0.5, "naver_spend": 1000.0})
    assert "rule.search_demand_cap" not in ids({"budget_use": 0.5, "naver_spend": 0.0})


def test_changes_set_and_set_from(sim_findings):
    m, findings = sim_findings["C4"]
    f = {x.id: x for x in findings}["rule.search_demand_cap"]
    by = {c.field_id: c for c in f.changes}
    assert by["naver.campaign.daily_budget"].new == m["naver_daily_spend"]
    assert by["meta.adset.daily_budget"].new == m["meta_daily_with_leftover"]
    c = by["naver.campaign.daily_budget"]
    assert isinstance(c, Change) and c.media == "naver" and c.rule_id == f.id and c.label and c.note

    f2 = {x.id: x for x in sim_findings["C2"][1]}["rule.placement_quality"]
    assert "Audience Network 제외" in f2.changes[0].new
    assert f2.changes[0].media == "meta"


def test_set_from_missing_drops_change_keeps_finding():
    m = {"budget_use": 0.5, "naver_spend": 1000.0, "naver_daily_spend": 8000}   # meta_daily_with_leftover 없음
    f = {x.id: x for x in diagnose.evaluate(m)}["rule.search_demand_cap"]
    assert f.status == "fired"
    assert [c.field_id for c in f.changes] == ["naver.campaign.daily_budget"]


def test_next_changes_only_fired_and_dedup_same_field():
    # weekly_freq_high와 target_saturation은 둘 다 meta.adset.age_gender를 바꾼다
    m = {"weekly_freq_max": 4.0, "saturation_max": 0.8}
    findings = diagnose.evaluate(m)
    changes = diagnose.next_changes(findings)
    ids = [c.field_id for c in changes]
    assert len(ids) == len(set(ids))
    age = [c for c in changes if c.field_id == "meta.adset.age_gender"]
    assert len(age) == 1
    assert age[0].rule_id == "rule.weekly_freq_high"          # 먼저 나온 규칙
    assert "새 사람에게 닿게" in age[0].note and "나이·성별 범위를 넓혀요" in age[0].note   # note 합침
    assert "meta.adset.location" in ids


def test_next_changes_ignores_passed():
    assert diagnose.next_changes(diagnose.evaluate({"weekly_freq_max": 1.0})) == []


def test_next_changes_does_not_mutate_findings():
    findings = diagnose.evaluate({"weekly_freq_max": 4.0, "saturation_max": 0.8})
    before = [c.note for f in findings for c in f.changes]
    diagnose.next_changes(findings)
    assert [c.note for f in findings for c in f.changes] == before


def test_advice_and_caveat_carried(sim_findings):
    f = {x.id: x for x in sim_findings["C1"][1]}
    assert f["rule.awareness_hidden"].advice and f["rule.awareness_hidden"].changes == []
    assert f["rule.awareness_freq_low"].caveat


def test_custom_rules_argument():
    rules = [{"id": "r.x", "title": "t", "funnel": "노출", "when": [{"metric": "a", "op": ">", "value": 1}],
              "says": "값은 {a}이고 {b}예요", "changes": [], "grade": "checked"}]
    f = diagnose.evaluate({"a": 5.0, "b": 0.25}, rules)
    assert len(f) == 1 and f[0].status == "fired" and f[0].grade == "checked"
    assert isinstance(f[0], Finding)
    assert "{" not in f[0].message


def test_nan_metric_is_no_data():
    np = pytest.importorskip("numpy")
    for bad in (float("nan"), np.float64("nan"), np.float32("nan")):
        f = diagnose.evaluate({"weekly_freq_max": bad})[0]
        assert f.id == "rule.weekly_freq_high" and f.status == "no_data"
    ok = diagnose.evaluate({"weekly_freq_max": np.float64(4.0)})[0]
    assert ok.status == "fired"


def test_set_from_nan_drops_change_keeps_finding():
    np = pytest.importorskip("numpy")
    for nan in (float("nan"), np.float64("nan")):
        m = {"budget_use": 0.5, "naver_spend": 1000.0, "naver_daily_spend": 8000,
             "meta_daily_with_leftover": nan}
        f = {x.id: x for x in diagnose.evaluate(m)}["rule.search_demand_cap"]
        assert f.status == "fired"
        assert [c.field_id for c in f.changes] == ["naver.campaign.daily_budget"]


# 희수 퍼널 규칙이 가상 데이터(sim)에서 걸리는 케이스를 고정한다. 바뀌면 의도한 변경인지 확인할 것.
HEESU_PINNED = {
    "rule.visit_no_sale": {"C1", "C2", "C1b"},
    "rule.keyword_no_sales": {"C1", "C1b"},
}


def test_heesu_funnel_rules_pinned_on_sim(sim_findings):
    got = {rid: set() for rid in HEESU_PINNED}
    for case, (_, findings) in sim_findings.items():
        for f in diagnose.fired(findings):
            if f.id in got:
                got[f.id].add(case)
    assert got == HEESU_PINNED


def test_calc_grade_passes_through_unchanged():
    rule = {r["id"]: r for r in specs.rules()}["rule.cac_over_margin"]
    assert rule["grade"] == "calc"
    f = {x.id: x for x in diagnose.evaluate(
        {"margin_gap": 1000.0, "est_cac": 5000, "margin_per_order": 4000})}["rule.cac_over_margin"]
    assert f.status == "fired" and f.grade == "calc"
    passed = {x.id: x for x in diagnose.evaluate({"margin_gap": -1.0})}["rule.cac_over_margin"]
    assert passed.status == "passed" and passed.grade == "calc"
