"""추적 링크 만들기 (T07): 같은 입력이면 늘 같은 링크.

- 스마트스토어: NT 꼬리표 (nt_source·nt_medium은 필수·영문만, nt_detail·nt_keyword는 선택·한글 가능)
- 자사몰: UTM 꼬리표 (utm_source·utm_medium·utm_campaign)
- 주소에 이미 붙어 있던 다른 꼬리표는 그대로 두고, 같은 이름만 덮어쓴다.
"""
import re
import unicodedata
from typing import List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def slugify(text: object, fallback: str = "item") -> str:
    """영문 소문자·숫자·밑줄(`[a-z0-9_]`)만 남김. 남는 게 없으면 fallback(이것도 같은 규칙으로 정리)."""
    raw = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    if slug:
        return slug
    if fallback and fallback != text:
        return slugify(fallback, fallback="")
    return ""


def nt_params(source: str, medium: str, detail: str = "", keyword: str = "") -> List[Tuple[str, str]]:
    """스마트스토어 NT 꼬리표 (정해진 순서). source·medium은 영문으로 정리, detail·keyword는 한글 그대로."""
    tags = [("nt_source", slugify(source, "ad")), ("nt_medium", slugify(medium, "paid")),
            ("nt_detail", (detail or "").strip()), ("nt_keyword", (keyword or "").strip())]
    return [(k, v) for k, v in tags if v]


def utm_params(source: str, medium: str, campaign: str, content: str = "") -> List[Tuple[str, str]]:
    """자사몰 UTM 꼬리표 (정해진 순서). 값은 모두 영문으로 정리."""
    tags = [("utm_source", slugify(source, "ad")), ("utm_medium", slugify(medium, "paid")),
            ("utm_campaign", slugify(campaign, "campaign")), ("utm_content", slugify(content, ""))]
    return [(k, v) for k, v in tags if v]


def query_string(params: List[Tuple[str, str]]) -> str:
    """꼬리표 목록 → `a=1&b=2` (한글은 %인코딩). 메타 'URL 매개변수' 칸에 그대로 넣는 값."""
    return urlencode(params)


def attach(url: str, params: List[Tuple[str, str]]) -> str:
    """주소에 꼬리표를 붙임. 기존 쿼리는 보존, 같은 이름은 덮어씀. 주소가 비어 있으면 ''."""
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    parts = urlsplit(url)
    names = {k for k, _ in params}
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in names]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept + list(params)), parts.fragment))


def nt_link(url: str, source: str, medium: str, detail: str = "", keyword: str = "") -> str:
    """스마트스토어 링크 + NT 꼬리표."""
    return attach(url, nt_params(source, medium, detail, keyword))


def utm_link(url: str, source: str, medium: str, campaign: str, content: str = "") -> str:
    """자사몰 링크 + UTM 꼬리표."""
    return attach(url, utm_params(source, medium, campaign, content))
