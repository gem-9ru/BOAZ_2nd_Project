# v2 개발 계약 (에이전트 공용)

> Prototype Ver 2.0.0. 기획: `plans/개발_티켓.md`, `plans/시연_시나리오.md`. 이 문서는 패키지끼리 맞물리는 **인터페이스**만 정한다.
> 사용자는 광고를 처음 하는 초보 판매자(예시: 소연베이크, 1인 수제 구움과자, 스마트스토어, 월 30만 원). 화면 문구는 쉬운 한국어, 전문 용어는 풀어서.

## 0. 공통 규칙
- 실행: 프로젝트 루트에서 `.venv/bin/python` (Python **3.9** — `match`, `X | Y` 타입, `list[int]` 같은 3.10+ 문법 금지. `typing.Optional/List/Dict` 사용)
- 테스트: `.venv/bin/python -m pytest v2/tests -q`. 내 패키지 테스트 파일은 `v2/tests/test_<패키지>.py`. **다른 패키지 파일이 아직 없거나 깨져 있어도 내 테스트만 책임진다.**
- **내 패키지 파일만 만들고 고친다.** 다른 패키지 파일·`v2/specs/*.yaml`·`v2/engine/{specs,ingest,metrics,effect}.py`·`requirements.txt`는 고치지 않는다. 사양이 틀렸거나 다른 모듈이 필요하면 최종 보고에 적는다.
- 테스트는 네트워크를 쓰지 않는다 (API는 가짜 함수로 바꿔 끼움). API 키는 출력·로그·예외 문구에 절대 넣지 않는다.
- git commit 하지 않는다 (오케스트레이터가 한다).
- 숫자에는 근거 등급을 붙인다: A 실측 · B 매체 추산 · C 공개 자료 · D 우리 가정 (`v2/specs/assumptions.yaml`).

## 1. 이미 있는 것 (오케스트레이터 작성, 고치지 말 것)
| 파일 | 내용 |
|---|---|
| `v2/specs/meta_fields.yaml`, `naver_fields.yaml` | 광고 관리자 칸 사양. kind: question / precheck / llm / auto / default / next_cycle. `auto:` 값은 auto 함수 이름 |
| `v2/specs/columns.yaml` | 결과 파일 입력 계약 (표 5개: meta_daily, meta_placement, naver_daily, store_daily, survey) |
| `v2/specs/rules.yaml` | 진단 규칙 16개. when(조건) · says(문장) · changes(다음 달 바꿀 칸: set 또는 set_from) · advice · caveat · grade |
| `v2/specs/assumptions.yaml` | 가정값 (CPM·CTR·CPC·실효 타겟·구매율) |
| `v2/engine/specs.py` | `fields(media)`, `all_fields()` (id→칸, media 포함), `columns()`, `rules()`, `assumptions()`, `check_all()` |
| `v2/engine/ingest.py` | `demo()`, `read_excel(path)`, `read_csvs(files)` → `Bundle(tables, problems)`; `Bundle.get(name)`, `.cases()`, `.modes()`, `.select(case, mode)` |
| `v2/engine/metrics.py` | `Context(budget, margin_per_order, start, end, target_sizes)`, `case_metrics(bundle, ctx) -> dict`, `fmt(name, value) -> str` |
| `v2/engine/effect.py` | `estimate(store, start, end, survey) -> Effect`, `ad_period(bundle)` |
| `v2/data/demo/소연베이크_가상광고데이터.xlsx` | 다정 가상 데이터. 케이스 C1·C2·C3·C4·C0·C1b, mode forecast(추천 예측)·sim(가상 실제). 광고 기간 2026-11-16~12-15 |

`case_metrics` 키: `meta_spend, naver_spend, total_spend, budget_use, naver_daily_spend, meta_daily_with_leftover, weekly_freq_max, awareness_weekly_freq_min, ctr_drop_max, saturation_max, link_clicks, link_ctr, meta_cpc_avg, cpc_rise, an_click_share, ig_spend_share, naver_ctr, naver_dead_keywords, naver_dead_keyword_names, effect, naive_lift, corrected_lift, lastclick_orders, est_orders, meta_sessions, cvr_meta, visit_per_click, lastclick_cac, est_cac, hidden_ratio, margin_per_order, margin_gap` (데이터가 없으면 키가 없거나 None)

## 2. 패키지와 인터페이스

### P1 diagnose — `v2/engine/diagnose.py` (T10, T02~T04·T11 테스트 포함)
```python
@dataclass
class Change:      # 다음 달에 바꿀 칸 하나
    field_id: str; label: str; media: str; new: object; note: str; rule_id: str
@dataclass
class Finding:
    id: str; title: str; funnel: str
    status: str            # "fired" | "passed" | "no_data"
    message: str           # says에 metrics.fmt로 숫자를 넣은 문장 (fired일 때)
    evidence: Dict[str, str]   # 조건에 쓰인 metric → 보기 좋은 값
    changes: List[Change]; advice: Optional[str]; caveat: Optional[str]; grade: str
def evaluate(metrics: dict, rules: Optional[list] = None) -> List[Finding]
def fired(findings) -> List[Finding]
def next_changes(findings) -> List[Change]   # fired만, 같은 칸은 먼저 나온 규칙 하나 (note는 합침)
```
- set_from은 metrics의 그 키 값으로 (없으면 그 Change는 빼고 Finding은 유지).
- **골든 테스트 (필수)**: 가상 데이터 mode=sim, Context(start=2026-11-16, end=2026-12-15)에서 다정 규칙 8개가 정확히 이렇게 걸림:
  weekly_freq_high 없음 · awareness_freq_low C1·C3 · creative_fatigue 없음 · placement_quality C2 · ig_share_low C2 · search_demand_cap C4 · target_saturation C3 · awareness_hidden C1·C2·C3·C1b. C0는 아무 규칙도 fired 아님.
- 기존 모듈 테스트도 이 패키지가 쓴다 (`v2/tests/test_core.py`): specs.check_all()==[], 데모 엑셀 표 5개 읽힘·problems 없음, 머리글 별칭(실제 메타 CSV 화면 이름)으로 읽기, 필수 열이 없을 때 고치는 법이 든 문제 문장, C0 sim 전후 +31%±3%p·보정 0~+5%, C1·C2·C3 sim 광고 덕분 검색 주문 추정이 정답 ±25% 안.

### P3 market — `v2/engine/naver_api.py`, `v2/engine/market.py` (T05, T08 엔진)
- `naver_api.py`: 키 읽기·서명(기존 `src/engine/keys.py`를 옮겨 씀: Streamlit secrets → 환경 변수 → 루트 `.env`), 검색광고 API `GET /keywordstool` (키 `NAVER_AD_API_KEY, NAVER_AD_SECRET_KEY, NAVER_AD_CUSTOMER_ID`, base `https://api.searchad.naver.com`), 데이터랩 HUB `POST https://naverapihub.apigw.ntruss.com` + 경로 `/shopping/v1/category/keyword/{gender,age,device}`, `/shopping/v1/category/{gender,age}` (키 `NAVER_HUB_CLIENT_ID, NAVER_HUB_CLIENT_SECRET`, 헤더 `X-NCP-APIGW-API-KEY-ID`/`X-NCP-APIGW-API-KEY`; 11/15 호출 확인됨, 응답 `results[0].data[]`의 `period, ratio, group`). 참고 코드: `src/engine/naver_source.py`, `src/engine/naver_hub.py`.
  - 캐시: `v2/data/cache/` (git 제외) → 없으면 `v2/data/cache_examples/` (커밋, 시연용 디저트 예시) → 없으면 None. 오류는 쉬운 문장으로, 앱을 멈추지 않음.
- `market.py`:
```python
def keyword_table(seeds: List[str], online: bool = True) -> Optional[pd.DataFrame]
    # 열: keyword, total_qc, mobile_qc, pc_qc, mobile_clicks, mobile_ctr(%), comp, tier(대표/세부/롱테일)
def classify(df, seeds) -> pd.DataFrame   # + intent: "선물·답례" | "시즌" | "상품" | "제외: 만들기" | "제외: 매장·지역" | "관련 낮음"
def audience(keyword: str, category: str = "50000006", online: bool = True) -> Optional[dict]
    # {"female": 0.82, "ages": {"10":..,"20":..,"30":..,"40":..,"50":..,"60":..}, "mobile": 0.75,
    #  "monthly": {"2025-11": 100, ...}, "peak_month": 11, "index": {"female": 1.3, "30": 2.8, ...}, "grade": "B"}
    # index = 키워드 비중 ÷ 분야 전체 비중 (category_baseline)
@dataclass
class MarketReport:
    seeds; groups: pd.DataFrame (intent별 키워드 수·검색수 합·평균 클릭률·대표 키워드)
    keywords: pd.DataFrame (classify 결과)
    recommended: List[str]   # 선물·답례·시즌·상품 중 세부(300~1만) 위주 최대 10개
    negatives: List[str]     # 제외 묶음 + 관련 낮음 상위
    audiences: Dict[str, dict]  # 추천 상위 3개 키워드의 audience
    headline: str            # 예: "답례품쿠키를 찾는 사람은 30대 여성이 분야 평균의 2.8배, 11월에 가장 많이 찾아요"
def build(seeds: List[str], online: bool = True) -> Optional[MarketReport]
```
- 시연 캐시: 실제 키로 디저트 예시 seeds `["휘낭시에", "쿠키선물세트", "답례품쿠키", "디저트선물", "수제쿠키"]`를 한 번 받아 `cache_examples/`에 저장 (키는 저장하지 않음, 응답만).
- 11/15 실측 참고: 답례품쿠키 여성 82%·30대 48%(식품 분야 30대 17%), 쿠키선물세트는 9월·2월 정점, 연관 키워드에 '서울가볼만한곳' 같은 무관 단어가 섞여 나옴.

### P4 planner — `v2/engine/planner.py`, `v2/engine/datacheck.py` (T09, T04)
```python
@dataclass
class BudgetPlan:
    budget: int; days: int; objective: str           # "트래픽" | "인지도"
    naver_cap_month: Optional[int]; naver_month: int; meta_month: int
    naver_daily: int; meta_daily: int; naver_bid: int   # 10원 단위
    demand_capped: bool                               # 네이버 수요가 예산 몫보다 작음
    meta_forecast: Dict[str, float]  # impressions, reach, frequency, weekly_frequency, link_clicks, cpm_low, cpm_high
    naver_forecast: Dict[str, float] # clicks, impressions
    notes: List[str]                 # 사장님에게 보여 줄 문장 (근거 등급 포함)
def plan_budget(budget: int, keywords: Optional[pd.DataFrame] = None, objective: str = "트래픽",
                days: int = 14, target_key: str = "넓게", naver_share_max: float = 0.5, cpc: Optional[int] = None) -> BudgetPlan
```
- 네이버 상한 = Σ(고른 키워드 월 검색수 × 네이버 CTR 가정 중간값) × CPC 가정 → 네이버 몫 = min(상한, 예산 × naver_share_max), 남는 돈은 메타.
- 메타 도달 = T·(1 − e^(−노출/T)) (T = 실효 타겟), 노출 = 지출 ÷ CPM × 1000, 링크 클릭 = 노출 × CTR (트래픽만).
- 키워드가 없으면 네이버 상한 없이 예산 × naver_share_max.
- `datacheck.py`: `check(bundle) -> pd.DataFrame` 열 `가정, 기대 범위, 관측값, 케이스, 통과` — 가상 데이터(sim)가 assumptions.yaml 범위대로 나왔는지 (트래픽 CPM, 인지도 CPM, 메타 링크 CTR, 네이버 CPC·CTR(브랜드 키워드 '소연베이크' 제외), forecast vs sim 지출 차이). 발표 10번 슬라이드용.

### P5 intake — `v2/engine/intake.py`, `v2/engine/tracking.py`, `v2/engine/copywriter.py` (T06, T07)
```python
@dataclass
class SetupContext:
    product: str; product_slug: str   # 영문 소문자 (NT 꼬리표용)
    store_type: str                   # "smartstore" | "own"
    month: str                        # "11월"
    media: List[str]                  # ["meta", "naver"]
    meta_daily: int = 0; naver_daily: int = 0; naver_bid: int = 0
    keywords: List[str] = field(default_factory=list); negatives: List[str] = field(default_factory=list)
    audience_hint: Optional[str] = None   # market 헤드라인에서 온 연령·성별 제안
def questions(media: List[str]) -> List[dict]     # kind in (precheck, question, llm), 광고 관리자 순서, shared_with 칸은 한 번만
def build_sheet(answers: Dict[str, object], ctx: SetupContext) -> pd.DataFrame
    # 고른 매체의 모든 칸: media, stage, field_id, label, value, kind_label(질문/사전 점검/챗봇 작성/자동/기본값/다음 사이클), why, changed(bool)
    # 값 우선순위: answers[field_id](덮어쓰기, 다음 달 변경 포함) > 묻는 칸의 답 > auto 함수 > default
def apply_changes(answers: Dict[str, object], changes: List["Change"]) -> Tuple[Dict[str, object], pd.DataFrame]
    # Change는 P1의 dataclass (field_id, label, media, new, note, rule_id) — duck typing으로 읽음, diagnose를 import하지 않음
    # 반환 diff 열: field_id, label, before, after, note
AUTO: Dict[str, Callable[[Dict, SetupContext], object]]  # campaign_name, adset_name, ad_name, meta_daily_budget, meta_tracking,
    # naver_campaign_name, naver_daily_budget, naver_bid, naver_keywords, naver_negative_keywords
```
- `tracking.py`: `slugify(text, fallback="item")` → `[a-z0-9_]`만, `nt_link(url, source, medium, detail, keyword)` (스마트스토어, nt_source·nt_medium 필수·영문만), `utm_link(url, source, medium, campaign)` (자사몰). 같은 입력 → 같은 링크, 기존 쿼리 보존.
- `copywriter.py`: `meta_copies(product, strengths, n=3)`, `naver_copies(product, strengths, n=3)` → `[{"headline", "text"}]`. `ANTHROPIC_API_KEY`가 있으면 Claude(`claude-haiku-5-5`)로, 없거나 실패하면 문장 틀. 네이버 제목 ≤15자·설명 20~45자 강제, '최저가·1위·최고·국내 유일' 같은 근거 없는 말 금지. 테스트는 가짜 클라이언트.

### P6 loop — `v2/engine/plan_io.py` (T12, P1·P5 뒤에)
```python
@dataclass
class Plan:
    version: str = "2.0.0"; month_index: int = 1; created: str = ""
    store: Dict[str, object]   # name, product, product_slug, store_type, price, margin_per_order, budget, seeds
    media: List[str]; answers: Dict[str, object]; budget_plan: Dict[str, object]
    history: List[Dict[str, object]]   # {"month": n, "fired": [rule ids], "changes": [diff rows]}
def to_json(plan) -> str; def from_json(text) -> Plan   # 잘못된 파일이면 PlanError(쉬운 문장)
def next_month(plan: Plan, findings) -> Tuple[Plan, pd.DataFrame]   # diagnose.next_changes → intake.apply_changes, month_index+1, history 추가
```
- 완료 기준: C2 sim 진단으로 next_month 하면 `meta.adset.placements`가 "Audience Network 제외"를 포함하고, C4는 네이버 하루 예산이 실제 쓴 만큼으로 바뀜.

### P7 app — `v2/app/main.py` (+ `v2/app/*.py`) (T14, 모두 뒤에)
- `streamlit run v2/app/main.py`. 스테퍼 3단계: ① 세팅(가게 정보 → 내 손님 찾기 → 예산·예측 → 질문 하나씩 → 세팅값 시트·링크·계획 파일 내려받기) ② 실행(측정 체크리스트, 결과 올릴 날) ③ 진단(결과 올리기 또는 예시 케이스 → 지표 → 진단 카드 → 효과 확인 → 다음 달 바뀐 칸 → 다음 달 시작).
- `UX_설계원칙.md` 7장 점검표를 지킨다. 대본: `plans/시연_시나리오.md`.
