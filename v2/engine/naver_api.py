"""네이버 API 호출 + 저장본(캐시) 한 곳에 모음 (v2).

- 키 읽기 순서: Streamlit secrets → 환경 변수 → 프로젝트 루트 .env. 키 값은 출력·로그·예외 문구에 넣지 않는다.
- 검색광고 API: GET /keywordstool (서명 필요). 데이터랩 HUB: POST 쇼핑 인사이트 (헤더 키).
- 저장본 순서: v2/data/cache/ (git 제외, 7일 안) → v2/data/cache_examples/ (시연용 고정) → 온라인 호출 → 오래된 저장본 → None.
- 오류는 NaverError(쉬운 문장)로 모아 두고, 위쪽(market)이 잡아서 앱을 멈추지 않는다.
- 호출 규칙: 키워드 도구는 호출 사이 간격, 429면 쉬었다 한 번만 다시, 연달아 429면 5분 동안 모든 호출을 멈춘다.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import requests

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
CACHE_DIR = ROOT / "v2" / "data" / "cache"
EXAMPLES_DIR = ROOT / "v2" / "data" / "cache_examples"
MAX_AGE_DAYS = 7

AD_BASE = "https://api.searchad.naver.com"
HUB_BASE = "https://naverapihub.apigw.ntruss.com"
AD_KEYS = ("NAVER_AD_API_KEY", "NAVER_AD_SECRET_KEY", "NAVER_AD_CUSTOMER_ID")
HUB_KEYS = ("NAVER_HUB_CLIENT_ID", "NAVER_HUB_CLIENT_SECRET")

# 호출 규칙 상태 (테스트에서 _sleep·_now를 바꿔 끼움)
KW_GAP = 1.5            # 키워드 도구 호출 사이 최소 간격(초)
RETRY_WAIT = 6.0        # 429 뒤 쉬는 시간(초)
BURST_COUNT, BURST_WINDOW, PAUSE_SECONDS = 2, 10.0, 300.0
_STATE = {"rate_hits": [], "paused_until": 0.0, "last_kw": 0.0}
_sleep, _now = time.sleep, time.time


class NaverError(Exception):
    """네이버 호출 실패. message는 사장님께 보여 줘도 되는 쉬운 문장 (키는 담기지 않음)."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.message, self.status = message, status


# ── 마지막 오류 (앱이 "왜 실시간 조회가 안 됐는지" 보여 주기용) ───────────────
_LAST = {"error": None}
UNKNOWN_ERROR = "네이버에서 값을 가져오는 중 문제가 생겼어요. 지금은 저장해 둔 값으로 보여 드려요."


def last_error() -> Optional[str]:
    """가장 최근 네이버 호출이 실패했으면 쉬운 문장, 성공했으면 None. (키 값은 담기지 않음)"""
    return _LAST["error"]


def _set_error(message: Optional[str]) -> None:
    _LAST["error"] = message


def _guarded(kind: str, key: str, online: bool, call: Callable[[], object]) -> Optional[dict]:
    """fetch_cached를 부르되 어떤 예외도 앱으로 새지 않게 막고, 실패 문장을 last_error에 남김."""
    try:
        data, _ = fetch_cached(kind, key, online, call)
    except NaverError as e:
        _set_error(e.message)
        return None
    except Exception:  # noqa: BLE001  (SSL·프록시 등 예상 못 한 오류도 앱을 멈추지 않음; 문구에는 원문을 넣지 않음)
        _set_error(UNKNOWN_ERROR)
        return None
    return data


# ── 키 읽기·서명 (src/engine/keys.py를 옮겨 씀) ─────────────────────────────
def _from_secrets(names: Iterable[str]) -> Dict[str, str]:
    try:
        import streamlit as st
        return {k: st.secrets.get(k) for k in names if st.secrets.get(k)}
    except Exception:  # noqa: BLE001  (secrets 파일 없음·Streamlit 밖)
        return {}


def _from_env_file(names: Iterable[str], path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            if k.strip() in names:
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def read_keys(names: Iterable[str], env_file: Optional[Path] = None) -> Optional[Dict[str, str]]:
    """이름마다 secrets → 환경 변수 → .env 순으로 찾음. 하나라도 없으면 None."""
    names = tuple(names)
    found: Dict[str, str] = {}
    sources = (lambda: _from_secrets(names), lambda: {k: os.environ[k] for k in names if os.environ.get(k)},
               lambda: _from_env_file(names, env_file or ENV_FILE))
    for source in sources:
        for k, v in source().items():
            found.setdefault(k, v)
        if all(found.get(k) for k in names):
            return {k: found[k] for k in names}
    return None


def naver_signature(secret: str, timestamp: str, method: str, uri: str) -> str:
    """검색광고 API 서명: HMAC-SHA256("{timestamp}.{METHOD}.{uri}") → Base64 (쿼리는 uri에 넣지 않음)."""
    msg = f"{timestamp}.{method}.{uri}".encode()
    return base64.b64encode(hmac.new(secret.encode(), msg, hashlib.sha256).digest()).decode()


def ad_available() -> bool:
    return read_keys(AD_KEYS) is not None


def hub_available() -> bool:
    return read_keys(HUB_KEYS) is not None


# ── 저장본 ────────────────────────────────────────────────────────────────
def cache_name(kind: str, key: str) -> str:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:10]
    return f"{kind}_{digest}.json"


def _load(path: Path) -> Optional[dict]:
    """저장본 한 개. 없거나 깨졌으면 None."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) and "response" in payload else None
    except (OSError, ValueError):
        return None


def _stale(payload: dict) -> bool:
    try:
        got = time.mktime(time.strptime(payload.get("fetched_at", ""), "%Y-%m-%d %H:%M:%S"))
    except (TypeError, ValueError):
        return True
    return _now() - got > MAX_AGE_DAYS * 86_400


def save(kind: str, key: str, response, directory: Optional[Path] = None) -> None:
    """응답만 저장 (요청 키·헤더는 저장하지 않음)."""
    base = directory or CACHE_DIR
    try:
        base.mkdir(parents=True, exist_ok=True)
        payload = {"key": key, "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "response": response}
        (base / cache_name(kind, key)).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass  # 저장 실패는 조용히 넘김 (다음에 다시 받으면 됨)


def fetch_cached(kind: str, key: str, online: bool, call: Callable[[], object]):
    """저장본 → 시연 저장본 → (online이면) call() → 오래된 저장본. → (응답, 출처) 또는 (None, "").
    call이 NaverError를 내면 오래된 저장본이 있으면 그것을, 없으면 NaverError를 그대로 올림."""
    name = cache_name(kind, key)
    mine = _load(CACHE_DIR / name)
    if mine is not None and (not online or not _stale(mine)):
        return mine["response"], "저장본"
    pinned = _load(EXAMPLES_DIR / name)
    if pinned is not None:
        return pinned["response"], "예시 저장본"
    if not online:
        return (mine["response"], "저장본") if mine else (None, "")
    try:
        data = call()
    except NaverError as e:
        if mine is not None:
            _set_error(e.message)        # 오래된 저장본으로 대신 보여 주지만 실시간 조회는 실패했음
            return mine["response"], "지난 저장본"
        raise
    if data is None:
        return (mine["response"], "지난 저장본") if mine else (None, "")
    save(kind, key, data)
    return data, "실시간"


# ── 검색광고 API: 키워드 도구 ────────────────────────────────────────────
def _paused() -> bool:
    return _now() < _STATE["paused_until"]


def _note_429() -> None:
    """429가 몇 초 안에 연달아 쌓이면 5분 동안 멈춤."""
    now = _now()
    hits = [h for h in _STATE["rate_hits"] if now - h <= BURST_WINDOW] + [now]
    _STATE["rate_hits"] = hits
    if len(hits) >= BURST_COUNT:
        _STATE["paused_until"] = now + PAUSE_SECONDS


def _http_ad(keys: Dict[str, str], params: dict):
    """서명해서 한 번 부름 → requests 응답. (테스트에서 이 함수를 바꿔 끼움)"""
    uri = "/keywordstool"
    ts = str(round(time.time() * 1000))
    headers = {"Content-Type": "application/json; charset=UTF-8", "X-Timestamp": ts,
               "X-API-KEY": keys["NAVER_AD_API_KEY"], "X-Customer": str(keys["NAVER_AD_CUSTOMER_ID"]),
               "X-Signature": naver_signature(keys["NAVER_AD_SECRET_KEY"], ts, "GET", uri)}
    return requests.get(AD_BASE + uri, params=params, headers=headers, timeout=20)


def _to_error(resp) -> NaverError:
    status = getattr(resp, "status_code", None)
    if status in (429,):
        return NaverError("네이버에 요청이 너무 많아 잠시 막혔어요. 몇 분 뒤 다시 시도해 주세요.", status)
    if status == 403:
        return NaverError("네이버 연결 권한이나 시계가 맞지 않아요. 지금은 저장해 둔 값으로 보여 드려요.", status)
    return NaverError("네이버에서 값을 못 가져왔어요. 지금은 저장해 둔 값으로 보여 드려요.", status)


def keyword_tool_raw(hints: List[str]) -> Optional[dict]:
    """연관 키워드 원본 응답({"keywordList": [...]}). 키가 없으면 None. 실패는 NaverError."""
    keys = read_keys(AD_KEYS)
    if keys is None:
        return None
    if _paused():
        raise NaverError("네이버에 요청이 몰려 5분 동안 쉬는 중이에요. 지금은 저장해 둔 값으로 보여 드려요.", 429)
    gap = KW_GAP - (_now() - _STATE["last_kw"])
    if gap > 0:
        _sleep(gap)
    params = {"hintKeywords": ",".join(hints), "showDetail": 1}
    for attempt in (0, 1):
        _STATE["last_kw"] = _now()
        try:
            resp = _http_ad(keys, params)
        except Exception as e:  # noqa: BLE001  (연결 실패뿐 아니라 SSL·프록시 오류도)
            raise NaverError("네이버에 연결하지 못했어요. 지금은 저장해 둔 값으로 보여 드려요.") from e
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError as e:
                raise NaverError("네이버 응답을 읽지 못했어요.", 200) from e
            if isinstance(data, dict) and "keywordList" in data:
                return data
            raise NaverError("네이버 응답이 예상과 달라요.", 200)
        if resp.status_code != 429:
            raise _to_error(resp)
        _note_429()
        if attempt == 1 or _paused():
            raise _to_error(resp)
        _sleep(RETRY_WAIT)
    return None


def keyword_tool(hints: List[str], online: bool = True) -> Optional[dict]:
    """힌트 키워드(최대 5개) → keywordstool 응답. 같은 묶음은 같은 저장본. 못 받으면 None."""
    hints = sorted({h.strip().replace(" ", "") for h in hints if h and h.strip()})[:5]
    if not hints:
        return None
    key = ",".join(hints)
    _set_error(None)
    return _guarded("keywordstool", key, online and ad_available(), lambda: keyword_tool_raw(hints))


# ── 데이터랩 HUB: 쇼핑 인사이트 ──────────────────────────────────────────
def _http_hub(keys: Dict[str, str], path: str, body: dict):
    """HUB에 POST 한 번 → requests 응답. (테스트에서 이 함수를 바꿔 끼움)"""
    headers = {"X-NCP-APIGW-API-KEY-ID": keys["NAVER_HUB_CLIENT_ID"],
               "X-NCP-APIGW-API-KEY": keys["NAVER_HUB_CLIENT_SECRET"], "Content-Type": "application/json"}
    return requests.post(HUB_BASE + path, headers=headers,
                         data=json.dumps(body, ensure_ascii=False).encode("utf-8"), timeout=20)


def hub_raw(path: str, body: dict) -> Optional[dict]:
    """HUB 한 번 호출 → 응답 dict. 키가 없으면 None. 실패는 NaverError."""
    keys = read_keys(HUB_KEYS)
    if keys is None:
        return None
    try:
        resp = _http_hub(keys, path, body)
    except Exception as e:  # noqa: BLE001
        raise NaverError("네이버 데이터랩에 연결하지 못했어요. 지금은 저장해 둔 값으로 보여 드려요.") from e
    if resp.status_code != 200:
        raise _to_error(resp)
    try:
        data = resp.json()
    except ValueError as e:
        raise NaverError("네이버 데이터랩 응답을 읽지 못했어요.", 200) from e
    if not isinstance(data, dict) or "results" not in data:
        raise NaverError("네이버 데이터랩 응답이 예상과 달라요.", 200)
    return data


def shopping_insight(path: str, category: str, keyword: Optional[str] = None, online: bool = True,
                     time_unit: str = "month", start: Optional[str] = None, end: Optional[str] = None) -> Optional[dict]:
    """쇼핑 인사이트 (분야 또는 분야+키워드). path 예: /shopping/v1/category/keyword/gender.
    저장본 이름은 (경로, 분야, 키워드)로만 정하고 기간은 넣지 않음 → 시연 저장본이 날짜와 상관없이 맞음."""
    key = f"{path}|{category}|{keyword or ''}|{time_unit}"
    body = {"startDate": start or _default_start(), "endDate": end or _default_end(), "timeUnit": time_unit,
            "category": category}
    if keyword:
        body["keyword"] = keyword
    _set_error(None)
    return _guarded("hub", key, online and hub_available(), lambda: hub_raw(path, body))


def _default_end() -> str:
    t = time.localtime(_now())
    y, m = (t.tm_year, t.tm_mon - 1) if t.tm_mon > 1 else (t.tm_year - 1, 12)
    # 지난달 말일 (28일로 둬도 월 단위 조회에는 영향 없음)
    last = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}[m]
    return f"{y:04d}-{m:02d}-{last:02d}"


def _default_start() -> str:
    """지난달 기준 12개월 전 달의 1일 (꽉 찬 12개월)."""
    end = _default_end()
    y, m = int(end[:4]), int(end[5:7])
    m += 1
    if m > 12:
        y, m = y, 1
    else:
        y -= 1
    return f"{y:04d}-{m:02d}-01"
