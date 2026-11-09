"""NAVER API HUB (네이버 클라우드): 데이터랩 검색어 트렌드 · 쇼핑 인사이트 조회 + 캐시.

- 2026-07-31 이후 새 키는 NAVER API HUB에서 발급 (예전 개발자센터 키와 헤더가 다름).
- 인증: 헤더 X-NCP-APIGW-API-KEY-ID(Client ID) / X-NCP-APIGW-API-KEY(Client Secret). 키는 출력하지 않는다.
- 키 위치: 프로젝트 루트 .env 또는 환경 변수·Streamlit secrets의 NAVER_HUB_CLIENT_ID, NAVER_HUB_CLIENT_SECRET
- 한도: 검색어 트렌드·쇼핑 인사이트 각각 월 50,000건, 키당 초당 50건. 2016-01-01 이후 데이터 (API HUB FAQ)
- 응답은 data/interim/naver_hub_cache/에 저장하고, 키가 없거나 호출이 막히면 캐시만 읽는다.
- API HUB 검색 API에는 쇼핑 검색(상품 가격)이 없다 → 객단가 후보는 이 모듈로 구할 수 없음.
"""
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "interim" / "naver_hub_cache"
# 예시 지수 파일 자리 (배포 앱용). 네이버 API HUB 약관(캐시 기간·출처 표기) 확인 뒤 넣을지 결정 → 지금은 비어 있음
# 형식: <검색어>.csv, 열 month(1~12), index(평균 1)
EXAMPLE_DIR = ROOT / "data" / "examples" / "seasonality"
BASE = "https://naverapihub.apigw.ntruss.com"
SEARCH_TREND = "/search-trend/v1/search"
KEY_NAMES = ("NAVER_HUB_CLIENT_ID", "NAVER_HUB_CLIENT_SECRET")


def _keys() -> Optional[Dict[str, str]]:
    keys = {k: os.environ.get(k) for k in KEY_NAMES}
    env = ROOT / ".env"
    if not all(keys.values()) and env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in KEY_NAMES and not keys.get(k.strip()):
                    keys[k.strip()] = v.strip().strip('"').strip("'")
    if not all(keys.values()):
        try:
            import streamlit as st
            keys = {k: keys.get(k) or st.secrets.get(k) for k in KEY_NAMES}
        except Exception:
            return None
    return keys if all(keys.values()) else None


def available() -> bool:
    return _keys() is not None


def _cache_path(path: str, body: dict) -> Path:
    digest = hashlib.md5((path + json.dumps(body, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest()[:12]
    return CACHE_DIR / f"{path.strip('/').replace('/', '_')}_{digest}.json"


class HubError(RuntimeError):
    """API HUB가 200이 아닌 응답이나 깨진 응답을 줌 (HTTP 오류). 키는 담기지 않음."""


def post(path: str, body: dict, online: bool = True) -> Optional[dict]:
    """캐시가 있으면 캐시, 없고 online이면 호출 후 저장. 키가 없으면 None. 연결 실패는 requests 오류, HTTP 오류는 HubError."""
    cache = _cache_path(path, body)
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))["response"]
        except (OSError, ValueError, KeyError):
            pass                                 # 깨진 캐시는 없는 것으로 (검수 A12)
    keys = _keys() if online else None
    if keys is None:
        return None
    headers = {"X-NCP-APIGW-API-KEY-ID": keys["NAVER_HUB_CLIENT_ID"], "X-NCP-APIGW-API-KEY": keys["NAVER_HUB_CLIENT_SECRET"],
               "Content-Type": "application/json"}
    r = requests.post(BASE + path, headers=headers, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), timeout=20)
    if r.status_code != 200:
        raise HubError(f"NAVER API HUB {path} 호출 실패: HTTP {r.status_code} {r.text[:300]}")
    try:
        data = r.json()
    except ValueError as e:
        raise HubError(f"NAVER API HUB {path} 응답이 JSON이 아님") from e
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"request": body, "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"), "response": data},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def _results_frame(data: dict) -> pd.DataFrame:
    """{"results": [{"title", "data": [{"period", "ratio"}]}]} → 열 = 그룹 이름, 행 = 기간."""
    frames = {}
    for res in data.get("results", []):
        d = pd.DataFrame(res.get("data", []))
        if len(d):
            frames[res["title"]] = d.set_index("period")["ratio"].astype(float)
    return pd.DataFrame(frames).sort_index()


def search_trend(groups: Dict[str, List[str]], start: str, end: str, time_unit: str = "month",
                 online: bool = True, **filters) -> Optional[pd.DataFrame]:
    """검색어 트렌드: 주제어(최대 5개) × 검색어(그룹당 최대 5개)의 상대 검색량 (기간 최대값 = 100).
    filters: device("pc"/"mo"), gender("m"/"f"), ages(["1".."11"])."""
    body = {"startDate": start, "endDate": end, "timeUnit": time_unit,
            "keywordGroups": [{"groupName": g, "keywords": kws[:5]} for g, kws in list(groups.items())[:5]]}
    body.update({k: v for k, v in filters.items() if v})
    data = post(SEARCH_TREND, body, online)
    return None if data is None else _results_frame(data)


def seasonality(keyword: str, years: int = 3, end: Optional[str] = None, online: bool = True) -> Optional[pd.Series]:
    """월별 계절 지수 (1~12월, 평균 = 1). 최근 years년 월간 검색 지수를 해마다 평균 1로 맞춘 뒤 같은 달끼리 평균.
    해마다 나누는 이유: 전체 검색량이 늘거나 줄어든 추세를 계절성과 섞지 않기 위해."""
    end_ts = pd.Timestamp(end) if end else (pd.Timestamp.today().normalize() - pd.offsets.MonthEnd(1))
    start_ts = (end_ts - pd.DateOffset(years=years)) + pd.offsets.MonthBegin(1)
    df = search_trend({keyword: [keyword]}, start_ts.strftime("%Y-%m-%d"), end_ts.strftime("%Y-%m-%d"), "month", online)
    return _index_from_frame(df)


PARTIAL_NOTE = "1년이 안 되는 자료라 계절 차이가 작게 보일 수 있어요"


def index_from_series(s: pd.Series) -> pd.Series:
    """월별 검색 지수 시계열 → 1~12월 계절 지수(평균 1). 꽉 찬 12개월이 있는 해만 써서 해마다 평균 1로 맞춤 (검수 A1:
    첫해·끝해가 몇 달뿐인데 그 해 평균으로 나누면 그 달들이 눌림). 꽉 찬 해가 없으면 예전처럼 하되 attrs["partial"]=True."""
    s = s.copy()
    s.index = pd.to_datetime(s.index)
    months = s.groupby(s.index.year).apply(lambda x: x.index.month.nunique())
    full = months[months == 12].index
    partial = len(full) == 0
    if not partial:
        s = s[s.index.year.isin(full)]
    s = s / s.groupby(s.index.year).transform("mean")
    idx = s.groupby(s.index.month).mean()
    idx = idx.reindex(range(1, 13)).fillna(1.0)
    idx = idx / idx.mean()
    idx.attrs["partial"] = partial
    return idx


def _index_from_frame(df: Optional[pd.DataFrame]) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None
    return index_from_series(df.iloc[:, 0])


def _from_saved(keyword: str) -> Optional[pd.Series]:
    """저장된 검색어 트렌드 응답 중 이 검색어 하나·월 단위인 가장 최근 것 (기간이 달라도 씀)."""
    best = None
    for f in sorted(CACHE_DIR.glob("search-trend_v1_search_*.json")) if CACHE_DIR.exists() else []:
        try:
            saved = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        req = saved.get("request", {})
        groups = req.get("keywordGroups", [])
        if req.get("timeUnit") == "month" and len(groups) == 1 and groups[0].get("keywords") == [keyword]:
            n = sum(len(r.get("data", [])) for r in saved.get("response", {}).get("results", []))
            rank = (n, saved.get("fetched_at", ""))        # 긴 기간(꽉 찬 해가 있을 가능성) 먼저, 그다음 최근 (A1)
            if best is None or rank > best[0]:
                best = (rank, saved)
    return None if best is None else _index_from_frame(_results_frame(best[1]["response"]))


def _from_example(keyword: str) -> Optional[pd.Series]:
    f = EXAMPLE_DIR / f"{keyword}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f).set_index("month")["index"].reindex(range(1, 13)).fillna(1.0)
    return d / d.mean()


def seasonality_safe(keyword: str, online: Optional[bool] = None) -> Tuple[Optional[pd.Series], str]:
    """(1~12월 지수 또는 None, 출처). 실시간 → 저장된 응답 → 예시 파일 → 없음. 어떤 오류도 앱을 멈추지 않는다."""
    keyword = (keyword or "").strip().replace(" ", "")
    if not keyword:
        return None, "계절성 미반영 (검색어 없음)"
    online = available() if online is None else online
    note = lambda i, s: s + (f" · {PARTIAL_NOTE}" if i.attrs.get("partial") else "")  # noqa: E731
    if online:
        try:
            idx = seasonality(keyword, online=True)
            if idx is not None:
                return idx, note(idx, "네이버 데이터랩 (검색어 트렌드)")
        except (requests.RequestException, HubError):   # 연결 실패·HTTP 오류만 → 아래 저장본으로 (코드 버그는 숨기지 않음, A15)
            pass
    idx = _from_saved(keyword)
    if idx is not None:
        return idx, note(idx, "네이버 데이터랩 (검색어 트렌드, 저장된 응답)")
    idx = _from_example(keyword)
    if idx is not None:
        return idx, "네이버 데이터랩 (검색어 트렌드, 예시 지수 파일)"
    return None, "계절성 미반영 (" + ("검색어 트렌드를 불러오지 못함" if online else "검색어 트렌드 키·저장본 없음") + ")"
