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
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "interim" / "naver_hub_cache"
BASE = "https://naverapihub.apigw.ntruss.com"
SEARCH_TREND = "/search-trend/v1/search"
SHOPPING_CATEGORIES = "/shopping/v1/categories"
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


def post(path: str, body: dict, online: bool = True) -> Optional[dict]:
    """캐시가 있으면 캐시, 없고 online이면 호출 후 저장. 실패하면 None (오류 내용에 키는 담기지 않음)."""
    cache = _cache_path(path, body)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["response"]
    keys = _keys() if online else None
    if keys is None:
        return None
    headers = {"X-NCP-APIGW-API-KEY-ID": keys["NAVER_HUB_CLIENT_ID"], "X-NCP-APIGW-API-KEY": keys["NAVER_HUB_CLIENT_SECRET"],
               "Content-Type": "application/json"}
    r = requests.post(BASE + path, headers=headers, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"NAVER API HUB {path} 호출 실패: HTTP {r.status_code} {r.text[:300]}")
    data = r.json()
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
    if df is None or df.empty:
        return None
    s = df.iloc[:, 0]
    s.index = pd.to_datetime(s.index)
    s = s / s.groupby(s.index.year).transform("mean")
    idx = s.groupby(s.index.month).mean()
    idx = idx.reindex(range(1, 13)).fillna(1.0)
    return idx / idx.mean()


def shopping_category_trend(categories: Dict[str, str], start: str, end: str, time_unit: str = "month",
                            online: bool = True, **filters) -> Optional[pd.DataFrame]:
    """쇼핑 인사이트 분야별 트렌드: {분야 이름: 분야 코드(예: 50000000 패션의류)} → 상대 클릭 추이."""
    body = {"startDate": start, "endDate": end, "timeUnit": time_unit,
            "category": [{"name": n, "param": [c]} for n, c in list(categories.items())[:3]]}
    body.update({k: v for k, v in filters.items() if v})
    data = post(SHOPPING_CATEGORIES, body, online)
    return None if data is None else _results_frame(data)
