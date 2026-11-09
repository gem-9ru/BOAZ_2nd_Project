"""광고 관리자 설정 가이드 (노션 11/9): 메타 목적 고르기, 자동 vs 수동, 네이버 첫 세팅 체크리스트.

확인 표시: ✅ 공식 문서로 확인 / △ 공식 문서가 아닌 다른 자료·코치 판단 / ❓ 확인 못 함 / 🧮 이 앱의 계산.
근거: 세팅 카드 data/rag/*.md (공식 도움말 요약, 항목마다 card = 카드 id). 2026-11-09 공식 문서와 맞춤 (data/rag/README.md '다른 곳' 15곳).
"""
from typing import Dict, List, Optional

from .acquisition import LEARNING_EVENTS_PER_WEEK

WEEKS_PER_MONTH = 30.4 / 7
DAILY_BUDGET_X = 10        # ✅ 메타: 일일 예산 ≥ 성과 목표 평균 비용 × 10 (결과당 비용 목표 입찰이면 × 5) [meta-bud-003]
DAILY_OVERSPEND = 0.75     # ✅ 메타: 어떤 날은 일일 예산보다 최대 75% 더 씀, 주 합계는 일일 예산 × 7 이하 [meta-bud-001]
NAVER_MIN_BID = {"파워링크": 70, "쇼핑검색": 50}   # ✅ 네이버 최소 입찰가 [naver-setup-011]


def daily_budget(monthly: float) -> float:
    """하루 예산 = 월 배분 ÷ 30.4일 (네이버·메타 공통, 앱 계산)."""
    return monthly / 30.4 if monthly > 0 else 0.0

META_OBJECTIVES = [
    # (목적, 메타가 찾아 주는 사람, 우리에게 맞을 때, 확인) — 목표 6개 ✅ [meta-obj-001]
    ("인지도", "광고를 기억할 가능성이 높은 사람에게 최대한 많이", "새 브랜드를 알릴 때. 바로 판매를 기대하면 안 맞아요", "✅"),
    ("트래픽", "웹사이트 같은 랜딩 페이지로 올 사람", "구매가 메타로 잡히지 않을 때(스마트스토어 등) 방문부터 모을 때. 누르는 사람 ≠ 사는 사람", "✅"),
    ("참여", "메시지·게시물 반응을 남길 사람", "게시물 반응·DM 상담이 목적일 때", "✅"),
    ("잠재 고객", "연락처를 남길 사람", "상담·예약 신청을 받을 때", "✅"),
    ("앱 홍보", "앱을 설치·사용할 사람", "앱이 있을 때만", "✅"),
    ("판매 (표에는 '매출')", "제품을 살 가능성이 높은 사람", "내 사이트에 픽셀 구매 이벤트가 있을 때. 스마트스토어에 픽셀을 달 수 있는지는 공식 확인 못 함 ❓", "✅"),
]


def meta_plan(meta_monthly: float, expected_cpa: float, pixel_ready: bool, stores: Optional[List[str]] = None,
              click_cost: Optional[float] = None) -> Dict:
    """메타 목적 추천과 예산 점검.
    - 스마트스토어(자사몰 없음)면 '판매'를 기본으로 권하지 않고 '트래픽': 스마트스토어 픽셀은 공식 확인 못 함 ❓ [meta-obj-003]
    - 머신 러닝 단계 ✅: 광고 세트당 마지막 큰 수정 뒤 7일 안에 결과 약 50개 [meta-lrn-001]
    - 일일 예산 권장 ✅: 성과 목표 평균 비용의 10배 이상 [meta-bud-003], 하루 최대 75% 더 쓸 수 있음 [meta-bud-001]"""
    stores = stores or []
    weekly = meta_monthly / WEEKS_PER_MONTH if meta_monthly > 0 else 0.0
    daily = daily_budget(meta_monthly)
    weekly_sales = weekly / expected_cpa if expected_cpa > 0 else 0.0
    learning_ok = weekly_sales >= LEARNING_EVENTS_PER_WEEK
    smartstore_only = "스마트스토어" in stores and "자사몰" not in stores
    if meta_monthly <= 0:
        objective, why, result_cost = None, "이번 배분에서는 메타 예산이 없어요.", None
    elif smartstore_only:
        objective, result_cost = "트래픽", click_cost
        why = ("스마트스토어로 보내는 광고라 '트래픽'을 기본으로 권해요. 스마트스토어에 메타 픽셀을 달아 구매를 메타로 보낼 수 있는지는 "
               "**공식 확인 못 함** ❓(대행사 자료는 어렵다고 안내)이라, 구매는 코치의 NT 꼬리표 링크로 판매처 통계에서 따로 세요. "
               "누르는 사람이 사는 사람은 아니라는 점은 꼭 기억하세요.")
    elif not pixel_ready:
        objective, result_cost = "트래픽", click_cost
        why = ("픽셀 구매 이벤트가 아직 없으면 메타가 '살 사람'을 배울 수 없어요. 우선 트래픽으로 방문을 모으고, "
               "픽셀을 설치한 뒤 판매로 바꾸세요.")
    else:
        objective, result_cost = "판매", expected_cpa
        why = ("판매가 목적이라 '판매'를 고르세요. " + (
            "예산이 머신 러닝 단계를 끝내기에 충분해요." if learning_ok else
            f"다만 주 예산 {weekly:,.0f}원으로는 주 약 {weekly_sales:.1f}건이라, 머신 러닝 단계 기준(광고 세트당 마지막 큰 수정 뒤 "
            f"7일 안에 결과 약 {LEARNING_EVENTS_PER_WEEK}개)에 못 미쳐 '제한된 머신 러닝'으로 남기 쉬워요. "
            "광고 세트를 하나로 모으고, 최적화 기준을 '장바구니 담기'처럼 더 자주 일어나는 이벤트로 시작하는 방법도 있어요."))
    rec_daily = result_cost * DAILY_BUDGET_X if result_cost else None
    return {"objective": objective, "why": why, "weekly": weekly, "weekly_sales": weekly_sales, "learning_ok": learning_ok,
            "daily": daily, "daily_max": daily * (1 + DAILY_OVERSPEND), "recommended_daily": rec_daily,
            "daily_ok": (rec_daily is None) or daily >= rec_daily}


AUTO_VS_MANUAL = [
    # (항목, 자동(어드밴티지+)일 때, 수동일 때, 처음엔, 확인)
    ("타깃", "메타가 살 사람을 넓게 찾음", "나이·관심사를 직접 고름", "자동(넓게). 예산이 작을수록 좁히면 머신 러닝이 느려져요", "△"),
    ("노출 위치", "인스타·페이스북·릴스 등에 알아서 배분", "위치를 직접 고름 (판매·잠재 고객·앱 홍보 목표는 수동 선택이 단계적으로 없어지는 중)",
     "자동", "✅"),
    ("예산", "캠페인 예산을 광고 세트에 알아서 나눔 (어드밴티지+ 캠페인 예산)", "광고 세트마다 예산을 정함", "광고 세트 1개면 어느 쪽이든 같아요", "✅"),
    ("입찰", "최고 볼륨 (기본 자동 입찰, 예전 이름 '최저 비용')", "결과당 비용 목표·비용 한도를 정함 (목표를 쓰면 일일 예산 ≥ 목표 × 5)",
     "자동(최고 볼륨). 한도는 손님 1명 한도를 알고 난 뒤", "✅"),
]
AUTO_CARDS = {"타깃": "meta-tgt-001", "노출 위치": "meta-plc-001", "예산": "meta-bud-002", "입찰": "meta-auto-002"}
META_NOTES = [
    # (내용, 확인, 카드)
    ("기여 설정 기본값은 클릭 후 7일·조회 후 1일·참여한 조회 후 1일이에요. 광고를 보기만 한 사람이 다음 날 산 것도 결과로 잡혀 "
     "광고 관리자의 구매 수가 실제 주문보다 많을 수 있어요.", "✅", "meta-msr-003"),
    ("화면에서는 '학습 단계'가 아니라 '머신 러닝 단계', '학습 제한'이 아니라 '제한된 머신 러닝'이라고 나와요. "
     "머신 러닝 중에는 하루 숫자로 판단하지 마세요.", "✅", "meta-lrn-001"),
]


def naver_bid_at(curve, spend: float) -> Optional[float]:
    """네이버 예상 실적 곡선에서 이 월 예산을 쓰게 되는 입찰가 (그 구간을 만든 입찰가) 🧮. 파워링크(키워드) 입찰 기준."""
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
    daily = daily_budget(naver_monthly)
    kind = "쇼핑검색광고 (쇼핑몰 상품형)" if smartstore else "사이트검색광고 (파워링크)"
    items = [
        {"step": "광고주 가입·비즈머니 충전", "detail": "네이버애즈에서 광고주 계정을 만들고 첫 달 예산만큼만 충전해요.", "check": "✅", "card": "naver-setup-002"},
        {"step": f"캠페인 유형: {kind}",
         "detail": ("스마트스토어 상품이 네이버 쇼핑 영역에 보이는 광고예요. 키워드를 넣지 않고 상품을 소재로 넣어요. "
                    "파워링크용 '웹사이트'와 별도로 '쇼핑몰' 비즈채널을 등록해 스마트스토어를 연결해요."
                    if smartstore else "키워드 검색 결과에 내 사이트를 문구와 함께 보여 주는 광고예요."),
         "check": "✅", "card": "naver-setup-006" if smartstore else "naver-setup-005"},
        {"step": "구조: 캠페인 → 광고그룹 → " + ("소재(상품)" if smartstore else "키워드·소재"),
         "detail": "처음엔 캠페인 1개, 광고그룹 1개로 시작하면 숫자를 보기 쉬워요.", "check": "✅", "card": "naver-setup-008"},
        {"step": f"하루 예산: {daily:,.0f}원",
         "detail": f"배분한 네이버 월 {naver_monthly:,.0f}원 ÷ 30.4일을 캠페인 하루 예산에 넣어요. 예산에 닿으면 그날 광고가 멈추고, "
                   "광고가 내려가기까지 시간이 걸려 조금 더 과금될 수 있어요.", "check": "🧮", "card": "naver-setup-009"},
    ]
    if smartstore:
        items.append({"step": f"기본 입찰가: 최소 {NAVER_MIN_BID['쇼핑검색']}원부터",
                      "detail": "쇼핑검색은 키워드별 입찰이 아니라 상품(광고그룹 기본 입찰가) 단위예요. 최소 50원으로 두고 보고서의 노출·클릭을 보며 조금씩 올려요. "
                                + (f"참고로 '{keyword}' 키워드(파워링크) 예상 실적에서 이 예산을 쓰는 입찰가는 약 {bid:,.0f}원이에요(쇼핑검색 입찰가와는 달라요)."
                                   if bid else ""),
                      "check": "✅", "card": "naver-setup-011"})
    elif bid:
        items.append({"step": f"기본 입찰가: 약 {bid:,.0f}원 (최소 {NAVER_MIN_BID['파워링크']}원)",
                      "detail": f"'{keyword}' 예상 실적에서 이 예산을 쓰게 되는 입찰가예요. 광고그룹 수정 창의 [예상 실적 보기]에 넣어 월 예산을 넘지 않는지 확인하세요.",
                      "check": "🧮", "card": "naver-setup-011"})
    items.append({"step": "노출 순위는 입찰가만으로 정해지지 않아요",
                  "detail": "검색어와 광고·사이트의 연관성, 광고 품질을 입찰가와 함께 봐서 정해져요. 파워링크는 품질을 '광고 연관지수'·'클릭 기대지수'(1~10)로 보여 줘요. "
                            "입찰가를 올려도 순위는 보장되지 않으니 다음 날 보고서의 노출수로 확인하세요.",
                  "check": "✅", "card": "naver-setup-012"})
    items.append({"step": "전환(구매) 추적 신청하고 캠페인에서 고르기",
                  "detail": "도구 > 전환 추적 관리 > 웹사이트에서 [+ 전환 추적 신청]. 스마트스토어는 신청하자마자 '설치 완료'이고, 자사몰은 안내 메일대로 스크립트를 설치해요. "
                            "신청한 뒤 캠페인 설정에서 그 전환 추적 대상을 골라야 리포트에 '총 전환수'가 잡혀요.",
                  "check": "✅", "card": "naver-setup-016"})
    items.append({"step": "광고 링크에 꼬리표", "detail": "코치가 만든 NT 꼬리표 링크(스마트스토어)나 UTM 링크(자사몰)를 쓰면 판매처 통계에서 따로 셀 수 있어요.",
                  "check": "🧮", "card": None})
    if smartstore:
        items.append({"step": "이런 상품도 있어요: ADVoost 쇼핑 · 스마트스토어 광고",
                      "detail": "예산만 정하면 AI가 상품·지면·입찰을 자동으로 정하는 쇼핑 광고예요(ADVoost 쇼핑은 전환 추적 필수, 스마트스토어 광고는 스마트스토어센터에서). "
                                "둘 중 하나만 쓰라고 안내돼요. 입찰가를 직접 정해 숫자를 배우려면 위 쇼핑검색광고가 맞아요.",
                      "check": "✅", "card": "naver-setup-007"})
    return items
