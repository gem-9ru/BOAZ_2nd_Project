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


# ── 한 달치만 고르기 (판매처 통계가 여러 달일 때) ─────────────────────
DATE_WORDS = ["날짜", "일자", "일별", "기간", "date", "day"]


def detect_date_column(df: pd.DataFrame) -> Optional[str]:
    """이름에 날짜 단어가 있고 값의 절반 이상이 날짜로 읽히는 열."""
    for c in df.columns:
        if any(w in str(c).lower() for w in DATE_WORDS):
            parsed = parse_dates(df[c])
            if parsed.notna().mean() >= 0.5:
                return c
    return None


def parse_dates(s: pd.Series) -> pd.Series:
    """'2026-10-01', '2026.10.01.', '2026/10/01', '20261001' 같은 날짜 문자열."""
    text = s.astype(str).str.strip().str.rstrip(".").str.replace(r"[./]", "-", regex=True)
    return pd.to_datetime(text, errors="coerce", format="mixed")


def months_in(df: pd.DataFrame, col: str) -> List[str]:
    return sorted(parse_dates(df[col]).dropna().dt.strftime("%Y-%m").unique().tolist())


def only_month(df: pd.DataFrame, col: str, month: str) -> pd.DataFrame:
    """month = 'YYYY-MM'인 행만."""
    return df[parse_dates(df[col]).dt.strftime("%Y-%m") == month]


# ── 퍼널 진단 (MVP 7a): 판매처 통계로 "들어온 100명 → 상품 본 ○명 → 담은 ○명 → 산 ○명" ─────────────
FUNNEL_MIN_VISITS = 100     # 들어온 사람이 이보다 적으면 판단 보류
# 단계: (키, 이전 키, 화면 이름, 빠질 때 할 일)
FUNNEL_DIAG_STEPS = [
    ("views", "visits", "들어와서 상품을 봄", "들어와서 바로 나가요. 광고 문구·사진과 실제 상품·첫 화면이 맞는지 먼저 보세요."),
    ("cart", "views", "상품을 보고 담음", "상품을 보고도 안 담아요. 상세페이지·가격·후기를 먼저 고치세요."),
    ("orders", "cart", "담고 삼", "담고도 안 사요. 배송비·결제 단계를 먼저 보세요 (공개 샘플에서도 장바구니 뒤 이탈이 큰 구간이에요)."),
]


def funnel_baseline() -> Dict[str, float]:
    """기준값: defaults.FUNNEL_STEPS의 GA4 공개 샘플 단계 전환율 (등급 C). 담고 삼 = 결제 시작 × 구매."""
    from . import defaults as D
    r = dict(D.FUNNEL_STEPS)
    return {"views": r["③ 상품 조회"], "cart": r["③ 장바구니"], "orders": r["③ 결제 시작"] * r["④ 구매"]}


def funnel_steps(totals: Dict[str, Optional[float]]) -> List[Dict]:
    """있는 단계끼리의 통과율과 기준 대비 비율: [{key, prev, name, rate, base, ratio, action}]."""
    base = funnel_baseline()
    steps = []
    for key, prev, name, action in FUNNEL_DIAG_STEPS:
        cur, before = totals.get(key), totals.get(prev)
        if cur and before:
            rate = cur / before
            steps.append({"key": key, "prev": prev, "name": name, "rate": rate, "base": base[key], "ratio": rate / base[key], "action": action})
    return steps


def lowest_step(totals: Dict[str, Optional[float]]) -> Optional[Dict]:
    """'가장 많이 빠지는 단계'의 규칙은 여기 하나: 기준 대비 비율(실측 ÷ 기준)이 가장 낮은 단계 (B5). 단계가 없으면 None."""
    steps = funnel_steps(totals)
    return min(steps, key=lambda s: s["ratio"]) if steps else None


def diagnose_funnel(totals: Dict[str, Optional[float]]) -> Optional[Dict]:
    """→ {"per100": [...], "steps": [...], "worst": 단계 또는 None, "hold"}. 들어온 사람(visits)이 있어야 100명 기준으로 그림.
    worst = lowest_step (들어온 사람이 적어 보류거나 모든 단계가 기준보다 좋으면 None)."""
    visits = totals.get("visits")
    steps = funnel_steps(totals)
    if not visits or not steps:
        return None
    short = {"views": "상품 본", "cart": "담은", "orders": "산"}
    per100 = [("들어온", 100.0)] + [(short[s["key"]], 100 * totals[s["key"]] / visits) for s in steps]
    hold = visits < FUNNEL_MIN_VISITS
    lowest = lowest_step(totals)
    worst = None if (hold or lowest["ratio"] >= 1) else lowest   # 보류 / 모든 단계가 기준보다 좋음
    return {"per100": per100, "steps": steps, "worst": worst, "hold": hold, "visits": visits}


def ad_or_store(ctr: Optional[float], diag: Optional[Dict], ctr_ok: float = 0.01) -> Optional[str]:
    """광고 리포트(클릭률)와 퍼널 진단을 합친 한 줄."""
    if ctr is None or not diag or diag["hold"]:
        return None
    if ctr < ctr_ok:
        return f"광고 클릭률이 {ctr:.1%}로 낮아요 → **광고 쪽부터** (문구·사진·타깃)."
    if diag["worst"]:
        return f"광고 클릭률은 {ctr:.1%}로 괜찮은데 가게 안에서 빠져요 → **광고보다 가게 쪽** ({diag['worst']['name']} 단계)."
    return f"광고 클릭률 {ctr:.1%}, 가게 안 단계도 기준보다 좋아요 → 예산을 늘려 볼 만해요."
