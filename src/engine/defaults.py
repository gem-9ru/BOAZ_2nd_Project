"""0단계(데이터 없는 광고주) 기본값.

표기: ✅ 실제 데이터에서 계산한 값 · PLACEHOLDER 임시값 (주석의 출처로 교체 예정, 산출물 → data/processed/).
data/processed/ 에 파일이 생기면 data_loader.py가 그 값을 우선 사용하고, 없을 때만 이 파일 값을 씁니다.
업종을 전제하지 않습니다: 키워드와 핵심 과업은 사용자 입력이고, 아래 값은 사용자가 화면에서 수정합니다.
통화 (기획안 결정 3): 금액은 모두 원화 사용자 입력. 외부 데이터는 비율·상대값만 쓰고 £·$ 환산은 하지 않습니다.
"""

# ── 시작 화면 ───────────────────────────────────────────────
CORE_TASKS = ["구매", "상담 신청", "회원 가입", "예약", "직접 입력"]
OMTM_OPTIONS = {
    "new_customers": "신규 고객 수",
    "profit": "12개월 누적 이익",
    "roas": "ROAS (매체 기준)",
}
MONTHLY_BUDGET = 3_000_000          # 원/월. 시연 시나리오 "월 300만 원" (실행계획 2-3)
MONTHS = 12                         # 시뮬레이션 기간 (월 단위 코호트)

# ── 획득: 채널 ──────────────────────────────────────────────
CHANNEL_SHARES = {"naver": 0.6, "meta": 0.4}   # PLACEHOLDER: 초기 배분 비율

NAVER_DEVICE = "MOBILE"             # 검색 대부분이 모바일 (가이드 1-6)
NAVER_CVR_MULT = 1.0                # 검색 의도 기준 채널 (전환율 배수 1.0)
NAVER_RETENTION_MULT = 1.0

META_BASE_CPC = 700.0               # PLACEHOLDER 원: 사용자 입력 CPC. 타깃을 고르면 Kaggle 상대 CPA 배수를 곱함
META_SATURATION = 0.3               # PLACEHOLDER: 광고비 100만 원 늘 때마다 CPC가 30% 상승 (사용자 노브)
META_CVR_MULT = 0.7                 # PLACEHOLDER: 소셜 클릭은 검색보다 구매 의도 낮음 → Kaggle CVR vs GA4 CVR 비교로 교체
META_RETENTION_MULT = 0.9           # PLACEHOLDER: 충동 유입 고객의 재구매 낮음 가정 → 1단계 CSV/2단계 데이터로 보정

# 메타 타깃별 상대 CPA 배수 ✅ Kaggle "Sales Conversion Optimization" (1,143개 광고)
# 캠페인(xyz_campaign_id)별 타깃 CPA ÷ 캠페인 CPA를 광고비 가중 평균 (심슨 패러독스 통제). 구매 = Approved_Conversion.
# → 획득 담당 Q2 산출물 data/processed/fb_target_metrics.csv (컬럼: target, rel_cpa, purchases)로 교체
META_TARGETS = {
    # target: (상대 CPA 배수, 구매 건수)
    "30-34 남": (0.477, 299), "30-34 여": (0.749, 195),
    "35-39 남": (0.812, 112), "35-39 여": (1.231, 95),
    "40-44 남": (1.041, 77), "40-44 여": (1.405, 93),
    "45-49 남": (1.347, 96), "45-49 여": (2.347, 112),
}

# ── 활성화: 퍼널 단계별 전환율 ────────────────────────────────
# ✅ GA4 샘플 사용자 기준 퍼널 (2020-11 ~ 2021-01, data/raw/ga4/ga4_funnel.csv 전체 합계, 방문 대비 구매 1.65%)
# 단계 이름은 업종 무관하게 일반화하고 괄호에 GA4 이벤트를 적음. 마지막 단계가 시작 화면에서 고른 핵심 과업.
# "랜딩 도착"(광고 클릭 → 방문)은 GA4에 없는 단계라 PLACEHOLDER.
FUNNEL_STEPS = [
    ("랜딩 도착", 0.85),            # PLACEHOLDER: 클릭 → session_start
    ("관심 행동", 0.229),           # ✅ session_start → view_item
    ("과업 시작", 0.205),           # ✅ view_item → add_to_cart
    ("과업 진행", 0.774),           # ✅ add_to_cart → begin_checkout
    ("과업 완료", 0.455),           # ✅ begin_checkout → purchase
]
GA4_EVENTS = ["visit_users", "view_users", "cart_users", "checkout_users", "purchase_users"]

# 단계별 이탈 처방 (인사이트 문장 · 실험 제안). 키는 FUNNEL_STEPS 이름
STEP_PRESCRIPTIONS = {
    "랜딩 도착": "광고 문구와 랜딩 첫 화면 메시지를 맞추고 페이지 로딩 속도를 줄이기",
    "관심 행동": "랜딩에서 핵심 상품·서비스로 가는 버튼을 첫 화면에 두고, 후기·가격을 바로 보여주기",
    "과업 시작": "상세 화면에 혜택·배송/일정 정보를 명확히 하고, 장바구니·신청 버튼을 고정하기",
    "과업 진행": "입력 항목을 줄이고 비회원 진행을 허용하기",
    "과업 완료": "간편결제·비회원 구매를 열고, 결제 직전 추가 비용을 미리 알리기",
}

# ── 획득: 네이버 키워드 분류 (기획안 결정 6, 월 검색수 PC+모바일) ──────────────
KEYWORD_TIERS = [(30_000, "대표"), (1_000, "세부"), (0, "롱테일")]

# ── 유지: r(t) = floor + (1 − floor)·e^(−decay·t), t = 첫 구매 후 경과 개월 ─────
RETENTION_FLOOR = 0.06              # PLACEHOLDER → UCI 코호트 리텐션(도매 고객 분리 후) 바닥값 적합
RETENTION_DECAY = 1.6               # PLACEHOLDER → 같은 적합의 감소율
# PMF 경고 (기획안 결정 5): 현재 리텐션에서 12개월 LTV/CAC < 1 이면 경고
PMF_LTV_CAC_THRESHOLD = 1.0

# ── 수익 ────────────────────────────────────────────────────
AOV = 60_000.0                      # PLACEHOLDER 원: 사용자 입력 (중앙값 기준). UCI·GA4 금액은 환산하지 않음
PURCHASE_FREQ = 1.1                 # PLACEHOLDER: 활성 고객 1명의 월 주문 수 → UCI customers.csv
MARGIN = 0.35                       # PLACEHOLDER: 공헌이익률 (사용자 입력 권장)

# ── 추천 ────────────────────────────────────────────────────
INVITE_RATE = 0.0                   # 사용자 입력 (실행계획: 기본 0)
INVITE_CONV = 0.10                  # 초대받은 사람 중 신규 고객이 되는 비율 (가정값)

# ── 경고 기준 ────────────────────────────────────────────────
SATURATION_RATIO = 2.0              # 한계 CPC가 평균 CPC의 2배 넘으면 "포화 구간" (실행계획 4-3)
LEVER_PCT = 0.10                    # 레버 비교 개선 폭 (+10%)

# ── (보조) 메타 캠페인 설계 가이드 — 규칙 기반, 실행계획 3-1 "메타 설계 가이드" ─────────────
# 목표 × 상품 유형 → 권장 구조. 업종이 아니라 '구매 결정 방식'으로 나눔.
META_GUIDE_GOALS = ["처음 알리기 (인지)", "방문·문의 늘리기 (트래픽·리드)", "구매·신청 늘리기 (전환)", "기존 고객 재구매"]
META_GUIDE_PRODUCTS = ["저관여·저가 (바로 사는 상품)", "고관여·고가 (비교 후 결정)", "지역 기반 서비스·예약"]
META_GUIDE = {
    "campaign": {
        META_GUIDE_GOALS[0]: "인지도·도달 캠페인, 빈도 상한 주 2~3회",
        META_GUIDE_GOALS[1]: "트래픽(랜딩 조회) 또는 잠재 고객(리드 양식) 캠페인",
        META_GUIDE_GOALS[2]: "판매(전환) 캠페인 + 픽셀/전환 API로 핵심 과업 이벤트 최적화",
        META_GUIDE_GOALS[3]: "판매 캠페인, 구매자 맞춤 타깃(최근 30~180일) 리타기팅",
    },
    "structure": {
        META_GUIDE_PRODUCTS[0]: "캠페인 1개 · 광고 세트 1~2개(넓은 타깃 + 관심사) · 소재 3~5개로 시작, 학습 단계 동안 예산 고정",
        META_GUIDE_PRODUCTS[1]: "탐색(넓은 타깃)과 리타기팅(사이트 방문자) 광고 세트를 나누고, 리타기팅에 예산 20~30%",
        META_GUIDE_PRODUCTS[2]: "지역 반경 타깃 광고 세트, 리드 양식·메시지 연결, 요일·시간대 확인",
    },
    "creative": {
        META_GUIDE_PRODUCTS[0]: "짧은 세로 영상(릴스)·사용 장면, 가격·혜택을 첫 3초에",
        META_GUIDE_PRODUCTS[1]: "캐러셀로 기능·비교·후기, 상세 랜딩으로 연결",
        META_GUIDE_PRODUCTS[2]: "실제 공간·사람 사진, 위치·예약 방법을 문구에 명시",
    },
}
