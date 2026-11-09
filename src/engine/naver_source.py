"""네이버 검색광고 API 조회 + 캐시.

- 키 읽기·서명은 src/engine/keys.py 하나: Streamlit secrets → 환경 변수 → .env 순 (NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY,
  NAVER_AD_CUSTOMER_ID). 키 값은 출력하지 않습니다.
- 응답은 data/interim/naver_cache/ 에 JSON으로 저장하고(git에 안 올림), 예시 1·2 캐시는 data/examples/naver_cache/(고정)에서 먼저 읽습니다.
- 200이 아닌 응답·이상한 응답은 NaverUnavailable(캐시에 남지 않음), 429는 규칙대로 쉬었다 1번만 다시, 연달아면 5분 멈춤.
- 캐시에 없는 키워드를 오프라인으로 요청하면 None을 돌려주고, 앱이 예시 키워드(캐시)로 대체합니다.
"""
import hashlib
import json
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

from . import defaults as D
from .data_loader import keyword_tier

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "interim" / "naver_cache"            # 사장님 검색어로 생기는 캐시 (git에 안 올림, 검수 A5)
EXAMPLE_CACHE_DIR = ROOT / "data" / "examples" / "naver_cache"   # 예시 1·2·예시 단어 고정 캐시 (먼저 읽고, 만료 없음)
SAMPLE_KEYWORD = "필라테스"  # 캐시에 들어 있는 예시 키워드 (업종 예시일 뿐, 엔진은 업종을 가정하지 않음)
CACHE_FORMAT = 2             # 돌려주는 표 형식 버전 (attrs: 받은 날짜·출처). 바꾸면 화면 캐시(st.cache_data)도 새로
MAX_AGE_DAYS = 7             # 받은 지 7일 지난 캐시는 온라인일 때 다시 받음 (검수 A6). 예시 캐시는 제외

# 입찰가를 촘촘하게 요청해야 계단 모양 곡선의 꺾이는 지점을 잡을 수 있음 (API는 한 번에 최대 100개)
BIDS = (
    [70, 100, 150, 200, 250]
    + list(range(300, 3001, 100))
    + list(range(3200, 6001, 200))
    + list(range(6500, 10001, 500))
)

MONTH_FACTOR = D.DAYS_PER_MONTH / D.NAVER_ESTIMATE_DAYS  # 네이버 예상 실적(28일) → 한 달

# 호출 규칙 (네이버_검색광고_API_종합.md 6장, 공지 2020-12-18): 429면 쉬었다 1번만 다시, 키워드 도구는 5~6배 길게,
# 몇 초 사이 429가 쌓이면 5분 이상 모든 호출을 멈춤. 키워드 도구는 호출 사이 간격.
RETRY_WAIT = {"keywordstool": 6.0, "estimate": 1.0}
KW_GAP = 1.0
BURST_COUNT, BURST_WINDOW, PAUSE_SECONDS = 2, 10.0, 300.0
_STATE = {"rate_hits": [], "paused_until": 0.0, "last_kw": 0.0}
_sleep, _now = time.sleep, time.time          # 테스트에서 바꿔 끼움

# 오류 코드 → 사장님 문장 (검수 A11, 종합 문서 7·11장)
ERROR_TEXT = {
    "7001": "한 번에 넣을 수 있는 검색어 수(5개)를 넘었어요. 5개 이하로 줄여 주세요.",
    "7002": "같은 검색어가 두 번 들어갔어요. 겹치는 단어를 빼 주세요.",
    "7003": "검색어에 쓸 수 없는 문자가 있어요. 특수문자를 빼 주세요.",
    "429": "네이버에 요청이 너무 많아 잠시 막혔어요. 몇 분 뒤 새로고침하면 다시 시도해요.",
    "1016": "네이버에 요청이 너무 많아 잠시 막혔어요. 몇 분 뒤 새로고침하면 다시 시도해요.",
    "paused": "네이버에 요청이 몰려 5분 동안 쉬는 중이에요. 그동안은 저장해 둔 값과 대략값으로 보여 드려요.",
    "403": "네이버 API 권한이나 시계가 맞지 않아요(키를 다시 확인하거나 잠시 뒤 다시). 지금은 대략값으로 보여 드려요.",
    "503": "네이버 API가 점검 중이에요. 점검이 끝나면 다시 시도해요.",
}


def error_text(code=None, status=None) -> str:
    for k in (code, status):
        if k is not None and str(k) in ERROR_TEXT:
            return ERROR_TEXT[str(k)]
    return "네이버 예상치를 못 불러와 대략값을 썼어요. 잠시 뒤 새로고침하면 다시 시도해요."


class NaverUnavailable(Exception):
    """네이버 API 결과를 못 받음 (연결 오류·타임아웃·200이 아닌 응답·이상한 응답). 캐시에 남지 않고, 화면은 대략값으로 내려감."""

    def __init__(self, reason: str = "", code=None, status=None):
        super().__init__(reason or f"code={code} status={status}")
        self.code, self.status = code, status

    @property
    def message(self) -> str:
        return error_text(self.code, self.status)

    @property
    def rate_limited(self) -> bool:
        return str(self.status) == "429" or str(self.code) in ("429", "1016")


def _bids_tag() -> str:
    return hashlib.md5(",".join(map(str, BIDS)).encode()).hexdigest()[:6]


def _cache_path(kind: str, key: str, base: Path = None) -> Path:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:10]
    return (base or CACHE_DIR) / f"{kind}_{digest}.json"


def _load(path: Path):
    """캐시 파일 하나. 깨졌으면 없는 것으로 (검수 A12)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) and "response" in payload else None
    except (OSError, ValueError):
        return None


def _read_cache(kind: str, key: str, legacy: Optional[str] = None, check=None):
    """→ (payload, pinned). 예시 캐시(고정) → 사용자 캐시 순. legacy 키 파일은 check(payload)가 참일 때만."""
    for base, pinned in ((EXAMPLE_CACHE_DIR, True), (CACHE_DIR, False)):
        for k in (key, legacy):
            if k is None:
                continue
            path = _cache_path(kind, k, base)
            payload = _load(path) if path.exists() else None
            if payload is not None and (k == key or check is None or check(payload)):
                return payload, pinned
    return None, False


def _stale(payload: dict) -> bool:
    try:
        fetched = time.mktime(time.strptime(payload.get("fetched_at", ""), "%Y-%m-%d %H:%M:%S"))
    except (TypeError, ValueError):
        return True
    return _now() - fetched > MAX_AGE_DAYS * 86_400


def _write_cache(kind: str, key: str, request: dict, response) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"request": request, "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "response": response}
    _cache_path(kind, key).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


KEY_NAMES = ("NAVER_AD_API_KEY", "NAVER_AD_SECRET_KEY", "NAVER_AD_CUSTOMER_ID")


def _secret_keys() -> Optional[dict]:
    """키 읽기는 keys.read_keys 하나 (secrets → 환경 변수 → .env, 검수 A13). 값은 출력하지 않음."""
    from .keys import read_keys
    return read_keys(KEY_NAMES)


def _env_call(keys: dict):
    """서명해서 부르는 함수 (keys.naver_signature). 키는 출력하지 않는다. 200이 아닌 응답은 NaverUnavailable (검수 A2)."""
    def call(method: str, uri: str, params=None, body=None):
        from .keys import naver_signature
        timestamp = str(round(time.time() * 1000))
        signature = naver_signature(keys["NAVER_AD_SECRET_KEY"], timestamp, method, uri)
        headers = {"Content-Type": "application/json; charset=UTF-8", "X-Timestamp": timestamp,
                   "X-API-KEY": keys["NAVER_AD_API_KEY"], "X-Customer": str(keys["NAVER_AD_CUSTOMER_ID"]),
                   "X-Signature": signature}
        try:
            r = requests.request(method, "https://api.searchad.naver.com" + uri, params=params, json=body,
                                 headers=headers, timeout=20)
        except requests.RequestException as e:
            raise NaverUnavailable(type(e).__name__) from e
        try:
            data = r.json()
        except ValueError:
            data = r.text
        if r.status_code != 200:
            code = data.get("code") if isinstance(data, dict) else None
            raise NaverUnavailable(f"HTTP {r.status_code}", code=code, status=r.status_code)
        return data
    return call


def _api_call():
    """키가 있으면 서명해 부르는 함수, 없으면 None. 키 읽기·서명은 keys 모듈 하나 (src/collect 스크립트는 불러오지 않음, A13)."""
    keys = _secret_keys()
    return _env_call(keys) if keys else None


def _safe(call, *args, **kw):
    """수집 모듈(src/collect)의 call이 내는 연결 오류도 NaverUnavailable 하나로 모음."""
    try:
        return call(*args, **kw)
    except NaverUnavailable:
        raise
    except Exception as e:  # noqa: BLE001  (requests 오류, 수집 모듈 내부 오류)
        raise NaverUnavailable(type(e).__name__) from e


def _check(data, ok_key: str):
    """정상 응답(ok_key가 있는 dict)이 아니면 NaverUnavailable (오류 응답·깨진 응답은 캐시에 남기지 않음)."""
    if isinstance(data, dict) and ok_key in data:
        return data
    code = data.get("code") if isinstance(data, dict) else None
    status = data.get("status") if isinstance(data, dict) else None
    raise NaverUnavailable("이상한 응답", code=code, status=status)


def _request(call, kind: str, method: str, uri: str, ok_key: str, **kw):
    """호출 규칙을 지켜 한 번 부름: 멈춤 중이면 바로 실패, 키워드 도구는 간격, 429면 쉬었다 1번만 다시 (검수 A4)."""
    if _now() < _STATE["paused_until"]:
        raise NaverUnavailable("멈춤 중", code="paused")
    if kind == "keywordstool":
        gap = KW_GAP - (_now() - _STATE["last_kw"])
        if gap > 0:
            _sleep(gap)
    for attempt in (0, 1):
        try:
            if kind == "keywordstool":
                _STATE["last_kw"] = _now()
            return _check(_safe(call, method, uri, **kw), ok_key)
        except NaverUnavailable as e:
            if not e.rate_limited:
                raise
            now = _now()
            hits = [h for h in _STATE["rate_hits"] if now - h <= BURST_WINDOW] + [now]
            _STATE["rate_hits"] = hits
            if len(hits) >= BURST_COUNT:
                _STATE["paused_until"] = now + PAUSE_SECONDS
                raise NaverUnavailable("연달아 429", code="paused") from e
            if attempt == 1:
                raise
            _sleep(RETRY_WAIT.get(kind, 1.0))


def api_available() -> bool:
    return _api_call() is not None


def _to_num(value) -> float:
    """숫자형·문자열 혼재 처리. "<10"은 5로 근사."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text.startswith("<"):
        return 5.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _frame_meta(df: pd.DataFrame, payload: Optional[dict], source: str) -> pd.DataFrame:
    df.attrs["fetched_at"] = (payload or {}).get("fetched_at", "")
    df.attrs["source"] = source
    return df


def _fetch_or_cache(kind: str, key: str, online: bool, fetch, legacy: Optional[str] = None, check=None):
    """캐시(예시 → 사용자) → 없거나 7일 지났고 온라인이면 새로 받음. 새로 받기가 실패하면 지난 캐시라도 씀.
    → (응답, payload, 출처) 또는 (None, None, "")."""
    payload, pinned = _read_cache(kind, key, legacy, check)
    if payload is not None and (pinned or not online or not _stale(payload)):
        return payload["response"], payload, "예시 저장본" if pinned else "저장본"
    if not online:
        return None, None, ""
    call = _api_call()
    if call is None:
        return (payload["response"], payload, "저장본") if payload else (None, None, "")
    try:
        request, data = fetch(call)
    except NaverUnavailable:
        if payload is not None:                  # 다시 받기 실패 → 지난 저장본 (받은 날짜를 화면에)
            return payload["response"], payload, "지난 저장본"
        raise
    _write_cache(kind, key, request, data)
    return data, {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")}, "실시간"


def keyword_tool(hints: List[str], online: bool = True) -> Optional[pd.DataFrame]:
    hints = sorted({h.strip().replace(" ", "") for h in hints if h.strip()})[:5]   # 중복 빼고 정렬 → 같은 묶음은 같은 캐시 (A10)
    if not hints:
        return None
    key = ",".join(hints)

    def fetch(call):
        params = {"hintKeywords": key, "showDetail": 1}
        return params, _request(call, "keywordstool", "GET", "/keywordstool", "keywordList", params=params)

    data, payload, source = _fetch_or_cache("keywordstool", key, online, fetch)
    if data is None:
        return None
    df = pd.DataFrame(data["keywordList"])
    out = pd.DataFrame({
        "keyword": df["relKeyword"],
        "pc_qc": df["monthlyPcQcCnt"].map(_to_num),
        "mobile_qc": df["monthlyMobileQcCnt"].map(_to_num),
        "mobile_clicks": df["monthlyAveMobileClkCnt"].map(_to_num),
        "mobile_ctr": df["monthlyAveMobileCtr"].map(_to_num),
        "comp": df["compIdx"],
    })
    out["total_qc"] = out["pc_qc"] + out["mobile_qc"]
    out["tier"] = out["total_qc"].map(keyword_tier)
    out = out.drop_duplicates("keyword").sort_values("total_qc", ascending=False).reset_index(drop=True)
    return _frame_meta(out, payload, source)


def bid_estimate(keyword: str, device: str = "MOBILE", online: bool = True) -> Optional[pd.DataFrame]:
    """입찰가별 예상 실적 (과거 28일 기준 → 월 환산). 컬럼: bid, impressions, clicks, cost.
    캐시는 API 원본(28일) 그대로 두고, 읽을 때 impressions·clicks·cost에 30.4/28을 곱한다 (입찰가는 그대로).
    캐시 키에 입찰가 목록(BIDS)을 넣음 (A6). 예전 키 파일은 요청한 입찰가 목록이 지금과 같을 때만 씀.
    df.attrs: fetched_at(받은 날짜), source(예시 저장본·저장본·지난 저장본·실시간)."""
    keyword = keyword.strip().replace(" ", "")
    key = f"{keyword}|{device}|{_bids_tag()}"

    def fetch(call):
        body = {"device": device, "key": keyword, "bids": BIDS}   # keywordplus는 2024-07-16 API 공지로 없어진 항목 (naver-api-003)
        data = _request(call, "estimate", "POST", "/estimate/performance/keyword", "estimate", body=body)
        _sleep(0.5)  # 호출 사이 간격 (가이드 1-5)
        return body, data

    same_bids = lambda p: list(p.get("request", {}).get("bids", [])) == list(BIDS)  # noqa: E731
    data, payload, source = _fetch_or_cache("estimate", key, online, fetch, legacy=f"{keyword}|{device}", check=same_bids)
    if data is None:
        return None
    df = pd.DataFrame(data["estimate"])[["bid", "impressions", "clicks", "cost"]].astype(float)
    df[["impressions", "clicks", "cost"]] *= MONTH_FACTOR
    df["keyword"] = keyword
    return _frame_meta(df.sort_values("bid").reset_index(drop=True), payload, source)


def recommend_keywords(kw: pd.DataFrame, seeds=(), n: int = 5) -> pd.DataFrame:
    """세부 키워드 기회: 월 검색수 300~1만(세부, 분석 Q1 기준) & 경쟁 낮음·중간.
    입력 키워드가 있으면 그 키워드를 포함한 것만 (연관 검색어에 섞인 무관 키워드 제외), 검색수 순."""
    seeds = [x for x in seeds if x]
    if kw is None or kw.empty or not {"tier", "comp", "keyword", "total_qc"} <= set(kw.columns):
        return pd.DataFrame(columns=["keyword", "total_qc"])   # 검색어 결과가 없으면 추천도 없음
    d = kw[(kw["tier"] == "세부") & (kw["comp"].isin(["낮음", "중간"])) & (~kw["keyword"].isin(seeds))].copy()
    if seeds:
        d = d[d["keyword"].map(lambda k: any(x in k for x in seeds)).astype(bool)]   # 빈 표에서도 행 필터로 동작하게
    return d.sort_values("total_qc", ascending=False).head(n)
