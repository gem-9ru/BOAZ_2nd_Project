"""초보자 광고 코치 (주 사용자: 광고·마케팅을 처음 하는 사장님).

기준: 초보자_코치_설계안.md 8장 "확정 값" (사용자 확정 11/5, 기획안 13장 #15).
사장님이 이미 아는 숫자(판매가, 1개 팔면 남는 돈, 재구매 감, 월 최대 광고비)만으로
① 손님 1명에 쓸 수 있는 최대 금액(손익분기 CPA) ② 광고가 맞는 상품인지(필요한 구매 비율 신호등)
③ 첫 달 계획(첫 채널, 시험 예산) ④ 한 달 뒤 판정(순서형)을 만든다.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ── 확정 값 (8장) ─────────────────────────────────────────────
SIGNAL_GREEN = 0.01       # 필요한 구매 비율 ≤ 1% 🟢
SIGNAL_YELLOW = 0.03      # 1~3% 🟡, 3% 초과 🔴
REFERENCE_RATES = {"GA4 공개 샘플 유료 검색 유입": 0.0119, "GA4 공개 샘플 전체": 0.0165}  # 참고 기준 (한 쇼핑몰 값, 업종 평균 아님)
REPURCHASE_PRESETS = {"거의 안 삼": 0.0, "가끔": 0.5, "자주": 2.0}   # 12개월 동안 다시 사는 횟수, 모두 가정값
TEST_SALES = 30           # 시험 예산 = 첫 구매 손익분기 × 30 (판매 30건이면 CPA 오차 약 ±18% = 1/√30)
WARN_SALES = 10           # 월 최대 예산이 손익분기 × 10 미만이면 "한 달로 판단이 어려울 수 있음"
MIN_DAYS = 14             # 판정 보류: 집행 14일 미만
MIN_SALES = 10            # 판정 보류: 광고로 온 판매 10건 미만 (오차 약 ±32%)
LEARNING_DAYS = 7         # 메타·카카오는 첫 7일 학습 구간: 이 기간 성과로 "줄이기" 금지
INCREASE = 0.20           # "계속"일 때 증액 폭 (업계 경험칙 △, 1차 근거 없음)
NAVER_QC_MIN = 1_000      # 🔧 자사몰: 상품 키워드 월 검색수가 이 이상이면 네이버 검색광고, 아니면 메타

STORES = ["스마트스토어", "쿠팡", "자사몰", "매장·예약"]
CATEGORIES = ["식품", "뷰티", "패션", "생활", "육아", "서비스·예약", "기타"]
# 판매처 → (첫 채널, 이유, 대략 클릭 비용을 어디서 구하나)
FIRST_CHANNEL = {
    "스마트스토어": ("네이버 쇼핑검색광고", "사려고 검색한 사람에게 내 상품이 바로 보입니다. 클릭할 때만 돈을 냅니다."),
    "쿠팡": ("쿠팡 광고 (AI 스마트 광고)", "쿠팡 안에서 검색한 사람에게 상단에 보입니다. 키워드·입찰을 쿠팡이 자동으로 맞춥니다."),
    "자사몰_검색": ("네이버 검색광고", "이 상품을 이미 검색하는 사람이 많습니다. 찾는 사람에게 먼저 보이는 게 가장 쌉니다."),
    "자사몰_메타": ("메타 광고 (인스타그램·페이스북)", "아직 검색하는 사람이 적은 상품입니다. 사람들이 찾기 전에 먼저 보여 줘야 합니다."),
    "매장·예약": ("네이버 플레이스 광고", "가까운 곳을 찾는 사람에게 지도·플레이스 위쪽에 보입니다. (근처 주민에게 알리려면 당근 광고도 대안)"),
}
LEARNING_CHANNELS = ("메타", "카카오")
PLAIN_STEPS = ["봤다", "눌렀다", "둘러봤다", "샀다", "다시 샀다", "소개했다"]   # 체인 6단계의 초보자 표기


@dataclass
class Breakeven:
    first: float          # 첫 구매만 본 손익분기 CPA = 1개 팔면 남는 돈
    year: float           # 재구매까지 본 값 (가정값) = 남는 돈 × (1 + 12개월 재구매 횟수)
    repurchases: float


def breakeven(profit_per_sale: float, repurchases: float) -> Breakeven:
    p = max(float(profit_per_sale), 0.0)
    return Breakeven(first=p, year=p * (1 + max(repurchases, 0.0)), repurchases=repurchases)


def required_rate(cpc: float, be_cpa: float) -> float:
    """필요한 구매 비율 = 클릭 1번 비용 ÷ 손익분기 CPA (클릭한 사람 중 몇 %가 사야 남나)."""
    return cpc / be_cpa if be_cpa > 0 else float("inf")


def signal(rate: float) -> Tuple[str, str]:
    if rate <= SIGNAL_GREEN:
        return "🟢", "광고로 남길 수 있는 상품입니다."
    if rate <= SIGNAL_YELLOW:
        return "🟡", "평균보다 잘 팔려야 남습니다. 상세페이지와 후기를 먼저 갖추고 작게 시작하세요."
    return "🔴", "광고만으로는 남기기 어렵습니다. 공동구매처럼 팔린 만큼만 내는 방식이나 가격·구성 조정을 먼저 보세요."


def first_channel(stores: List[str], monthly_search: Optional[float] = None) -> Tuple[str, str]:
    """판매처를 따라 첫 채널 1개. 여러 곳에서 팔면 스마트스토어 > 쿠팡 > 자사몰 > 매장 순으로 하나."""
    for s in STORES:
        if s in stores:
            if s == "자사몰":
                key = "자사몰_검색" if (monthly_search or 0) >= NAVER_QC_MIN else "자사몰_메타"
                return FIRST_CHANNEL[key]
            return FIRST_CHANNEL[s]
    return FIRST_CHANNEL["자사몰_메타"]


def test_budget(max_budget: float, be_first: float) -> Tuple[float, Optional[str]]:
    """시험 예산 = min(월 최대 예산, 첫 구매 손익분기 × 30). 최대 예산이 손익분기 × 10 미만이면 경고."""
    budget = min(max(max_budget, 0.0), be_first * TEST_SALES)
    warn = None
    if be_first > 0 and max_budget < be_first * WARN_SALES:
        warn = (f"한 달 {max_budget:,.0f}원으로는 판단할 만큼 판매가 모이지 않을 수 있습니다 "
                f"(손님 1명에 최대 {be_first:,.0f}원이면 판매 10건에 {be_first * WARN_SALES:,.0f}원 필요). 두 달을 합쳐 판단하세요.")
    return budget, warn


@dataclass
class SalesBasis:
    value: Optional[float]
    source: str
    warning: Optional[str] = None
    conservative: bool = False
    side_by_side: Optional[Tuple[float, float]] = None   # (쿠폰 판매, 광고 리포트 전환) 둘 다 있으면


def ad_sales(coupon: Optional[float] = None, report: Optional[float] = None,
             total: Optional[float] = None, baseline: Optional[float] = None) -> SalesBasis:
    """광고로 온 판매 수: 쿠폰·전용 링크 > 광고 리포트 전환 > 전체 − 평소 판매 > 전체(경고 + 한 단계 보수적)."""
    both = (coupon, report) if (coupon is not None and report is not None) else None
    if coupon is not None:
        note = "쿠폰을 안 쓰고 산 손님은 빠져 실제보다 적을 수 있습니다." if both is None else None
        return SalesBasis(coupon, "쿠폰·전용 링크로 센 판매", note, side_by_side=both)
    if report is not None:
        return SalesBasis(report, "광고 화면의 전환 수",
                          "광고 화면 기준이라 광고가 없어도 샀을 손님이 섞일 수 있습니다.")
    if total is not None and baseline is not None:
        return SalesBasis(max(total - baseline, 0.0), "전체 판매 − 광고 전 평소 판매",
                          "광고 전보다 늘어난 판매만 셌습니다. 같은 시기에 다른 일(행사·계절)이 있었다면 섞일 수 있습니다.")
    if total is not None:
        return SalesBasis(total, "전체 판매",
                          "광고 외 판매가 포함되어 실제보다 좋게 보일 수 있습니다. 판정을 한 단계 보수적으로 냅니다.",
                          conservative=True)
    return SalesBasis(None, "없음", "판매 수를 넣어 주세요.")


@dataclass
class Verdict:
    step: int             # 0 보류 / 1 계속 / 2 유지 / 3 상세페이지 / 4 검색어·소재
    level: str            # info / success / warning / error (화면 색)
    title: str
    detail: str
    next_budget: Optional[float] = None   # 다음 달 제안 예산. paused면 "고친 뒤 다시 시험할 금액"
    cpa: Optional[float] = None
    rate: Optional[float] = None
    paused: bool = False                  # 고칠 때까지 광고를 멈춰야 하는가


def judge(days: int, spend: float, clicks: float, sales: SalesBasis, be: Breakeven,
          planned_cpc: float, channel: str = "") -> Verdict:
    """8-2 순서형 판정: 위에서부터 처음 맞는 것 하나."""
    s = sales.value or 0.0
    cpa = spend / s if s > 0 else None
    rate = s / clicks if clicks > 0 else None
    need = required_rate(planned_cpc, be.first)
    expected_clicks = spend / planned_cpc if planned_cpc > 0 else 0.0
    learning = any(c in channel for c in LEARNING_CHANNELS) and days < LEARNING_DAYS

    # 0. 판단 보류
    if days < MIN_DAYS or s < MIN_SALES:
        why = []
        if days < MIN_DAYS:
            why.append(f"광고를 {days}일 돌렸습니다 (최소 {MIN_DAYS}일)")
        if s < MIN_SALES:
            why.append(f"광고로 온 판매가 {s:,.0f}건입니다 (최소 {MIN_SALES}건, 이보다 적으면 우연일 수 있음)")
        if learning:
            hint = f"{channel}는 처음 {LEARNING_DAYS}일 동안 보여 줄 사람을 찾는 학습 중이라, 이 기간 성과로 줄이면 안 됩니다. 그대로 두세요."
        elif expected_clicks > 0 and clicks < expected_clicks * 0.5:
            hint = "클릭이 예상의 절반도 안 됩니다. 검색어를 늘리거나 입찰가를 조금 올려 보세요."
        elif clicks >= expected_clicks * 0.5 and s == 0 and clicks > 0:
            hint = "클릭은 들어오는데 아직 한 건도 안 팔렸습니다. 상세페이지(사진·후기·가격 안내)를 먼저 손보세요."
        else:
            hint = "같은 예산으로 2주 더 돌린 뒤 다시 판단하세요."
        return Verdict(0, "info", "아직 판단하기 이릅니다", " · ".join(why) + "  \n" + hint, cpa=cpa, rate=rate)

    # 1. 첫 구매만으로 남음
    if cpa <= be.first:
        if sales.conservative:   # 전체 판매로만 센 경우 한 단계 보수적으로
            return Verdict(2, "success", "유지하세요 (광고 외 판매가 섞였을 수 있어 늘리지는 않음)",
                           f"손님 1명에 {cpa:,.0f}원이 들었고, 첫 구매만으로 {be.first:,.0f}원까지는 남습니다. "
                           "다음 달에는 쿠폰이나 전용 링크로 광고 판매를 따로 세어 보세요.", spend, cpa, rate)
        return Verdict(1, "success", f"계속하세요. 다음 달 예산을 {INCREASE:.0%} 늘려 보세요",
                       f"손님 1명에 {cpa:,.0f}원이 들었고, 첫 구매만으로 {be.first:,.0f}원까지는 남습니다. "
                       f"(20% 증액은 업계 경험칙입니다. 클릭 비용이 크게 오르는지 지켜보세요.)", spend * (1 + INCREASE), cpa, rate)

    # 2. 재구매까지 치면 남음 (가정값에 기댄 판정)
    if cpa <= be.year:
        return Verdict(2, "warning", "유지하면서 다시 사게 만드세요",
                       f"손님 1명에 {cpa:,.0f}원이 들어 첫 구매만으로는 {cpa - be.first:,.0f}원 모자랍니다. "
                       f"다시 사는 손님이 '{_preset_name(be.repurchases)}' 정도라면 {be.year:,.0f}원까지 남습니다 (가정값에 기댄 판정). "
                       "재구매 쿠폰·메시지로 다시 오게 만드세요.", spend, cpa, rate)

    # 3. 들어온 사람이 안 삼 → 판매 1건마다 손해이므로 줄여도 손해가 이어짐: 멈추고, 고친 뒤 판단 가능한 최소 금액으로 재시험
    if rate is not None and rate < need:
        restart = be.first * MIN_SALES
        return Verdict(3, "error", "상세페이지를 고칠 때까지 광고를 멈추세요",
                       f"눌러 들어온 사람 100명 중 {rate * 100:.1f}명이 샀습니다. 남으려면 {need * 100:.1f}명이 사야 합니다. "
                       f"지금은 판매 1건마다 손해라 예산을 줄여도 손해가 이어집니다. 사진·후기·가격 안내를 고친 뒤 "
                       f"**{restart:,.0f}원**으로 다시 시험하세요 (판매 {MIN_SALES}건을 볼 수 있는 최소 금액).",
                       restart, cpa, rate, paused=True)

    # 4. 그 밖: 클릭이 비쌈
    return Verdict(4, "warning", "검색어나 광고 소재를 바꿔 클릭 비용을 낮추세요",
                   f"들어온 사람은 잘 사지만(100명 중 {(rate or 0) * 100:.1f}명), 클릭 1번에 {spend / max(clicks, 1):,.0f}원으로 비쌉니다. "
                   "더 구체적인 검색어(예: 상품명 + 특징)나 다른 사진·문구로 바꿔 보세요.", spend, cpa, rate)


def retention_scale_for(repurchases: float, floor: float, decay: float, purchase_freq: float, months: int = 12) -> float:
    """코치 재구매 프리셋(12개월 동안 다시 사는 횟수)을 다음 단계 엔진의 리텐션 곡선 높이로 바꾼다.
    엔진에서 손님 1명의 12개월 재구매 횟수 = 월 구매 횟수 × Σ r(t), t = 1..11 → 이 값이 프리셋과 같아지는 배수.
    곡선 모양(바닥값·감소 속도)은 다음 단계 슬라이더를 따르고, 높이만 맞춘다 (가정값)."""
    from .model import FunnelParams
    base = FunnelParams(retention_floor=floor, retention_decay=decay, purchase_freq=purchase_freq, months=months)
    per_customer = float(base.retention(months)[1:].sum()) * purchase_freq
    return max(repurchases, 0.0) / per_customer if per_customer > 0 else 0.0


def _preset_name(repurchases: float) -> str:
    for k, v in REPURCHASE_PRESETS.items():
        if abs(v - repurchases) < 1e-9:
            return k
    return f"1년에 {repurchases:g}번"
