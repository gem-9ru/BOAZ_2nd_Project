"""네이버 검색광고 API 연결 테스트.

프로젝트 루트의 .env 파일에 아래 세 줄을 넣고 실행합니다 (키 값은 출력하지 않음).
    NAVER_AD_API_KEY=...
    NAVER_AD_SECRET_KEY=...
    NAVER_AD_CUSTOMER_ID=...

실행: python src/collect/naver_api_test.py
"""
import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import requests

BASE_URL = "https://api.searchad.naver.com"
ROOT = Path(__file__).resolve().parents[2]


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


ENV = load_env(ROOT / ".env")
API_KEY = ENV["NAVER_AD_API_KEY"]
SECRET_KEY = ENV["NAVER_AD_SECRET_KEY"]
CUSTOMER_ID = ENV["NAVER_AD_CUSTOMER_ID"]


def headers(method: str, uri: str) -> dict:
    timestamp = str(round(time.time() * 1000))
    message = f"{timestamp}.{method}.{uri}"
    signature = base64.b64encode(
        hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": API_KEY,
        "X-Customer": str(CUSTOMER_ID),
        "X-Signature": signature,
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
