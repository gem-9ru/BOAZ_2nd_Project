"""네이버 검색광고 API 조회 + 캐시.

- 서명·호출은 src/collect/naver_api_test.py의 `call`을 그대로 씁니다 (키는 .env에서 읽고, 출력하지 않음).
  .env가 없는 배포 환경(Streamlit Cloud)에서는 같은 방식으로 서명하되 키를 환경 변수/secrets
  (NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY, NAVER_AD_CUSTOMER_ID)에서 읽습니다.
- 응답은 data/interim/naver_cache/ 에 JSON으로 저장하고, 오프라인 모드에서는 캐시만 읽습니다.
- 캐시에 없는 키워드를 오프라인으로 요청하면 None을 돌려주고, 앱이 예시 키워드(캐시)로 대체합니다.
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
import requests

from . import defaults as D
from .data_loader import keyword_tier

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "interim" / "naver_cache"
SAMPLE_KEYWORD = "필라테스"  # 캐시에 들어 있는 예시 키워드 (업종 예시일 뿐, 엔진은 업종을 가정하지 않음)

# 입찰가를 촘촘하게 요청해야 계단 모양 곡선의 꺾이는 지점을 잡을 수 있음 (API는 한 번에 최대 100개)
BIDS = (
    [70, 100, 150, 200, 250]
    + list(range(300, 3001, 100))
    + list(range(3200, 6001, 200))
    + list(range(6500, 10001, 500))
)

MONTH_FACTOR = D.DAYS_PER_MONTH / D.NAVER_ESTIMATE_DAYS  # 네이버 예상 실적(28일) → 한 달


def _cache_path(kind: str, key: str) -> Path:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:10]
    return CACHE_DIR / f"{kind}_{digest}.json"


def _read_cache(kind: str, key: str):
    path = _cache_path(kind, key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _write_cache(kind: str, key: str, request: dict, response) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"request": request, "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "response": response}
    _cache_path(kind, key).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


KEY_NAMES = ("NAVER_AD_API_KEY", "NAVER_AD_SECRET_KEY", "NAVER_AD_CUSTOMER_ID")


def _secret_keys() -> Optional[dict]:
    keys = {k: os.environ.get(k) for k in KEY_NAMES}
    if not all(keys.values()):
        try:
            import streamlit as st
            keys = {k: st.secrets.get(k) for k in KEY_NAMES}
        except Exception:
            return None
    return keys if all(keys.values()) else None


class NaverUnavailable(Exception):
    """네이버 API에 연결하지 못함 (네트워크 오류·타임아웃). 화면은 이걸 잡아 대략값으로 내려감."""


def _env_call(keys: dict):
    """naver_api_test.call과 같은 서명 방식. 키는 출력하지 않는다."""
    def call(method: str, uri: str, params=None, body=None):
        timestamp = str(round(time.time() * 1000))
        signature = base64.b64encode(hmac.new(keys["NAVER_AD_SECRET_KEY"].encode(),
                                              f"{timestamp}.{method}.{uri}".encode(), hashlib.sha256).digest()).decode()
        headers = {"Content-Type": "application/json; charset=UTF-8", "X-Timestamp": timestamp,
                   "X-API-KEY": keys["NAVER_AD_API_KEY"], "X-Customer": str(keys["NAVER_AD_CUSTOMER_ID"]),
                   "X-Signature": signature}
        try:
            r = requests.request(method, "https://api.searchad.naver.com" + uri, params=params, json=body,
                                 headers=headers, timeout=20)
        except requests.RequestException as e:
            raise NaverUnavailable(type(e).__name__) from e
        try:
            return r.json()
        except ValueError:
            return r.text
    return call


def _api_call():
    """src/collect의 call 함수(.env)를 우선 쓰고, 없으면 환경 변수·secrets 키로 서명. 둘 다 없으면 None."""
    collect_dir = str(ROOT / "src" / "collect")
    if collect_dir not in sys.path:
        sys.path.insert(0, collect_dir)
    try:
        import naver_api_test  # noqa: WPS433 (수집 담당 모듈 재사용)
        return naver_api_test.call
    except Exception:
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


def keyword_tool(hints: List[str], online: bool = True) -> Optional[pd.DataFrame]:
    hints = [h.strip().replace(" ", "") for h in hints if h.strip()][:5]
    if not hints:
        return None
    key = ",".join(hints)
    cached = _read_cache("keywordstool", key)
    data = cached["response"] if cached else None
    if data is None and online:
        call = _api_call()
        if call is None:
            return None
        params = {"hintKeywords": key, "showDetail": 1}
        data = _safe(call, "GET", "/keywordstool", params=params)
        if not (isinstance(data, dict) and "keywordList" in data):
            return None
        _write_cache("keywordstool", key, params, data)
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
    return out.drop_duplicates("keyword").sort_values("total_qc", ascending=False).reset_index(drop=True)


def bid_estimate(keyword: str, device: str = "MOBILE", online: bool = True) -> Optional[pd.DataFrame]:
    """입찰가별 예상 실적 (과거 28일 기준 → 월 환산). 컬럼: bid, impressions, clicks, cost.
    캐시는 API 원본(28일) 그대로 두고, 읽을 때 impressions·clicks·cost에 30.4/28을 곱한다 (입찰가는 그대로)."""
    keyword = keyword.strip().replace(" ", "")
    key = f"{keyword}|{device}"
    cached = _read_cache("estimate", key)
    data = cached["response"] if cached else None
    if data is None and online:
        call = _api_call()
        if call is None:
            return None
        body = {"device": device, "key": keyword, "bids": BIDS}   # keywordplus는 2024-07-16 API 공지로 없어진 항목 (naver-api-003)
        data = _safe(call, "POST", "/estimate/performance/keyword", body=body)
        if not (isinstance(data, dict) and "estimate" in data):
            return None
        _write_cache("estimate", key, body, data)
        time.sleep(0.5)  # 호출 사이 간격 (가이드 1-5)
    if data is None:
        return None
    df = pd.DataFrame(data["estimate"])[["bid", "impressions", "clicks", "cost"]].astype(float)
    df[["impressions", "clicks", "cost"]] *= MONTH_FACTOR
    df["keyword"] = keyword
    return df.sort_values("bid").reset_index(drop=True)


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
