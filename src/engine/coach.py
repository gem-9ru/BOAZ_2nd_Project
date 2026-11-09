"""초보자 광고 코치 (주 사용자: 광고·마케팅을 처음 하는 사장님).

기준: 초보자_코치_설계안.md 8장 "확정 값" (사용자 확정 11/5, 기획안 13장 #15).
사장님이 이미 아는 숫자(판매가, 1개 팔면 남는 돈, 재구매 감, 월 최대 광고비)만으로
① 손님 1명에 쓸 수 있는 최대 금액(손익분기 CPA) ② 광고가 맞는 상품인지(필요한 구매 비율 신호등)
③ 첫 달 계획(네이버·메타 예산 배분, 시험 예산) ④ 한 달 뒤 판정(순서형)을 만든다.
매체 범위는 네이버 검색광고·메타 두 개 (노션 11/9 기획, plans/pending/notion-v2-alignment.md Q1).
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

# ── 확정 값 (8장) ─────────────────────────────────────────────
# 참고 기준 (한 쇼핑몰 값, 업종 평균 아님). 방문한 손님 중 산 비율 = 방문 기준 (필요한 비율은 클릭 기준)
# '전체'는 유입 매체가 지워진 손님 '(data deleted)'를 뺀 값 (그 묶음만 구매율 8%로 튀는 마스킹 이상값, 분석 보고서 4장). 엔진 퍼널과 같은 범위
REFERENCE_RATES = {"GA4 공개 샘플 유료 검색 유입": 0.0119, "GA4 공개 샘플 전체": 0.0149}
REPURCHASE_PRESETS = {"거의 안 삼": 0.0, "가끔": 0.5, "자주": 2.0, "매달(정기)": 6.0}   # 12개월 동안 다시 사는 횟수, 모두 가정값(등급 D)
# '매달(정기)' 6회: 원두·사료처럼 다 쓰면 다시 사는 소모품 (사용자 결정 11/9). 첫 달 뒤 손님 일부가 꾸준히 돌아오는 곡선으로 1년 6회
# '자주' 2회는 분석 Q4(UCI) 범위 안: 매출 기준 약 1.5회분(LTV = 첫 주문 2.45배), 리텐션 곡선 기준 약 2.2회 (도매 섞임). '가끔' 0.5회는 근거 약함 (GA4 3개월 안 재구매 11.8%)
TEST_SALES = 30           # 시험 예산 = 첫 구매 손익분기 × 30 (판매 30건이면 CPA 오차 약 ±18% = 1/√30)
WARN_SALES = 10           # 월 최대 예산이 손익분기 × 10 미만이면 "한 달로 판단이 어려울 수 있음"
MIN_DAYS = 14             # 판정 보류: 집행 14일 미만
MIN_SALES = 10            # 판정 보류: 광고로 온 판매 10건 미만 (오차 약 ±32%)
LEARNING_DAYS = 7         # 메타·카카오는 첫 7일 학습 구간: 이 기간 성과로 "줄이기" 금지
INCREASE = 0.20           # "계속"일 때 증액 폭 (업계 경험칙 △, 1차 근거 없음)

STORES = ["스마트스토어", "쿠팡", "자사몰", "매장·예약"]   # 판매처: 광고 링크(NT·UTM)·쿠폰 만들 때만 씀
CATEGORIES = ["식품", "뷰티", "패션", "생활", "육아", "서비스·예약", "기타"]
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
    target = max(repurchases, 0.0)

    def per_customer(scale: float) -> float:   # 재구매 횟수 = 손님 1명 가치 − 첫 구매 1번. 리텐션은 100%에서 잘리므로 배수와 횟수가 비례하지 않음
        return base.with_changes(retention_scale=scale).per_customer_value(months) - 1.0

    if per_customer(1.0) <= 0 or target <= 0:
        return 0.0
    cap = purchase_freq * (months - 1)              # 매달 다시 와도 이 이상은 안 됨
    target = min(target, cap * 0.999)
    lo, hi = 0.0, 1.0
    while per_customer(hi) < target:
        hi *= 2
    for _ in range(60):                             # 이분법
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if per_customer(mid) < target else (lo, mid)
    return hi


def _preset_name(repurchases: float) -> str:
    for k, v in REPURCHASE_PRESETS.items():
        if abs(v - repurchases) < 1e-9:
            return k
    return f"1년에 {repurchases:g}번"


# ── v0.9 UX 개편 (UX_개편안.md 3-3 ~ 3-6): 계산 규칙은 그대로, 보여 주는 방식만 ──────────────
LOSS_REFERENCE_RATE = REFERENCE_RATES["GA4 공개 샘플 유료 검색 유입"]   # 손실 예상에 쓰는 보통 구매 비율 (참고 기준)
INTERVIEW_QUESTIONS = [
    "상품을 보고도 사지 않았던 이유가 뭐였나요? (가격, 배송, 믿음, 정보 부족 중에서)",
    "사기 전에 더 알고 싶었던 게 있었나요? (맛·크기·사용법·후기 등)",
    "비슷한 상품을 산다면 어디서 사나요? 그곳이 더 좋은 점은?",
]


def budget_options(be_first: float, max_budget: float) -> List[Dict]:
    """시험 예산 3안 (타협 효과, 가운데 = 권장 기본 선택). 권장이 최대보다 크면 최대로 맞추고 작게 시작만 남김."""
    small = be_first * MIN_SALES
    rec = be_first * TEST_SALES
    if rec > max_budget:
        opts = []
        if small < max_budget:
            opts.append({"key": "small", "label": "작게 시작", "amount": small, "error": "±32%", "why": f"판매 {MIN_SALES}건: 판단할 수 있는 최소"})
        opts.append({"key": "recommended", "label": "권장 (= 최대)", "amount": max_budget, "error": None,
                     "why": f"권장(판매 {TEST_SALES}건, {rec:,.0f}원)이 최대보다 커서 최대로 맞춤"})
        return opts
    return [
        {"key": "small", "label": "작게 시작", "amount": small, "error": "±32%", "why": f"판매 {MIN_SALES}건: 판단할 수 있는 최소"},
        {"key": "recommended", "label": "권장", "amount": rec, "error": "±18%", "why": f"판매 {TEST_SALES}건: 판단이 꽤 정확해짐"},
        {"key": "max", "label": "최대", "amount": max_budget, "error": None, "why": "사장님이 정한 한 달 상한"},
    ]


def expected_loss(budget: float, cpc: float, profit_per_sale: float, rate: float = LOSS_REFERENCE_RATE) -> Tuple[float, float]:
    """(예상 판매 수, 예상 손해). 예상 판매 = 예산 ÷ 클릭 비용 × 보통 구매 비율, 손해 = 예산 − 예상 판매 × 남는 돈 (음수면 이익)."""
    sales = budget / cpc * rate if cpc > 0 else 0.0
    return sales, budget - sales * profit_per_sale


def realized_loss(spend: float, sales: float, profit_per_sale: float) -> float:
    """지난달 실제 손해 = 쓴 돈 − 광고로 온 판매 × 남는 돈 (첫 구매 기준)."""
    return spend - sales * profit_per_sale


def biggest_drop(totals: Dict[str, Optional[float]], labels: Dict[str, str], order: List[str]) -> Optional[Tuple[str, str, float]]:
    """판매처 통계 합계에서 가장 많이 빠지는 구간 (이전 단계 이름, 다음 단계 이름, 통과율).
    규칙은 퍼널 진단(measure.diagnose_funnel, 기준 대비 비율) 하나를 읽음 (B5). order는 호출부 정리 전까지 남은 인자 (쓰지 않음)."""
    from .measure import diagnose_funnel
    diag = diagnose_funnel(totals)
    if diag is None:
        return None
    s = diag["lowest"]
    return labels[s["prev"]], labels[s["key"]], s["rate"]


KST = ZoneInfo("Asia/Seoul")   # 광고 시작일·경과일·판정 가능일은 한국 날짜 기준 (서버는 UTC)


def today_kst(now: Optional[datetime] = None) -> date:
    """한국 시간 오늘 날짜. now는 시간대가 있는 시각 (테스트용)."""
    return (now or datetime.now(KST)).astimezone(KST).date()


BUDGET_PICKS = ("small", "recommended", "max", "none")   # 시험 예산 선택지 키 (budget_options + 광고 안 함)


def rates_for(split: Dict, be: "Breakeven") -> Tuple[float, float, float]:
    """실제로 쓴 배분(split)의 평균 클릭 비용 → (cpc, 첫 구매 필요 구매율, 1년 필요 구매율).
    고른 예산으로 다시 나눴으면 그 split을 넘긴다 (B1: 권장 예산 값이 남지 않게)."""
    cpc = split["cpc"]
    return cpc, required_rate(cpc, be.first), required_rate(cpc, be.year)


def next_month_grades(grades: Dict[str, str], naver_measured: bool, meta_measured: bool, cvr_measured: bool) -> Dict[str, str]:
    """한 달 뒤 실측으로 다시 계산할 때의 등급. 재 실측한 값은 A, 재구매는 처음 계산 등급 그대로 (실측 C·프리셋 D, B2)."""
    return {"aov": "A", "margin": "A", "cpc_naver": "A" if naver_measured else "B",
            "cpc_meta": "A" if meta_measured else grades["cpc_meta"], "cvr": "A" if cvr_measured else "C",
            "retention": grades["retention"]}


def default_budget_pick(action: str) -> str:
    """시험 예산 기본 선택 = 실제로 권하는 값 (UX 설계원칙 4장). 결론이 '준비가 먼저'(100번 중 50번 미만)면 '광고 안 함'."""
    return "none" if action == "prep" else "recommended"


def mc_grades(meta_cpc_measured: bool) -> Dict[str, str]:
    """코치 몬테카를로에서 흔드는 입력과 등급: 판매가·마진은 사장님 입력(A), 네이버 클릭은 예상 실적(B),
    메타 클릭은 직접 넣으면 A·아니면 가정(D), 구매 비율은 GA4 공개 샘플(C), 재구매는 프리셋 가정(D)."""
    return {"aov": "A", "margin": "A", "cpc_naver": "B", "cpc_meta": "A" if meta_cpc_measured else "D",
            "cvr": "C", "retention": "D"}


# ── 네이버·메타 예산 배분 (노션 Q1) ──────────────────────────────
SPLIT_SHARES = (1.0, 0.7, 0.5, 0.3, 0.0)   # 비교 표: 네이버 비율


def coach_params(price: float, profit: float, repurchases: float):
    """코치 숫자로 엔진 파라미터를 만든다: 객단가 = 판매가, 마진 = 남는 돈 ÷ 판매가, 재구매 프리셋으로 곡선 높이."""
    from . import defaults as D
    from .model import FunnelParams
    scale = retention_scale_for(repurchases, D.RETENTION_FLOOR, D.RETENTION_DECAY, D.PURCHASE_FREQ)
    return FunnelParams(aov=float(price), margin=float(profit) / float(price), retention_scale=scale)


def split_budget(budget: float, naver_curve, meta_cpc: float, params, meta_sat: Optional[float] = None) -> Dict:
    """시험 예산을 네이버·메타에 나눔. 같은 돈으로 새 손님이 가장 많은 배분 (optimize_allocation 재사용, 예산 전부 씀):
    네이버 검색어 수요(예상 실적 곡선)가 메타보다 싸게 손님을 데려오는 구간까지 네이버를 채우고 남는 돈을 메타로.
    naver_curve가 없으면(검색어 없음·예측 실패) 모두 메타."""
    from . import defaults as D
    from .acquisition import Channel, MetaCurve
    from .model import simulate
    from .optimize import optimize_allocation
    from .montecarlo import one_month
    sat = D.META_SATURATION if meta_sat is None else meta_sat
    has_naver = naver_curve is not None and getattr(naver_curve, "capacity", 0) > 0
    chans = []
    if has_naver:
        chans.append(Channel("naver", "네이버 검색광고", naver_curve, D.NAVER_CVR_MULT, D.NAVER_RETENTION_MULT))
    chans.append(Channel("meta", "메타 광고", MetaCurve(meta_cpc, sat), D.META_CVR_MULT, D.META_RETENTION_MULT))
    budget = max(float(budget), 0.0)
    if has_naver and budget > 0:
        spends = optimize_allocation(chans, budget, params, "new_customers", full_budget=True)["spends"]
        naver = min(float(spends[0]), naver_curve.capacity)
        spends = [naver, budget - naver]
    else:
        spends = [budget]
    res = simulate(chans, spends, params)
    clicks = res.summary["clicks_total"] / params.months
    naver = spends[0] if has_naver else 0.0
    rows = []
    if has_naver:
        for share in SPLIT_SHARES:
            n = min(budget * share, naver_curve.capacity)
            # 코치 단위 = 한 달 광고 → 그 달 손님 코호트의 12개월 이익 − 그 한 달 광고비 (montecarlo.one_month와 같은 식)
            m = one_month(chans, [n, budget - n], params)
            rows.append({"share": share, "naver": n, "meta": budget - n, "new_customers": m["new"],
                         "profit_cohort": m["profit"], "profit_first": m["first_only"]})
    return {
        "naver": naver, "meta": budget - naver, "has_naver": has_naver, "spends": spends, "channels": chans,
        "clicks": clicks, "cpc": (budget / clicks) if clicks > 0 else float(meta_cpc),
        "naver_capacity": naver_curve.capacity if has_naver else 0.0,
        "naver_marginal_cpc": naver_curve.marginal_cpc(naver) if (has_naver and naver > 0) else None,
        "meta_cpc": float(meta_cpc), "result": res, "table": rows,
    }


# ── 손익분기 재구매율 지도 (노션 Q3) ──────────────────────────────
def breakeven_grid(price: float, margin: float, cpa: float, my_repurchases: float, n_price: int = 31, n_rep: int = 41) -> Dict:
    """판매가(가로) × 1년 재구매 횟수(세로) → 손님 1명이 남기는 돈 − 데려오는 데 든 돈(CPA).
    손님 1명이 남기는 돈 = 판매가 × 마진 × (1 + 재구매 횟수) (breakeven().year와 같은 식).
    본전 선: 재구매 = CPA ÷ (판매가 × 마진) − 1."""
    import numpy as np
    prices = np.linspace(price * 0.5, price * 2.0, n_price)
    need_here = cpa / (price * margin) - 1 if price * margin > 0 else 0.0
    rep_max = float(min(max(4.0, need_here * 1.3, my_repurchases * 1.5), 30.0))
    reps = np.linspace(0.0, rep_max, n_rep)
    profit = prices[None, :] * margin * (1 + reps[:, None]) - cpa
    boundary = np.maximum(cpa / (prices * margin) - 1, 0.0)
    return {"prices": prices, "reps": reps, "profit": profit, "boundary": boundary, "need_here": max(need_here, 0.0),
            "my_price": float(price), "my_rep": float(my_repurchases), "cpa": float(cpa), "margin": float(margin)}
