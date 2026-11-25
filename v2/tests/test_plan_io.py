"""P6 plan_io 테스트: 완료 기준(C2·C4 다음 달), JSON 왕복, 깨진·다른 파일."""
import json

import pandas as pd
import pytest

from v2.engine import diagnose, ingest, metrics, plan_io
from v2.engine.plan_io import Plan, PlanError

CTX = metrics.Context(start=pd.Timestamp("2026-11-16"), end=pd.Timestamp("2026-12-15"))


def make_plan():
    return Plan(
        created="2026-11-15",
        store={"name": "소연베이크", "product": "구움과자", "product_slug": "soyeon", "store_type": "smartstore",
               "price": 18000, "margin_per_order": 7000, "budget": 300000, "seeds": ["답례품쿠키"], "month": "11월"},
        media=["meta", "naver"], answers={"meta.ad.website_url": "https://smartstore.naver.com/soyeon/products/1"},
        budget_plan={"meta_daily": 6000, "naver_daily": 4000, "naver_bid": 300}, history=[])


@pytest.fixture(scope="module")
def sim():
    bundle = ingest.demo()
    out = {}
    for case in ("C2", "C4", "C0"):
        m = metrics.case_metrics(bundle.select(case, "sim"), CTX)
        out[case] = (m, diagnose.evaluate(m))
    return out


def test_c2_switches_to_instagram_placements(sim):
    plan = make_plan()
    new, diff = plan_io.next_month(plan, sim["C2"][1])
    assert "Instagram" in new.answers["meta.adset.placements"]
    assert new.answers["meta.ad.media"] == "둘 다"
    assert (diff["before"] != diff["after"]).all()               # 같은 값으로 '바뀐' 칸은 없다
    assert "meta.adset.placements" in set(diff["field_id"])
    assert new.month_index == 2 and plan.month_index == 1
    assert "meta.adset.placements" not in plan.answers          # 원본은 그대로
    assert new.history[-1]["month"] == 1
    assert "rule.placement_quality" in new.history[-1]["fired"]
    assert "meta.adset.placements" in new.answers["_changed"]


def test_c4_naver_daily_becomes_actual_spend(sim):
    metrics_c4, findings = sim["C4"]
    plan = make_plan()
    plan.budget_plan.update(naver_daily=10000, meta_daily=0)   # 한도 없이 하루 1만 원까지 쓰게 세팅했던 경우
    new, diff = plan_io.next_month(plan, findings)
    actual = metrics_c4["naver_daily_spend"]
    assert new.answers["naver.campaign.daily_budget"] == int(round(actual))
    assert new.budget_plan["naver_daily"] == int(round(actual))
    assert new.budget_plan["naver_daily"] < 10000
    row = diff[diff["field_id"] == "naver.campaign.daily_budget"].iloc[0]
    assert row["before"] == "10,000원"          # 바꾸기 전 값은 예산 계획의 값
    assert row["after"].endswith("원")


def test_c0_changes_nothing(sim):
    plan = make_plan()
    new, diff = plan_io.next_month(plan, sim["C0"][1])
    assert diff.empty and {k: v for k, v in new.answers.items() if k != "_changed"} == plan.answers
    assert new.month_index == 2 and new.history[-1]["fired"] == []


def test_two_months_chain(sim):
    p2, _ = plan_io.next_month(make_plan(), sim["C2"][1])
    p3, _ = plan_io.next_month(p2, sim["C4"][1])
    assert p3.month_index == 3 and [h["month"] for h in p3.history] == [1, 2]


def test_json_roundtrip_after_next_month(sim):
    new, _ = plan_io.next_month(make_plan(), sim["C4"][1])
    text = plan_io.to_json(new)
    json.loads(text)                                     # 순수 JSON
    back = plan_io.from_json(text)
    assert back == new
    assert plan_io.from_json(text.encode("utf-8")) == new


def test_roundtrip_default_plan():
    p = make_plan()
    assert plan_io.from_json(plan_io.to_json(p)) == p


@pytest.mark.parametrize("bad", ["", "   ", "{깨진", "[1, 2]", "42", '{"foo": 1}', b"\xff\xfe\x00",
                                 '{"format": "other-app", "store": {}, "media": [], "answers": {}, "budget_plan": {}, "history": []}'])
def test_broken_or_foreign_files_raise_friendly_error(bad):
    with pytest.raises(PlanError) as e:
        plan_io.from_json(bad)
    msg = str(e.value)
    assert "계획 파일" in msg and "Traceback" not in msg


def test_wrong_version_and_shapes():
    good = json.loads(plan_io.to_json(make_plan()))
    for patch in ({"version": "1.0.0"}, {"media": "meta"}, {"answers": []}, {"month_index": 0}, {"month_index": "2"}):
        with pytest.raises(PlanError):
            plan_io.from_json(json.dumps({**good, **patch}))
    del good["history"]
    with pytest.raises(PlanError) as e:
        plan_io.from_json(json.dumps(good))
    assert "history" in str(e.value)


def test_numpy_values_are_saved():
    import numpy as np
    p = make_plan()
    p.answers["x"] = np.float64(1.5)
    assert plan_io.from_json(plan_io.to_json(p)).answers["x"] == 1.5


def _fired(*changes_per_rule):
    return [diagnose.Finding(id="r%d" % i, title="t", funnel="f", status="fired", changes=list(cs))
            for i, cs in enumerate(changes_per_rule)]


def test_noop_change_is_skipped():
    plan = make_plan()
    ch = diagnose.Change("meta.adset.placements", "노출 위치", "meta",
                         "어드밴티지+ 노출 위치, Audience Network 제외", "n", "r0")
    new, diff = plan_io.next_month(plan, _fired([ch]))
    assert diff.empty
    assert "meta.adset.placements" not in new.answers
    assert "meta.adset.placements" not in new.answers["_changed"]


def test_falls_back_to_next_rule_when_first_is_noop():
    plan = make_plan()
    same = diagnose.Change("meta.adset.placements", "노출 위치", "meta",
                           "어드밴티지+ 노출 위치, Audience Network 제외", "첫 규칙", "r0")
    other = diagnose.Change("meta.adset.placements", "노출 위치", "meta",
                            "수동 노출 위치: Instagram 피드·스토리·릴스", "둘째 규칙", "r1")
    new, diff = plan_io.next_month(plan, _fired([same], [other]))
    assert new.answers["meta.adset.placements"] == other.new
    row = diff.iloc[0]
    assert row["after"] == other.new and row["note"] == "둘째 규칙"


def _plc(plan):
    return plan.answers.get("meta.adset.placements")


def test_c2_repeated_does_not_flip_placements(sim):
    p = make_plan()
    p2, d1 = plan_io.next_month(p, sim["C2"][1])
    assert "meta.adset.placements" in set(d1["field_id"])
    after1 = _plc(p2)
    p3, d2 = plan_io.next_month(p2, sim["C2"][1])
    p4, d3 = plan_io.next_month(p3, sim["C2"][1])
    for d in (d2, d3):
        assert "meta.adset.placements" not in set(d["field_id"])
    assert _plc(p3) == after1 and _plc(p4) == after1 and "Instagram" in after1


def test_c2_c4_alternating_chain_is_stable(sim):
    p = make_plan()
    values = []
    for case in ("C2", "C4", "C2", "C4", "C2"):
        p, diff = plan_io.next_month(p, sim[case][1])
        values.append(_plc(p))
        if len(values) > 1:
            assert "meta.adset.placements" not in set(diff["field_id"])
    assert len(set(values)) == 1 and "Instagram" in values[0]


def test_old_history_without_new_data_still_loads(sim):
    p2, _ = plan_io.next_month(make_plan(), sim["C2"][1])
    back = plan_io.from_json(plan_io.to_json(p2))
    p3, diff = plan_io.next_month(back, sim["C2"][1])
    assert diff.empty


def test_measured_daily_budget_may_return_to_earlier_value():
    p = make_plan()
    p.budget_plan["naver_daily"] = 10000
    for want in (5000, 8000, 5000):
        ch = diagnose.Change("naver.campaign.daily_budget", "일 예산", "naver", want, "n", "rule.search_cap")
        p, diff = plan_io.next_month(p, _fired([ch]))
        assert list(diff["field_id"]) == ["naver.campaign.daily_budget"], want
        assert p.budget_plan["naver_daily"] == want
        assert p.answers["naver.campaign.daily_budget"] != ""


def test_measured_set_from_rule_value_may_return():
    pairs = plan_io._measured_pairs()
    rid = next(r for r, f in pairs if f == "meta.adset.cost_goal")
    p = make_plan()
    for want in (300, 450, 300):
        ch = diagnose.Change("meta.adset.cost_goal", "목표 비용", "meta", want, "n", rid)
        p, diff = plan_io.next_month(p, _fired([ch]))
        assert list(diff["field_id"]) == ["meta.adset.cost_goal"], want
    ch = diagnose.Change("meta.adset.cost_goal", "목표 비용", "meta", 300, "n", rid)
    _, diff = plan_io.next_month(p, _fired([ch]))
    assert diff.empty                                    # 같은 값이면 그대로 건너뜀


def test_budget_keys_are_real_fields():
    """일 예산·입찰 칸 id가 칸 사양에 실제로 있어야 다음 달 예산 계획도 같이 맞춰진다."""
    from v2.engine import plan_io, specs
    assert set(plan_io.BUDGET_KEYS) <= set(specs.all_fields())
