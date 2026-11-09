"""MVP 7d 3단계: 광고 세팅값 (ad_setup.build_settings) — 코치 숫자와 같은지, 단계·카드·출처, 문구 검사, 계획 파일 저장."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine import NaverCurve  # noqa: E402
from src.engine import ad_setup as AS  # noqa: E402
from src.engine import coach as C  # noqa: E402
from src.engine import defaults as D  # noqa: E402
from src.engine import guide as G  # noqa: E402
from src.engine import session_schema as SS  # noqa: E402
from src.engine import setup_rag as SR  # noqa: E402
from src.engine.montecarlo import one_month  # noqa: E402


def _curve():
    df = pd.DataFrame({"bid": [100, 300, 600, 1000], "cost": [20_000, 60_000, 120_000, 200_000],
                       "clicks": [80, 180, 290, 400], "impressions": [0] * 4})
    return NaverCurve({"원두커피": df})


def _answer(price=20_000, profit=7_000, budget=300_000, curve="x"):
    return C.solve(C.CoachInputs(price, profit, budget, "원두커피"), _curve() if curve else None, C.repurchase_source("매달(정기)"))


def test_settings_match_coach_numbers():
    """시트의 숫자 = 코치 숫자 (하루 예산 = 월 ÷ 30.4, 10원 단위)."""
    a = _answer()
    p = AS.build_settings(a, ["스마트스토어"], keyword="원두커피", month="2611")
    sp = a.split
    assert p.value("naver", "daily_budget") == AS._won(sp.naver_spend / D.DAYS_PER_MONTH)
    assert p.value("naver", "bizmoney") == AS._won(sp.naver_spend)
    assert p.value("meta", "daily_budget") == AS._won(sp.meta.spend / D.DAYS_PER_MONTH)
    assert p.value("naver", "bid") == AS.SHOPPING_MIN_BID                                  # 스마트스토어 = 쇼핑검색 최소 50원
    assert p.value("naver", "campaign_type").startswith("쇼핑검색")
    assert p.value("meta", "objective") == "트래픽"                                       # 스마트스토어만 → 트래픽
    assert p.numbers["naver"] == sp.naver_spend and p.numbers["meta"] == sp.meta.spend


def test_steps_follow_the_manager_order_and_cards_exist():
    p = AS.build_settings(_answer(), ["스마트스토어"], keyword="원두커피", powerlink=True)
    naver = [s.key for s in p.for_media("naver")]
    assert naver[0] == "account" and naver[-1] == "tracking"
    assert naver.index("campaign") < naver.index("adgroup") < naver.index("creative") < naver.index("pl_campaign") < naver.index("pl_keywords")
    assert [s.key for s in p.for_media("meta")] == ["objective", "budget", "audience", "placement", "creative", "measure"]
    for s in p.steps:
        assert s.cards and all(SR.by_id(c) is not None for c in s.cards), s.key       # 근거 카드가 실제로 있음
        assert all(it.source in (AS.CALC, AS.OWNER, AS.DRAFT) for it in s.items)
    # 파워링크 추가: 확장 검색·ADVoost Max 첫 달 끄기, 제외 키워드 초안, 하루 예산은 반씩
    assert p.value("naver", "pl_exp_search") is False and p.value("naver", "pl_advoost_max") is False
    assert "레시피" in p.value("naver", "pl_negatives")
    assert p.value("naver", "daily_budget") + p.value("naver", "pl_daily_budget") == AS._won(p.numbers["naver"] / D.DAYS_PER_MONTH)


def test_media_choice_and_zero_budget():
    a = _answer()
    assert {s.media for s in AS.build_settings(a, ["스마트스토어"], media="naver").steps} == {"naver"}
    assert {s.media for s in AS.build_settings(a, ["스마트스토어"], media="meta").steps} == {"meta"}
    only_meta = _answer(curve=None)                 # 검색어 없음 → 모두 메타
    assert AS.build_settings(only_meta, ["스마트스토어"]).for_media("naver") == []


def test_one_smartstore_rule():
    assert AS.is_smartstore(["스마트스토어"]) and AS.is_smartstore([]) and not AS.is_smartstore(["자사몰"])
    assert AS.own_site(["자사몰", "스마트스토어"]) and not AS.own_site(["스마트스토어"]) and not AS.own_site([])
    # 자사몰만 → 파워링크 기본, 메타는 픽셀이 있으면 판매
    a = _answer()
    p = AS.build_settings(a, ["자사몰"], pixel_ready=True, keyword="원두커피")
    assert p.value("naver", "campaign_type").startswith("파워링크") and p.value("meta", "objective") == "판매"
    assert G.meta_plan(142_000, 100_000, False, ["스마트스토어"], 1_300)["objective"] == "트래픽"


def _example(kw, price, profit, budget):
    from src.engine import naver_source as ns
    est = ns.bid_estimate(kw, device=D.NAVER_DEVICE, online=False)          # 저장된 예시 예상 실적 (네트워크 안 씀)
    return C.solve(C.CoachInputs(price, profit, budget, kw), NaverCurve({kw: est}), C.repurchase_source("매달(정기)"))


@pytest.mark.parametrize("kw,price,profit,budget", [("원두커피", 20_000, 7_000, 300_000), ("프로틴쉐이크", 79_000, 39_500, 500_000)])
def test_meta_cpa_is_meta_only(kw, price, profit, budget):
    """A3 결정 (예시 1·2): 메타 손님 1명 비용 = 메타 예산 ÷ 메타 새 손님 (코치 100번 평균 새 손님의 메타 몫), 전체 CPA와 다름."""
    a = _example(kw, price, profit, budget)
    sp = a.split
    assert sp.naver_spend > 0 and sp.meta.spend > 0
    m = one_month([sp.channels[-1]], [sp.meta.spend], a.params)["new"]
    n = one_month(sp.channels[:1], [sp.naver_spend], a.params)["new"]
    assert one_month(sp.channels, sp.spends, a.params)["new"] == pytest.approx(m + n)        # 엔진 새 손님은 매체별로 더해짐
    meta_new = a.prediction["new"] * m / (m + n)
    cpa = AS.meta_cpa(sp, a.params, a.prediction["new"])
    assert cpa == pytest.approx(sp.meta.spend / meta_new)
    assert abs(cpa - a.budget / a.prediction["new"]) > 1.0     # 섞인 전체 CPA와 다름 (원두는 배분이 두 매체 한계 비용을 맞춰 0.2%만 다름)
    p = AS.build_settings(a, ["자사몰"], pixel_ready=True, keyword=kw)
    assert p.meta_cpa == pytest.approx(cpa) and p.numbers["cpa"] == pytest.approx(cpa)
    assert p.meta_plan["recommended_daily"] == pytest.approx(cpa * G.DAILY_BUDGET_X)          # 판매 목표: 결과 비용 × 10


def test_meta_zero_hides_meta_lines():
    a = _answer()
    zero = C.split_budget(10_000, _curve(), 1_300.0, a.params)                    # 작은 예산 → 모두 네이버
    assert zero.meta.spend == 0 and AS.meta_cpa(zero, a.params, 1.0) is None


def test_owner_values_override_and_save_to_plan():
    a = _answer()
    p = AS.build_settings(a, ["스마트스토어"], keyword="원두커피", owner={"naver.region_exclude": "제주", "meta.age": "25"})
    it = p.item("naver", "region_exclude")
    assert it.value == "제주" and it.source == AS.OWNER
    s = p.to_settings()
    assert s["naver.region_exclude"] == "제주" and all(isinstance(k, str) for k in s)
    plan = SS.Plan(inputs={}, prediction={}, started=None, settings={**s, "_edited": ["naver.region_exclude"]})
    back = SS.Plan.from_json(plan.to_json())                                               # 계획 파일 검사를 통과
    assert back.settings["naver.region_exclude"] == "제주" and back.settings["_edited"] == ["naver.region_exclude"]


def test_rows_for_sheet():
    rows = AS.build_settings(_answer(), ["스마트스토어"], keyword="원두커피").rows()
    assert rows and set(rows[0]) == {"매체", "단계", "항목", "값", "출처", "메모", "찾을 곳"}
    assert any(r["항목"] == "하루 예산 (원)" and r["출처"].startswith("🧮") for r in rows)


def test_no_ad_warning_and_bid_warning():
    a = _answer()                                      # 원두 예시: 광고 안 함 추천
    p = AS.build_settings(a, ["스마트스토어"], keyword="원두커피", powerlink=True)
    assert p.no_ad == (a.default_pick == "none")
    if p.no_ad:
        assert any("광고 안 함" in w for w in p.warnings)


@pytest.mark.parametrize("text,kind,expect", [
    ("수제 마카롱 6구 선물세트 당일제작", "naver_title", "15자"),
    ("짧음", "naver_desc", "20~45자"),
    ("국내 최고 마카롱", "naver_title", "최상급"),
    ("오늘만 9,900원 특가로 만나 보세요 지금 바로", "naver_desc", "가격"),
    ("신상품 입고!!!!!! 지금 바로 확인하세요 정말로", "naver_desc", "특수문자"),
    ("당일 제작 선물 포장", "naver_promo1", "10자"),
])
def test_copy_checks(text, kind, expect):
    assert any(expect in m for m in AS.check_copy(text, kind))


def test_copy_check_passes_clean_text():
    assert AS.check_copy("수제 마카롱 6구", "naver_title") == []
    assert AS.check_copy("매일 아침 굽는 수제 마카롱, 선물 포장해 드려요", "naver_desc") == []


def test_draft_copy_without_key_uses_only_given_words():
    d = AS.draft_copy("수제 마카롱 6구", "당일 제작", "선물 포장")
    assert len(d["naver_title"]) <= AS.NAVER_TITLE_MAX
    assert AS.NAVER_DESC_RANGE[0] <= len(d["naver_desc"]) <= AS.NAVER_DESC_RANGE[1]
    assert not any(w in " ".join(d.values()) for w in ("최고", "1위", "100%"))


class FakeClient:
    def __init__(self, payload):
        self.payload, self.sent = payload, None
        self.messages = self

    def create(self, **kw):
        self.sent = kw
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text=json.dumps(self.payload, ensure_ascii=False))])


def test_answer_remembers_six_turns_and_gets_settings():
    hist = []
    for i in range(10):
        hist += [{"role": "user", "content": f"질문 {i} 010-1234-5678"}, {"role": "assistant", "content": f"답 {i}"}]
    client = FakeClient({"answer": "하루 예산은 2,230원이에요.", "card_ids": ["naver-setup-009"]})
    found = SR.find("하루 예산 어디에 넣어?", media="naver")
    p = AS.build_settings(_answer(), ["스마트스토어"], keyword="원두커피")
    SR.answer(client, "하루 예산 어디에 넣어?", found, {"settings": AS.context_lines(p, "naver")}, history=hist)
    msgs = client.sent["messages"]
    assert len(msgs) == SR.HISTORY_TURNS * 2 + 1 and msgs[0]["content"] == "질문 4 [전화번호 지움]"
    assert "광고 세팅값" in msgs[-1]["content"][-1]["text"] and "하루 예산 (원)" in msgs[-1]["content"][-1]["text"]


def test_ai_copy_drafts_and_fallback():
    client = FakeClient({"drafts": [{"naver_title": "수제 마카롱", "naver_desc": "매일 굽는 수제 마카롱, 선물 포장해 드려요",
                                     "meta_text": "x", "meta_headline": "y"}] * 3})
    assert len(SR.draft_copy(client, "수제 마카롱", "매일 굽기", "선물 포장")) == 3
    with pytest.raises(Exception):
        SR.draft_copy(FakeClient({"drafts": []}), "x")


def test_stuck_searches_step_cards_first():
    found = SR.find_in("어떻게 해?", ["naver-setup-017"], media="naver")
    assert found == [] or found[0][0].id == "naver-setup-017" or found[0][1] >= SR.MIN_SCORE
    found = SR.find_in("지역 설정 어디서 해?", ["naver-setup-017", "naver-setup-011"], media="naver")
    assert found and found[0][0].id == "naver-setup-017"


def test_screen_keeps_only_owner_edits():
    """화면: 사장님이 고친 칸만 덮어쓰고, 안 고친 칸은 코치 숫자를 따라감 (app/setup_view.settings_plan)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
    import setup_view as V
    a = _answer()
    ans = {"answer": a, "kw": "원두커피", "split": a.split}
    ss = {"setup_media": "both"}
    base = V.settings_plan(ans, ss, ["스마트스토어"])
    wk = V._wkey("naver", "region_exclude")
    ss["_set_defaults"] = {wk: base.value("naver", "region_exclude"), V._wkey("naver", "daily_budget"): 999}
    ss[wk] = "제주"                                  # 사장님이 고침
    ss[V._wkey("naver", "daily_budget")] = 999       # 예전 기본값 그대로 (안 고침) → 코치 숫자를 따라감
    p = V.settings_plan(ans, ss, ["스마트스토어"])
    assert p.value("naver", "region_exclude") == "제주" and p.item("naver", "region_exclude").source == AS.OWNER
    assert p.value("naver", "daily_budget") == base.value("naver", "daily_budget")
    V.restore_settings(ss, {"naver.bid": 80, "meta.age": "25", "_edited": ["naver.bid"]})
    assert ss[V._wkey("naver", "bid")] == 80 and V._wkey("meta", "age") not in ss


@pytest.mark.parametrize("media,kw", [("meta", None), ("naver", None), ("naver", "pl")])
def test_use_draft_fills_fields_via_callback(media, kw):
    """D1: '이 초안 쓰기'는 버튼 콜백에서 값을 넣고(칸을 그리기 전), 그 값이 칸과 세팅값 시트에 들어감."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
    import setup_view as V
    a = _answer()
    ans = {"answer": a, "kw": "원두커피", "split": a.split}
    ss = {"setup_media": "both", "setup_powerlink": kw == "pl"}
    plan = V.settings_plan(ans, ss, ["스마트스토어"])
    key = {"meta": "creative", "naver": "pl_creative" if kw == "pl" else "creative"}[media]
    step = next(s for s in plan.for_media(media) if s.key == key)
    d = {"naver_title": "수제 마카롱 6구", "naver_desc": "매일 굽는 수제 마카롱, 선물 포장해 드려요",
         "meta_text": "매일 굽는 수제 마카롱. 선물 포장해 드려요. 지금 스토어에서 확인해 보세요.", "meta_headline": "수제 마카롱 6구"}
    # 칸을 한 번 그린 상태 (기본값 기억) → 콜백 → 다음 실행
    ss["_set_defaults"] = {}
    for it in step.items:
        wk = V._wkey(media, it.key)
        ss[wk] = V._to_widget(it.value)
        ss["_set_defaults"][wk] = ss[wk]
    V.use_draft(ss, step, d)
    after = V.settings_plan(ans, ss, ["스마트스토어"])
    if media == "meta":
        assert after.value("meta", "headline") == d["meta_headline"] and after.value("meta", "primary_text") == d["meta_text"]
        assert after.item("meta", "headline").source == AS.DRAFT
    elif kw == "pl":
        assert after.value("naver", "pl_title") == d["naver_title"] and after.value("naver", "pl_description") == d["naver_desc"]
    else:
        assert after.value("naver", "promo1") == d["naver_title"][:AS.NAVER_PROMO1_MAX]
    rows = after.rows()
    assert any(r["값"] in (d["meta_headline"], d["naver_title"][:AS.NAVER_PROMO1_MAX], d["naver_title"]) for r in rows)
    # 화면 코드가 같은 실행에서 칸 값을 직접 바꾸지 않음 (Streamlit 예외 원인)
    src = (Path(__file__).resolve().parents[1] / "app" / "setup_view.py").read_text(encoding="utf-8")
    assert "on_click=use_draft" in src
