"""세팅 입구 (T06): 칸 사양(YAML)을 읽어 질문을 만들고, 광고 관리자 '세팅값 시트'를 채운다.

- 질문 목록은 코드에 적어 두지 않는다. v2/specs/*_fields.yaml 의 kind가 question·precheck·llm인 칸이 곧 질문이다.
- 값 우선순위: answers[칸 id] (덮어쓰기·다음 달 변경 포함) > 같이 쓰는 칸의 답(shared_with) > auto 함수 > default
- apply_changes는 진단이 낸 Change를 속성으로만 읽는다 (diagnose를 import하지 않음).
"""
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import pandas as pd

from . import specs
from . import tracking

ASKED = ("precheck", "question", "llm")
CHANGED_KEY = "_changed"   # answers 안에 바뀐 칸 id를 쌓아 두는 예약 키 (apply_changes가 적음)
KIND_LABEL = {"question": "질문", "precheck": "사전 점검", "llm": "챗봇 작성",
              "auto": "자동", "default": "기본값", "next_cycle": "다음 사이클"}
SHEET_COLUMNS = ["media", "stage", "field_id", "label", "value", "kind_label", "why", "changed"]
DIFF_COLUMNS = ["field_id", "label", "before", "after", "note"]
EMPTY_TEXT = {"naver.keywords.list": "'내 손님 찾기'에서 고르면 채워져요",
              "naver.keywords.negative": "제외할 검색어 없음"}
OBJECTIVE_SLUG = {"트래픽": "traffic", "인지도": "awareness"}


@dataclass
class SetupContext:
    product: str
    product_slug: str                 # 영문 소문자 (NT 꼬리표용)
    store_type: str                   # "smartstore" | "own"
    month: str                        # "11월"
    media: List[str]                  # ["meta", "naver"]
    meta_daily: int = 0
    naver_daily: int = 0
    naver_bid: int = 0
    keywords: List[str] = field(default_factory=list)
    negatives: List[str] = field(default_factory=list)
    audience_hint: Optional[str] = None   # market 헤드라인에서 온 연령·성별 제안


# ── 사양 읽기 ─────────────────────────────────────────────

def _media_fields(media: List[str]) -> List[dict]:
    """고른 매체의 칸을 매체 순서대로, 매체 안에서는 광고 관리자 순서대로."""
    out: List[dict] = []
    seen = set()
    for m in media:
        if m in seen:
            continue
        seen.add(m)
        if m not in ("meta", "naver"):
            raise ValueError(f"아직 지원하지 않는 매체예요: {m}")
        out.extend(dict(f, media=m) for f in specs.fields(m)["fields"])
    return out


def questions(media: List[str]) -> List[dict]:
    """사장님께 물을 칸 (precheck·question·llm). shared_with 대상이 이미 물어지면 다시 묻지 않는다."""
    fields = _media_fields(media)
    asked_ids = {f["id"] for f in fields if f["kind"] in ASKED}
    out = []
    for f in fields:
        if f["kind"] not in ASKED:
            continue
        if f.get("shared_with") in asked_ids:
            continue
        out.append({
            "id": f["id"], "media": f["media"], "stage": f["stage"], "label": f["label"], "kind": f["kind"],
            "ask": f["ask"], "input": f.get("input") or ("choice" if f.get("options") else "text"),
            "options": list(f.get("options") or []), "default": f.get("default"), "why": f["why"],
            "map": dict(f.get("map") or {}), "suggest_from": f.get("suggest_from"),
        })
    return out


# ── 값 정하기 ─────────────────────────────────────────────

def _blank(v: object) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, (list, tuple, dict)) and not v)


def _answer(answers: Dict[str, object], fid: str) -> object:
    return answers.get(fid)


def _answered(f: dict, answers: Dict[str, object]) -> object:
    """칸의 답: 자기 id → 같이 쓰는 칸 id 순. 없으면 None."""
    v = _answer(answers, f["id"])
    if _blank(v) and f.get("shared_with"):
        v = _answer(answers, f["shared_with"])
    return None if _blank(v) else v


def resolve(f: dict, answers: Dict[str, object], ctx: Optional[SetupContext]) -> object:
    """칸 하나의 값. 우선순위: 답(덮어쓰기) > auto 함수 > default (age_gender는 시장 제안이 있으면 그것)."""
    v = _answered(f, answers)
    if v is not None:
        return v
    if f["kind"] == "auto" and ctx is not None:
        fn = AUTO.get(f.get("auto"))
        if fn is not None:
            return fn(answers, ctx)
    if f.get("suggest_from") == "market_age_gender" and ctx is not None and ctx.audience_hint:
        return ctx.audience_hint
    return f.get("default")


def _won(n: object) -> str:
    try:
        return f"{int(n):,}원"
    except (TypeError, ValueError):
        return str(n)


def show(f: dict, value: object) -> str:
    """시트에 보여 줄 글. 표 열이 한 종류(문자)로 유지되게 모두 문자열로."""
    if isinstance(value, dict):
        if "headline" in value or "text" in value:
            return " / ".join(str(value[k]) for k in ("headline", "text") if value.get(k))
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ", ".join(str(x) for x in value)
    if isinstance(value, bool):
        return "예" if value else "아니요"
    if isinstance(value, (int, float)) and f["id"].endswith(("daily_budget", ".bid", "cost_goal")):
        return _won(value)
    if _blank(value) and f["id"] in EMPTY_TEXT:
        return EMPTY_TEXT[f["id"]]
    if _blank(value):
        return "아직 입력 전이에요" if f["kind"] in ASKED else "비워 둠"
    return str(value)


def build_sheet(answers: Dict[str, object], ctx: SetupContext) -> pd.DataFrame:
    """고른 매체의 모든 칸을 광고 관리자 순서로 채운 세팅값 시트."""
    changed = set(answers.get(CHANGED_KEY) or [])
    rows = []
    for f in _media_fields(ctx.media):
        rows.append({
            "media": f["media"], "stage": f["stage"], "field_id": f["id"], "label": f["label"],
            "value": show(f, resolve(f, answers, ctx)), "kind_label": KIND_LABEL[f["kind"]],
            "why": f["why"], "changed": f["id"] in changed,
        })
    return pd.DataFrame(rows, columns=SHEET_COLUMNS)


# ── 다음 달 바꾸기 ─────────────────────────────────────────

def _merge_list(before: object, new: object) -> object:
    """제외 키워드처럼 쌓아 가는 목록: 기존 + 새 것 (중복 없이, 순서 유지)."""
    def items(v: object) -> List[str]:
        if isinstance(v, (list, tuple)):
            return [str(x) for x in v]
        return [s.strip() for s in re.split(r"[,\n]", str(v)) if s.strip()] if not _blank(v) else []
    out: List[str] = []
    for x in items(before) + items(new):
        if x not in out:
            out.append(x)
    return out


def is_noop(answers: Dict[str, object], change: "object", ctx: Optional[SetupContext] = None) -> bool:
    """바뀔 값이 지금 값(build_sheet가 보여 줄 값)과 같으면 True. 문자열로 맞춰 비교한다."""
    fields = specs.all_fields()
    fid = change.field_id
    spec = fields.get(fid, {"id": fid, "kind": "default"})
    before = resolve(spec, answers, ctx) if fid in fields else answers.get(fid)
    after = change.new
    if fid.endswith(".negative"):
        after = _merge_list(before, after)
    return str(show(spec, before)).strip() == str(show(spec, after)).strip()


def apply_changes(answers: Dict[str, object], changes: List["object"],
                  ctx: Optional[SetupContext] = None) -> Tuple[Dict[str, object], pd.DataFrame]:
    """Change(field_id, label, media, new, note, rule_id)를 answers에 반영. 원본 answers는 건드리지 않음.

    ctx를 주면 '바꾸기 전 값'에 자동값(예: 일 예산)까지 정확히 적는다. 제외 키워드는 기존 목록에 더한다.
    반환: (새 answers, diff 표: field_id, label, before, after, note)
    """
    fields = specs.all_fields()
    new_answers = dict(answers)
    done: List[str] = []   # 이번 달에 바뀐 칸만 (이전 달 표시는 비운다. 값은 answers에 그대로 남는다)
    rows = []
    for ch in changes:
        fid = ch.field_id
        if is_noop(new_answers, ch, ctx):
            continue
        spec = fields.get(fid, {"id": fid, "kind": "default"})
        before = resolve(spec, new_answers, ctx) if fid in fields else new_answers.get(fid)
        after = ch.new
        if fid.endswith(".negative"):
            after = _merge_list(before, after)
        new_answers[fid] = after
        if fid not in done:
            done.append(fid)
        rows.append({"field_id": fid, "label": getattr(ch, "label", "") or spec.get("label", fid),
                     "before": show(spec, before), "after": show(spec, after), "note": getattr(ch, "note", "")})
    new_answers[CHANGED_KEY] = done
    return new_answers, pd.DataFrame(rows, columns=DIFF_COLUMNS)


# ── 자동으로 채우는 칸 (AUTO) ─────────────────────────────────

def _slug(ctx: SetupContext) -> str:
    return tracking.slugify(ctx.product_slug, fallback=tracking.slugify(ctx.product, "item"))


def _mm(ctx: SetupContext) -> str:
    m = re.search(r"\d+", ctx.month or "")
    return m.group(0).zfill(2) if m else tracking.slugify(ctx.month, "m")


def _meta_objective(answers: Dict[str, object]) -> str:
    """캠페인 목표 답 → 'traffic' | 'awareness' (답이 없으면 기본값 = 스토어 방문 늘리기)."""
    f = specs.all_fields()["meta.campaign.objective"]
    raw = answers.get("meta.campaign.objective") or f["default"]
    return OBJECTIVE_SLUG.get(f["map"].get(raw, raw), "traffic")


def campaign_name(answers: Dict[str, object], ctx: SetupContext) -> str:
    """상품_목표_월 (예: soyeon_traffic_11)."""
    return f"{_slug(ctx)}_{_meta_objective(answers)}_{_mm(ctx)}"


def adset_name(answers: Dict[str, object], ctx: SetupContext) -> str:
    """상품_지역_타겟 (예: soyeon_nationwide_broad)."""
    spec = specs.all_fields()
    loc = answers.get("meta.adset.location") or spec["meta.adset.location"]["default"]
    age = answers.get("meta.adset.age_gender")
    broad = _blank(age) or "넓게" in str(age)
    return f"{_slug(ctx)}_{'local' if '내 지역' in str(loc) else 'nationwide'}_{'broad' if broad else 'custom'}"


def ad_name(answers: Dict[str, object], ctx: SetupContext) -> str:
    """상품_형식_사진 (예: soyeon_single_square) — 어떤 사진의 결과인지 구분."""
    spec = specs.all_fields()
    fmt = str(answers.get("meta.ad.format") or spec["meta.ad.format"]["default"])
    media = str(answers.get("meta.ad.media") or spec["meta.ad.media"]["default"])
    pic = "both" if "둘 다" in media else "vertical" if "세로" in media else "square"
    return f"{_slug(ctx)}_{'carousel' if '여러' in fmt else 'single'}_{pic}"


def meta_daily_budget(answers: Dict[str, object], ctx: SetupContext) -> object:
    return ctx.meta_daily if ctx.meta_daily > 0 else "예산 단계에서 정해져요"


def _website_url(answers: Dict[str, object]) -> str:
    return str(answers.get("meta.ad.website_url") or answers.get("naver.ad.landing_url") or "").strip()


def meta_tracking_params(answers: Dict[str, object], ctx: SetupContext) -> List[Tuple[str, str]]:
    """메타 광고에 붙일 꼬리표 목록 (스마트스토어 NT / 자사몰 UTM). 캠페인 이름이 꼬리표에 들어감."""
    name = campaign_name(answers, ctx)
    if ctx.store_type == "own":
        return tracking.utm_params("meta", "paid_social", name, ad_name(answers, ctx))
    return tracking.nt_params("meta", "paid_social", name)


def meta_tracking(answers: Dict[str, object], ctx: SetupContext) -> str:
    """'URL 매개변수' 칸에 넣는 값 (예: nt_source=meta&nt_medium=paid_social&nt_detail=...)."""
    return tracking.query_string(meta_tracking_params(answers, ctx))


def meta_final_link(answers: Dict[str, object], ctx: SetupContext) -> str:
    """상품 페이지 주소 + 꼬리표 (주소가 없으면 빈 글)."""
    return tracking.attach(_website_url(answers), meta_tracking_params(answers, ctx))


def naver_campaign_name(answers: Dict[str, object], ctx: SetupContext) -> str:
    f = specs.all_fields()["naver.campaign.type"]
    raw = answers.get("naver.campaign.type") or f["default"]
    kind = "shopping" if f["map"].get(raw, raw) == "쇼핑검색" else "powerlink"
    return f"{_slug(ctx)}_{kind}_{_mm(ctx)}"


def naver_daily_budget(answers: Dict[str, object], ctx: SetupContext) -> object:
    return ctx.naver_daily if ctx.naver_daily > 0 else "예산 단계에서 정해져요"


def naver_bid(answers: Dict[str, object], ctx: SetupContext) -> object:
    return ctx.naver_bid if ctx.naver_bid > 0 else "예산 단계에서 정해져요"


def naver_keywords(answers: Dict[str, object], ctx: SetupContext) -> object:
    return list(ctx.keywords)


def naver_negative_keywords(answers: Dict[str, object], ctx: SetupContext) -> object:
    return list(ctx.negatives)


AUTO: Dict[str, Callable[[Dict, SetupContext], object]] = {
    "campaign_name": campaign_name,
    "adset_name": adset_name,
    "ad_name": ad_name,
    "meta_daily_budget": meta_daily_budget,
    "meta_tracking": meta_tracking,
    "naver_campaign_name": naver_campaign_name,
    "naver_daily_budget": naver_daily_budget,
    "naver_bid": naver_bid,
    "naver_keywords": naver_keywords,
    "naver_negative_keywords": naver_negative_keywords,
}
