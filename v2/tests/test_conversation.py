"""C 대화 엔진 테스트 (네트워크 없음, 서비스는 가짜)."""
import json
from types import SimpleNamespace

import pandas as pd
import pytest

from v2.engine import chat_parse as cp
from v2.engine import conversation as cv
from v2.engine import copywriter, intake, planner


# ── 가짜 서비스 ──
def fake_report(recommended=("답례품쿠키", "쿠키선물세트")):
    kw = pd.DataFrame({"keyword": list(recommended), "total_qc": [5000, 3000], "intent": ["선물·답례", "상품"]})
    return SimpleNamespace(recommended=list(recommended), negatives=["만들기"], headline="30대 여성이 많이 찾아요",
                           groups=pd.DataFrame({"intent": ["선물·답례"], "count": [1]}), keywords=kw,
                           audiences={"답례품쿠키": {"female": 0.82, "ages": {"20": 0.2, "30": 0.48}}})


class Fake:
    def __init__(self):
        self.calls = []
        self.market_report = fake_report()
        self.help_answer = SimpleNamespace(kind="help", text="종료일은 광고가 끝나는 날이에요.", field_id="meta.adset.end_date",
                                           sources=[{"title": "메타 도움말", "url": "https://example.com", "check": "✅"}],
                                           stream=None)

    def services(self):
        def market(seeds):
            self.calls.append(("market", list(seeds)))
            return self.market_report

        def plan(store, mkt, objective, days):
            self.calls.append(("plan", store["budget"], objective, days, mkt))
            kw = pd.DataFrame(mkt["rows"]) if isinstance(mkt, dict) and mkt.get("rows") else None
            return planner.plan_budget(store["budget"], kw, objective=objective, days=days)

        def help_(q, step, ctx):
            self.calls.append(("help", q, step, ctx))
            return self.help_answer

        def copies(product, strengths):
            self.calls.append(("copies", product, strengths))
            return {"meta": [{"headline": "촉촉한 구움과자", "text": "버터 향 가득"},
                             {"headline": "선물하기 좋아요", "text": "예쁜 포장"}],
                    "naver": [{"headline": "수제 구움과자", "text": "정성껏 만든 구움과자를 만나 보세요"},
                              {"headline": "답례품 쿠키", "text": "소량 주문도 가능한 수제 쿠키예요"}]}
        return cv.Services(market=market, plan=plan, help=help_, questions=intake.questions, copies=copies)


@pytest.fixture
def fk():
    return Fake()


@pytest.fixture
def sv(fk):
    return fk.services()


def say(st, sv, *texts):
    for t in texts:
        st = cv.handle(st, t, sv)
    return st


def last(st):
    return cv.last_turn(st)


def kinds(st):
    return [t["kind"] for t in st["turns"]]


# ── chat_parse ──
@pytest.mark.parametrize("text,want", [
    ("2만 6천원", 26000), ("26,000", 26000), ("26000원", 26000), ("3만", 30000), ("30만원", 300000),
    ("1.5만", 15000), ("삼만", 30000), ("만원", 10000), ("5천원", 5000), ("1억2천만", 120000000),
    ("한 달에 30만원 정도", 300000), ("이만 육천원", 26000), (30000, 30000),
    ("", None), ("abc", None), ("30%", None), ("오늘", None), (None, None)])
def test_parse_money(text, want):
    assert cp.parse_money(text) == want


def test_parse_choice():
    yn = ["있어요", "없어요"]
    assert cp.parse_choice("네", yn) == "있어요"
    assert cp.parse_choice("아니요", yn) == "없어요"
    assert cp.parse_choice("2번", yn) == "없어요"
    days = ["7일", "14일", "30일"]
    assert cp.parse_choice("14", days) == "14일"
    assert cp.parse_choice("1", days) == "7일"
    obj = ["스토어 방문 늘리기", "가게 알리기"]
    assert cp.parse_choice("방문", obj) == "스토어 방문 늘리기"
    assert cp.parse_choice("알리기", obj) == "가게 알리기"
    assert cp.parse_choice("네", obj) is None        # 예/아니요로 갈리지 않는 선택지
    assert cp.parse_choice("모르겠어요", obj) is None
    assert cp.parse_choice("5", obj) is None
    assert cp.parse_choice("충전했어요", ["충전했어요", "아직이에요"]) == "충전했어요"


def test_parse_words_url_slug():
    assert cp.parse_words("휘낭시에, 쿠키") == ["휘낭시에", "쿠키"]
    assert cp.parse_words("수제 쿠키") == ["수제", "쿠키"]
    assert cp.parse_words("") == []
    assert cp.is_url("https://smartstore.naver.com/a/products/1") and cp.is_url("smartstore.naver.com/a")
    assert not cp.is_url("안녕하세요") and not cp.is_url("a b.com")
    assert cp.suggest_slug("소연베이크") == "soyeonbake"
    assert cp.suggest_slug("!!") == "item" and cp.suggest_slug("") == "item"
    assert cp.suggest_slug("Soyeon Cake 2") == "soyeoncake2"


def test_looks_like_question():
    assert cp.looks_like_question("종료일 안 넣으면 어떻게 돼?")
    assert cp.looks_like_question("하루 얼마 써야 해요")
    for answer in ("네", "2만 6천원", "1", "스토어 방문 늘리기", "휘낭시에, 쿠키"):
        assert not cp.looks_like_question(answer)


@pytest.mark.parametrize("text", ["네 맞아요", "네네", "네, 맞아요", "네 좋아요", "응 맞아", "예 그렇게 해주세요", "네 이대로요",
                                  "네 맞습니다", "그렇습니다", "네", "고칠 거 없어요"])
def test_yes_variants(text):
    assert cp.parse_yes_no(text) is True


@pytest.mark.parametrize("text", ["그래도 아니요", "아니요", "아뇨 고칠래요", "고칠래요", "싫어요", "no"])
def test_no_variants(text):
    assert cp.parse_yes_no(text) is False


def test_yes_no_unknown():
    assert cp.parse_yes_no("") is None and cp.parse_yes_no("글쎄요") is None


@pytest.mark.parametrize("name", ["언제나베이커리", "어느새쿠키", "어떤하루", "이게진짜쿠키", "혹시베이크", "몇시베이크", "뭐든"])
def test_names_are_not_questions(name):
    assert not cp.looks_like_question(name)
    assert not cp.looks_like_question(name, strict=True)


def test_name_step_accepts_question_like_names(sv, fk):
    st = cv.start(["meta", "naver"])
    st = cv.handle(st, "언제나베이커리", sv)
    assert st["store"]["name"] == "언제나베이커리" and st["step"] == "product"
    st = cv.handle(st, "어느새쿠키", sv)
    assert st["store"]["product"] == "어느새쿠키" and not any(c[0] == "help" for c in fk.calls)


# ── 가게 질문 ──
def test_start_first_prompt(sv):
    st = cv.start(["meta", "naver"])
    assert st["phase"] == "store" and last(st).role == "bot" and "가게 이름" in last(st).text
    with pytest.raises(ValueError):
        cv.start([])
    with pytest.raises(ValueError):
        cv.start(["tiktok"])


def test_store_flow_and_echo(sv):
    st = cv.start(["meta", "naver"])
    st = say(st, sv, "소연베이크", "수제 구움과자", "2만 6천원")
    assert any("26,000원으로 이해했어요" in t["text"] for t in st["turns"])
    st = say(st, sv, "8000", "30만원", "스마트스토어", "soyeonbake")
    assert st["phase"] == "confirm"
    card = last(st)
    assert card.kind == "confirm_card" and card.chips == ["맞아요", "고칠래요"]
    labels = {i["label"]: i["value"] for i in card.data["items"]}
    assert labels["판매가"] == "26,000원" and labels["한 달 광고비"] == "300,000원"
    assert "31%" in labels["1개 팔면 남는 돈"]
    assert cv.to_store(st)["margin_per_order"] == 8000


def test_validation_gives_fix_and_stays(sv):
    st = cv.start(["meta"])
    st = say(st, sv, "소연베이크", "쿠키")
    for bad, step in (("글쎄요", "price"),):
        st2 = cv.handle(st, bad, sv)
        assert last(st2).kind == "error" and st2["step"] == step and "예:" in last(st2).text and last(st2).chips
    st = say(st, sv, "26000")
    st2 = cv.handle(st, "3만", sv)                       # 남는 돈 > 판매가
    assert last(st2).kind == "error" and "판매가" in last(st2).text and st2["step"] == "margin"
    st3 = cv.handle(st, "30%", sv)                       # 퍼센트로 말하기
    assert cv.to_store(st3)["margin_per_order"] == 7800 and st3["step"] == "budget"
    st = say(st, sv, "8000")
    st2 = cv.handle(st, "30", sv)                        # 단위 빠진 광고비
    assert last(st2).kind == "error" and "30만원" in last(st2).text and st2["step"] == "budget"
    st = say(st, sv, "30만원")
    st2 = cv.handle(st, "글쎄요", sv)
    assert last(st2).kind == "error" and st2["step"] == "channel" and cv.CHANNELS[0] in last(st2).chips
    st = say(st, sv, "카페24")                           # 별칭
    assert st["store"]["store_type"] == "own"
    st2 = cv.handle(st, "소연", sv)                      # 한글 영문 이름 → 영문으로 바꿔 줌
    assert st2["store"]["slug"] == "soyeon" and st2["phase"] == "confirm"
    st2 = cv.handle(st, "Soyeon-Bake", sv)
    assert st2["store"]["slug"] == "soyeon_bake"
    assert any("바꿔서" in t["text"] for t in st2["turns"])


def test_input_state_is_not_mutated(sv):
    st = cv.start(["meta"])
    before = json.dumps(st, sort_keys=True)
    cv.handle(st, "소연베이크", sv)
    assert json.dumps(st, sort_keys=True) == before


def test_empty_text_reasks(sv):
    st = cv.handle(cv.start(["meta"]), "   ", sv)
    assert last(st).text.startswith("가게 이름") or "가게 이름" in last(st).text
    assert any(t["kind"] == "error" for t in st["turns"])


# ── 확인 카드 · 고치기 ──
def test_confirm_fix_flow(sv, fk):
    st = cv.demo_state(sv)
    assert last(st).kind == "confirm_card"
    st = cv.choose(st, "고칠래요", sv)
    assert st["step"] == "fix" and "판매가" in last(st).chips
    st = cv.choose(st, "판매가", sv)
    assert st["phase"] == "store" and st["step"] == "price" and st["editing"]
    st = say(st, sv, "28,000원")
    assert last(st).kind == "confirm_card" and cv.to_store(st)["price"] == 28000
    st = cv.choose(st, "맞아요", sv)
    assert st["phase"] == "market"


def test_confirm_unclear_answer(sv):
    st = cv.demo_state(sv)
    st = cv.handle(st, "글쎄요", sv)
    assert last(st).kind == "error" and last(st).chips == ["맞아요", "고칠래요"] and st["phase"] == "confirm"


def test_demo_state_values(sv):
    st = cv.demo_state(sv)
    s = cv.to_store(st)
    assert (s["name"], s["product"], s["price"], s["margin_per_order"], s["budget"], s["store_type"], s["product_slug"]) == \
           ("소연베이크", "수제 구움과자", 26000, 8000, 300000, "smartstore", "soyeonbake")
    json.dumps(st)


# ── 내 손님 · 예산 ──
def run_to_budget(st, sv):
    st = cv.choose(st, "맞아요", sv)
    st = cv.choose(st, "구움과자", sv)
    assert st["step"] == "pick" and last(st).kind == "market_card"
    return cv.choose(st, "이대로 쓸게요", sv)


def test_audience_hint_matches_headline(sv):
    from v2.engine import market as mk
    aud = {"female": 0.8, "ages": {"20": 0.2, "30": 0.3, "40": 0.45}, "index": {"20": 1.0, "30": 1.82, "40": 1.1},
           "monthly": {}, "peak_month": None}
    rep = fake_report()
    rep.audiences = {"답례품쿠키": aud}
    rep.headline = mk.headline("답례품쿠키", aud)
    hint = cv._audience_hint(rep)
    assert "30대 여성" in rep.headline and hint == "30대 여성 중심"


def test_market_and_budget(sv, fk):
    st = cv.demo_state(sv)
    st = cv.choose(st, "맞아요", sv)
    assert st["phase"] == "market" and last(st).chips and "구움과자" in last(st).chips
    st = cv.choose(st, "구움과자", sv)
    card = last(st)
    assert card.kind == "market_card" and "답례품쿠키" in card.data["recommended"] and card.data["audience_hint"] == "30대 여성 중심"
    assert ("market", ["구움과자"]) in fk.calls
    st = cv.choose(st, "이대로 쓸게요", sv)
    assert st["phase"] == "budget" and st["step"] == "objective"
    st = cv.choose(st, "스토어 방문 늘리기", sv)
    assert st["step"] == "days" and "14일" in last(st).chips
    st = cv.choose(st, "14일", sv)
    card = last(st)
    assert card.kind == "budget_card" and card.chips == ["이대로 할게요", "목표·기간 다시 고를래요"]
    plan = planner.plan_budget(300000, pd.DataFrame(st["market"]["rows"]), "트래픽", 14)
    assert card.data["plan"]["naver_month"] == plan.naver_month and card.data["plan"]["meta_daily"] == plan.meta_daily
    assert "{:,}".format(plan.naver_month) in card.text
    st = cv.choose(st, "이대로 할게요", sv)
    assert st["phase"] == "ask"
    # 목표·기간은 다시 묻지 않는다
    assert cv.OBJECTIVE_KEY in st["answers"] and st["step"] not in (cv.OBJECTIVE_KEY, cv.END_DATE_KEY)
    assert st["answers"]["meta.adset.end_date"] == "14일"
    json.dumps(st)


def test_market_words_typed_and_retry(sv, fk):
    st = cv.choose(cv.demo_state(sv), "맞아요", sv)
    st = say(st, sv, "휘낭시에, 쿠키")
    assert ("market", ["휘낭시에", "쿠키"]) in fk.calls
    st = cv.choose(st, "다른 단어로 찾을래요", sv)
    assert st["step"] == "seeds"
    fk.market_report = None
    st = say(st, sv, "마들렌")
    assert st["step"] == "fail" and last(st).kind == "error" and "자료 없이 넘어갈래요" in last(st).chips
    st = cv.choose(st, "자료 없이 넘어갈래요", sv)
    assert st["phase"] == "budget" and st["market"]["picked"] == ["마들렌"]


def test_objective_invalid(sv):
    st = run_to_budget(cv.demo_state(sv), sv)
    st2 = cv.handle(st, "글쎄요", sv)
    assert last(st2).kind == "error" and st2["step"] == "objective" and "스토어 방문 늘리기" in last(st2).chips
    st = cv.handle(st, "가게 알리기", sv)
    st2 = cv.handle(st, "백년", sv)
    assert last(st2).kind == "error" and st2["step"] == "days"
    st = cv.handle(st, "2주", sv)
    assert st["days"] == 14 and st["objective"] == "인지도"


def test_naver_only_skips_objective(sv):
    st = cv.start(["naver"])
    st = say(st, sv, "소연베이크", "쿠키", "2만6천", "8천", "20만", "스토어", "soyeon", "맞아요", "쿠키", "이대로 쓸게요")
    assert st["phase"] == "budget" and st["step"] == "ok" and last(st).kind == "budget_card"
    assert st["objective"] == "트래픽"


# ── 칸 질문 ──
def to_ask(sv):
    st = run_to_budget(cv.demo_state(sv), sv)
    st = cv.choose(st, "스토어 방문 늘리기", sv)
    st = cv.choose(st, "14일", sv)
    return cv.choose(st, "이대로 할게요", sv)


def test_full_flow_to_done(sv, fk):
    st = to_ask(sv)
    guard = 0
    while st["phase"] == "ask" and guard < 40:
        guard += 1
        q = next(x for x in st["qs"] if x["id"] == st["step"])
        t = last(st)
        assert t.data.get("qid") == q["id"]
        if q["kind"] == "llm":
            st = cv.handle(st, "버터 향이 진해요", sv)
            assert st["sub"] == "pick" and len(last(st).chips) == 2
            st = cv.choose(st, last(st).chips[0], sv)
        elif q["input"] == "choice":
            st = cv.choose(st, q["options"][-1] if q["id"] == "meta.pre.fb_page" else q["options"][0], sv)
        elif q["input"] == "url":
            st = cv.handle(st, "https://smartstore.naver.com/soyeonbake/products/1", sv)
        else:
            st = cv.handle(st, "soyeonbake_official", sv)
    assert st["phase"] == "done" and last(st).kind == "done"
    ans = cv.to_answers(st)
    assert ans["meta.ad.website_url"].startswith("https://") and ans["meta.pre.ig_account"] == "soyeonbake_official"
    assert ans["meta.creative.copy"]["headline"] == "촉촉한 구움과자"
    assert ans["naver.ad.copy"]["headline"] == "수제 구움과자"          # 네이버 칸은 네이버 길이의 문구
    assert "naver.ad.landing_url" not in ans                              # 메타와 같은 주소를 쓰는 칸은 다시 묻지 않음
    # 시트가 이 답으로 만들어진다
    ctx = intake.SetupContext(product="수제 구움과자", product_slug="soyeonbake", store_type="smartstore", month="11월",
                              media=["meta", "naver"])
    sheet = intake.build_sheet(ans, ctx)
    assert len(sheet) > 20
    assert "아직 입력 전이에요" not in sheet[sheet.field_id == "meta.ad.website_url"].value.iloc[0]
    json.dumps(st)


def test_precheck_negative_adds_why(sv):
    st = to_ask(sv)
    assert st["step"] == "meta.pre.fb_page"
    st = cv.handle(st, "없어요", sv)
    assert any(t["text"].startswith("참고:") for t in st["turns"])


def test_choice_error_keeps_step_with_options(sv):
    st = to_ask(sv)
    st2 = cv.handle(st, "글쎄", sv)
    assert last(st2).kind == "error" and st2["step"] == st["step"] and last(st2).chips == ["있어요", "없어요"]
    assert cv.handle(st, "네", sv)["answers"]["meta.pre.fb_page"] == "있어요"


def test_bad_url_error_with_example(sv):
    st = to_ask(sv)
    while st["step"] != "meta.ad.website_url":
        st = cv.choose(st, next(x for x in st["qs"] if x["id"] == st["step"]).get("options", ["x"])[0], sv) \
            if next(x for x in st["qs"] if x["id"] == st["step"])["input"] == "choice" else cv.handle(st, "x", sv)
    st2 = cv.handle(st, "상품 페이지요", sv)
    assert last(st2).kind == "error" and "https://" in last(st2).text and st2["step"] == "meta.ad.website_url"
    st2 = cv.choose(st, "나중에 입력할게요", sv)
    assert st2["answers"]["meta.ad.website_url"] == ""


def test_skip_rest(sv):
    st = to_ask(sv)
    st = cv.choose(st, cv.SKIP_REST_CHIP, sv)
    assert st["phase"] == "done" and last(st).kind == "done"
    ans = cv.to_answers(st)
    assert ans["meta.campaign.special_category"] == "아니요" and ans["meta.adset.end_date"] == "14일"
    assert ans["meta.creative.copy"]["headline"]               # 문구도 만들어 채움


def test_skip_rest_too_early(sv):
    st = cv.skip_rest(cv.demo_state(sv), sv)
    assert st["phase"] == "confirm" and last(st).kind == "confirm_card"
    assert any(t["kind"] == "error" for t in st["turns"])


def test_edit_answer_then_resume(sv):
    st = to_ask(sv)
    st = cv.handle(st, "네", sv)                                  # 첫 질문 답
    first = st["step"]
    st = cv.edit(st, "meta.pre.fb_page")
    assert st["phase"] == "ask" and st["step"] == "meta.pre.fb_page" and st["editing"]
    st = cv.handle(st, "없어요", sv)
    assert st["answers"]["meta.pre.fb_page"] == "없어요" and st["step"] == first and not st["editing"]


def test_edit_budget_and_market(sv):
    st = to_ask(sv)
    st = cv.edit(st, "budget_plan")
    assert st["phase"] == "budget" and st["step"] == "objective"
    st = cv.choose(st, "가게 알리기", sv)
    st = cv.choose(st, "30일", sv)
    assert st["plan"]["objective"] == "인지도" and st["plan"]["days"] == 30
    st = cv.choose(st, "이대로 할게요", sv)
    assert st["phase"] == "ask"
    st = cv.edit(st, "market")
    st = say(st, sv, "마들렌")
    st = cv.choose(st, "이대로 쓸게요", sv)
    assert last(st).kind != "error" and st["phase"] == "ask"      # 목표·기간 그대로 예산을 다시 계산하고 이어 감
    assert any(t["kind"] == "budget_card" for t in st["turns"][-8:])


def test_edit_store_replans(sv, fk):
    st = to_ask(sv)
    st = cv.edit(st, "price")
    st = say(st, sv, "30,000원")
    assert last(st).kind == "confirm_card"
    n = len(fk.calls)
    st = cv.choose(st, "맞아요", sv)
    assert any(c[0] == "plan" for c in fk.calls[n:]) and st["phase"] == "ask"
    assert cv.edit(st, "no.such.field")["turns"][-1]["kind"] == "error"


def test_editable_lists_answers(sv):
    st = to_ask(sv)
    st = cv.handle(st, "네", sv)
    keys = [e["key"] for e in cv.editable(st)]
    assert keys[:7] == ["name", "product", "price", "margin", "budget", "channel", "slug"]
    assert "market" in keys and "budget_plan" in keys and "meta.pre.fb_page" in keys
    assert cv.OBJECTIVE_KEY not in keys


# ── 질문 → 도움말 → 같은 질문 다시 ──
def test_question_at_every_step_gets_help_then_reask(sv, fk):
    st = cv.start(["meta", "naver"])
    q = "이건 왜 물어보는 거예요?"
    st2 = cv.handle(st, q, sv)
    assert [t["kind"] for t in st2["turns"][-2:]] == ["help", "text"]
    assert last(st2).text == last(st).text and st2["step"] == "name"    # 같은 질문을 다시
    assert st2["turns"][-2]["data"]["sources"][0]["check"] == "✅"
    for phase_state in (cv.demo_state(sv), run_to_budget(cv.demo_state(sv), sv), to_ask(sv)):
        before = last(phase_state)
        after = cv.handle(phase_state, "이게 뭐예요?", sv)
        assert after["turns"][-2]["kind"] == "help" and last(after).text == before.text
        assert after["phase"] == phase_state["phase"] and after["step"] == phase_state["step"]
    help_calls = [c for c in fk.calls if c[0] == "help"]
    assert help_calls[-1][2] == "meta.pre.fb_page"          # 지금 칸 id가 전달됨
    assert "store" in help_calls[-1][3] and help_calls[-1][3]["plan"]["budget"] == 300000


def test_chips_are_never_questions(sv, fk):
    st = cv.demo_state(sv)
    n = len(fk.calls)
    cv.choose(st, "고칠래요", sv)
    assert not any(c[0] == "help" for c in fk.calls[n:])


def test_help_failure_does_not_break_chat(sv, fk):
    def boom(*a):
        raise RuntimeError("x")
    sv2 = cv.Services(sv.market, sv.plan, boom, sv.questions, sv.copies)
    st = cv.handle(cv.start(["meta"]), "왜요?", sv2)
    assert st["turns"][-2]["kind"] == "help" and last(st).kind == "text" and st["step"] == "name"


def test_help_stream_side_channel(sv, fk):
    fk.help_answer = SimpleNamespace(kind="llm", text="", field_id=None, sources=[], stream=iter(["안녕", "하세요"]))
    st = cv.handle(cv.start(["meta"]), "광고 계정이 뭐예요?", sv)
    json.dumps(st)                                   # 스트림 객체가 state에 들어가지 않음
    gen = cv.take_stream(st)
    assert "".join(gen) == "안녕하세요" and cv.take_stream(st) is None
    st = cv.set_help_text(st, "안녕하세요")
    assert st["turns"][-2]["text"] == "안녕하세요" and st["turns"][-2]["data"]["stream"] is False


def test_custom_is_question_hook(sv):
    sv2 = cv.Services(sv.market, sv.plan, sv.help, sv.questions, sv.copies, is_question=lambda t: t.startswith("Q:"))
    st = cv.handle(cv.start(["meta"]), "Q: 뭐죠", sv2)
    assert st["turns"][-2]["kind"] == "help"
    st = cv.handle(cv.start(["meta"]), "왜요?", sv2)           # 훅이 아니라고 하면 답으로 처리
    assert st["store"]["name"] == "왜요?"


def test_done_phase_text(sv):
    st = cv.choose(to_ask(sv), cv.SKIP_REST_CHIP, sv)
    st2 = cv.handle(st, "고마워요", sv)
    assert st2["phase"] == "done" and last(st2).kind == "text"


def test_copy_retype_strengths(sv, fk):
    st = to_ask(sv)
    while st["step"] != "meta.creative.copy":
        q = next(x for x in st["qs"] if x["id"] == st["step"])
        st = cv.choose(st, q["options"][0], sv) if q["input"] == "choice" else cv.choose(st, "나중에 입력할게요", sv)
    st = cv.handle(st, "버터 향", sv)
    st = cv.handle(st, "소량 포장도 돼요", sv)           # 라벨이 아니면 새 장점으로 다시 만듦
    assert [c for c in fk.calls if c[0] == "copies"][-1][2] == "소량 포장도 돼요" and st["sub"] == "pick"
    st = cv.handle(st, "2", sv)
    assert st["answers"]["meta.creative.copy"]["headline"] == "선물하기 좋아요"


# ── 실제 서비스 연결 ──
def test_make_services_wiring(monkeypatch):
    monkeypatch.setattr(copywriter, "_read_key", lambda: None)
    sv = cv.make_services(online=False)
    assert callable(sv.market) and sv.is_question("어떻게 해요?") and not sv.is_question("2만원")
    ans = sv.help("종료일이 뭐예요?", "meta.adset.end_date", {})
    assert ans.kind in ("none", "help", "coach", "llm") and hasattr(ans, "text")   # helpdesk가 없어도 깨지지 않음
    qs = sv.questions(["meta", "naver"])
    assert qs and qs[0]["id"] == "meta.pre.fb_page"
    cp_ = sv.copies("수제 구움과자", "버터 향")
    assert cp_["meta"] and cp_["naver"] and set(cp_["naver"][0]) >= {"headline", "text"}
    plan = sv.plan({"budget": 300000, "media": ["meta", "naver"]}, None, "트래픽", 14)
    assert plan.budget == 300000 and plan.naver_month + plan.meta_month == 300000
    only_meta = sv.plan({"budget": 300000, "media": ["meta"]}, {"rows": []}, "트래픽", 14)
    assert only_meta.naver_month == 0
    rep = sv.market(["휘낭시에", "쿠키선물세트", "답례품쿠키"])      # 오프라인(저장된 예시 자료)만, 없으면 None
    assert rep is None or rep.recommended is not None


def test_real_services_smoke_flow(monkeypatch):
    """진짜 planner·intake·copywriter로 처음부터 끝까지 (market만 가짜)."""
    monkeypatch.setattr(copywriter, "_read_key", lambda: None)
    real = cv.make_services(online=False)
    sv = cv.Services(market=lambda seeds: fake_report(), plan=real.plan, help=lambda *a: SimpleNamespace(
        kind="none", text="자료에 없어요", field_id=None, sources=[], stream=None),
        questions=real.questions, copies=real.copies)
    st = cv.demo_state(sv)
    st = cv.choose(st, "맞아요", sv)
    st = cv.choose(st, "구움과자", sv)
    st = cv.choose(st, "이대로 쓸게요", sv)
    st = cv.choose(st, "스토어 방문 늘리기", sv)
    st = cv.choose(st, "14일", sv)
    st = cv.choose(st, "이대로 할게요", sv)
    st = cv.choose(st, cv.SKIP_REST_CHIP, sv)
    assert st["phase"] == "done"
    s = cv.to_store(st)
    ctx = intake.SetupContext(product=s["product"], product_slug=s["product_slug"], store_type=s["store_type"],
                              month=s["month"], media=s["media"], keywords=s["seeds"], negatives=s["negatives"])
    sheet = intake.build_sheet(cv.to_answers(st), ctx)
    assert sheet[sheet.field_id == "meta.campaign.name"].value.iloc[0].startswith("soyeonbake_traffic_")
    json.dumps(st)


def test_not_knowing_is_a_help_request(sv):
    st = cv.handle(cv.demo_state(sv), "잘 모르겠어요", sv)
    assert st["turns"][-2]["kind"] == "help"


def test_market_failure_says_why(sv, fk):
    """검색 실패 말풍선에 이유가 붙는다 (배포 앱에 네이버 키가 없을 때 원인을 바로 알 수 있게)."""
    sv2 = cv.Services(sv.market, sv.plan, sv.help, sv.questions, sv.copies,
                      market_error=lambda: "네이버 키가 없어요")
    st = cv.choose(cv.demo_state(sv2), "맞아요", sv2)
    fk.market_report = None
    st = say(st, sv2, "마들렌")
    assert st["step"] == "fail" and "이유: 네이버 키가 없어요" in last(st).text
    json.dumps(st)
    # 이유를 모르면 예전 문장 그대로
    st = cv.choose(cv.demo_state(sv), "맞아요", sv)
    st = say(st, sv, "마들렌")
    assert "이유:" not in last(st).text
