# AARRR 기반 광고 예산 시뮬레이터

광고 예산이 획득 → 활성화 → 유지 → 수익 → 추천으로 어떻게 이어지는지 12개월을 시뮬레이션하고,
**광고비 증액 · 채널 재배분 · 퍼널 개선 · 자동 메시지** 중 무엇을 먼저 할지 같은 기준(12개월 남는 돈 증가)으로 비교하는 Streamlit 웹 서비스입니다 (BOAZ 2차 프로젝트, Track 3).
마케터가 쓰는 4개 도구(광고 관리자, 로그 분석, 어트리뷰션, 마케팅 자동화)를 다시 만들지 않고, 각 도구에서 나온 숫자를 받아 예산 결정 하나로 잇습니다.
기획은 [기획안.md](기획안.md), 기능 명세는 [기능명세_4개도구.md](기능명세_4개도구.md), 기준 문서는 [프로젝트_실행계획.md](프로젝트_실행계획.md).

배포: https://ad-budget-simulator.streamlit.app/ (프로토타입 v0.5)

## 화면

| 탭 | 답하는 질문 | 주요 기능 |
|---|---|---|
| ① 시작 | 1년 뒤 광고가 남겨 주는 돈은? | 객단가·마진·월 예산, 목표(OMTM), 데이터 준비 체크리스트 → 0단계/1단계 판정, 광고 성과 CSV |
| ② 광고 관리자 | 이 예산을 어느 매체·키워드에 얼마나? | 네이버 키워드 입찰가 곡선·포화 경고·세부 키워드 추천, 메타 CPC(또는 CPM·CTR), 학습 가능 예산 경고 |
| ③ 로그 분석 | 손님이 어디서 새고, 고치면 얼마가 남나? | 퍼널 단계 전환율(GA4 샘플 또는 내 유입경로 CSV), 가장 큰 기회, 세그먼트 비교·z-검정 |
| ④ 어트리뷰션 | 매체 보고 숫자를 믿고 나눠도 되나? | 5개 모델 기여 비교·변동폭 판정, 정제 전/후(자기 참조) 스위치, 보정 전후 배분, 매체 보고 vs GA4 체크리스트 |
| ⑤ 자동화 | 메시지가 광고비보다 나은가? | 장바구니 이탈·재구매·휴면 복귀 시나리오, 손익분기 반응률, 같은 돈을 광고에 쓸 때와 비교, 규제 배지, 대조군 실험 |
| ⑥ 결과·우선순위 | 무엇을 먼저 할까? | 4개 선택지 비교(PMF 경고 시 광고비 증액 보류), 선택지별 실험 카드, KPI·그래프·월별 CSV |

오른쪽 아래 **💬 도우미**는 규칙 기반 챗봇입니다. 용어 뜻, 지금 계산된 내 숫자, 숫자 출처, 먼저 할 일을 답합니다 (LLM 없음, `app/helpbot.py`의 `answer()`만 바꾸면 교체 가능).

## 로컬 실행
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app/main.py
.venv/bin/python -m pytest -q tests
```
네이버 API 키는 프로젝트 루트 `.env`에 둡니다 (`NAVER_AD_API_KEY`, `NAVER_AD_SECRET_KEY`, `NAVER_AD_CUSTOMER_ID`).
키가 없으면 `data/interim/naver_cache/`의 저장된 응답으로 오프라인 실행합니다.

## 배포 (Streamlit Community Cloud)
1. GitHub 저장소 연결 → Main file path `app/main.py`, Python 3.11 또는 3.12
2. Settings → Secrets에 `.streamlit/secrets.toml.example` 형식으로 키 입력 (환경 변수로도 읽음)
3. 배포 후 ② 광고 관리자에서 "네이버에서 지금 바로 조회"가 켜지는지 확인. 막히면 캐시(오프라인)로 시연

## 구조
| 경로 | 내용 |
|---|---|
| `src/engine/model.py` | 12개월 코호트 시뮬레이션 (`simulate`, 메시지 발송비 `extra_cost_m`) |
| `src/engine/acquisition.py` | 네이버 입찰가 곡선(볼록 껍질·한계 CPC), 메타 CPC 포화, 학습 가능 예산 점검 |
| `src/engine/optimize.py` | 예산 최적화, 레버 비교(손익분기 비용), 예산 스캔, ⑥ 4개 선택지 `compare_options` |
| `src/engine/attribution.py` | 경로 정제(자기 참조 제거), 5개 모델 기여, 총 전환 보존 보정계수 |
| `src/engine/automation.py` | 자동 메시지 시나리오 3종, 손익분기 반응률 |
| `src/engine/data_loader.py` | 기본값 로더, 퍼널 CSV 파서, 세그먼트 비교, 채널 전환율 배수 우선순위(CSV > 매체별 > 기본값) |
| `src/engine/` 그 밖 | `insights`(경고·인사이트), `experiment`(표본 크기), `naver_source`(API·캐시, 28일 → 월 환산), `defaults`(기본값·출처) |
| `app/` | 화면 (`main.py`), 차트 (`charts.py`), 도우미 챗봇 (`helpbot.py`), 광고 성과 CSV 예시 |
| `src/collect/` | 네이버 API 수집 스크립트 |
| `data/raw/ga4/` | GA4 공개 샘플 쿼리 결과 (퍼널, 구매 경로) |
| `data/processed/` | 팀 분석 산출물을 두면 엔진이 자동으로 우선 사용 (아래) |

## 입력 파일 형식
| 파일 | 컬럼 | 쓰이는 곳 |
|---|---|---|
| 광고 성과 CSV (업로드) | source, spend, clicks, conversions (이름이 달라도 매핑) | ① → 채널별 CPC·전환율 |
| 유입경로 CSV (업로드) | 세그먼트 열 + 단계별 사용자 수 열 (예: segment, 방문, 상담, 계약) | ③ 퍼널·세그먼트 비교 |
| 전환 경로 CSV (업로드) | path(접점을 " > "로 연결), conversions, [revenue] | ④ 어트리뷰션 |
| `data/processed/ga4_funnel.csv` | medium, visit_users, view_users, cart_users, checkout_users, purchase_users | ③ 기본 퍼널 (없으면 `data/raw/ga4/`) |
| `data/processed/fb_target_metrics.csv` | target, rel_cpa, purchases | ② 메타 타깃 상대 CPA (없으면 `defaults.py`) |
| `data/processed/cohort_retention.csv` | months_since, retention, [customers], [segment] | ⑤ 리텐션 곡선 적합 (없으면 임시값) |

금액은 모두 원화 사용자 입력이고, 외부 데이터는 비율·상대값만 씁니다 (기획안 결정 3).
자동화의 도달 비율·발송비·반응률은 기본값을 두지 않고 사용자가 입력합니다.
