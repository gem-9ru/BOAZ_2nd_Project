"""네이버 검색광고 API 연결 테스트.

키는 src/engine/keys.py의 read_keys 하나로 읽습니다: Streamlit secrets → 환경 변수 → 프로젝트 루트 .env (키 값은 출력하지 않음).
.env를 쓴다면 아래 세 줄을 넣습니다.
    NAVER_AD_API_KEY=...
    NAVER_AD_SECRET_KEY=...
    NAVER_AD_CUSTOMER_ID=...

실행: python src/collect/naver_api_test.py
"""
import json
import sys
import time
from pathlib import Path

import requests

BASE_URL = "https://api.searchad.naver.com"
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.engine.keys import naver_signature, read_keys  # noqa: E402  (키 읽기·서명은 엔진과 같은 함수, 검수 A13)

KEY_NAMES = ("NAVER_AD_API_KEY", "NAVER_AD_SECRET_KEY", "NAVER_AD_CUSTOMER_ID")


def _keys() -> dict:
    """부를 때 키를 읽음 (import 때 .env를 바로 읽지 않음). 없으면 키 이름만 알려 주는 오류 (값은 출력하지 않음)."""
    keys = read_keys(KEY_NAMES)
    if keys is None:
        raise RuntimeError("네이버 검색광고 키가 없어요: " + ", ".join(KEY_NAMES) + " (secrets·환경 변수·.env 중 한 곳에 넣어 주세요)")
    return keys


def headers(method: str, uri: str) -> dict:
    keys = _keys()
    timestamp = str(round(time.time() * 1000))
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": keys["NAVER_AD_API_KEY"],
        "X-Customer": str(keys["NAVER_AD_CUSTOMER_ID"]),
        "X-Signature": naver_signature(keys["NAVER_AD_SECRET_KEY"], timestamp, method, uri),
    }


def call(method: str, uri: str, params=None, body=None):
    r = requests.request(method, BASE_URL + uri, params=params, json=body,
                         headers=headers(method, uri), timeout=20)
    print(f"[{method} {uri}] HTTP {r.status_code}")
    try:
        return r.json()
    except ValueError:
        return r.text


def main():
    kw = call("GET", "/keywordstool", params={"hintKeywords": "필라테스", "showDetail": 1})
    if isinstance(kw, dict) and "keywordList" in kw:
        print("응답 최상위 키:", list(kw.keys()))
        print("연관 키워드 수:", len(kw["keywordList"]))
        print(json.dumps(kw["keywordList"][:3], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(kw, ensure_ascii=False, indent=2)[:1000])

    time.sleep(1)
    est = call("POST", "/estimate/performance/keyword",
               body={"device": "MOBILE", "keywordplus": True, "key": "필라테스",
                     "bids": [100, 300, 500, 1000, 2000, 5000]})
    print(json.dumps(est, ensure_ascii=False, indent=2)[:1500])


if __name__ == "__main__":
    main()
