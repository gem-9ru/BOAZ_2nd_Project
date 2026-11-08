"""초보자 측정 키트: GA4 없이 "어느 광고로 팔렸나"를 셀 수 있게 하는 두 가지.

1. 광고 링크·쿠폰 만들기
   - 스마트스토어: NT 파라미터 (nt_source·nt_medium 필수, 영문만 / nt_detail·nt_keyword 선택, 한글 가능)
     → 스마트스토어 통계 > 마케팅분석 > 사용자정의채널에서 확인 (마케팅 대행사 자료 기준, 네이버 공식 문서 미확인)
   - 자사몰: UTM (utm_source·utm_medium·utm_campaign·utm_content) → GA4·카페24 등 분석 도구가 읽음
   - 쿠팡: 외부 링크 꼬리표로 구분되지 않음 → 쿠폰 코드와 쿠팡 광고 리포트로 셈
2. 판매처 통계 파일 읽기: 스마트스토어·쿠팡·카페24 등에서 내려받은 일별 통계의 열 이름을 짐작해 방문·조회·장바구니·구매·매출로 맞춤
   (정확한 열 이름은 판매처마다 다르고 공식 양식을 확인하지 못해, 화면에서 사용자가 고칠 수 있게 함)
"""
import re
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

# 채널 → (화면 이름, 꼬리표 source, 꼬리표 medium, 쿠폰 접두어). 같은 채널은 늘 같은 이름으로 (나중에 합칠 때 섞이지 않게)
CHANNELS = {
    "naver_search": ("네이버 검색·쇼핑검색광고", "naver", "cpc", "NV"),
    "meta": ("메타 (인스타그램·페이스북)", "meta", "paid_social", "MT"),
    "kakao": ("카카오 광고", "kakao", "display", "KK"),
    "youtube": ("유튜브", "youtube", "video", "YT"),
    "influencer": ("인플루언서·공동구매", "influencer", "social", "IF"),
    "blog": ("블로그·체험단", "blog", "review", "BL"),
    "message": ("카카오 메시지·문자", "crm", "message", "MS"),
    "place": ("네이버 플레이스·당근", "local", "local", "LC"),
    "coupang": ("쿠팡 광고", "coupang", "cpc", "CP"),
}
STORE_NOTES = {
    "스마트스토어": "스마트스토어는 NT 꼬리표를 씁니다. 결과는 스마트스토어 통계 → 마케팅분석 → 사용자정의채널에서 봅니다. "
                "네이버 검색·쇼핑검색광고처럼 네이버 안에서 들어오는 손님은 꼬리표 없이도 스마트스토어가 따로 셉니다.",
    "자사몰": "자사몰은 UTM 꼬리표를 씁니다. GA4나 쇼핑몰 관리자(카페24 등)의 유입 분석에서 utm_source별로 봅니다.",
    "쿠팡": "쿠팡은 외부 링크의 꼬리표로 손님을 나눠 볼 수 없습니다. 광고마다 다른 쿠폰 코드를 쓰고, 쿠팡 광고 리포트의 판매 수와 나란히 보세요.",
    "매장·예약": "예약 링크(네이버 예약 등)에 꼬리표를 붙이거나, 광고마다 다른 쿠폰·방문 코드를 쓰세요.",
}


def _slug(text: str) -> str:
    """영문·숫자·밑줄만 (nt_source·nt_medium·utm 값은 영문만 안전)."""
    return re.sub(r"[^a-z0-9_]+", "_", (text or "").strip().lower()).strip("_")


def campaign_name(month: str, product: str = "") -> str:
    """캠페인 이름 규칙: yymm + 상품(영문). 예: 2611_coffee. 매달 같은 규칙이면 나중에 합쳐 볼 수 있음."""
    p = _slug(product)
    return f"{month}_{p}" if p else month


def build_link(base_url: str, channel: str, store: str, campaign: str, detail: str = "", keyword: str = "") -> Optional[str]:
    """광고에 붙일 링크. 기존 주소의 다른 꼬리표는 그대로 두고 덮어씀. 쿠팡은 None (꼬리표로 구분 안 됨)."""
    url = (base_url or "").strip()
    if not url or store == "쿠팡":
        return None
    if not re.match(r"^https?://", url):
        url = "https://" + url
    _, src, med, _ = CHANNELS[channel]
    if store == "스마트스토어":
        tags = {"nt_source": src, "nt_medium": med, "nt_detail": detail or campaign, "nt_keyword": keyword}
    else:
        tags = {"utm_source": src, "utm_medium": med, "utm_campaign": campaign, "utm_content": _slug(detail) or None}
    tags = {k: v for k, v in tags.items() if v}
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in tags]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query + list(tags.items())), parts.fragment))


def coupon_code(channel: str, month: str, product: str = "") -> str:
    """광고별 쿠폰 코드: 채널 접두어 + yymm (+ 상품 앞 4글자). 예: MT2611COFF. 영문 대문자·숫자만."""
    p = re.sub(r"[^A-Z0-9]", "", _slug(product).upper())[:4]
    return f"{CHANNELS[channel][3]}{month}{p}"


# ── 판매처 통계 파일 읽기 ─────────────────────────────────────────
# 열 이름 짐작 규칙: 앞에 있는 단어가 먼저 맞으면 그 열로 (판매처마다 이름이 달라 사용자가 고칠 수 있게)
FIELDS = {
    "visits": ("방문 (유입)", ["유입수", "방문자수", "방문수", "방문", "유입", "세션", "visit", "session", "users"]),
    "views": ("상품 조회", ["상품상세", "상세조회", "상품조회", "조회수", "페이지뷰", "view"]),
    "cart": ("장바구니", ["장바구니", "cart"]),
    "orders": ("구매 수", ["결제수", "결제건수", "구매건수", "주문건수", "주문수", "구매수", "판매수", "판매건수", "결제상품수량", "order", "purchase"]),
    "revenue": ("매출", ["결제금액", "판매금액", "주문금액", "매출", "revenue", "sales", "amount"]),
}
FUNNEL_ORDER = ["visits", "views", "cart", "orders"]


def detect_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """열 이름 → 항목. 한 열은 한 항목에만 씀 (예: '결제금액'이 구매 수로 잡히지 않게 매출부터 확인)."""
    norm = {c: re.sub(r"\s+", "", str(c)).lower() for c in columns}
    out, used = {}, set()
    for field in ["revenue", "cart", "views", "orders", "visits"]:
        out[field] = None
        for word in FIELDS[field][1]:
            hit = next((c for c in columns if c not in used and word.lower() in norm[c]), None)
            if hit is not None:
                out[field] = hit
                used.add(hit)
                break
    return {k: out[k] for k in FIELDS}


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[,원\s%]", "", regex=True), errors="coerce").fillna(0)


def store_totals(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> Dict[str, Optional[float]]:
    """맞춘 열의 합계 (일별 행을 모두 더함). 없는 항목은 None."""
    return {k: (float(_num(df[c]).sum()) if c and c in df.columns else None) for k, c in mapping.items()}


def store_funnel(totals: Dict[str, Optional[float]]) -> Optional[pd.DataFrame]:
    """있는 항목만으로 퍼널 표 (한 줄): 다음 단계 '로그 분석'의 퍼널 업로드 형식과 같은 열."""
    cols = [k for k in FUNNEL_ORDER if totals.get(k)]
    if len(cols) < 2:
        return None
    return pd.DataFrame([{FIELDS[k][0]: totals[k] for k in cols}])
