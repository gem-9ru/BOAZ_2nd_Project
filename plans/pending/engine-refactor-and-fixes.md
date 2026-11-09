# 코치 엔진 정리와 버그 수정 (MVP 7e)

> 작성 2026-11-10 · 기획 세션 · 상태: **확정 (11/10)**, 1단계 개발 요청
> 근거: 구조 점검 1편 (app/main.py), 2편 (한 달 뒤 흐름·코치 엔진·예전 엔진). 버그는 모두 코드에서 직접 확인함.
> 함께 보는 계획: `plans/pending/setup-chatbot-optimization.md` (7d). 7d의 '광고 세팅값'은 이 계획의 Answer·Plan 위에 얹힘.
> 마감 12/3, 12/1부터는 리허설만 → 개발은 **11/30까지**.

## 목표 (재는 방법)
- 버그 8개가 테스트로 고정되어 다시 생기지 않는다 (버그마다 실패하는 테스트를 먼저 쓰고 고침).
- 핵심 계산이 화면 파일 밖으로 나온다: `app/main.py`의 모듈 맨 위 계산(701–781)과 한 달 뒤 다시 계산(614–630)이 엔진 함수 호출 한 줄씩이 된다.
- 테스트 158개 + 새 테스트 모두 통과, 예시 1(원두)·2(단백질) 숫자는 **결정된 변경(Q1·Q2) 말고는 그대로**.

## 버그 목록 (확인됨)
| # | 버그 | 위치 | 고치는 단계 |
|---|---|---|---|
| B1 | 고른 예산으로 다시 나눠도 클릭 비용·필요 구매율은 권장 예산 값 | main.py:752–753, 778 | 1단계 (작은 수정) → 2단계에서 구조로 |
| B2 | 한 달 뒤 다시 계산 때 재구매 등급 D 고정 (실측이면 C), 문구도 "아직 가정" | main.py:629, 636 | 1단계 |
| B3 | 계획 파일에 재구매 실측값 없음 → 불러오면 '실측'이 '가끔' | report.py:18, main.py:703–704 | 1단계 |
| B4 | 계획 파일 검사: bool·NaN·무한대 통과, 없는 날짜 통과 → 4단계에서 멈춤 | report.py:48, 51, 53 | 1단계 |
| B5 | '가장 많이 빠지는 단계' 규칙 세 개 | coach.py:230, measure.py:181, insights.py:30 | 4단계 |
| B6 | 손님 1명 가치: 손익분기 p·(1+재구매) vs 시뮬레이션 p·(1.1+재구매) | coach.py:41, montecarlo.py:28 | 4단계 (Q1) |
| B7 | 네이버 리포트: '비용'이 '평균클릭비용'에 걸릴 수 있음, 전환 유형 행 합산, 합계 행 | report.py:66, 75, 127 | 1단계 (제외어·합계 행) + 4단계 (어댑터) |
| B8 | 메타 클릭 비용 기본값이 네이버 대략값 1,300원 | main.py:747 | 1단계 (Q2) |

## 단계

### 1단계: 버그를 지금 구조에서 막기 (S, ~11/13)
지금 구조를 크게 바꾸지 않고, 버그마다 **실패하는 테스트 → 최소 수정**.
- B1: 다시 나눈 split에서 `cpc`·`need`·`need_year`를 다시 계산해 `ans`에 넣음.
- B2: `g2["retention"]`을 처음 계산의 `grades["retention"]`에서 가져오고, 문구는 실측이면 "재구매는 주문 내역 실측(C)".
- B3: 계획 파일에 `repurchase_measured`(숫자 dict) 저장·불러오기, PLAN_VERSION 2 + 1→2 변환.
- B4: 숫자는 bool 제외·유한한 수만, 날짜는 `date.fromisoformat`로 진짜 날짜만, 선택지 값(q_repurchase·q_budget_pick·q_category)은 허용 목록.
- B7 일부: 제외어에 '평균' 추가, '합계'·'총계' 행 버림.
- B8: `NAVER_FALLBACK_CPC`를 메타 기본값으로 쓰는 곳에 `META_FALLBACK_CPC = 1_300`(같은 값, 출처·등급 C 주석) 상수를 새로 두고 그걸 씀. 숫자 변화 없음.
- 확인: `.venv/bin/python -m pytest -q` (158 + 새 테스트), 예시 1·2 숫자 비교표.
- 바뀔 파일: app/main.py (B1·B2·B8 몇 줄), src/engine/report.py, tests/test_report.py, tests/test_coach_pipeline.py(새)
- 선행: 없음

### 2단계: 코치 '풀기'를 엔진으로 — `CO.solve` → `Answer` (M, ~11/18)
- 인터페이스:
  ```python
  @dataclass
  class Answer:  # 화면이 아는 전부
      be: Breakeven; options: list; pick: str; budget: float     # 고른 예산 (광고 안 함이면 권장 금액)
      split: Split; mc: dict; grades: dict; prediction: dict
      cpc: float; need: float; need_year: float; default_pick: str
      cpc_src: str; ch_name: str
  def solve(inputs: CoachInputs, naver_curve, repurchase: RepurchaseSource,
            pick: str | None = None, actuals: Actuals | None = None) -> Answer
  ```
  - `CoachInputs`: price, profit, max_budget, stores, meta_cpc(없으면 None), keyword.
  - `RepurchaseSource`: 이름(프리셋 또는 '실측') + 1년 횟수 + 등급(프리셋 D / 실측 C). `rep_value`·`rep_word`·'실측' 대체가 여기로.
  - `pick=None`이면 기본 선택 규칙 적용. 사장님이 고른 값을 주면 그 예산으로 다시 나눔 (두 번 계산은 solve 안에 숨김).
  - `actuals`(한 달 뒤 실측: 네이버 클릭·비용, 메타 클릭·비용, 주문, 클릭 합계)가 있으면 곡선 보정·CVR·등급 A를 넣어 다시 계산 → report_section의 614–630이 `solve(..., actuals=)` 한 줄.
  - `Split`(데이터클래스): `naver: Leg|None, meta: Leg, table, naver_capacity, naver_marginal_cpc`. `Leg = spend, curve, cpc`. `channels[0]` 파고들기를 없앰. **기존 `split_budget`의 dict 반환은 이 단계에서 Split으로 바꾸고 호출 6곳을 함께 고침** (확장→이전→정리 순으로, 단계마다 테스트 통과).
- 등급표(grade_rows)·배분 이유(split_card)도 Answer가 들고 나옴 → 등급 정보는 한 곳(B 계열 재발 방지).
- 전역 `price`·`stores`·`cparams`·`repurchase`를 함수 인자로.
- 확인: solve 단위 테스트(기본 선택 바뀜, 고른 예산 다시 나눔, 광고 안 함, 실측 C, actuals로 다시 계산), 예시 1·2가 1단계 뒤 숫자와 같음.
- 바뀔 파일: src/engine/coach.py, app/main.py (701–781, 614–630, 647–690), tests/test_coach.py, tests/test_coach_pipeline.py
- 선행: 1단계

### 3단계: 상태 키 선언 + Plan (M, ~11/21)
- `src/engine/session_schema.py`: 기능별 키를 한 번 선언 (`persist`=단계 이동 때 유지, `plan`=계획 파일, `reset`='내 숫자로 시작' 때 지움). `_KEEP`·`PLAN_INPUT_KEYS`·초기화 목록을 이 선언에서 만듦.
- `Plan` 데이터클래스: 입력, 재구매 실측, 한 달 뒤 입력(쓴 돈·클릭·쿠폰·리포트·합계), 예측, 시작일, **세팅값(7d용 빈 자리)**. `to_json`/`from_json`(엄격한 검사, 버전 변환), `apply_plan(ss, plan)`.
- 단계 이동: `go_to(step)`, `reset()`, `load_plan()` — `coach_step`을 쓰는 7곳이 이 셋만 부름.
- 확인: 계획 왕복 테스트(모든 키), 초기화가 선언된 키를 다 지우는지, 단계 열림 규칙.
- 바뀔 파일: src/engine/session_schema.py(새), src/engine/report.py (계획 부분 이동), app/main.py (224–232, 501–527, 783–829, 1011–1014), tests/test_session_schema.py(새)
- 선행: 1단계 (2단계와 따로 진행 가능, 같은 main.py라 **순서대로**)

### 4단계: 계산 한 곳씩 (M, ~11/26)
- 4a 손님 1명 가치 (B6): `model.per_customer_value(params, months)` 하나, `breakeven`·`breakeven_grid`·`MC._per_customer_gp`가 모두 부름. 첫 달 = 1번 구매(Q1), 그 뒤 달 × PURCHASE_FREQ. `retention_scale_for`도 같은 정의로. 같은 값 확인 테스트(원두·단백질 프리셋에서 breakeven.year == MC 손님 가치).
- 4b 퍼널 진단 하나 (B5): `measure.diagnose_funnel`(기준 대비 비율)만 남김. `coach.biggest_drop`·`insights.biggest_drop`은 그 결과를 읽게, 할 일 문장 표 둘(STEP_PRESCRIPTIONS, FUNNEL_DIAG_STEPS)을 하나로.
- 4c 파일 어댑터 (B7): `src/engine/uploads.py`에 `guess_columns(fields, columns)` 하나 + `NaverReport`·`MetaReport`·`StoreStats`·`SmartstoreOrders` 어댑터 (별칭·거를 행·비용 VAT 기준·전환 유형=구매만·개인정보 열 버리기를 각자 가짐). report·measure·orders의 열 추측 세 벌 삭제. MVP 8(실제 네이버 리포트 열)은 이 어댑터의 별칭만 고치면 됨.
- 4d 상수·판정 (Q3): 30.4·주당 일수·판매 기준을 `defaults`에서만 가져옴, WARN_SALES·MIN_SALES 하나로. '광고 안 함'은 `MC.action` 하나: main.py `verdict()`(1712)와 insights의 PMF·최적 지출 문장은 같은 판정을 보여 주고 LTV/CAC는 참고 숫자로.
- 4e 정리: `data_loader.describe_sources` 삭제, `omtm_value` 내보내기 삭제, `_ga4_table` 캐시, "(data deleted)"를 상수로.
- 확인: 각 항목 테스트 + 전체 pytest + 예시 숫자 비교표.
- 바뀔 파일: model.py, coach.py, montecarlo.py, measure.py, insights.py, report.py, orders.py, uploads.py(새), defaults.py, data_loader.py, main.py (호출부), tests
- 선행: 2단계 (4a·4b는 1단계 뒤 바로도 가능)

### 5단계: 7d 얹기 (setup-chatbot-optimization.md 1~3단계)
- 7d의 '광고 세팅값 모듈'(`ad_setup.build_settings(answer, media) -> SettingsPlan`)은 2단계 Answer를 받고, 세팅값은 3단계 Plan의 빈 자리에 저장.
- 순서·범위는 7d 계획 그대로.
- 선행: 2·3단계

### 리허설 전 마무리 (~11/30)
- 배포 앱에서 예시 1·2로 1→4단계 끝까지, 계획 파일 내려받기→올리기, 주문·판매처 파일 올리기 확인.
- 발표 숫자 갱신(`중간발표_갱신_문장.md`): Q1·Q2로 바뀐 숫자만.

## 결정 기록
| 결정 | 고른 것 | 이유 |
|---|---|---|
| 순서 | 버그 먼저(작은 수정+테스트) → solve → Plan → 계산 한 곳씩 → 7d | 마감 안전, 7d가 Answer·Plan 위에 올라감 |
| 재구매 실측 등급 | 처음 계산·한 달 뒤 모두 C | 관찰분 A + 1년 연장 곡선 C (42c6378과 같은 판단) |
| 퍼널 진단 기준 | 기준(GA4 공개 표본) 대비 비율 | 7a에서 정한 방식, 단계마다 원래 비율이 달라서 그냥 최솟값은 늘 같은 단계를 짚음 |
| 계획 파일 | 버전 2, 1→2 변환 | 이미 내려받은 계획 파일을 버리지 않게 |
| Q1 손님 1명 가치 | 첫 달은 딱 1번 구매, 그 뒤 달부터 PURCHASE_FREQ(1.1)번. 손익분기 식에 시뮬레이션을 맞춤 | 사용자 결정 (11/10). 보수적, 발표 숫자 조금 낮아짐 (대략 원두 4→3, 단백질 75→70, 메타만 계산 기준) → 4a 뒤 발표 문장 갱신 |
| Q2 메타 클릭 비용 기본값 | 1,300원 유지, 상수 이름을 `META_FALLBACK_CPC`(출처: 네이버 키워드 63개 중앙값, 등급 C)로 | 사용자 결정 (11/10). 숫자 그대로, '메타에 네이버 값' 혼동만 없앰 |
| Q3 '광고 안 함' 판정 | 코치 기준 하나 (100번 중 ○번, 80·50). '더 보기'는 같은 판정을 보여 주고 LTV/CAC·최적 지출은 참고 숫자로만 | 사용자 결정 (11/10) |
| Q4 범위·일정 | ①②③⑤는 11/30까지 확정. ④ 중 손님 가치(4a)·퍼널(4b)은 함께, 파일 어댑터(4c)·상수(4d)·정리(4e)는 11/26까지 못 끝내면 발표 뒤로 | 사용자 결정 (11/10) |

| 4b '더 보기' 퍼널 문장 | 시뮬레이션 단계는 그냥 최솟값 유지, 코치·퍼널 카드만 기준 대비 비율로 통일. 할 일 문장 표 두 개 합치기는 보류 | 기획 세션 판단 (11/10, 리팩토링 세션 질문): 더 보기는 판매처 실측이 아니라 기준 대비가 늘 1.0이 됨. 화면 문구 변화 없음 |
| 메타 기본 CPC 등급 | D 하나로 (INPUT_GRADES도 D, 몬테카를로 그대로) | 사용자 결정 (11/10). 숫자 그대로 |

## 다음에 정할 것
- 4b: 할 일 문장 표 두 개(STEP_PRESCRIPTIONS 5단계, FUNNEL_DIAG_STEPS 3단계) 합치기 — 화면 문구가 바뀌어 사용자 확인 후.
- 배포 앱에서 계획 파일 내려받기→올리기, 실측 + 한 달 뒤 C 캡션 화면 확인은 아직 (테스트로만 확인).
- 4c: 네이버 리포트 실제 열 이름은 팀원 파일(MVP 8)이 와야 확정. 그 전엔 지금 별칭 유지 + 확인 안 된 것 ❓.
- 5단계: 7d 계획의 남은 질문(메타 노출 위치 단계)은 7d 3단계 시작 때.

## 늘 / 절대
- 늘: 버그마다 실패하는 테스트 먼저, 단계마다 전체 pytest 통과, 예시 1·2 숫자 비교표, UX 체크리스트(화면이 바뀌면).
- 절대: 한 번에 갈아엎기, 테스트 없이 옮기기, 광고 계정 쓰기, 개인정보 저장, 결정되지 않은 숫자 변경.

## 진행
| 단계 | 상태 |
|---|---|
| 1 버그 막기 | ✅ 3e7992e (테스트 158→177, 예시 1·2 기본 결과 그대로, 고른 예산≠권장일 때 클릭 비용·필요 구매율만 의도대로 바뀜) |
| 2 solve → Answer | 대기 |
| 3 상태 키·Plan | 대기 |
| 4 계산 한 곳씩 | 대기 |
| 5 7d | 대기 |
