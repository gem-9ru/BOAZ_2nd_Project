"""0단계(데이터 없는 광고주) 기본값 — 모두 임시 값(PLACEHOLDER)입니다.

각 값 옆 주석의 출처에서 실제 값이 나오면 이 파일만 바꾸면 됩니다 (데이터 담당 팀원 산출물 → data/processed/).
업종을 전제하지 않습니다: 키워드와 핵심 과업은 사용자 입력이고, 아래 값은 사용자가 화면에서 수정합니다.
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

META_BASE_CPC = 700.0               # PLACEHOLDER 원. → Kaggle 타깃별 CPC(fb_target_metrics.csv) + 환율 보정 예정
META_SATURATION = 0.3               # PLACEHOLDER: 광고비 100만 원 늘 때마다 CPC가 30% 상승 (사용자 노브)
META_CVR_MULT = 0.7                 # PLACEHOLDER: 소셜 클릭은 검색보다 구매 의도 낮음 → Kaggle CVR vs GA4 CVR 비교로 교체
META_RETENTION_MULT = 0.9           # PLACEHOLDER: 충동 유입 고객의 재구매 낮음 가정 → 1단계 CSV/2단계 데이터로 보정

# ── 활성화: 퍼널 단계별 전환율 ────────────────────────────────
# PLACEHOLDER → GA4 샘플 퍼널(ga4_funnel.csv: session_start → view_item → add_to_cart → purchase)
# 단계 이름은 업종 무관하게 일반화. "과업 완료"가 시작 화면에서 고른 핵심 과업.
FUNNEL_STEPS = [
    ("랜딩 도착", 0.85),            # 클릭 → 랜딩 페이지 로드
    ("관심 행동", 0.45),            # 상품·서비스 상세 조회
    ("과업 시작", 0.30),            # 장바구니·신청서 작성 시작
    ("과업 완료", 0.50),            # 결제·신청 완료 = 신규 고객
]

# ── 유지: r(t) = floor + (1 − floor)·e^(−decay·t), t = 첫 구매 후 경과 개월 ─────
RETENTION_FLOOR = 0.06              # PLACEHOLDER → UCI 코호트 리텐션(도매 고객 분리 후) 바닥값 적합
RETENTION_DECAY = 1.6               # PLACEHOLDER → 같은 적합의 감소율
PMF_FLOOR_THRESHOLD = 0.05          # 바닥값이 이보다 낮으면 PMF 경고 (그로스 해킹: 리텐션 평탄화 여부)

# ── 수익 ────────────────────────────────────────────────────
AOV = 60_000.0                      # PLACEHOLDER 원 → UCI 주문 금액 "중앙값"(£302.6, 도매 영향) 대신 업종 벤치마크/사용자 입력
PURCHASE_FREQ = 1.1                 # PLACEHOLDER: 활성 고객 1명의 월 주문 수 → UCI customers.csv
MARGIN = 0.35                       # PLACEHOLDER: 공헌이익률 (사용자 입력 권장)

# ── 추천 ────────────────────────────────────────────────────
INVITE_RATE = 0.0                   # 사용자 입력 (실행계획: 기본 0)
INVITE_CONV = 0.10                  # 초대받은 사람 중 신규 고객이 되는 비율 (가정값)

# ── 경고 기준 ────────────────────────────────────────────────
SATURATION_RATIO = 2.0              # 한계 CPC가 평균 CPC의 2배 넘으면 "포화 구간" (실행계획 4-3)
LEVER_PCT = 0.10                    # 레버 비교 개선 폭 (+10%)
