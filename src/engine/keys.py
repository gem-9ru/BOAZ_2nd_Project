"""API 키 읽기와 네이버 검색광고 서명을 한 곳에서 (검수 A13).

- 읽는 순서: Streamlit secrets → 환경 변수 → 프로젝트 루트 .env (배포 앱의 secrets가 먼저).
- 키 값은 어디에도 출력·로그·예외 문구로 내보내지 않는다. 돌려주는 dict도 화면에 그리지 않는다.
- src/collect/naver_api_test.py(수집 담당 스크립트)는 손대지 않고, 엔진은 더 이상 그 모듈을 불러오지 않는다.
"""
import base64
import hashlib
import hmac
import os
from pathlib import Path
from typing import Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"


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
    for source in (lambda: _from_secrets(names), lambda: {k: os.environ[k] for k in names if os.environ.get(k)},
                   lambda: _from_env_file(names, env_file or ENV_FILE)):
        for k, v in source().items():
            found.setdefault(k, v)
        if all(found.get(k) for k in names):
            return {k: found[k] for k in names}
    return None


def naver_signature(secret: str, timestamp: str, method: str, uri: str) -> str:
    """네이버 검색광고 API 서명: HMAC-SHA256("{timestamp}.{METHOD}.{uri}") → Base64 (쿼리는 uri에 넣지 않음)."""
    return base64.b64encode(hmac.new(secret.encode(), f"{timestamp}.{method}.{uri}".encode(), hashlib.sha256).digest()).decode()
