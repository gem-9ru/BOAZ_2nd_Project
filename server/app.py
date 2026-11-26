"""광고 코치 v3 서버: 크롬 확장이 부르는 HTTP 창구. 계산은 server/engine에 있다.

- COACH_OFFLINE=1 이면 네이버를 부르지 않고 저장본만 쓴다 (시연장 네트워크 대비).
- COACH_NO_LLM=1 이면 Claude를 부르지 않고 문장 틀로 문구를 만든다.
"""
import datetime
import json
import logging
import os
import threading
import time
from typing import List, Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from server.engine import brands, copywriter, market, naver_api, specs
from server.engine.meta_export import read_export
from server.engine.loop import run as loop_run, simulate as loop_simulate

# 로그: coach.* 로거만 stderr로 (uvicorn 로거는 건드리지 않음). 수준은 COACH_LOG_LEVEL (기본 INFO)
_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _log_level(value: Optional[str]) -> str:
    """COACH_LOG_LEVEL 값 → 로그 수준 이름. 비었거나 잘못 적었으면 INFO (서버가 뜨다가 멈추지 않게)."""
    name = (value or "").strip().upper()
    return name if name in _LEVELS else "INFO"


_coach_log = logging.getLogger("coach")
if not _coach_log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    _coach_log.addHandler(_h)
    _coach_log.propagate = False
_coach_log.setLevel(_log_level(os.environ.get("COACH_LOG_LEVEL")))
log = logging.getLogger("coach.api")

MAX_KEYWORDS = 10
MAX_MODIFIERS = 15   # 좋은 점 칩 (브랜드·가게 이름을 거른 뒤)
_NAVER_LOCK = threading.Lock()   # naver_api의 조회일·오류는 모듈 전역 → 요청을 한 번에 하나씩

app = FastAPI(title="광고 코치 v3")
app.add_middleware(CORSMiddleware, allow_origin_regex=r"chrome-extension://.*",
                   allow_methods=["*"], allow_headers=["*"])


def _online() -> bool:
    return os.environ.get("COACH_OFFLINE") != "1"


@app.get("/health")
def health() -> dict:
    return {"ok": True}


class ResearchIn(BaseModel):
    product: str
    seeds: Optional[List[str]] = None   # 비우면 상품 이름 하나로 찾음
    category: Optional[str] = None      # 쇼핑인사이트 분야 code. 비우면 서버가 추정
    keywords: Optional[List[str]] = None   # 사장님이 고른 검색어 (손님 무리를 이 안에서만 묶음)


def _category_out(code: Optional[str], guessed: bool) -> Optional[dict]:
    if not code:
        return None
    name = next((c["name"] for c in market.CATEGORIES if c["code"] == code), code)
    return {"code": code, "name": name, "guessed": guessed}


@app.post("/research")
def research(body: ResearchIn) -> dict:
    t0 = time.perf_counter()
    out = _research(body)
    cat = out.get("category")
    log.info("research done product=%s category=%s guessed=%s segments=%d modifiers=%d source=%s notice=%s ms=%d",
             body.product, cat["code"] if cat else None, bool(cat and cat["guessed"]), len(out.get("segments") or []),
             len(out.get("modifiers") or []), out.get("source"), "yes" if out.get("notice") else "no",
             (time.perf_counter() - t0) * 1000)
    return out


def _good_points(product: str, mods: List[dict]) -> List[dict]:
    """좋은 점 칩: 다른 가게·브랜드 이름(스탠리·투썸…)을 Claude로 걸러 MAX_MODIFIERS개, 묶음 이름은 상품에 맞게(재질·기능…).
    낱말만 보내고 숫자는 안 보낸다. 오프라인·LLM 끔이면 이미 물어본 것만 쓰고, 묶음은 원래대로(포장·맛·재료·배송·양·그 밖)."""
    drop, groups = brands.classify(product, [m["word"] for m in mods], client=None if _online() else False)
    if drop:
        log.info("good points brands dropped n=%d", len(drop))
    kept = [m for m in mods if m["word"] not in drop][:MAX_MODIFIERS]
    return [{**m, "group": groups.get(m["word"], m["group"])} for m in kept]


def _shorter_names(product: str) -> List[str]:
    """자료가 없을 때 더 짧게 찾아볼 말: 뒤쪽 조각부터 ('수제 버터 쿠키' → '버터 쿠키', '쿠키'). 최대 3개."""
    pieces = product.split()
    return [" ".join(pieces[i:]) for i in range(1, len(pieces)) if len(" ".join(pieces[i:])) >= 2][:3]


def _similar_words(product: str, kw) -> List[str]:
    """추천할 말이 없을 때 대신 찾아볼 말: 네이버 연관 검색어 중 검색이 많은 것 3개 (상품 이름 그대로·만들기·매장 말 제외)."""
    me = product.replace(" ", "")
    try:
        rows = kw[~kw["intent"].astype(str).str.startswith("제외")].sort_values("total_qc", ascending=False)
        words = [k for k in rows["keyword"] if k.replace(" ", "") != me]
    except (KeyError, AttributeError):
        words = []
    return (words or _shorter_names(product))[:3]


def _research(body: ResearchIn) -> dict:
    seeds = [s for s in (body.seeds or [body.product]) if s.strip()]   # 검색 자료 요청용 (저장본 이름이 이 목록으로 정해짐)
    with _NAVER_LOCK:
        given = body.category if body.category in {c["code"] for c in market.CATEGORIES} else None   # 모르는 code는 없는 셈
        code, cands = (given, []) if given else market.category_guess(body.product, _online())
        if code:   # 정해진 분야는 빼고, 남은 가까운 후보는 [바꾸기]에서 먼저 보여 준다
            cands = [c for c in cands if c != code]
        report = market.build(seeds, online=_online(), category=code, keep=body.keywords, product=body.product)
        why = naver_api.last_error()
    mods = _good_points(body.product, report.modifiers if report else [])
    wide = {"category": _category_out(code, not given), "categories": [dict(c) for c in market.CATEGORIES],
            "category_candidates": [{"code": c, "name": _category_out(c, True)["name"]} for c in cands]}
    if report is None:   # 키 없음·429·네트워크 → 그 이유를 그대로 (키 값은 담기지 않음)
        notice = f"{why} 잠시 뒤 다시 시도해 주세요." if why else "네이버에서 이 상품 검색 자료를 찾지 못했어요. 상품을 다른 말로 적어 보세요."
        return {"headline": "", "keywords": [], "audience": None, "fetched": "", "source": "cache", "notice": notice,
                **wide, "segments": [], "modifiers": [], "product_stats": None,
                "suggestions": [] if why else _shorter_names(body.product)}
    if not report.recommended:
        return {"headline": report.headline, "keywords": [], "audience": None, "fetched": report.fetched,
                "source": "cache", "notice": "추천할 만한 검색어를 찾지 못했어요. 상품을 더 흔한 말로 적어 보세요.",
                **wide, "segments": [], "modifiers": mods, "product_stats": report.product_stats,
                "suggestions": _similar_words(body.product, report.keywords)}
    kw = report.keywords.set_index("keyword")["total_qc"]
    keywords = [{"keyword": k, "total_qc": int(kw[k])} for k in report.recommended[:MAX_KEYWORDS] if k in kw]
    audience = None
    if report.audiences:
        name, aud = next(iter(report.audiences.items()))
        audience = {"keyword": name, "female": aud["female"], "ages": aud["ages"], "top_age": market.top_age(aud)}
    today = datetime.date.today().isoformat()
    sources = [{"part": part, "label": label, "fetched": report.fetched_parts[part], "today": report.fetched_parts[part] == today}
               for part, label in (("product", "검색어·연령"), ("baseline", "분야 평균")) if part in report.fetched_parts]
    live = report.fetched_parts.get("product", report.fetched) == today   # 이 상품 자료가 오늘 받은 것이면 실시간
    return {"headline": report.headline, "keywords": keywords, "audience": audience, "fetched": report.fetched,
            "source": "live" if live else "cache", "sources": sources, "negatives": report.negatives[:20], "notice": None,
            **wide, "segments": report.segments, "modifiers": mods, "product_stats": report.product_stats}


class SplitIn(BaseModel):
    keyword: str
    category: str
    ages: dict = {}   # 나이대 → 비중 (/research가 준 audience.ages). 적게 찾는 나이대는 묻지 않음


@app.post("/audience/split")
def audience_split(body: SplitIn) -> dict:
    """연령 막대를 여성·남성으로 나눠 그리기: 나이대마다 그 안의 여성 비중. 화면에 그림이 열릴 때 따로 부른다 (저장해 둠)."""
    if body.category not in {c["code"] for c in market.CATEGORIES}:
        return {"female_by_age": {}}
    ages = {str(k): float(v) for k, v in body.ages.items() if str(k) in market.AGE_GROUPS}
    with _NAVER_LOCK:
        out = market.female_by_age(body.keyword.replace(" ", ""), body.category, ages, _online())
    log.info("audience split keyword=%s ages=%d", body.keyword, len(out))
    return {"female_by_age": out}


ASKED_KINDS = ("question", "precheck")
SET_KINDS = ("default", "auto", "next_cycle")


class SegmentIn(BaseModel):
    intent: str
    label: str
    peak_month: Optional[int] = Field(None, ge=1, le=12)   # 시즌일 때만 옴 (1~12월)


class CopiesIn(BaseModel):
    product: str
    strengths: List[str] = []
    keywords: List[str] = []
    avoid: List[str] = []      # ① 찾기의 뺄 말: 문구에 넣지 않는다
    segment: Optional[SegmentIn] = None   # ① 찾기에서 고른 손님 무리
    tone: Optional[str] = None            # 문구 말투: 친근하게 | 깔끔하게 | 감성적으로 (모르는 값은 무시)


@app.post("/copies")
def copies(body: CopiesIn) -> dict:
    t0 = time.perf_counter()
    out = _copies(body)
    log.info("copies done source=%s n=%d segment=%s ms=%d", out["source"], len(out["copies"]),
             body.segment.intent if body.segment else None, (time.perf_counter() - t0) * 1000)
    return out


def _copies(body: CopiesIn) -> dict:
    client = copywriter.make_client()
    # 상품 이름에 들어 있는 말은 빼지 않는다 (예: '쿠키만들기 키트'를 파는데 '쿠키만들기'를 빼면 문구가 남지 않음)
    product = body.product.replace(" ", "")
    avoid = [w for w in body.avoid if w.strip() and w.replace(" ", "") not in product]
    clean = lambda cs: [c for c in cs if not any(w in c["text"] + c["headline"] for w in avoid)]
    words = list(body.strengths) + list(body.keywords)
    seg = body.segment.model_dump() if body.segment else None
    made, used_claude = copywriter.meta_copies_with_source(body.product, list(body.strengths), n=3, client=client or False,
                                                           tone=body.tone,
                                                           segment=seg, keywords=list(body.keywords))
    made = clean(made)
    if len(made) < 3:   # 뺄 말이 들어간 문구를 버렸으면 문장 틀로 채운다
        for c in clean(copywriter.meta_copies(body.product, words, n=6, client=False, segment=seg)):
            if len(made) >= 3:
                break
            if c not in made:
                made.append(c)
    return {"copies": [{"primary_text": c["text"], "headline": c["headline"],
                        "basis": copywriter.basis(c, words, seg)} for c in made],
            "source": "claude" if used_claude else "template"}


@app.get("/fields")
def fields() -> dict:
    """묻는 칸(질문·사전 점검)과, 묻지 않고 기본값으로 두는 칸(이유 한 줄)."""
    all_meta = specs.fields("meta")["fields"]
    asked = [{"id": f["id"], "kind": f["kind"], "label": f["label"], "ask": f["ask"],
              "options": f.get("options"), "default": f.get("default"), "why": f.get("why", ""), "help": f.get("help"),
              "then_ask": f.get("then_ask"), "default_if": f.get("default_if"), "note_if": f.get("note_if"),
              "custom": f.get("custom"), "custom_for": f.get("custom_for"), "answer_as": f.get("answer_as"),
              "stage": f.get("stage", ""), "required": bool(f.get("required"))}
             for f in all_meta if f.get("kind") in ASKED_KINDS]
    preset = [{"id": f["id"], "label": f["label"], "default": str(f["default"]), "why": f["why"]}
              for f in all_meta if f.get("kind") in SET_KINDS and f.get("default") is not None and f.get("why")]
    return {"fields": asked, "defaults": preset}


# ── 분석 페이지: 0 검증 → 5 다음 세팅 (server/engine/loop) ────────────────────
import secrets  # noqa: E402

from fastapi import HTTPException  # noqa: E402

DEMO_CSV = os.path.join(os.path.dirname(__file__), "data", "demo", "오븐로그_메타AB_20261117-20261120.csv")
# 예시 2: 희수 실험 (scripts/heesu_example.py 가 정리 엑셀에서 만든 파일 · 타깃과 노출 위치를 함께 바꾼 묶음 비교)
EXAMPLES = {"ovenlog": DEMO_CSV,
            "heesu": os.path.join(os.path.dirname(__file__), "data", "demo", "희수_메타AB_20261117-20261120.csv")}
from collections import OrderedDict  # noqa: E402

MAX_PLANS = 200          # 서버 메모리에 남기는 분석 결과 수 (넘으면 가장 오래된 것부터 지움)
MAX_UPLOAD_BYTES = 5 * 1024 * 1024   # 메타 결과 CSV는 보통 수십 KB
_PLANS: "OrderedDict[str, dict]" = OrderedDict()   # 코드 → 분석 결과 (시연용, 서버 메모리에만)
_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # 헷갈리는 O·0·I·1 제외


def _store(result: dict) -> dict:
    code = "".join(secrets.choice(_CODE_CHARS) for _ in range(4))
    while code in _PLANS:
        code = "".join(secrets.choice(_CODE_CHARS) for _ in range(4))
    _PLANS[code] = result
    while len(_PLANS) > MAX_PLANS:
        _PLANS.popitem(last=False)
    return {**result, "code": code}


def _loop(bundle, settings=None):
    if "meta_daily" not in bundle.tables:
        msg = " ".join(bundle.problems) or "메타 결과를 읽지 못했어요. 광고 관리자에서 일·노출 위치 기준으로 내보내 주세요."
        return JSONResponse(status_code=400, content={"error": msg})
    return _store(loop_run.run(bundle, settings=settings))


def _settings(raw: Optional[str]) -> Optional[dict]:
    """확장 프로그램 계획 파일의 세팅값 (칸 id → 값). 형식이 틀리면 없는 것으로 본다."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else None


@app.post("/analysis")
async def analysis_upload(file: UploadFile = File(...), settings: Optional[str] = Form(None),
                          settings_key: Optional[str] = Form(None)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=400, content={"error": f"파일이 {MAX_UPLOAD_BYTES // 1024 // 1024}MB보다 커요. 광고 관리자에서 비교할 광고 세트만 골라 다시 내보내 주세요."})
    given = _settings(settings) or _SETTINGS.get(settings_key or "")   # 직접 넣은 5문항이 우선, 없으면 확장이 넘긴 세팅값
    return _loop(read_export(data), given)


@app.get("/analysis/example")
def analysis_example(settings_key: Optional[str] = None, name: str = "ovenlog"):
    if name not in EXAMPLES:
        return JSONResponse(status_code=404, content={"error": "그런 예시는 없어요."})
    return _loop(read_export(EXAMPLES[name]), _SETTINGS.get(settings_key or ""))


# ── 세팅값 넘기기 (v4 8장): 확장 프로그램 → 분석 페이지. 값은 URL에 넣지 않고, 서버가 보관하고 키만 넘긴다 ──
_SETTINGS: "OrderedDict[str, dict]" = OrderedDict()


class SettingsIn(BaseModel):
    settings: dict


@app.post("/settings")
def keep_settings(body: SettingsIn):
    key = secrets.token_urlsafe(12)
    _SETTINGS[key] = {str(k): str(v) for k, v in body.settings.items() if v not in (None, "")}
    while len(_SETTINGS) > MAX_PLANS:
        _SETTINGS.popitem(last=False)
    return {"key": key, "count": len(_SETTINGS[key])}


@app.get("/settings/{key}")
def read_settings(key: str):
    s = _SETTINGS.get(key)
    if s is None:
        raise HTTPException(status_code=404, detail="세팅값을 찾지 못했어요. 확장 프로그램에서 분석 페이지를 다시 열어 주세요.")
    return {"count": len(s), "settings": s}


class SimulateIn(BaseModel):
    code: str
    arm: str
    budget: float
    total: float = 100_000   # Test & Roll용 전체 광고 예산
    days: Optional[int] = None   # AN-05 기간 토글 (4일/7일): 하루 금액이 써 본 적 있는지


@app.post("/simulate")
def simulate(body: SimulateIn):
    plan = _PLANS.get(body.code.upper())
    arm = next((a for a in (plan or {}).get("summary", {}).get("arms", []) if a["name"] == body.arm), None)
    if arm is None:
        raise HTTPException(status_code=404, detail="분석 결과나 광고 세트를 찾지 못했어요. 파일을 다시 올려 주세요.")
    budget = max(body.budget, 0.0)
    out = loop_simulate.run(arm, budget)
    # 써 본 적 없는 금액은 '가설' (화면에서 점선). Test & Roll은 따로 받은 전체 예산 기준.
    return {**out, **loop_simulate.tried(arm, budget, body.days if body.days and body.days > 0 else None),
            "next_test": loop_simulate.next_test_budget(max(body.total, 0.0))}


@app.get("/plan/{code}")
def plan(code: str):
    p = _PLANS.get(code.upper())
    if p is None:
        raise HTTPException(status_code=404, detail="코드를 찾지 못했어요. 분석 페이지의 코드를 다시 확인해 주세요.")
    m = p.get("matrix") or {}
    return {**p["next"], "badge": (p["verdict"] or {}).get("badge"), "code": code.upper(),
            "keep": m.get("keep", []), "watch": m.get("watch", []), "dont": m.get("dont", [])}


class AssistantIn(BaseModel):
    code: str
    step: str
    question: Optional[str] = None


@app.post("/assistant")
def assistant_reply(body: AssistantIn):
    """분석 페이지 오른쪽 어시스턴트: 질문이 없으면 그 단계 첫 말풍선, 있으면 그 단계 결과 JSON으로 설명."""
    from server.engine.loop import assistant
    p = _PLANS.get(body.code.upper())
    if p is None:
        raise HTTPException(status_code=404, detail="분석 결과를 찾지 못했어요. 파일을 다시 올려 주세요.")
    if not body.question:
        return assistant.opening(p, body.step)
    return assistant.answer(p, body.step, body.question, client=copywriter.make_client())


# ── 분석 페이지 화면 (web/ 를 빌드한 web/dist) ────────────────────────────────
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

WEB_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")


@app.get("/", include_in_schema=False)
def root():
    """주소만 열면(ad-assistant.gem-9ru.com) 분석 페이지로."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/analysis")


@app.get("/analysis")
def analysis_page():
    index = os.path.join(WEB_DIST, "index.html")
    if not os.path.exists(index):
        return JSONResponse(status_code=503, content={"error": "분석 페이지가 아직 빌드되지 않았어요. web 폴더에서 npm run build를 실행해 주세요."})
    return FileResponse(index)


# 서버를 켠 뒤에 web을 빌드해도 자산이 보이게 항상 연결한다 (폴더가 없으면 요청 때 404)
app.mount("/analysis/assets", StaticFiles(directory=os.path.join(WEB_DIST, "assets"), check_dir=False), name="analysis-assets")
