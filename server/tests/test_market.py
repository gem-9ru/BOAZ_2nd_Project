"""P3 market 테스트: 네트워크 없이 (HTTP 층은 가짜), 시연 저장본(cache_examples)으로 확인."""
import json

import pandas as pd
import pytest

from server.engine import market, naver_api as api

SEEDS = ["휘낭시에", "쿠키선물세트", "답례품쿠키", "디저트선물", "수제쿠키"]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """내 저장본 폴더는 임시 폴더로, 대기는 건너뛰고, 진짜 HTTP는 막는다."""
    monkeypatch.setattr(api, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(api, "_sleep", lambda s: None)
    monkeypatch.setitem(api._STATE, "paused_until", 0.0)
    monkeypatch.setitem(api._STATE, "last_kw", 0.0)
    monkeypatch.setitem(api._STATE, "rate_hits", [])

    class NetworkUsed(BaseException):      # Exception이 아니라서 앱쪽의 넓은 except에도 삼켜지지 않음
        pass

    def boom(*a, **k):
        raise NetworkUsed("테스트에서 네트워크를 쓰면 안 돼요")
    monkeypatch.setattr(api, "_http_ad", boom)
    monkeypatch.setattr(api, "_http_hub", boom)


def no_keys(monkeypatch):
    monkeypatch.setattr(api, "read_keys", lambda names, env_file=None: None)


def fake_keys(monkeypatch):
    monkeypatch.setattr(api, "read_keys", lambda names, env_file=None: {n: "x" for n in names})


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


# ── 저장본 / 오프라인 ──────────────────────────────────────────────────────
def test_offline_uses_cache_examples():
    df = market.keyword_table(SEEDS, online=False)
    assert df is not None and len(df) > 100
    assert {"keyword", "total_qc", "mobile_qc", "pc_qc", "mobile_clicks", "mobile_ctr", "comp", "tier"} <= set(df.columns)
    assert "답례품쿠키" in set(df["keyword"])
    assert df["total_qc"].is_monotonic_decreasing


def test_unknown_seed_offline_returns_none():
    assert market.keyword_table(["존재하지않는검색어zzz"], online=False) is None
    assert market.build(["존재하지않는검색어zzz"], online=False) is None
    assert market.audience("존재하지않는검색어zzz", online=False) is None


def test_missing_keys_online_falls_back_without_crash(monkeypatch):
    no_keys(monkeypatch)
    assert market.keyword_table(["없는말qqq"], online=True) is None      # 키도 저장본도 없음 → None
    assert market.keyword_table(SEEDS, online=True) is not None          # 키 없어도 시연 저장본
    assert not api.ad_available() and not api.hub_available()


def test_read_keys_env_file(tmp_path, monkeypatch):
    for n in api.AD_KEYS:
        monkeypatch.delenv(n, raising=False)
    env = tmp_path / ".env"
    env.write_text("NAVER_AD_API_KEY=a\nNAVER_AD_SECRET_KEY='b'\n# NAVER_AD_CUSTOMER_ID=zzz\n", encoding="utf-8")
    assert api.read_keys(api.AD_KEYS, env_file=env) is None               # 한 개 모자람
    env.write_text("NAVER_AD_API_KEY=a\nNAVER_AD_SECRET_KEY='b'\nNAVER_AD_CUSTOMER_ID=3\n", encoding="utf-8")
    assert api.read_keys(api.AD_KEYS, env_file=env) == {"NAVER_AD_API_KEY": "a", "NAVER_AD_SECRET_KEY": "b",
                                                        "NAVER_AD_CUSTOMER_ID": "3"}


def test_signature_is_stable_base64():
    s = api.naver_signature("secret", "1700000000000", "GET", "/keywordstool")
    assert s == api.naver_signature("secret", "1700000000000", "GET", "/keywordstool")
    assert s != api.naver_signature("secret", "1700000000001", "GET", "/keywordstool")
    assert len(s) == 44


# ── 온라인 경로 (가짜 HTTP) ──────────────────────────────────────────────
KW_BODY = {"keywordList": [
    {"relKeyword": "테스트쿠키", "monthlyPcQcCnt": "< 10", "monthlyMobileQcCnt": 900, "monthlyAveMobileClkCnt": 30.5,
     "monthlyAveMobileCtr": 3.4, "compIdx": "낮음"},
    {"relKeyword": "테스트쿠키세트", "monthlyPcQcCnt": 100, "monthlyMobileQcCnt": 400, "monthlyAveMobileClkCnt": 10,
     "monthlyAveMobileCtr": 2.0, "compIdx": "중간"}]}


def test_online_call_is_saved_and_reused(monkeypatch, tmp_path):
    fake_keys(monkeypatch)
    calls = []
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: calls.append(params) or Resp(200, KW_BODY))
    df = market.keyword_table(["테스트쿠키"], online=True)
    assert list(df["keyword"]) == ["테스트쿠키세트", "테스트쿠키"] or list(df["keyword"]) == ["테스트쿠키", "테스트쿠키세트"]
    assert df.set_index("keyword").loc["테스트쿠키", "pc_qc"] == 5.0     # "< 10" → 5
    assert len(calls) == 1 and calls[0]["showDetail"] == 1
    saved = list((tmp_path / "cache").glob("keywordstool_*.json"))
    assert len(saved) == 1 and "headers" not in json.loads(saved[0].read_text(encoding="utf-8"))
    market.keyword_table(["테스트쿠키"], online=True)                    # 저장본 재사용
    assert len(calls) == 1


def test_429_backs_off_once_then_succeeds(monkeypatch):
    fake_keys(monkeypatch)
    answers = [Resp(429), Resp(200, KW_BODY)]
    slept = []
    monkeypatch.setattr(api, "_sleep", slept.append)
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: answers.pop(0))
    assert market.keyword_table(["백오프쿠키"], online=True) is not None
    assert api.RETRY_WAIT in slept and answers == []


def test_repeated_429_pauses_and_returns_none(monkeypatch):
    fake_keys(monkeypatch)
    n = []
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: n.append(1) or Resp(429))
    assert market.keyword_table(["연속429"], online=True) is None
    assert len(n) == 2 and api._paused()
    assert market.keyword_table(["연속429다른"], online=True) is None   # 멈춤 중이라 호출하지 않음
    assert len(n) == 2


def test_http_error_and_bad_payload_do_not_crash(monkeypatch):
    fake_keys(monkeypatch)
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: Resp(500))
    assert market.keyword_table(["오류쿠키"], online=True) is None
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: Resp(200, {"oops": 1}))
    assert market.keyword_table(["이상쿠키"], online=True) is None
    monkeypatch.setattr(api, "_http_hub", lambda keys, path, body: Resp(403))
    assert market.audience("오류쿠키", online=True) is None


def test_no_secret_in_error_text(monkeypatch):
    fake_keys(monkeypatch)
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: Resp(403))
    with pytest.raises(api.NaverError) as e:
        api.keyword_tool_raw(["a"])
    assert "SECRET" not in str(e.value).upper() and e.value.status == 403


# ── 분류 ──────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def classified():
    df = market.keyword_table(SEEDS, online=False)
    return market.classify(df, SEEDS)


def test_classify_on_cached_real_data(classified):
    kw = classified.set_index("keyword")["intent"]
    assert kw["답례품쿠키"] == "선물·답례"
    assert kw["쿠키선물세트"] == "선물·답례"
    assert kw["쿠키만들기"] == "제외: 만들기"
    assert kw["광주맛집"] == "제외: 매장·지역"
    assert kw["수제쿠키"] == "상품"
    assert set(classified["intent"]) <= {"선물·답례", "시즌", "상품", "제외: 만들기", "제외: 매장·지역", "관련 낮음"}
    assert (classified["intent"] == "시즌").any()


def test_classify_small_cases():
    df = pd.DataFrame({"keyword": ["크리스마스쿠키", "서울가볼만한곳", "꽈배기", "마들렌레시피"], "total_qc": [1, 1, 1, 1],
                       "mobile_ctr": [0, 0, 0, 0]})
    out = market.classify(df, ["쿠키"]).set_index("keyword")["intent"]
    assert out["크리스마스쿠키"] == "시즌"
    assert out["서울가볼만한곳"] == "제외: 매장·지역"
    assert out["꽈배기"] == "관련 낮음"
    assert out["마들렌레시피"] == "제외: 만들기"


def test_season_word_beats_gift_word():
    df = pd.DataFrame({"keyword": ["수능선물", "수능쿠키", "크리스마스선물", "빼빼로선물", "추석선물세트", "답례품쿠키"],
                       "total_qc": [1] * 6, "mobile_ctr": [0] * 6})
    out = market.classify(df, ["쿠키"]).set_index("keyword")["intent"]
    assert out["수능선물"] == out["수능쿠키"] == "시즌"
    assert out["크리스마스선물"] == out["빼빼로선물"] == out["추석선물세트"] == "시즌"
    assert out["답례품쿠키"] == "선물·답례"


def test_typo_of_seed_and_occasion_words_are_not_negatives(classified):
    kw = classified.set_index("keyword")["intent"]
    assert kw["빼낭시에"] == "상품"                  # 휘낭시에 오타 = 사려는 사람
    assert kw["뚱낭시에"] == "상품"
    assert kw["생일"] == "선물·답례"
    neg = market.negative_list(classified)
    assert "빼낭시에" not in neg and "생일" not in neg
    assert "꽈배기" in neg                            # 진짜 무관한 말은 그대로 제외 후보


def test_variant_detection_small():
    assert market.is_variant("빼낭시에", ["휘낭시에"]) and market.is_variant("휘낭싀에", ["휘낭시에"])
    assert not market.is_variant("꽈배기", ["휘낭시에"]) and not market.is_variant("휘낭시에", ["휘낭시에"])
    df = pd.DataFrame({"keyword": ["기념일", "집들이", "생일"], "total_qc": [1] * 3, "mobile_ctr": [0] * 3})
    assert set(market.classify(df, ["쿠키"])["intent"]) == {"선물·답례"}


def test_tiers():
    assert [market.tier_of(x) for x in (20000, 10000, 300, 299, 5)] == ["대표", "대표", "세부", "롱테일", "롱테일"]


def test_recommend_and_negatives(classified):
    rec = market.recommend(classified, seeds=SEEDS)
    assert 3 <= len(rec) <= 10
    intents = classified.set_index("keyword")["intent"]
    assert all(intents[k] in market.BUYABLE for k in rec)
    assert "답례품쿠키" in rec or "쿠키선물세트" in rec
    neg = market.negative_list(classified)
    assert "쿠키만들기" in neg and "광주맛집" in neg and not set(neg) & set(rec)
    low = set(classified.loc[classified["intent"] == "관련 낮음", "keyword"])
    assert low and set(neg) & low                            # 관련 낮음 상위도 빠지지 않고 들어옴
    assert len(neg) <= 20
    groups = market.group_summary(classified)
    assert {"intent", "count", "total_qc", "mobile_ctr", "top_keyword"} == set(groups.columns)
    assert groups["count"].sum() == len(classified)


# ── 손님(성별·연령) ───────────────────────────────────────────────────────
def test_audience_index_vs_baseline():
    base = {"female": 0.6, "male": 0.4, "ages": {"10": 0.05, "20": 0.2, "30": 0.2, "40": 0.25, "50": 0.2, "60": 0.1}}
    idx = market.audience_index(0.9, {"10": 0.0, "20": 0.2, "30": 0.5, "40": 0.2, "50": 0.1, "60": 0.0}, base)
    assert idx["female"] == 1.5 and idx["male"] == 0.25
    assert idx["30"] == 2.5 and idx["20"] == 1.0 and idx["10"] == 0.0
    assert market.audience_index(0.9, {"30": 0.5}, None) == {}


def test_audience_from_cached_real_data():
    a = market.audience("답례품쿠키", online=False)
    assert a is not None and a["grade"] == "B"
    assert 0.78 <= a["female"] <= 0.86                       # 11/15 실측: 여성 82%
    assert abs(sum(a["ages"].values()) - 1) < 0.02
    assert 0.40 <= a["ages"]["30"] <= 0.55                   # 30대 48%
    assert 0.6 <= a["mobile"] <= 0.9
    assert a["peak_month"] in range(1, 13) and len(a["monthly"]) == 12 and max(a["monthly"].values()) == 100
    assert 2.4 <= a["index"]["30"] <= 3.3                    # 분야 평균(30대 17%)의 약 2.8배
    assert a["index"]["female"] > 1.1


def test_audience_without_baseline_has_empty_index(monkeypatch):
    monkeypatch.setattr(market, "category_baseline", lambda category=market.DEFAULT_CATEGORY, online=True: None)
    a = market.audience("답례품쿠키", online=False)
    assert a is not None and a["index"] == {}


# ── 헤드라인 / build ─────────────────────────────────────────────────────
def test_headline_text():
    a = market.audience("답례품쿠키", online=False)
    text = market.headline("답례품쿠키", a)
    assert text.startswith("답례품쿠키를 찾는 사람은 ")
    assert "30대 여성이 분야 평균의 2.8" in text
    assert text.endswith("11월에 가장 많이 찾아요")


def test_headline_variants():
    flat = {"female": 0.5, "ages": {"10": 0.1, "20": 0.2, "30": 0.3, "40": 0.2, "50": 0.1, "60": 0.1},
            "monthly": {"2025-01": 100, "2025-02": 95}, "peak_month": 1, "index": {"30": 1.0}}
    assert market.headline("케이크", flat) == "케이크를 찾는 사람은 30대가 가장 많아요"
    assert "정보는 아직 못 가져왔어요" in market.headline("케이크", None)
    assert "약 1,200번" in market.headline("케이크", None, 1200)
    assert market._obj("쿠키") == "를" and market._obj("휘낭시에") == "를" and market._obj("선물세트") == "를"
    assert market._obj("답례품") == "을" or market._obj("답례품") == "를"


def test_build_offline_report():
    r = market.build(SEEDS, online=False)
    assert isinstance(r, market.MarketReport)
    assert r.seeds == SEEDS and len(r.keywords) > 100
    assert 3 <= len(r.recommended) <= 10 and r.negatives
    assert 1 <= len(r.audiences) <= 3
    assert set(r.audiences) <= set(r.recommended)
    assert r.headline and "찾는 사람은" in r.headline
    assert set(r.groups["intent"]) >= {"선물·답례", "상품"}


# ── 마지막 오류 / 넓은 예외 처리 ──────────────────────────────────────────
def test_last_error_exposed_and_reset(monkeypatch):
    fake_keys(monkeypatch)
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: Resp(403))
    assert market.keyword_table(["오류A쿠키"], online=True) is None
    msg = api.last_error()
    assert msg and "네이버" in msg and "SECRET" not in msg.upper()
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: Resp(200, {"keywordList": []}))
    api.keyword_tool(["성공B쿠키"], online=True)
    assert api.last_error() is None                       # 성공하면 비워짐
    monkeypatch.setattr(api, "_http_hub", lambda keys, path, body: Resp(500))
    assert market.audience("오류C쿠키", online=True) is None
    assert api.last_error()


def test_unexpected_exception_does_not_escape(monkeypatch):
    fake_keys(monkeypatch)

    def ssl_boom(*a, **k):
        raise RuntimeError("SSL: CERTIFICATE_VERIFY_FAILED secret-ish")
    monkeypatch.setattr(api, "_http_ad", ssl_boom)
    monkeypatch.setattr(api, "_http_hub", ssl_boom)
    assert market.build(["예외쿠키"], online=True) is None
    assert api.last_error() and "SSL" not in api.last_error()
    assert market.audience("예외쿠키", online=True) is None
    assert api.last_error()
    # 호출 아래층이 이상한 응답 객체를 줘도 앱으로 새지 않음
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: object())
    assert market.keyword_table(["이상한응답쿠키"], online=True) is None
    assert api.last_error()


def test_stale_cache_fallback_still_records_error(monkeypatch):
    fake_keys(monkeypatch)
    api.save("keywordstool", "낡은쿠키", {"keywordList": []})
    monkeypatch.setattr(api, "_now", lambda: __import__("time").time() + 30 * 86_400)
    monkeypatch.setattr(api, "_http_ad", lambda keys, params: Resp(500))
    assert api.keyword_tool(["낡은쿠키"], online=True) == {"keywordList": []}
    assert api.last_error()




def test_fetch_parts_split_product_and_category_baseline():
    from server.engine import naver_api as api
    assert api.part_of("hub", "/shopping/v1/category/age|50000006||month") == "baseline"
    assert api.part_of("hub", "/shopping/v1/category/keyword/age|50000006|수제쿠키|month") == "product"
    assert api.part_of("keywordstool", "수제쿠키") == "product"
    api.reset_fetched()
    api._note_fetched("2026-11-22 12:00:00", "product")
    api._note_fetched("2026-11-20 09:00:00", "product")
    api._note_fetched("2026-11-15 14:35:09", "baseline")
    assert api.fetched_parts() == {"product": "2026-11-20", "baseline": "2026-11-15"}
    assert api.oldest_fetched() == "2026-11-15"


def test_lead_audience_is_the_most_distinctive_one():
    """장표 15장: 대표는 분야 평균 대비 배수가 가장 큰 키워드 (수제 쿠키 → 답례품쿠키, 30대 2.84배)."""
    a = {"ages": {"30": 0.31, "40": 0.34}, "index": {"30": 1.82, "40": 1.1}, "female": 0.82}
    b = {"ages": {"30": 0.48, "20": 0.17}, "index": {"30": 2.84, "20": 0.9}, "female": 0.82}
    assert market.lead_audience({"쿠키선물세트": a, "답례품쿠키": b}) == "답례품쿠키"
    assert market.lead_audience({}) is None
    r = market.build(["수제 쿠키"], online=False)
    assert next(iter(r.audiences)) == "답례품쿠키"
    assert r.headline.startswith("답례품쿠키를 찾는 사람은 30대 여성이 분야 평균의 2.84배")
