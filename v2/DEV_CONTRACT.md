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

## 3. 개발 중 더해진 것 (2026-11-16 갱신)
| 모듈 | 더해진 것 |
|---|---|
| `naver_api` | `last_error() -> Optional[str]`: 마지막 조회 실패 이유(쉬운 문장), 조회 시작·성공 때 지워짐. 모든 예외를 잡아 앱을 멈추지 않음 |
| `market` | 씨앗 단어의 오타·변형(예: 빼낭시에)은 '상품', 생일·기념일은 '선물·답례', 시즌 단어(수능·빼빼로·크리스마스 등)가 선물 단어보다 먼저. `groups` 열: intent, count, total_qc, mobile_ctr, top_keyword |
| `diagnose` | None·NaN은 '데이터 없음'. 규칙 등급에 `calc`(계산) 추가 |
| `intake` | `is_noop()`: 지금 값과 같은 변경은 건너뜀. `_changed`는 그 달 변경만 |
| `plan_io` | 같은 칸에 규칙이 여럿이면 지금 값과 다른 첫 규칙 값. 예전 달에 거쳐 간 값으로는 되돌리지 않음(예산·결과당 비용 같은 측정값, 제외 키워드는 예외) |
| `app` | 위젯은 `ui.init_widget`으로 시작값을 한 번만 넣음(`value=`와 `key=` 같이 쓰지 않음). 조사 도우미 `ui.josa`. 2개월 차부터 '이번 달에 바뀐 칸' 표, 바뀐 게 없으면 '새로 바꿀 칸이 없어요' |

## 4. 기획과 다른 점 (해결 필요)
- **세팅은 챗봇 질답으로 하기로 함(기획 개정본 11/10).** 지금 v2는 ①-4 질문 단계만 채팅 말풍선이고, 가게 정보·내 손님 찾기·예산은 입력 폼이다. '이렇게 이해했어요' 확인 카드와 '세팅하다 막히면 물어보기'(근거·출처가 붙은 답)가 빠져 있다. → 5장에서 해결

## 5. 챗봇 세팅 (2026-11-16, v1을 참고하지 않고 새로 설계)
> 결정: ① 세팅 전체를 **챗봇 질답**으로 한다. **v1의 코드·자료(`src/`, `app/`, `data/rag/`, `tests/`)는 읽지도 옮기지도 않는다.** v2 칸 사양(`v2/specs/*_fields.yaml`)에서 출발한다.
> 설계 원칙: **빠르게** — 대부분의 턴은 LLM 없이 규칙으로 즉시 답한다. **정확하게** — 숫자는 엔진 값만, 설명은 칸별 도움말(공식 출처·확인일)만 근거로, 근거에 없으면 "자료에 없어요"와 공식 도움말 링크.
>
> | 층 | 하는 일 | LLM |
> |---|---|---|
> | 대화 엔진 | 질문 순서(칸 사양), 답 해석(금액·선택·번호), 확인 카드, 고치기 | 없음 |
> | 엔진 숫자 | 예산 배분·예상 주문·진단 (planner·metrics) | 없음 |
> | 칸별 도움말 | 지금 칸·같은 단계 칸 안에서 미리 쓴 답(출처 포함)을 바로 | 없음 |
> | 자유 질문 | 도움말로 답이 안 될 때만, 도움말+코치 숫자를 근거로 스트리밍 답 | Claude Opus 5.5 (effort low) |

### K 칸별 도움말 — `v2/specs/help/meta.yaml`, `v2/specs/help/naver.yaml`, `v2/tests/fixtures/help_eval.yaml`
- **공식 도움말을 새로 조사**해서 쓴다 (메타 비즈니스 도움말 센터·Meta for Business, 네이버 검색광고 고객센터·광고주센터 도움말 등 공식 페이지). 블로그·대행사 자료는 공식에서 못 찾았을 때만, 그때는 `check: "△"`.
- 저작권: 원문을 옮기지 않고 요약. 직접 인용은 칸당 15단어 이하 1곳까지, 따옴표로.
- 형식 (칸 사양의 모든 칸 id마다 하나, 칸 사양에 없는 id 금지):
```yaml
- field_id: meta.adset.end_date
  summary: "3~5문장. 이 칸이 무엇이고, 초보 판매자는 무엇을 넣으면 되는지. 화면에 보이는 글자는 그대로."
  faq:
    - q: "종료일 안 넣으면 어떻게 돼?"
      a: "1~3문장 답"
  keywords: [종료일, 끝나는 날, 언제까지, 기간]     # 사장님이 쓸 법한 말 (검색용)
  sources: [{title: "...", url: "https://..."}]
  check: "✅"            # ✅ 공식에서 확인 / △ 공식에서 못 찾아 다른 자료 / ❓ 확인 못 함
  checked: "2026-11-16"
```
- `help_eval.yaml`: 칸마다 사장님 말투의 시험 질문 1~2개(faq 질문을 그대로 복사하지 말고 바꿔 말하기) + 칸과 상관없는 질문 몇 개(`expect: none`). 형식: `- {q: "...", step: "<지금 묻는 칸 id>", expect: "<맞는 칸 id 또는 none>"}`

### H 도움말 엔진 — `v2/engine/helpdesk.py`
```python
def load_help(dir=SPEC_DIR/"help") -> Dict[str, dict]            # field_id → 도움말 항목
def is_question(text: str) -> bool     # 질문인가 답인가. "2만 6천원", "네", "1", "스토어 방문 늘리기", "휘낭시에, 쿠키" → False
@dataclass
class HelpAnswer:
    kind: str                # "help" | "coach" | "llm" | "none"
    text: str
    field_id: Optional[str]
    sources: List[Dict[str, str]]   # [{"title","url","check"}]
    stream: Optional[Iterator[str]] = None   # kind=="llm"일 때 화면이 st.write_stream으로 그림
def answer(question: str, step_id: Optional[str] = None, ctx: Optional[dict] = None, client=None) -> HelpAnswer
```
- 찾는 순서: ① 지금 칸(step_id) ② 같은 단계(stage) 칸 ③ 같은 매체 전체. 점수 = 질문 단어와 faq 질문·keywords·라벨의 겹침(한국어 조사 떼기, 동의어). 충분히 맞으면 **미리 쓴 답(faq a 또는 summary)을 그대로** + sources (kind="help").
- "얼마 나눠?", "하루 얼마?", "몇 개 팔아야 남아?" 같은 코치 숫자 질문은 kind="coach": ctx(예산 계획·가게 숫자)의 값만으로 답, 값이 없으면 지어내지 않음.
- 못 찾으면: client가 있을 때만 kind="llm" — **모델 `claude-opus-5-5`, `output_config={"effort": "low"}`, 스트리밍(`client.messages.stream`), 짧은 `max_tokens`(약 400), 시스템 프롬프트 = 규칙 + 해당 매체 도움말 전체(프롬프트 캐시 `cache_control`), 서버 측 거절 대비 `betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"`, `stop_reason=="refusal"`이면 none으로.** 근거(도움말·ctx) 밖 사실은 쓰지 말고 모르면 모른다고. 타임아웃(약 15초)·오류면 none. 키는 `ANTHROPIC_API_KEY`(Streamlit secrets → 환경 변수 → .env, 값 출력 금지). client 없으면 kind="none": "자료에 없어요" + 지금 칸의 공식 출처 링크.
- 시험: `help_eval.yaml`로 **칸 맞힘 90% 이상, none 문항은 none으로**, 도움말 답 평균 응답 50ms 이하(LLM 제외). LLM 경로는 가짜 client로 시험(네트워크 금지).

### C 대화 엔진 — `v2/engine/chat_parse.py`, `v2/engine/conversation.py` (순수 파이썬, 상태는 JSON으로 저장 가능)
```python
# chat_parse.py
def parse_money(text) -> Optional[int]     # "2만 6천원"·"26,000"·"3만"·"30만원"·"1.5만"·"삼만" → 정수, 못 읽으면 None
def parse_choice(text, options) -> Optional[str]   # 번호·부분 일치·예/아니요
def parse_words(text) -> List[str]
def suggest_slug(product) -> str           # 영문 소문자 후보, 없으면 "item"
def is_url(text) -> bool
# conversation.py
@dataclass
class Turn: role: str; text: str; kind: str = "text"; data: Dict = field(default_factory=dict); chips: List[str] = field(default_factory=list)
    # kind: text | confirm_card | market_card | budget_card | help | error | done
@dataclass
class Services:   # 화면이 넣어 줌, 테스트는 가짜
    market: Callable[[List[str]], object]                       # → MarketReport | None
    plan: Callable[[dict, Optional[object], str, int], object]   # store, market, objective, days → BudgetPlan
    help: Callable[[str, Optional[str], dict], object]           # question, step_id, ctx → HelpAnswer
    questions: Callable[[List[str]], List[dict]]                 # intake.questions
    copies: Callable[[str, str], Dict[str, list]]                # product, strengths → {"meta": [...], "naver": [...]}
def start(media) -> dict; def handle(state, text, sv) -> dict; def choose(state, chip, sv) -> dict
def edit(state, key) -> dict; def skip_rest(state, sv) -> dict
def to_answers(state) -> Dict[str, object]; def to_store(state) -> dict; def demo_state(sv) -> dict
```
- 흐름: 가게(이름 → 상품 → 판매가 → 1개 남는 돈 → 한 달 광고비 → 판매처 → 영문 이름) → **확인 카드 "이렇게 이해했어요"**(맞아요/고칠래요) → 내 손님(상품 단어 제안 칩 → market_card) → 예산(목표·기간 칩 → budget_card) → 칸 질문(intake.questions 순서, 문구 칸은 장점을 받아 copies → 칩) → done.
- 어느 단계에서든 `is_question`이면 sv.help(지금 칸 id) 답을 help Turn으로 보이고 **같은 질문을 다시** 묻는다. 못 읽은 답은 error Turn(고치는 법 + 예시 칩), 단계 그대로. 해석한 값은 되말한다("26,000원으로 이해했어요").
- `demo_state`: 소연베이크(수제 구움과자, 26,000원, 남는 돈 8,000원, 월 30만 원, 스마트스토어, soyeonbake)를 채워 확인 카드까지 온 상태.

### U 화면 — `v2/app/setup.py`, `v2/app/run.py`, `v2/app/diagnose.py`(+ `v2/app/chat.py`, `v2/app/board.py`, `v2/app/guide.py`)
> 사용자 결정(11/16): **왼쪽은 작업판, 오른쪽은 챗봇 대화 (11/16 사용자 변경: 채팅을 오른쪽으로). 캐릭터 하나가 왼쪽 작업판을 돌아다니며 오른쪽 챗봇이 지금 말하는 칸·카드를 가리킨다.** ① 세팅 · ② 실행 · ③ 진단 모두 같은 배치.

**배치**
- `st.columns([7, 5])` (왼쪽 작업판, 오른쪽 대화). 좁은 화면에서는 대화가 위, 작업판이 아래로 쌓이고 캐릭터는 숨기되 강조 테두리는 남긴다.
- 오른쪽 대화: `st.chat_message` 기록(높이 고정 `st.container(height=…)`로 스크롤), 맨 아래 `st.chat_input`, 마지막 bot Turn의 칩(`st.pills`/버튼 줄). help 답은 출처 링크와 ✅/△/❓, kind=="llm"이면 `st.write_stream`.
- 왼쪽 작업판 = 대화가 채워 가는 결과물. 단계별:
  | 대화 단계 | 왼쪽 작업판 |
  |---|---|
  | 가게·확인 | '가게 카드': 이름·상품·판매가·남는 돈·광고비·판매처·영문 이름. 답하는 대로 채워짐, 빈칸은 '아직' |
  | 내 손님 | 손님 판: 헤드라인, 검색어 묶음, 누가(연령·성별 막대), 언제(월별 선), 광고 검색어·제외어 |
  | 예산 | 예산 판: 네이버·메타 하루 예산, 예상 클릭·도달·주문, 근거 등급, 손해 가능성 문장 |
  | 칸 질문 | **세팅 보드**: 매체 → 단계(캠페인·광고 세트·광고…) → 칸 줄. 줄마다 라벨·값·종류 배지(질문/사전 점검/챗봇 작성/자동/기본값/다음 사이클). 답하면 그 줄 값이 바로 바뀜 |
  | done | 세팅 보드 전체 + 내려받기(계획 파일·CSV·엑셀). 표가 필요하면 `st.dataframe`은 아래 '표로 보기'에만 |
  | ② 실행 | 체크리스트 카드·추적 링크·결과 올릴 날. 오른쪽 대화가 항목을 하나씩 안내('다음' 칩) |
  | ③ 진단 | 지표 카드·진단 카드·효과 확인·다음 달 바뀐 칸. 오른쪽 대화가 걸린 진단을 하나씩 설명('다음 카드' 칩), 사장님 질문은 helpdesk로 |
- 칸·카드마다 `st.container(key="t-<안전한 id>")`로 감싸 가리킬 수 있게 한다(id의 '.'은 '-'로). 예: 세팅 보드 줄 `t-meta-adset-end_date`, 가게 카드 항목 `t-store-price`, 진단 카드 `t-rule-placement_quality`.

**가리키기 (focus)**
- 지금 가리킬 대상 `focus`는 화면이 대화 상태에서 계산한다(대화 엔진 수정 없음): store 단계면 그 store 키, fields 단계면 지금 칸 id, 카드 Turn이면 그 판, ②③에서는 안내 중인 항목.
- 캐릭터: **우리가 직접 만든 단순한 캐릭터**(SVG/CSS, 기존 캐릭터·브랜드를 흉내 내지 않음. 예: 둥근 '코치' 얼굴 + 가리키는 손). 다시 그릴 때 focus 대상 컨테이너 안(오른쪽 가장자리, 채팅 쪽)에 캐릭터와 짧은 말풍선(예: "여기에 들어가요")을 그리고, CSS keyframes로 오른쪽(채팅 쪽)에서 미끄러져 들어오게 한다. 대상에는 강조 테두리(색만이 아니라 두께·아이콘으로도 구분).
- 스크롤: 작은 `st.components.v1.html` 스크립트로 부모 문서의 `.st-key-t-…`를 `scrollIntoView({block:"center"})`. 접근이 막히면 조용히 건너뛴다(기능은 그대로).
- `prefers-reduced-motion`이면 애니메이션 없이 위치만. 캐릭터는 정보를 대신하지 않는다: 같은 내용이 오른쪽 대화와 강조 테두리에도 있어야 한다(UX_설계원칙: 꼭 알아야 할 정보를 장식에 숨기지 않기).
- 끄기 스위치('캐릭터 보이기' 토글, 즉시 반영).

**그 밖**
- 진행 표시(가게 → 확인 → 손님 → 예산 → 세팅 질문), '지난 답 고치기' 칩, '남은 질문은 권장 답으로'. 2개월 차부터 '이번 달에 바뀐 칸'은 세팅 보드에서 바뀐 줄 강조 + 캐릭터가 첫 바뀐 줄을 가리킴.
- 홈 '예시로 해 보기' → demo_state (확인 카드부터 이어서 대화, 왼쪽 작업판엔 채워진 가게 카드).
- 위젯 규칙(ui.init_widget, value=와 key= 같이 쓰지 않기), ui.josa 유지. 외부 패키지 추가 금지.

**색과 글자 (11/16 사용자 결정: 라이트 모드)**
- 테마는 `.streamlit/config.toml`의 `[theme]`(라이트 고정, 기준색 `#2F5D8A`, 본문 `#2B3340`, 보조 글자 `#6B7686`, 배경 `#FFFFFF`, 카드 `#F7F8FA`, 글꼴 Pretendard). 앱 코드에서 다크용 색을 따로 넣지 않는다.
- 차트 색 고정: 네이버 `#4C78A8`, 메타 `#C8661A`(초록 금지), 이익·손해에만 초록·빨강. 바뀐 칸 강조는 연노랑 바탕 + 테두리·아이콘.
- 상태 배지는 연한 바탕 + 진한 글자 + 아이콘 + 글자 라벨 (기획안_개정본_세팅코치.md 5-5 표).

### U2 가리키기 개선 (11/16, REA 레퍼런스 분석 `조사/05_UI_레퍼런스_가리키며안내하기.md`)
- 작업판 안에서만 스포트라이트: focus 대상이 있으면 **왼쪽 작업판의 다른 칸·카드는 흐리게**(불투명도 약 0.45, 전환 0.2초), 대상은 그대로 + 기준색 테두리·옅은 그림자. 오른쪽 채팅은 절대 흐리게 하지 않음.
- 캐릭터를 발표 화면에서도 보이게 키움(얼굴 약 44px 이상). 말풍선 = **칸·카드 이름 + 진행 "3/12"**(채팅의 진행 숫자와 같게) + 대상 쪽을 가리키는 화살표. 짧은 말 한 줄(예: "여기에 들어가요").
- 스크롤은 대상이 화면 밖일 때만 `scrollIntoView({behavior:"smooth", block:"center"})`, 움직임 줄이기 설정이면 `behavior:"auto"`.
- 접근성: 캐릭터·말풍선 장식은 `aria-hidden="true"`, 대신 화면에 안 보이는 `aria-live="polite"` 영역에 "지금 보는 칸: 종료 날짜 (3/12)"를 바꿔 씀.
- 외부 투어 라이브러리는 쓰지 않음(Streamlit 다시 그리기와 충돌). CSS와 기존 `guide.py` 안에서만.
