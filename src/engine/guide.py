"""광고 관리자 설정 가이드 (노션 11/9): 메타 목적 고르기, 자동 vs 수동, 네이버 첫 세팅 체크리스트.

확인 표시: ✅ 공식 문서·실제 파일로 확인 / △ 대행사 안내·업계 경험 기준(공식 문서 미확인) / 🧮 이 앱의 계산.
출처(△): 메타 목표 6개와 의미, 네이버 쇼핑검색광고 구조(캠페인 → 광고그룹 → 소재, 쇼핑몰 상품형, 품질지수 × 입찰가)는
대행사 안내(inside.ampm.co.kr) 기준. 메타 학습 구간 주 약 50건은 acquisition.LEARNING_EVENTS_PER_WEEK와 같은 근거(△).
"""
from typing import Dict, List, Optional

from .acquisition import LEARNING_EVENTS_PER_WEEK

WEEKS_PER_MONTH = 30.4 / 7

META_OBJECTIVES = [
    # (목적, 메타가 찾아 주는 사람, 우리에게 맞을 때, 확인)
    ("인지도", "광고를 많이 보고 기억할 사람", "새 브랜드를 알릴 때. 바로 판매를 기대하면 안 맞아요", "△"),
    ("트래픽", "링크를 누를 사람", "구매 데이터(픽셀)가 아직 없을 때 방문부터 모을 때. 누르는 사람 ≠ 사는 사람", "△"),
    ("참여", "좋아요·댓글·메시지를 남길 사람", "게시물 반응·DM 상담이 목적일 때", "△"),
    ("잠재 고객", "연락처를 남길 사람", "상담·예약 신청을 받을 때", "△"),
    ("앱 홍보", "앱을 설치·사용할 사람", "앱이 있을 때만", "△"),
    ("판매", "살 가능성이 높은 사람", "판매가 목적이고 픽셀 구매 이벤트가 설치돼 있을 때 (스마트스토어는 연동 여부 확인)", "△"),
]


def meta_plan(meta_monthly: float, expected_cpa: float, pixel_ready: bool) -> Dict:
    """메타 목적·자동 여부 추천. 판매 목적 학습에는 광고 세트당 주 약 50건이 필요(△)한데,
    주 예산 ÷ 예상 CPA가 그보다 한참 적으면 '판매'로 최적화해도 학습이 끝나지 않는다."""
    weekly = meta_monthly / WEEKS_PER_MONTH if meta_monthly > 0 else 0.0
    weekly_sales = weekly / expected_cpa if expected_cpa > 0 else 0.0
    learning_ok = weekly_sales >= LEARNING_EVENTS_PER_WEEK
    if meta_monthly <= 0:
        objective, why = None, "이번 배분에서는 메타 예산이 없어요."
    elif not pixel_ready:
        objective, why = "트래픽", ("픽셀 구매 이벤트가 아직 없으면 메타가 '살 사람'을 배울 수 없어요. 우선 트래픽으로 방문을 모으고, "
                                   "픽셀을 설치한 뒤 판매로 바꾸세요.")
    else:
        objective = "판매"
        why = ("판매가 목적이라 '판매'를 고르세요. " + (
            "예산이 학습에 충분해요." if learning_ok else
            f"다만 주 예산 {weekly:,.0f}원으로는 주 약 {weekly_sales:.1f}건이라 학습 기준(주 약 {LEARNING_EVENTS_PER_WEEK}건)에 못 미쳐요. "
            "광고 세트를 하나로 모으고, 최적화 기준을 '장바구니 담기'처럼 더 자주 일어나는 이벤트로 시작하는 방법도 있어요."))
    return {"objective": objective, "why": why, "weekly": weekly, "weekly_sales": weekly_sales, "learning_ok": learning_ok}


AUTO_VS_MANUAL = [
    # (항목, 자동(어드밴티지+)일 때, 수동일 때, 처음엔, 확인)
    ("타깃", "메타가 살 사람을 넓게 찾음", "나이·관심사를 직접 고름", "자동(넓게). 예산이 작을수록 좁히면 학습이 느려져요", "△"),
    ("노출 위치", "인스타·페이스북·릴스 등에 알아서 배분", "위치를 직접 고름", "자동", "△"),
    ("예산", "캠페인 예산을 광고 세트에 알아서 나눔", "광고 세트마다 예산을 정함", "광고 세트 1개면 어느 쪽이든 같아요", "△"),
    ("입찰", "최저 비용(자동 입찰)", "비용 상한·목표 단가를 정함", "자동. 상한은 손님 1명 한도를 알고 난 뒤", "△"),
]


def naver_bid_at(curve, spend: float) -> Optional[float]:
    """네이버 예상 실적 곡선에서 이 월 예산을 쓰게 되는 입찰가 (그 구간을 만든 입찰가) 🧮."""
    if curve is None or spend <= 0 or not getattr(curve, "segments", None):
        return None
    acc = 0.0
    for seg in curve.segments:
        acc += seg["dcost"]
        if spend <= acc + 1e-9:
            return float(seg["bid"]) if seg["bid"] == seg["bid"] else None
    return float(curve.segments[-1]["bid"])


def naver_checklist(naver_monthly: float, bid: Optional[float], keyword: str, stores: List[str]) -> List[Dict[str, str]]:
    smartstore = "스마트스토어" in stores or not stores
    daily = naver_monthly / 30.4 if naver_monthly > 0 else 0.0
    kind = "쇼핑검색광고 (쇼핑몰 상품형)" if smartstore else "사이트검색광고 (파워링크)"
    items = [
        {"step": "광고주 가입·비즈머니 충전", "detail": "네이버 광고(searchad.naver.com)에서 광고주 계정을 만들고 첫 달 예산만큼만 충전해요.", "check": "△"},
        {"step": f"캠페인 유형: {kind}",
         "detail": ("스마트스토어 상품이 네이버 쇼핑 검색 결과에 보이는 광고예요. 쇼핑 파트너존 인증으로 스마트스토어를 연동해요."
                    if smartstore else "검색 결과 위쪽에 내 사이트가 보이는 광고예요."), "check": "△"},
        {"step": "구조: 캠페인 → 광고그룹 → 소재(상품)", "detail": "처음엔 캠페인 1개, 광고그룹 1개로 시작하면 숫자를 보기 쉬워요.", "check": "△"},
        {"step": f"하루 예산: {daily:,.0f}원", "detail": f"배분한 네이버 월 {naver_monthly:,.0f}원 ÷ 30.4일. 하루 예산이 다 쓰이면 그날 광고가 멈춰요.", "check": "🧮"},
    ]
    if bid:
        items.append({"step": f"기본 입찰가: 약 {bid:,.0f}원",
                      "detail": f"'{keyword}' 예상 실적에서 이 예산을 쓰게 되는 입찰가예요. 노출 순위는 입찰가 × 품질지수라 같은 입찰가도 결과가 달라요.",
                      "check": "🧮"})
    items.append({"step": "전환(구매) 추적 켜기",
                  "detail": "한 달 뒤 리포트에 '전환수'가 잡히려면 전환 추적이 필요해요. 스마트스토어는 연동 상태를, 자사몰은 전환 스크립트 설치를 확인하세요.",
                  "check": "△"})
    items.append({"step": "광고 링크에 꼬리표", "detail": "코치가 만든 NT 꼬리표 링크(스마트스토어)나 UTM 링크(자사몰)를 쓰면 판매처 통계에서 따로 셀 수 있어요.", "check": "🧮"})
    return items
