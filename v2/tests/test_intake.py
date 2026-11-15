"""P5 intake·tracking·copywriter 테스트 (네트워크 없음, 가짜 클라이언트)."""
import json
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlsplit

import pytest

from v2.engine import copywriter as cw
from v2.engine import intake, specs, tracking

CTX = intake.SetupContext(product="구움과자", product_slug="soyeon", store_type="smartstore", month="11월",
                          media=["meta", "naver"], meta_daily=6000, naver_daily=4000, naver_bid=300,
                          keywords=["답례품쿠키", "휘낭시에선물"], negatives=["만들기", "레시피"])
URL = "https://smartstore.naver.com/soyeon/products/123?foo=bar"


@pytest.fixture(autouse=True)
def no_real_key(monkeypatch):
    """진짜 키가 있어도 테스트가 네트워크를 쓰지 않게."""
    monkeypatch.setattr(cw, "_read_key", lambda: None)


def change(field_id, new, note="이유", label="칸", media="meta", rule_id="rule.x"):
    return SimpleNamespace(field_id=field_id, label=label, media=media, new=new, note=note, rule_id=rule_id)


# ── questions ──
def test_questions_come_from_specs():
    qs = intake.questions(["meta", "naver"])
    expected = [f["id"] for m in ("meta", "naver") for f in specs.fields(m)["fields"]
                if f["kind"] in ("precheck", "question", "llm")]
    ids = [q["id"] for q in qs]
    # 같이 쓰는 칸은 한 번만 (네이버 URL·문구 칸이 빠짐)
    assert "naver.ad.landing_url" not in ids and "naver.ad.copy" not in ids
    assert ids == [i for i in expected if i not in ("naver.ad.landing_url", "naver.ad.copy")]
    assert all(q["ask"] and q["why"] for q in qs)


def test_questions_naver_only_keeps_shared_fields():
    ids = [q["id"] for q in intake.questions(["naver"])]
    assert "naver.ad.landing_url" in ids and "naver.ad.copy" in ids
    assert all(i.startswith("naver.") for i in ids)


def test_questions_unknown_media():
    with pytest.raises(ValueError):
        intake.questions(["tiktok"])


# ── AUTO ──
def test_auto_registry_covers_yaml():
    used = {f["auto"] for f in specs.all_fields().values() if f["kind"] == "auto"}
    assert used <= set(intake.AUTO)
    assert used >= {"campaign_name", "adset_name", "ad_name", "meta_daily_budget", "meta_tracking",
                    "naver_campaign_name", "naver_daily_budget", "naver_bid", "naver_keywords",
                    "naver_negative_keywords"}


def test_auto_values():
    a = {}
    assert intake.AUTO["campaign_name"](a, CTX) == "soyeon_traffic_11"
    assert intake.AUTO["campaign_name"]({"meta.campaign.objective": "가게 알리기"}, CTX) == "soyeon_awareness_11"
    assert intake.AUTO["adset_name"](a, CTX) == "soyeon_nationwide_broad"
    assert intake.AUTO["ad_name"]({"meta.ad.media": "둘 다"}, CTX) == "soyeon_single_both"
    assert intake.AUTO["naver_campaign_name"](a, CTX) == "soyeon_powerlink_11"
    assert intake.AUTO["meta_daily_budget"](a, CTX) == 6000
    assert intake.AUTO["naver_keywords"](a, CTX) == ["답례품쿠키", "휘낭시에선물"]
    assert intake.AUTO["meta_tracking"](a, CTX).startswith("nt_source=meta&nt_medium=paid_social&nt_detail=")


def test_meta_tracking_own_store_uses_utm():
    ctx = intake.SetupContext(product="x", product_slug="x", store_type="own", month="11월", media=["meta"])
    assert intake.meta_tracking({}, ctx).startswith("utm_source=meta&utm_medium=paid_social&utm_campaign=x_traffic_11")


def test_final_link_keeps_existing_query():
    link = intake.meta_final_link({"meta.ad.website_url": URL}, CTX)
    q = dict(parse_qsl(urlsplit(link).query))
    assert q["foo"] == "bar" and q["nt_source"] == "meta"
    assert intake.meta_final_link({}, CTX) == ""


# ── build_sheet ──
def test_sheet_covers_every_field_of_selected_media():
    df = intake.build_sheet({}, CTX)
    expected = [f["id"] for m in CTX.media for f in specs.fields(m)["fields"]]
    assert list(df["field_id"]) == expected
    assert list(df.columns) == intake.SHEET_COLUMNS
    assert (df["value"].map(type) == str).all()
    assert not df["changed"].any()
    meta_only = intake.build_sheet({}, intake.SetupContext(product="a", product_slug="a", store_type="own",
                                                          month="11월", media=["meta"]))
    assert set(meta_only["media"]) == {"meta"}


def test_sheet_value_priority():
    def val(df, fid):
        return df.set_index("field_id").loc[fid, "value"]
    # default
    assert val(intake.build_sheet({}, CTX), "meta.campaign.buying_type") == "경매"
    # auto
    assert val(intake.build_sheet({}, CTX), "meta.campaign.name") == "soyeon_traffic_11"
    assert val(intake.build_sheet({}, CTX), "meta.adset.daily_budget") == "6,000원"
    # 묻는 칸의 답
    assert val(intake.build_sheet({"meta.adset.end_date": "7일"}, CTX), "meta.adset.end_date") == "7일"
    # 덮어쓰기가 auto보다 우선
    df = intake.build_sheet({"meta.adset.daily_budget": 9000}, CTX)
    assert val(df, "meta.adset.daily_budget") == "9,000원"
    # 같이 쓰는 칸은 메타 답을 따라감
    df = intake.build_sheet({"meta.ad.website_url": URL, "meta.creative.copy": "촉촉해요"}, CTX)
    assert val(df, "naver.ad.landing_url") == URL and val(df, "naver.ad.copy") == "촉촉해요"
    # 안 채운 질문은 안내 문구
    assert val(intake.build_sheet({}, CTX), "meta.ad.website_url") == "아직 입력 전이에요"
    assert "답례품쿠키" in val(intake.build_sheet({}, CTX), "naver.keywords.list")


def test_sheet_audience_hint_and_copy_dict():
    ctx = intake.SetupContext(product="a", product_slug="a", store_type="own", month="11월", media=["meta"],
                              audience_hint="30대 여성")
    df = intake.build_sheet({"meta.creative.copy": {"headline": "제목", "text": "본문"}}, ctx).set_index("field_id")
    assert df.loc["meta.adset.age_gender", "value"] == "30대 여성"
    assert df.loc["meta.creative.copy", "value"] == "제목 / 본문"


# ── apply_changes ──
def test_apply_changes_duck_typing_and_diff():
    answers = {"meta.adset.end_date": "14일"}
    ch = [change("meta.adset.end_date", "7일", note="짧게", label="종료 날짜"),
          change("meta.adset.placements", "수동 노출 위치: Instagram 피드·스토리·릴스", label="노출 위치")]
    new, diff = intake.apply_changes(answers, ch)
    assert answers == {"meta.adset.end_date": "14일"}          # 원본 그대로
    assert new["meta.adset.end_date"] == "7일"
    assert list(diff.columns) == intake.DIFF_COLUMNS
    row = diff.set_index("field_id").loc["meta.adset.end_date"]
    assert (row["before"], row["after"], row["note"]) == ("14일", "7일", "짧게")
    assert diff.set_index("field_id").loc["meta.adset.placements", "before"].startswith("어드밴티지+")
    sheet = intake.build_sheet(new, CTX).set_index("field_id")
    assert sheet.loc["meta.adset.end_date", "changed"] and sheet.loc["meta.adset.placements", "changed"]
    assert not sheet.loc["meta.campaign.buying_type", "changed"]
    assert "Instagram" in sheet.loc["meta.adset.placements", "value"]


def test_apply_changes_skips_noop():
    same = change("meta.adset.placements", "어드밴티지+ 노출 위치, Audience Network 제외", label="노출 위치")
    new, diff = intake.apply_changes({}, [same], CTX)
    assert diff.empty and "meta.adset.placements" not in new and new["_changed"] == []


def test_apply_changes_auto_field_before_uses_ctx():
    new, diff = intake.apply_changes({}, [change("naver.campaign.daily_budget", 2500, media="naver")], CTX)
    assert diff.iloc[0]["before"] == "4,000원" and diff.iloc[0]["after"] == "2,500원"
    assert intake.build_sheet(new, CTX).set_index("field_id").loc["naver.campaign.daily_budget", "value"] == "2,500원"


def test_apply_changes_negative_keywords_accumulate():
    new, diff = intake.apply_changes({}, [change("naver.keywords.negative", ["쿠키클래스", "만들기"], media="naver")], CTX)
    assert new["naver.keywords.negative"] == ["만들기", "레시피", "쿠키클래스"]
    assert "쿠키클래스" in diff.iloc[0]["after"]


def test_apply_changes_empty():
    new, diff = intake.apply_changes({"a": 1}, [])
    assert new["a"] == 1 and diff.empty and list(diff.columns) == intake.DIFF_COLUMNS


# ── tracking ──
def test_slugify():
    assert tracking.slugify("Soyeon Bake!") == "soyeon_bake"
    assert tracking.slugify("소연베이크") == "item"
    assert tracking.slugify("소연베이크", fallback="cookie") == "cookie"
    assert tracking.slugify("", fallback="") == ""


def test_nt_link_deterministic_english_only():
    a = tracking.nt_link(URL, "Meta!", "페이드 소셜", "11월 캠페인", "답례품쿠키")
    assert a == tracking.nt_link(URL, "Meta!", "페이드 소셜", "11월 캠페인", "답례품쿠키")
    q = dict(parse_qsl(urlsplit(a).query))
    assert q["nt_source"] == "meta" and q["nt_medium"] == "paid"      # 영문만 (한글은 fallback)
    assert q["nt_detail"] == "11월 캠페인" and q["nt_keyword"] == "답례품쿠키"
    assert q["foo"] == "bar"


def test_nt_link_overrides_same_tag_and_adds_scheme():
    a = tracking.nt_link("smartstore.naver.com/s/p/1?nt_source=old", "meta", "paid_social")
    assert a.startswith("https://") and "old" not in a and a.count("nt_source") == 1
    assert tracking.nt_link("", "meta", "paid") == ""


def test_utm_link():
    a = tracking.utm_link("https://shop.example.com/p?x=1", "meta", "paid_social", "Soyeon 11")
    q = dict(parse_qsl(urlsplit(a).query))
    assert q == {"x": "1", "utm_source": "meta", "utm_medium": "paid_social", "utm_campaign": "soyeon_11"}


# ── copywriter ──
def fake_client(payload=None, raises=False, text=None):
    calls = []

    class Msgs:
        def create(self, **kw):
            calls.append(kw)
            if raises:
                raise RuntimeError("boom sk-ant-SECRET")
            body = text if text is not None else json.dumps(payload, ensure_ascii=False)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=body)])
    return SimpleNamespace(messages=Msgs(), calls=calls)


def assert_naver_ok(copies, n=3):
    assert len(copies) == n
    for c in copies:
        assert cw.check_copy("naver", c) == []
        assert 1 <= len(c["headline"]) <= 15 and 20 <= len(c["text"]) <= 45


def test_templates_without_key(monkeypatch):
    monkeypatch.setattr(cw, "_read_key", lambda: None)
    assert cw.make_client() is None
    assert_naver_ok(cw.naver_copies("수제 구움과자", "촉촉해요, 버터 향이 진해요"))
    metas = cw.meta_copies("수제 구움과자", ["촉촉해요"], n=3)
    assert len(metas) == 3 and all(cw.check_copy("meta", c) == [] for c in metas)
    assert len({(c["headline"], c["text"]) for c in metas}) == 3


def test_force_templates_even_with_client():
    fc = fake_client([])
    cw.naver_copies("쿠키", "촉촉해요", client=False)
    assert fc.calls == []


def test_templates_handle_odd_input():
    assert_naver_ok(cw.naver_copies("아주아주아주 긴 상품 이름을 가진 수제 구움과자 세트", ""), 3)
    assert_naver_ok(cw.naver_copies("쿠키", "x", n=3), 3)
    assert cw.naver_copies("쿠키", "촉촉해요", n=0) == []


def test_banned_claims_never_appear_templates():
    for fn in (cw.naver_copies, cw.meta_copies):
        for c in fn("최고 쿠키", "국내 유일 수제, 최저가, 1위, 촉촉해요, 100% 버터", client=False):
            assert not cw.has_banned(c["headline"]) and not cw.has_banned(c["text"])


def test_llm_path_uses_client_and_enforces_limits():
    payload = [
        {"headline": "촉촉한 수제 쿠키", "text": "버터 향 가득한 수제 구움과자, 지금 만나 보세요"},   # 통과
        {"headline": "이 제목은 열다섯 글자를 훌쩍 넘어가요 정말로", "text": "버터 향 가득한 수제 구움과자, 지금 만나 보세요"},  # 제목 초과
        {"headline": "최저가 쿠키", "text": "버터 향 가득한 수제 구움과자, 지금 만나 보세요"},       # 금지어
        {"headline": "짧아요", "text": "너무 짧음"},                                              # 설명 부족
    ]
    fc = fake_client(payload)
    out = cw.naver_copies("수제 구움과자", "촉촉해요", n=3, client=fc)
    assert len(fc.calls) == 1 and fc.calls[0]["model"] == "claude-haiku-5-5"
    assert out[0] == payload[0]
    assert_naver_ok(out)
    assert all("최저가" not in c["headline"] for c in out)


def test_llm_failure_or_garbage_falls_back():
    for fc in (fake_client(raises=True), fake_client(text="죄송해요, 못 써요"), fake_client(text='[{"a":1}]')):
        assert_naver_ok(cw.naver_copies("수제 구움과자", "촉촉해요", client=fc))


def test_llm_markdown_wrapped_json_ok():
    good = {"headline": "수제 구움과자", "text": "촉촉하고 버터 향이 진한 구움과자를 만나 보세요"}
    out = cw.naver_copies("수제 구움과자", "촉촉해요", n=1, client=fake_client(text="```json\n" + json.dumps([good], ensure_ascii=False) + "\n```"))
    assert out == [good]


def test_meta_llm_limits_and_special_chars():
    long_text = "가" * 130
    payload = [{"headline": "촉촉해요", "text": long_text},
               {"headline": "봄맞이 쿠키", "text": "★★ 버터 향 가득 쿠키 ★★ 지금 만나요"}]
    out = cw.meta_copies("쿠키", "촉촉해요", n=2, client=fake_client(payload))
    assert len(out) == 2 and all(cw.check_copy("meta", c) == [] for c in out)
    assert all("★" not in c["text"] for c in out)


def test_key_not_in_error_or_output(monkeypatch):
    monkeypatch.setattr(cw, "_read_key", lambda: "sk-ant-SECRET")
    monkeypatch.setattr(cw, "make_client", lambda: fake_client(raises=True))
    out = cw.naver_copies("쿠키", "촉촉해요")
    assert "SECRET" not in json.dumps(out, ensure_ascii=False)


def test_make_client_reads_key_without_network(monkeypatch):
    monkeypatch.setattr(cw, "_read_key", lambda: "sk-ant-test")
    client = cw.make_client()
    assert client is not None and hasattr(client, "messages")
