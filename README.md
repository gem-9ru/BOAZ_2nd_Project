# AARRR 기반 광고 예산 시뮬레이터

광고 예산이 획득 → 활성화 → 유지 → 수익 → 추천으로 어떻게 이어지는지 12개월을 시뮬레이션하고,
예산을 늘릴지 · 채널을 바꿀지 · 퍼널의 어느 단계를 먼저 고칠지 추천하는 Streamlit 웹 서비스 (BOAZ 2차 프로젝트, Track 3).
기획은 [기획안.md](기획안.md), 기준 문서는 [프로젝트_실행계획.md](프로젝트_실행계획.md).

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
3. 배포 후 ② 획득 설계에서 "네이버 API 실시간 조회"가 켜지는지 확인. 막히면 캐시(오프라인)로 시연

## 구조
| 경로 | 내용 |
|---|---|
| `src/engine/` | AARRR 엔진: `acquisition`(포화 곡선), `model`(12개월 코호트), `optimize`(예산 최적화·레버·예산 스캔), `insights`(경고·인사이트), `experiment`(표본 크기), `data_loader`(기본값 로더), `naver_source`(API·캐시), `defaults`(기본값) |
| `app/` | Streamlit 화면 5개 탭 (`main.py`), 차트 (`charts.py`), 1단계 CSV 예시 |
| `src/collect/` | 네이버 API 수집 스크립트 |
| `data/processed/` | 팀 분석 산출물을 두면 엔진이 자동으로 우선 사용 (아래) |

## 엔진 기본값 연결 (`data/processed/`)
| 파일 | 컬럼 | 쓰이는 곳 |
|---|---|---|
| `ga4_funnel.csv` | medium, visit_users, view_users, cart_users, checkout_users, purchase_users | ③ 단계별 전환율 (없으면 `data/raw/ga4/`) |
| `fb_target_metrics.csv` | target, rel_cpa, purchases | ② 메타 타깃 상대 CPA (없으면 `defaults.py`) |
| `cohort_retention.csv` | months_since, retention, [customers], [segment] | ③ 리텐션 곡선 적합 (없으면 임시값) |

금액은 모두 원화 사용자 입력이고, 외부 데이터는 비율·상대값만 씁니다 (기획안 결정 3).
