# AARRR 기반 광고 예산 시뮬레이터

**광고를 처음 하는 사장님**이 첫 달 광고비를 정하고, 한 달 뒤 계속할지 판단하도록 돕는 Streamlit 웹 서비스입니다 (BOAZ 2차 프로젝트, Track 3).
첫 탭 **🧭 광고 코치**가 판매가와 1개 팔면 남는 돈만으로 "손님 1명에 얼마까지 써도 되나"를 알려 주고, 4단계(내 가게 → 답 보기 → 광고 준비 → 한 달 뒤)로 첫 광고를 안내합니다.
나머지 6개 탭은 **다음 단계**입니다. 광고 데이터가 쌓이면 광고비가 접촉 → 반응 → 행동 → 구매 → 재구매 → 추천으로 어떻게 이어지는지 12개월을 시뮬레이션하고,
**광고비 증액 · 채널 재배분 · 퍼널 개선 · 자동 메시지** 중 무엇을 먼저 할지 같은 기준(12개월 남는 돈 증가)으로 비교합니다. 수익(매출·이익)은 단계가 아니라 모든 단계에 걸친 돈의 축입니다 (밸류체인 v3).
기획은 [기획안.md](기획안.md), 코치 설계는 [초보자_코치_설계안.md](초보자_코치_설계안.md), 화면 원칙은 [UX_설계원칙.md](UX_설계원칙.md).

## 버전별 주소
| 버전 | 앱 | 코드 |
|---|---|---|
| v0.9 (현재, main): 코치 4단계 화면(내 가게 → 답 보기 → 광고 준비 → 한 달 뒤), 예시 체험, 시험 예산 3안, 손해 금액 | https://ad-budget-simulator.streamlit.app/ | [v0.9.2](https://github.com/gem-9ru/BOAZ_2nd_Project/tree/v0.9.2) |
| v0.8: 코치 + 측정 키트(광고 링크·쿠폰, 판매처 통계 파일) | (main에 덮어씀) | [v0.8](https://github.com/gem-9ru/BOAZ_2nd_Project/tree/v0.8) |
| v0.7: 초보자 광고 코치 (고정) | https://ad-budget-simulator-v07.streamlit.app/ (`release/v0.7` 브랜치, Python 3.12) | [v0.7](https://github.com/gem-9ru/BOAZ_2nd_Project/tree/v0.7) |
| v0.6.1 (밸류체인·공동구매, 코치 전) | — | [v0.6.1](https://github.com/gem-9ru/BOAZ_2nd_Project/tree/v0.6.1) |
| v0.5.1 (11/5 밸류체인 반영 전) | — | [v0.5.1](https://github.com/gem-9ru/BOAZ_2nd_Project/tree/v0.5.1) |
| v0.4 (11/5 기획 반영 전) | https://ad-budget-simulator-v04.streamlit.app/ (`release/v0.4` 브랜치) | [v0.4](https://github.com/gem-9ru/BOAZ_2nd_Project/tree/v0.4) |

전체 버전 목록은 [Tags](https://github.com/gem-9ru/BOAZ_2nd_Project/tags), v0.4 → v0.5.1 변경은 [비교](https://github.com/gem-9ru/BOAZ_2nd_Project/compare/v0.4...v0.5.1), v0.5.1 → v0.6.1은 [비교](https://github.com/gem-9ru/BOAZ_2nd_Project/compare/v0.5.1...v0.6.1).

## 화면

| 탭 | 답하는 질문 | 주요 기능 |
|---|---|---|
| 🧭 광고 코치 (첫 탭) | 광고비를 얼마까지 써도 되고, 한 달 뒤 계속해도 되나? | 4단계 스테퍼: ① 내 가게(판매가·남는 돈·최대 광고비·검색어) → ② 답 보기(손님 1명 한도 ÷ 클릭 비용 → 100명 중 몇 명이 사야 남나 → 신호등) → ③ 광고 준비(첫 채널 1개, 시험 예산 3안 + 광고 안 함, 준비 3가지, 광고 링크·쿠폰 만들기) → ④ 한 달 뒤(쓴 돈·클릭·판매 수 또는 판매처 통계 파일 → 판정과 다음 할 일 하나). 예시 체험(원두 쇼핑몰) |
| 시작 · 다음 단계 | 1년 뒤 광고가 남겨 주는 돈은? | 객단가·마진·월 예산(코치 값으로 미리 채움), 목표(OMTM), 데이터 준비 토글 → 0단계/1단계 판정, 광고 성과 CSV |
| 광고 관리자 | 이 예산을 어느 매체·키워드에 얼마나? | 네이버 키워드 입찰가 곡선·포화 경고·세부 키워드 추천, 메타 CPC(또는 CPM·CTR), 학습 가능 예산 경고 |
| 로그 분석 | 손님이 어디서 새고, 고치면 얼마가 남나? | 퍼널 단계 전환율(GA4 샘플, 내 유입경로 CSV, 또는 코치에 올린 판매처 통계), 가장 큰 기회, 세그먼트 비교·z-검정 |
| 어트리뷰션 | 매체 보고 숫자를 믿고 나눠도 되나? | 5개 모델 기여 비교·변동폭 판정, 정제 전/후(자기 참조) 스위치, 보정 전후 배분, 매체 보고 vs GA4 체크리스트 |
| 자동화 | 메시지가 광고비보다 나은가? | 장바구니 이탈·재구매·휴면 복귀 시나리오, 재구매 곡선 프리셋(보통 / 재구매 많은 업종), 손익분기 반응률, 규제 배지, 대조군 실험 |
| 결과·우선순위 | 무엇을 먼저 할까? | 4개 선택지 비교(PMF 경고 시 광고비 증액 보류), 선택지별 실험 카드, KPI·그래프·월별 CSV |

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
| `src/engine/naver_hub.py`, `seasonal.py` | 네이버 API HUB 데이터랩 검색어 트렌드 → 월별 계절 지수(평균 1), 실패 시 저장본 → 예시 파일(`data/examples/seasonality/`) → 미반영 |
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
