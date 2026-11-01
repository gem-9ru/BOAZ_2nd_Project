"""네이버 검색광고 API 조회 + 캐시.

- 서명·호출은 src/collect/naver_api_test.py의 `call`을 그대로 씁니다 (키는 .env에서 읽고, 출력하지 않음).
- 응답은 data/interim/naver_cache/ 에 JSON으로 저장하고, 오프라인 모드에서는 캐시만 읽습니다.
- 캐시에 없는 키워드를 오프라인으로 요청하면 None을 돌려주고, 앱이 예시 키워드(캐시)로 대체합니다.
"""
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd

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


def _api_call():
    """src/collect의 call 함수를 가져온다. .env가 없거나 키가 없으면 None."""
    collect_dir = str(ROOT / "src" / "collect")
    if collect_dir not in sys.path:
        sys.path.insert(0, collect_dir)
    try:
        import naver_api_test  # noqa: WPS433 (수집 담당 모듈 재사용)
    except Exception:
        return None
    return naver_api_test.call


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
        data = call("GET", "/keywordstool", params=params)
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
    return out.drop_duplicates("keyword").sort_values("total_qc", ascending=False).reset_index(drop=True)


def bid_estimate(keyword: str, device: str = "MOBILE", online: bool = True) -> Optional[pd.DataFrame]:
    """입찰가별 예상 실적 (월간 예상치로 간주). 컬럼: bid, impressions, clicks, cost."""
    keyword = keyword.strip().replace(" ", "")
    key = f"{keyword}|{device}"
    cached = _read_cache("estimate", key)
    data = cached["response"] if cached else None
    if data is None and online:
        call = _api_call()
        if call is None:
            return None
        body = {"device": device, "keywordplus": True, "key": keyword, "bids": BIDS}
        data = call("POST", "/estimate/performance/keyword", body=body)
        if not (isinstance(data, dict) and "estimate" in data):
            return None
        _write_cache("estimate", key, body, data)
        time.sleep(0.5)  # 호출 사이 간격 (가이드 1-5)
    if data is None:
        return None
    df = pd.DataFrame(data["estimate"])[["bid", "impressions", "clicks", "cost"]].astype(float)
    df["keyword"] = keyword
    return df.sort_values("bid").reset_index(drop=True)
