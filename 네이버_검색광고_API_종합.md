# 네이버 검색광고 API 종합

> 작성 2026-11-09 · 기획 세션
> 출처: 공식 문서 사이트 https://naver.github.io/searchad-apidoc (gh-pages 브랜치 전체), 공식 저장소 naver/searchad-apidoc(README, 오류 코드표, 샘플), 공식 위키 FAQ
> 원본 명세 JSON 9개: `assets/json/*.json` (Swagger 2.0). 화면(ads.naver.com)은 Claude 도구에서 막혀 있어 화면 글자와는 대조하지 않았습니다.

## 0. 한눈에

| 묶음 | 명세 파일 | 엔드포인트 | 하는 일 | 우리 앱 |
|---|---|---|---|---|
| 광고 관리 (NCC) | `ncc-heroes-ncc.json` | 79 | 캠페인 → 광고그룹 → 키워드·소재·확장소재, 비즈채널, 타깃, 공유 예산, 라벨 | 광고 세팅값 항목의 기준 (만들지는 않음) |
| 키워드 도구 | `ncc-keywordstool.json` | 1 | 연관 키워드 + 월간 검색수·클릭·경쟁 | **사용 중** (코치 Q1 수요) |
| 예상 실적·입찰가 | `estimate.json` | 10 | 입찰가별 노출·클릭·비용 예상, 순위별·최소 노출 입찰가 | **사용 중** (`/estimate/performance`) |
| 성과 통계 | `ncc-report.json` | 8 | 바로 보는 통계(`/api/stats`), 내려받는 대용량 리포트(`/api/stat-reports`) | MVP 8 리포트 열 이름의 공식 근거 후보 |
| 마스터 리포트 | `master-report.json` | 5 | 계정 안 모든 객체(캠페인·키워드·소재…)의 목록 파일 | 쓰지 않음 |
| 비즈머니 | `ncc-heroes-billing.json` | 4 | 잔액, 충전·소진 이력 | 쓰지 않음 |
| 도구 | `ncc-heroes-tool.json` | 14 | 노출 제한 IP, 서류, 분석 연동, 세금계산서 | 쓰지 않음 |
| 검수 이력 | `ncc-inspect-history.json` | 2 | 소재·키워드 검토(심사) 이력 | 심사 표현 카드 참고 |
| 계정 (통합) | `atower.json` | 4 | 광고 계정·관리 계정 목록, 구성원 | 쓰지 않음 |

호출 주소는 모두 `https://api.searchad.naver.com`입니다. 키는 광고 관리 화면의 도구 > API 관리자에서 받습니다.

## 1. 광고 관리 (NCC): 무엇을 무엇 아래에 만드나

```
광고 계정 (customerId)
├─ 비즈채널 (channels): 웹사이트·쇼핑몰·전화 등. 검토를 받아야 쓸 수 있음
├─ 공유 예산 (shared-budgets): 여러 캠페인·광고그룹이 함께 쓰는 하루 예산
├─ 캠페인 (campaigns): 유형·하루 예산·소진 방식·전환 추적·기간
│   └─ 광고그룹 (adgroups): 캠페인 ID + 비즈채널 ID 필요
│       ├─ 타깃 (targets / criterion): 요일·시간, 지역, 매체, PC/모바일, 나이, 성별
│       ├─ 제외 키워드 (restricted-keywords)
│       ├─ 키워드 (keywords): 광고그룹 ID 필요, 키워드별 입찰가
│       ├─ 소재 (ads): 단일형·반응형·쇼핑 상품형 …
│       └─ 확장소재 (ad-extensions): 캠페인·광고그룹·소재 어디에나 붙음
└─ 라벨 (labels): 즐겨찾기 묶음
```

### 캠페인 유형 (`campaignTp`)
| 값 | 화면 이름 (추정) | 메모 |
|---|---|---|
| WEB_SITE | 파워링크 (사이트검색광고) | 키워드 입찰 |
| SHOPPING | 쇼핑검색광고 | 스마트스토어 판매자에게 코치가 권하는 유형 |
| POWER_CONTENTS | 파워컨텐츠 | |
| BRAND_SEARCH | 브랜드검색 | 계약형 |
| PLACE | 플레이스 | 지역 가게 |

광고그룹 유형(`adgroupType`)은 더 잘게 나뉩니다: WEB_SITE, SHOPPING, INFORMATION, PRODUCT, BRAND_SEARCH, PLACE, CATALOG, BRAND_ZONE, SHOPPING_BRAND, LOCAL_AD, BRAND_NEW, DOOH.

### 항목과 범위 (광고 세팅값의 기준)
| 단계 | 항목 | 범위·기본값 |
|---|---|---|
| 캠페인 | 하루 예산 `dailyBudget` + 사용 여부 `useDailyBudget` | 기본 사용 안 함, 0 |
| 캠페인 | 소진 방식 `deliveryMethod` | 기본 ACCELERATED(빠른 소진), STANDARD(균등) |
| 캠페인 | 전환 추적 `trackingMode` | TRACKING_DISABLED / AUTO_TRACKING_MODE / PASS_THROUGH_SITE_MODE |
| 캠페인 | 기간 `usePeriod`, 시작·종료일 | 날짜는 한국 자정 기준 |
| 광고그룹 | 기본 입찰가 `bidAmt` | 70~100,000원, 비우면 70 |
| 광고그룹 | 하루 예산 | 70원부터 |
| 광고그룹 | PC·모바일 입찰 가중치 | 10~500% |
| 광고그룹 | **확장 검색 `useExpSearch`** | **기본 켜짐**, 확장 검색에 쓸 예산 비율 기본 100% |
| 광고그룹 | **ADVoost Max `aiAdsOptIn`** | **파워링크 + 확장 검색 광고그룹에서 기본 켜짐** |
| 광고그룹 | 소재 노출 방식 `adRollingType` | ROUND_ROBIN(번갈아) / PERFORMANCE(성과 순) |
| 광고그룹 | 자동 입찰 `systemBiddingType`, `autobidStrategy` | 자동 입찰 전략은 쇼핑검색 쇼핑몰 상품형만 |
| 타깃 | 일정 SD·지역 RL·반경 RP·기기 DV·나이 AG·성별 GN·오디언스 AD | 가중치 50~500%, 노출 제외 가능 |
| 키워드 | 입찰가 `bidAmt` 또는 그룹 입찰가 사용 | 70~100,000원 |
| 소재 | 유형 | TEXT_45(단일형), RSA_AD(반응형), SHOPPING_PRODUCT_AD(쇼핑 상품, 입찰 정보 필요) 외 13종 |
| 확장소재 | 유형 | 추가 제목·설명, 하위 링크, 가격 링크, 홍보 문구, 전화, 위치, 예약, 톡톡 등 36종. 이미지형·쇼핑 부가정보 등 일부는 API로 못 만듦 |

## 2. 키워드 도구 (`/keywordstool`)
- 넣는 것: 키워드(최대 5개), 또는 등록된 웹사이트, 업종, 시즌 월·테마
- 받는 것: 연관 키워드, 최근 30일 PC·모바일 검색수(10 미만은 "< 10" 글자), 최근 4주 평균 클릭 수·클릭률, 평균 노출 광고 수, 경쟁 정도
- 우리 앱: `src/engine/naver_source.py`가 씀. 카드 naver-api-001·002

## 3. 예상 실적·입찰가 (`/estimate`)
| 엔드포인트 | 하는 일 |
|---|---|
| `/estimate/performance/{type}` | 입찰가 목록 → 각 입찰가의 예상 노출·클릭·비용 (최대 100개) |
| `/estimate/performance-bulk` | 키워드 × 입찰가 묶음 (최대 200개) |
| `/estimate/average-position-bid/{type}` | 순위(1위, 2위…)에 필요한 평균 입찰가 |
| `/estimate/median-bid/{type}` | 입찰가 중앙값 |
| `/estimate/exposure-minimum-bid/{type}` | 노출되려면 최소 얼마 |
| `/npla-estimate/*` | 쇼핑검색(NPLA) 순위별·최소 노출 입찰가 |
| `/npc-estimate/*` | 파워컨텐츠(NPC) 입찰가·예상 실적 |

- `{type}`은 keyword(키워드 글자) 또는 id(등록된 키워드 ID)
- **쇼핑검색 입찰가도 `/npla-estimate`로 추정할 수 있습니다.** 지금 앱은 파워링크 예상 실적만 씁니다. 쇼핑검색을 기본으로 권하는 코치와 맞추려면 이 API를 볼 만합니다 (기획 후보).

## 4. 성과 통계 (`/api/stats`, `/api/stat-reports`)
- `/api/stats`: 캠페인·광고그룹·키워드 ID로 바로 조회. 기간·날짜 프리셋·일별 쪼개기를 지원하고, breakdown으로 PC/모바일·요일·시간대·지역별로 나눌 수 있음
- 받는 숫자: 노출 `impCnt`, 클릭 `clkCnt`, 클릭률 `ctr`, 클릭당 비용 `cpc`, 총비용 `salesAmt`(부가세 포함), 전환 `ccnt`, 직접 전환율 `drtCrto`, 구매 전환 수 `purchaseCcnt`, 구매 전환 매출 `purchaseConvAmt`, 구매 ROAS `purchaseRor`, 평균 노출 순위 `avgRnk`(파워링크만), 영상 조회 `viewCnt`
- `/api/stat-reports`: 하루치 대용량 리포트를 만들어 내려받음. 유형 13가지: AD, AD_DETAIL, AD_CONVERSION, AD_CONVERSION_DETAIL, ADEXTENSION, ADEXTENSION_CONVERSION, EXPKEYWORD(확장 검색 키워드), SHOPPINGKEYWORD_DETAIL, SHOPPINGKEYWORD_CONVERSION_DETAIL, SHOPPINGBRANDPRODUCT(+_CONVERSION), CRITERION(+_CONVERSION)
- **MVP 8(네이버 리포트 열 이름)과 연결:** 화면에서 내려받는 리포트 열은 이 항목들과 같은 뜻일 가능성이 큽니다. 화면 리포트 파일로 대조하기 전에는 ❓로 둡니다.

## 5. 나머지
- **마스터 리포트:** 계정 안 객체 30종의 목록을 파일로 받음. 캠페인, 키워드, 소재, 품질지수(Qi), 시즌 이벤트, 쇼핑 상품, 반응형 소재 등이 들어 있음
- **비즈머니:** 잔액, 충전·소진 이력
- **도구:** 노출 제한 IP(부정 클릭 대비), 서류 제출, 분석 도구 연동, 세금계산서 위임일
- **검수 이력:** 소재·키워드가 언제 어떤 이유로 승인·반려됐는지
- **계정(atower):** 광고 계정 번호(`adAccountNo`)와 관리 계정 목록

> 6~11장은 공지·릴리스 노트 227개(2016-05~2026-10), 위키 FAQ, 오류 코드표, 파이썬 샘플을 읽고 정리했습니다. 파일 이름은 공식 문서 사이트의 `_posts` 기준입니다.
---

## 6. 인증·호출 규칙

**기본 주소**
- 지금 주소: `https://api.searchad.naver.com` (2022-12-22 정식 시작, `2022-11-25-notice1.md`).
- 옛 주소 `api.naver.com`은 2023-03-22 오후 4시에 끝남. 잠깐 새 주소로 넘겨줬지만 예고 없이 끊긴다고 함 (`2023-03-22-notice1.md`).
- 2022년 타깃팅 개편 때 잠깐 Sandbox(`sandbox-api.searchad.naver.com`)를 열었다가 2022-04-25에 닫음. 지금은 테스트 서버가 없음 ❓ (`2022-04-01-notice1.md`).

**키 받기**
- 광고주센터 [도구 → API 사용 관리]에서 라이선스(API-KEY)와 비밀키(SECRET)를 받음 (`markdown-ko-KR.json`).
- 키를 다른 사람에게 넘기면 안 됨(약관 제5조). 대행사는 광고주 키를 받지 말고, 권한을 위임받은 자기 계정 키를 써야 함 (`FAQ.asciidoc`).
- 2026-07: 계정 통합 뒤 옛 Agent를 정리하다가 일부 비밀키가 바뀐 일이 있었음. "비밀키가 바뀌었다"는 응답이 오면 광고주센터에서 새 키를 확인하거나 다시 받아야 함 (`2026-07-02-notice.md`).

**요청마다 넣는 헤더 4개**

| 헤더 | 값 |
|---|---|
| `X-API-KEY` | 발급받은 라이선스 |
| `X-Customer` | 조회할 광고주의 **검색광고 고객 ID(CUSTOMER_ID)** |
| `X-Timestamp` | 지금 시각. 1970년부터 센 **밀리초**(문서에는 'unix timestamp'라고만 적혀 있지만 예시와 샘플은 13자리 밀리초) |
| `X-Signature` | 아래 방법으로 만든 서명 |

**서명 만드는 법** (`markdown-ko-KR.json`, `python-sample/examples/signaturehelper.py`)
1. 문자열을 만든다: `{timestamp}.{HTTP메서드}.{요청 경로}`. 예: `1457082455307.GET./ncc/campaigns`
2. 비밀키로 HMAC-SHA256을 계산한다.
3. 결과 바이트를 Base64로 바꾼다.
- 요청 경로에는 **물음표 뒤 쿼리를 넣지 않음**. 파이썬 샘플은 `uri='/ncc/campaigns'`로 서명하고 쿼리는 `params=`로 따로 보냄. 문서에 규칙으로 적혀 있지는 않고 샘플을 보고 판단함 ❓
- 시계가 어긋나면 `403 Forbidden`과 함께 `invalid-timestamp`("Request has expired")가 옴. 해결: 서버 시간을 NTP로 맞추고, 타임스탬프를 호출 바로 전에 만든다 (`FAQ.asciidoc`). 허용 오차가 몇 초인지는 문서에 없음 ❓
- 샘플 헤더에는 `Content-Type: application/json; charset=UTF-8`이 들어 있음. 2025-12-01부터 STAT-REPORT는 웹 표준 형식으로만 호출할 수 있음(Content-Type이 겹치지 않게) (`2025-10-30-notice1.md`).

**호출 제한과 재시도**
- 전체 호출 횟수에는 제한이 없음. 대신 **광고주(고객 ID)마다 속도 제한**이 있음. 정해진 숫자가 없고 1초보다 짧은 단위로 재며, 시스템이 바쁜 정도에 따라 실시간으로 바뀜 (`FAQ.asciidoc`).
- 속도를 넘으면 HTTP `429 Too Many Requests`(오류 코드 표에서는 429, 1016 '너무 많은 접속')가 옴. 잠시 쉬었다가 다시 부르면 됨.
- **키워드 도구(RelKwdStat, `/keywordstool`)는 따로 더 엄격함** (`2020-12-18-notice.md`):
  - 다른 기능보다 호출 속도가 약 1/5~1/6 수준.
  - 고객 ID뿐 아니라 **부르는 쪽 IP**도 함께 셈. IP당 속도는 다른 기능의 약 1/2.
  - 429가 오면 다른 기능보다 5~6배 길게 쉬고 다시 부를 것.
  - 몇 초 사이에 429가 계속 쌓이면 **5분 이상 모든 호출을 멈춘 뒤** 다시 시도할 것.
  - 여러 고객 ID를 한꺼번에 부를 때는 장비나 네트워크를 나눌 것.
- 정기 점검 중에는 `503`이 옴 (오류 코드 표).
- 대용량 보고서(STAT-REPORT) 작업이 `ERROR`나 `WAITING`에서 멈추면 다시 요청하면 된다고 안내함 (`2023-02-28-notice1.md`).

**고객 ID(CUSTOMER_ID)와 광고계정 ID(adAccountNo)의 차이** (`FAQ-검색광고-ID-(CUSTOMER_ID)-와-통합광고-ID-(adAccountNo).md`)
- 2025-09-01 네이버 광고 플랫폼이 통합되면서 새로 생긴 번호가 **adAccountNo(통합 광고계정 번호)**.
- 검색광고 Open API는 여전히 **CUSTOMER_ID로만** 동작함. adAccountNo를 넣으면 동작하지 않음.
- 통합 화면에서는 CUSTOMER_ID를 보여 주는 메뉴가 없음. 두 번호를 짝짓는 방법은 아래 API를 차례로 부르는 것뿐 (`FAQ-ManagedCustomerLink-Fade‐out.asciidoc`):
  1. `GET /ad-accounts`: 내가 구성원인 광고계정 목록
  2. `GET /manager-accounts`: 내가 구성원인 관리계정 목록
  3. `GET /manager-accounts/{managerAccountNo}/child-ad-accounts`: 관리계정 아래 광고계정 목록
  4. 1번과 3번을 합치면 접근할 수 있는 전체 계정이 됨. 권한이 겹치면 더 높은 권한이 적용됨(OWNER > MASTER > READ_ONLY).
- 옛 `GET /customer-links`(ManagedCustomerLink, `MYCLIENTS`/`MYMANAGER`)는 2025-09-15에 끝남. 파이썬 샘플에는 아직 이 호출이 남아 있음 (`2025-08-07-notice2.md`).
- 관리계정을 거쳐 접근할 수 있는 회원 목록은 지금은 조회할 수 없음.

---

## 7. 오류 코드 (대표만)

출처: `NaverSA_API_Error_Code_MAP.md`. 2026년에 새로 생긴 코드는 릴리즈 노트에서 가져옴.

| 묶음 | 코드 | 뜻 |
|---|---|---|
| **공통** | 1001 | 요청한 ID나 대상을 찾을 수 없음 |
| | 1002 / 1011 | 잘못된 요청 / 잘못된 데이터 |
| | 1007·1008·1010 | JSON 형식이 맞지 않음 |
| | 1014 | 최대 개수를 넘음 |
| | 1006 / 1018 | 권한 없음 / 접근 권한 없음 |
| **호출 제한·점검** | **429** | 요청이 너무 많음(속도 제한) |
| | **1016** | 접속을 너무 많이 시도함 |
| | 503 | 정기 점검 중 |
| | 403 invalid-timestamp | 타임스탬프가 너무 오래됨(FAQ) |
| **입찰가** | **2102** | 입찰가 값이 잘못됨 |
| | **3703** | 광고그룹 입찰가가 잘못됨 |
| | 3708 | 콘텐츠 매체 입찰가가 잘못됨 |
| | 3717 | 매체 입찰가 가중치가 잘못됨 |
| | **3904** | 키워드 입찰가가 잘못됨 |
| | 3916 | 기본 입찰가 사용 여부나 입찰가 값이 없거나 잘못됨 |
| **예산** | **3505** | 캠페인 하루 예산 값이 잘못됨 |
| | **3704 / 3720** | 광고그룹 하루 예산 값, 또는 예산 사용 여부가 잘못됨 |
| | 3724 | 광고그룹에 예산 정보가 없음 |
| **검수(심사)** | 3103 | 제한 상태인 광고는 수정할 수 없음 |
| | 3402 / 3823 / 3914 | 노출제한 상태일 때만 재검수를 요청할 수 있음 |
| | 3903 | 반려된 키워드는 수정할 수 없음 |
| | 3909 | 광고 노출이 금지된 키워드 |
| | 4012 / 4013 | 확장소재 재검토 요청이 불가한 유형이거나 메시지가 잘못됨 |
| | 4703 | 검수를 통과한 소재나 키워드가 없음 |
| **키워드** | 3905·3907·3908 | 키워드 중복 |
| | 3906 / 3913 | 허용하지 않는 특수문자 / 길이 초과 |
| | 3910·3911·3912 | 캠페인·그룹·계정당 키워드 수 초과 |
| | 3923 | 이 캠페인 유형에서는 키워드를 만들 수 없음 |
| **광고그룹·캠페인** | 3501 / 3701 | 캠페인 / 광고그룹이 없음 |
| | 3710 / 3506 | 같은 이름이 이미 있음 |
| | 3714 / 3715 | 캠페인당·계정당 광고그룹 수 초과 |
| | 3709, 3721~3723, 3728 | 키워드 플러스(키워드 확장) 관련. 2024-08 기능 종료로 사실상 쓰이지 않음 ❓ |
| **확장소재** | 4001~4014 | 없음, ID 오류, 유형 오류, 기간 설정 오류 등 |
| **타깃팅** | 4401~4406 | 타깃 ID, 데이터, 유형 오류 |
| **키워드 도구** | **7001** | 넣을 수 있는 키워드 수 초과 |
| | **7002** | 입력 키워드에 중복이 있음 |
| | **7003** | 키워드에 쓸 수 없는 문자가 있음 |
| **보고서(공지에만 나옴)** | 11003 | `/stats`에 서로 다른 캠페인 유형의 ID를 섞어 보냄 (`2017-10-17-notice.md`) |
| | 10004 | 보고서 제공 기간 밖의 날짜로 요청함(2022-10 전까지는 11001) (`2022-09-28-notice1.md`) |
| **ADVoost 플레이스(2026-09 신규)** | 3752 / 3753 | 스마트플레이스에 업체 이미지가 없음 / 업체 정보를 불러오지 못함 |
| | 3754·4422 / 3755 | 애드부스트 ON 그룹에서는 제외 검색어 등록 불가 / 고급 옵션(입찰가, 가중치, 확장 검색 등) 변경 불가 |
| | 3756 | 병의원 업종은 ADVoost 플레이스를 쓸 수 없음 |
| | 3837~3840 | 연동형 소재는 삭제, ON/OFF 변경, 직접 등록이 불가하고, 애드부스트 ON 그룹에는 소재를 추가할 수 없음 |
| | 4029 / 4420 / 4421 / 5117 | 애드부스트 ON 그룹에서는 확장소재 추가, 매체 변경, 태그 설정, 요일·시간 외 타깃팅 변경이 불가 |
| | 3749 | 광고그룹 속성 중 바꿀 수 없는 필드를 수정하려 함 |

- 2026-06-10부터 캠페인과 확장소재의 기간 필드(`periodStartDt`, `periodEndDt`)는 **한국 자정을 UTC로 쓴 값**(예: `...T15:00:00.000Z`)만 받음. 시·분·초가 있으면 `400`이 옴 (`2026-06-10-notice.md`).
- 오류 코드 표(md)에는 2026년 신규 코드가 아직 없음. 표가 최신이 아님 ❓

---

## 8. FAQ 핵심

**요일·시간 타깃(옛 방식 비트값)** (`FAQ.asciidoc`)
- 요일마다 24개 비트를 씀. 0~1시가 0번 비트, 23~24시가 23번 비트.
- 원하는 시간의 2^시 값을 모두 더함. 범위는 0(없음)~16777215(하루 종일). 예: 0시·1시는 1+2=3, 22시·23시는 12582912.
- **2022-04-26부터 광고그룹의 요일·시간, 지역, 성별, 연령 타깃은 Criterion API로 바뀜** (`2022-04-26-release-note.md`). 요일·시간 코드 규칙은 `SD`+요일 3자+시작 시 2자리+끝 시 2자리(예: `SDWED0009`). 입찰 가중치는 50~500%.
- **조심할 점**: `PUT /ncc/criterion/{그룹ID}/{type}` 요청 본문에 넣지 않은 코드는 모두 '사용 안 함'으로 바뀜. 비트값 방식은 지금 브랜드검색 소재 타깃에만 남아 있는 것으로 보임 ❓

**지역 코드** (`FAQ.asciidoc`, `REGN_NO`)
- 9 서울, 2 경기, 11 인천, 8 부산, 6 대구, 5 광주, 7 대전, 10 울산, 17 세종, 1 강원, 3 경남, 4 경북, 12 전남, 13 전북특별자치도, 15 충남, 16 충북, 14 제주, 99 국내(상세 위치 확인 불가), 0 해외, -1 알 수 없음.
- **18 '전남광주통합특별시'**가 새로 들어 있음. 언제 생겼는지 공지가 없음 ❓
- Criterion 지역 코드는 `RL`+법정동 코드(2~8자리), 반경은 `RP`+순번(9자리). 반경은 사전(dictionary)으로 조회할 수 없음.
- 쇼핑검색 그룹에도 2023-10-18부터 지역 타깃이 생겼지만 **제외만** 할 수 있고 가중치는 100으로 고정 (`2023-10-18-release-note.md`).

**확장소재를 API로 만들 수 없는 유형**
- API로 **등록 불가**:
  - `SHOPPING_BRAND_VIDEO`, `SHOPPING_BRAND_IMAGE`, `SHOPPING_BRAND_BROADCAST` (`2021-03-17`)
  - `PLACE_SMART_ORDER` (`2021-06-21`)
  - `SHOPPING_BRAND_EVENT` (`2021-10-27`)
- **등록 기능 종료**: `PRICE_LINKS`(가격링크), 2025-02-05 (`2025-02-05-release-note.md`).
- ADVoost 플레이스가 켜진 광고그룹에는 어떤 확장소재도 추가할 수 없음(4029).
- 반대로 최근 **API로 등록할 수 있게 된 유형**:
  - `POWER_LINK_IMAGE`, `IMAGE_SUB_LINKS`: Base64 이미지, JPEG·PNG, 5MB 이하, 214x214 고정. 이미지 서브링크는 최대 3개 (`2025-06-25`)
  - `WEBSITE_INFO` (`2025-05-14`)
  - `TALKTALK_CONSULTATION` (`2026-06-04`)
- FAQ 표에 있는 `PLACE_BEAUTY_STYLE`, `SHOPPING_BRAND_DAY`, `SHOPPING_WEB`, `DESCRIPTION_EXTRA`는 API로 등록할 수 있는지 공지가 없음 ❓
- 소재도 API로 만들 수 없는 유형이 많음: 쇼핑 브랜드형 3종, `LOCAL_AD`, `BRAND_SEARCH_NEW_AD`, `MEDICAL_AD`, `ADVOOST_PLACE_AD`(시스템이 자동으로 만듦). 상품그룹과 `SHOPPING_BRAND` 비즈채널도 만들 수 없음.

**통계(`/stats`) 조회 규칙** (`FAQ-stat.asciidoc` + 공지)
- 지표 이름:
  - 기본: `impCnt` 노출, `clkCnt` 클릭, `ctr`, `cpc`, `salesAmt` 총비용
  - 전환: `ccnt` 전환수, `crto` 전환율, `convAmt` 전환매출, `ror` ROAS, `cpConv` 전환당비용
  - 순위: `avgRnk` 평균 노출 순위, `pcNxAvgRnk`, `mblNxAvgRnk`
  - 기타: `viewCnt` 동영상 조회, `actCnt` 반응
  - 2025-10 추가: `pcNxAvgCpc`, `mblNxAvgCpc`
  - 2026 추가: `purchaseCcnt`, `purchaseConvAmt`, `purchaseRor`
- `timeRange`: breakdown(세부 나눔)이 없으면 최근 **2년** 안에서 한 번에 **92일**까지. breakdown이 있으면 파워링크·쇼핑·파워콘텐츠는 7일, 브랜드검색·플레이스는 120일(한 번에 90일).
- `ids`에 여러 ID를 넣을 때는 **모두 같은 캠페인 유형**이어야 함(아니면 11003).
- Criterion ID(`그룹ID~코드`)로도 조회할 수 있음. 단 `recentAvgRnk`·`recentAvgCpc`·`pcNxAvgRnk`·`mblNxAvgRnk`는 쓸 수 없고, breakdown은 `pcMblTp`·`dayw`만 됨.
- breakdown에서 `genderNm`·`ageRangeNm`·`regnR3Nm`은 2024-11-07에 없어짐.
- 2025-10-27부터 지연이 3시간에서 **2시간**으로 줄었고 `cycleBaseTm`은 분 단위로 갱신됨. `recentAvgRnk`·`recentAvgCpc`는 항상 0이 나옴.
- `statType`: `NPLA_SCH_KEYWORD`(쇼핑검색 검색어별, 최근 30일, 노출 순으로 최대 1000개), `BRND_CONTRACT`.
- **STAT-REPORT(대용량 보고서)** 보관 기간:
  - AD, AD_CONVERSION, ADEXTENSION, EXPKEYWORD, CRITERION 등: 365일
  - AD_DETAIL, SHOPPINGKEYWORD_DETAIL: 180일
  - AD_CONVERSION_DETAIL, SHOPPINGKEYWORD_CONVERSION_DETAIL: 45일
  - 만들어 둔 파일은 **14일** 뒤 지워짐(2025-10 전에는 40일).
  - 지표가 바뀌면 상태가 `changed`로 바뀌고 그 파일은 받을 수 없음. 성과는 최대 48시간 안에 고쳐질 수 있음.
- 같은 FAQ에 `NAVERPAY_CONVERSION`을 365일로 적어 두었지만, 이 보고서는 2025-05-09에 끝남. FAQ가 최신이 아님 ❓
- 키워드의 1년 검색량 추이는 API로 주지 않음. 네이버 데이터랩 API(상대값)를 쓰라고 안내함.

**기타 FAQ**
- 공유예산은 캠페인용·그룹용 각 20개까지 만들 수 있고, 예산 하나에 대상 200개까지 묶을 수 있음.
- 상태(`status`)는 위 단계 상태까지 계산한 값임. 그룹 상태에는 비즈머니, 캠페인, 채널, 예산이 모두 반영됨. 상태 이유 코드 예: `CAMPAIGN_LIMITED_BY_BUDGET`, `GROUP_LIMITED_BY_BUDGET`, `LACK_OF_ACCOUNT_BALANCE`.

---

## 9. 변경 이력 (중요한 것만)

### 2016
- 05-02: `/estimate/first-page-bid` 경로가 `/estimate/exposure-minimum-bid`로 바뀜. median과 exposure-minimum에 `period`(DAY는 어제 기준, MONTH는 최근 28일)가 필수가 됨 (`2016-05-02-release-note.md`)
- 05-09: 캠페인, 그룹, 키워드 목록에 페이지 나눔(`baseSearchId`, `recordSize`)이 생김 (`2016-05-09`)
- 05-23: 0/1 정수 필드가 boolean으로 바뀜(`userLock`, `useDailyBudget` 등) (`2016-05-23`)
- 06-13: STAT-REPORT `AD_COST`가 없어지고 Bizmoney `getCost`로 대체됨 (`2016-06-13`)
- 07-11: `/estimate/performance-bulk` 신규, 한 번에 최대 200개 (`2016-07-11`)
- 10-17: `/stats`에 `statType=NPLA_SCH_KEYWORD` 추가. Target 조회·수정 API 신규 (`2016-10-17`)

### 2017
- 01-12 / 02-02: 쇼핑(`/npla-estimate/...`)과 파워콘텐츠(`/npc-estimate/...`) 예상 입찰가 API (`2017-01-12`, `2017-02-02`)
- 02-01: `POWER_CONTENTS` 캠페인과 `CONTENTS` 채널 신규. 키워드 플러스 제외 키워드 API (`2017-02-01`)
- 03-09: 보고서를 zip으로 받는 헤더 `X-Accept-Encoding: zip` (`2017-03-09`)
- 03-21: 확장소재 기간 설정 필드. `HEADLINE`, `DESCRIPTION`, `SUB_LINKS`, `PRICE_LINKS` 신규 (`2017-03-21`)
- 05-24: 확장소재 ID로 `/stats` 조회 가능 (`2017-05-24`)
- 06-21: 보고서 파일을 30일 뒤 자동 삭제 (`2017-06-21`)
- 09-11: EXPKEYWORD에서 콘텐츠 매체의 문맥 매칭이 빠짐 (`2017-09-11-notice.md`)
- 11-08: `/stats`의 ids에 같은 캠페인 유형만 넣도록 제한(11003) (`2017-11-08`)
- 12-14: `POWER_LINK_IMAGE`, `IMAGE_SUB_LINKS` 확장소재 신규 (`2017-12-14`)

### 2018
- 01-31: `/npc-estimate/performance` (`2018-01-31`)
- 02-21: 쇼핑 검색어 상세 보고서와 전환 상세 보고서 (`2018-02-21`)
- 07-18: `adRollingType`(PERFORMANCE / ROUND_ROBIN) (`2018-07-18`)
- 07-31: `PLACE` 캠페인과 `PLACE_AD` 소재 (`2018-07-31`)
- 09-19: 쇼핑 `CATALOG` 그룹, 소재, 확장소재 (`2018-09-19`)
- 10-31: Bizmoney charge, exhaust, period 조회 (`2018-10-31`)

### 2019
- 02-26: 옛 IP 서비스 종료. 도메인으로 부르라고 안내 (`2019-02-26-notice.md`)
- 02-27: `AD_TAG` 타깃(카탈로그 소재용) (`2019-02-27`)
- 04-03: 파워링크 자동입찰 `systemBiddingType=ML`. 하루 예산이 필수이고 입찰가를 넣으면 오류 (`2019-04-03`)
- 04-17: 쇼핑 그룹 콘텐츠 매체 입찰가와 가중치 (`2019-04-17`)
- 05-15 / 09-04: `NAVER_TV_VIDEO`, `NAVER_BLOG_REVIEW` 확장소재와 `enable` 필드 (`2019-05-15`, `2019-09-04`)
- 05-30: `viewCnt`, `actCnt` 지표, 보고서 View count 열 (`2019-05-30`)
- 12-18: 쇼핑 자동입찰 `MAXCONV` (`2019-12-18`)

### 2020
- 09-10 / 12-18: 키워드 도구에서 429가 늘어남. 속도 1/5~1/6, IP 기준 제한 가이드 (`2020-09-10-notice.md`, `2020-12-18-notice.md`)

### 2021
- 03-17: **쇼핑검색 브랜드형** 신규. `SHOPPING_BRAND` 그룹(입찰가 최소 300원), 키워드 `shopping_brand_keyword_type`, 상품그룹 조회 API, `/stats`에 성별·연령 breakdown과 `topImpRto` (`2021-03-17-release-note.md`, `2021-03-10-notice1.md`)
- 03-31: STAT-REPORT `SHOPPINGBRANDPRODUCT`(+전환) (`2021-03-09-notice1.md`)
- 06-21: 플레이스 검색 `LOCAL_AD` 그룹과 소재. 소재는 API 등록 불가 (`2021-06-21`)
- 09-15: 쇼핑 브랜드형 상단노출 최소 입찰가 `/estimate/shopping-brand/type/pc_mins`, `mobile_mins`, 최대 200개 (`2021-09-15-release-note.md`)
- 10-27: 쇼핑 브랜드형 이미지 썸네일형과 배너형 소재 (`2021-10-27`)

### 2022
- 04-26(실제 적용 04-27): **타깃팅 관리 방식 개편**. 요일·시간, 지역, 성별, 연령이 `/ncc/criterion`으로 옮겨 감. 광고그룹 조회 결과에서 이 타깃이 빠짐 (`2022-04-26-release-note.md`)
- 04-26: Criterion 마스터, `/stats`에 Criterion ID (`2022-04-14-notice1.md`, `2022-04-19-notice1.md`)
- 04-28: 네이버페이 전환 보고서에 검색어 열(9번)이 추가되고 열 순서가 바뀜 (`2022-03-31-notice1.md`)
- 06-03: 쇼핑 검색어 보고서에 검색어를 주는 매체가 9개로 늘어남 (`2022-06-03-notice1.md`)
- 07-21: STAT-REPORT `CRITERION`, `CRITERION_CONVERSION` (`2022-07-21-notice1.md`)
- 09-20 → 12-22: 새 도메인 `api.searchad.naver.com` (`2022-09-20-notice1.md`, `2022-11-25-notice1.md`)
- 10-26: 기간 밖으로 보고서를 요청하면 오는 오류가 11001에서 10004로 바뀜 (`2022-09-28-notice1.md`)
- 12-12: 매체 이름 변경. '함께 찾은 파워링크'가 '파워링크 스마트블록'이 됨(ID 447344·447349) (`2022-12-14-notice1.md`)

### 2023 (자세히)
- 02-01: 신제품검색 `BRAND_NEW` 그룹과 `BRAND_SEARCH_NEW_AD` 소재. 둘 다 API로 등록 불가 (`2023-02-01-release-note.md`)
- 03-22: **`api.naver.com` 완전 종료** (`2023-03-22-notice1.md`)
- 04-26: **공유예산** 신규
  - `/ncc/shared-budgets` CRUD
  - 캠페인·그룹에 `sharedBudgetId` 등 필드
  - 캠페인·그룹 마스터에 shared_budget_id 열, SharedBudget 마스터 신규
  - 브랜드검색과 플레이스는 지원하지 않음
  - (`2023-04-26-release-note.md`, `2023-04-26-notice1.md`)
- 06-28: 파워링크 그룹에 `useCloseVariant`(유사검색어) 추가. 기본값 true (`2023-06-28-release-note.md`)
- 06-29: 그룹 마스터 20번 열에 Using CloseVariant (`2023-06-29-notice1.md`)
- 07-10: EXPKEYWORD 변경 (`2023-07-03-notice1.md`)
  - 8번 **Search Keyword Type** 열 추가(1 확장, 2 유사)
  - 중복 행 제거
  - 이름이 '키워드 플러스 성과 보고서'에서 '**파워링크 검색어 보고서**'로 바뀜
- 07-09: 마스터와 STAT-REPORT 이름 일괄 변경. 코드는 그대로 (`2023-07-09-notice1.md`)
- 08-14: EXPKEYWORD에 확장 검색(스마트블록) 지표 추가. 타입 1이 '확장(Extend)'으로 바뀜 (`2023-08-10-notice1.md`)
- 08-23: **이용자 세그먼트(잠재고객) 타깃(Beta)**, Criterion 유형 `AD` (`2023-08-23-release-note.md`, `2023-08-18-notice1.md`)
- 09-13: ManagedKeyword의 `PCPLMaxDepth` 필드 삭제 (`2023-08-14-notice1.md`)
- 10-18: 쇼핑검색 그룹에 지역 타깃 추가(제외만 가능) (`2023-10-18-release-note.md`)
- 11-13: EXPKEYWORD Search Keyword Type에 0(일치) 추가. 검색어 보고서에 주는 매체를 광고 시스템 다차원 보고서 기준으로 맞춤 (`2023-10-13-notice2.md`, `2023-11-13-notice1.md`)

### 2024 (자세히)
- 01-25: 캠페인 삭제 API. 아래 요소까지 한꺼번에 지우고 복구할 수 없음. `DELETE /ncc/campaigns/{id}`, `?ids=` (`2024-01-25-release-note.md`)
- 02-07: 웹사이트 비즈채널에 `siteName` 필수. 1~10자, 한글·영문·숫자만 (`2024-02-07-release-note.md`)
- 03-20: **반응형 소재 `RSA_AD`**와 `assets`. Asset, AdAssetLink, RsaAd 마스터 신규 (`2024-03-20-release-note.md`, `2024-03-13-notice1.md`)
- 05-22: 마스터와 보고서 이름 다시 변경. 예: Ad 마스터는 'Powerlink Single Ad master', CRITERION은 'Criterion Performance Report' (`2024-05-21-notice1.md`)
- 07-03: **전환 유형(Conversion Type)이 숫자에서 문자열로 바뀜** (`2024-05-30-notice1.md`)
  - 1이 `purchase`, 2가 `sign_up`, 3이 `add_to_cart`, 4가 `lead`, 5가 `custom001`
  - 새로 생긴 값: `custom002~010`, `add_to_wishlist`, `subscribe`, `schedule`, `view_content`
  - 대상 보고서: 전환 보고서 5종
- 08-16 / 08-19: **키워드 확장(Beta, keywordplus) 종료** (`2024-07-16-notice1.md`, `2024-08-19-release-note.md`, `2024-08-19-notice1.md`)
  - 광고그룹에서 `useKeywordPlus`, `keywordPlusWeight`, `useCloseVariant`가 빠짐
  - **`/estimate/performance`와 `performance-bulk` 요청의 `keywordplus` 필드가 빠짐**
  - 이 필드를 계속 보내도 오류는 나지 않고 무시됨
  - 그룹 마스터의 11, 12, 20번 열이 빈 문자열로 나옴
- 08-26 → 12-01: 쇼핑 상품 마스터와 카탈로그 마스터의 PC/모바일 가격이 하나로 합쳐짐. 20번 열(Mobile)은 12-01에 삭제 (`2024-08-26-notice1.md`)
- 10-02: **파워링크 확장 검색** (`2024-09-13-release-note.md`, `2024-07-22-notice1.md`)
  - 그룹에 `useExpSearch`, `expSearchBudgetRatio`, `sharedExpSearchBudgetRatio` 추가
  - '노출제한 키워드'가 '제외 검색어'로 바뀜. type은 `EXP_SEARCH`와 `KEYWORD_PLUS_RESTRICT`(스마트블록·유사검색어)
  - 그룹 예산 마스터와 공유예산 마스터에 Expanded Search Budget Ratio 열 추가
- 10-10: EXPKEYWORD Search Keyword Type에 5(일치) 추가 (`2024-08-27-notice1.md`)
- 11-07: `/stats` breakdown에서 `genderNm`, `ageRangeNm`, `regnR3Nm` 삭제 (`2024-11-07-release-note.md`, `2024-10-31-notice1.md`)
- 11-13: 플레이스 검색 그룹도 매체 타깃(검색·콘텐츠, 네이버·파트너)을 고를 수 있음 (`2024-11-13-release-note.md`)
- 11-20: 쇼핑검색 캠페인에 `trackingUrlCustomParams`(최대 5쌍) (`2024-11-20-release-note.md`)

### 2025 (자세히)
- 02-05: `PRICE_LINKS` 확장소재 등록 종료 (`2025-02-05-release-note.md`)
- 04-09 → 05-09: **네이버페이 전환 보고서(`NAVERPAY_CONVERSION`) 종료**. 4/9부터 갱신이 멈췄고, 5/9부터는 과거 데이터도 볼 수 없음 (`2025-04-02-notice1.md`)
- 05-13: 비즈사이트 영역 노출이 끝남. **`/estimate/average-position-bid` PC 순위 범위가 1~15에서 1~10으로 줄어듦**. 11~15를 넣으면 400 (`2025-05-13-notice1.md`)
- 05-14: `WEBSITE_INFO` 확장소재를 API로 등록할 수 있게 됨(`agree:true`). `MEDICAL_AD`(병의원) 소재 유형 추가, API 등록은 불가 (`2025-05-14-release-note.md`)
- 06-25: `POWER_LINK_IMAGE`와 `IMAGE_SUB_LINKS`를 Base64 이미지로 API 등록 (`2025-06-25-release-note.md`)
- 07-01: 검색어 보고서 3종(EXPKEYWORD, SHOPPINGKEYWORD_DETAIL, SHOPPINGKEYWORD_CONVERSION_DETAIL)의 집계 기준이 검색 매체로 바뀜 (`2025-06-02-notice1.md`)
  - 검색어가 없을 때 쓰던 '-' 행이 없어짐
  - EXPKEYWORD 타입이 0(일치), 1(확장), 2(유사)로 정리됨
- 08-06: **Bizmoney `get(cost)` 종료**. get, charge, period, exhaust는 계속 제공 (`2025-06-26-notice.md`)
- 08-13 → 09-10: 쇼핑 자동입찰 `MAXCONV` 종료. 남아 있던 `MAXCONV`는 9/10에 `NONE`으로 바뀜 (`2025-07-30-notice1.md`)
- 08-20: 파워링크 병의원 소재 마스터 `HospitalAd` (`2025-08-12-notice1.md`)
- 09-01: **광고계정 통합** (`2025-08-12-release-note1.md`, `2025-08-07-notice1.md`, `2025-08-07-notice2.md`)
  - `/ad-accounts`, `/ad-accounts/{no}/members`, `/manager-accounts`, `/manager-accounts/{no}/child-ad-accounts` 신규
  - Account 마스터 종료(9/15)
  - ManagedCustomerLink 종료(9/15)
- 10-01: 브랜드검색 계약(TimeContract)과 신제품검색 계약(BrandNewContract) 조회 API (`2025-10-01-release-note1.md`)
- 10-15: 쇼핑 **전환목표 자동입찰(Beta)** 시작. 쇼핑몰 상품형 그룹에 `autobidStrategy` (`2025-10-15-release-note.md`)
  - `autobidBidGoal`: `NONE` 또는 `MAX_CONV_VALUE`
  - 나머지 값(CPC, NO_CAP, 0)은 고정
- 10-19 / 10-27: 보고서 다운로드 URL에 `fileVersion` 파라미터가 붙음 (`2025-10-20-notice1.md`)
- 10-27: **지표 실시간화** (`2025-09-26-notice2.md`, `2025-09-26-notice1.md`)
  - STAT-REPORT의 과거 파일이 모두 지워지고 보관 기간이 14일로 줄어듦
  - 지표가 바뀌면 `changed` 상태가 됨
  - `/stats` 지연이 2시간으로 줄어듦
  - `recentAvgRnk`와 `recentAvgCpc`는 0이 나옴
  - `pcNxAvgCpc`, `mblNxAvgCpc` 신규
  - 쇼핑 브랜드형 상품 보고서와 확장소재 보고서는 집계 기준이 바뀌면서 과거 데이터도 다시 계산됨
- 11-26: 에누리 매체 ID가 바뀜(45714를 791888로, 36379를 791889로). 클릭은 최대 20일까지 옛 ID로 잡힐 수 있음 (`2025-11-28-notice1.md`)
- 12-01: STAT-REPORT 호출 시 Content-Type 헤더 중복을 허용하지 않음 (`2025-10-30-notice1.md`)
- 12-03: **검수 이력 조회 API** (`2025-12-03-release-note.md`)
  - `GET /ncc/inspect-history/{id}`, `POST /ncc/inspect-history`(최대 100건)
  - 최근 3개월, 비즈채널·소재·확장소재·키워드·애셋
- 12-11: 파워링크 키워드에 `adRelevanceScore`(광고 연관 지수)와 `expectedClickScore`(클릭 기대 지수) 추가 (`2025-12-11-release-note.md`)

### 2026 (자세히)
- 03-30: **STAT-REPORT의 모든 COST 열이 double에서 long(정수)으로 바뀌고 VAT가 포함됨**. 과거 날짜는 예전 값 그대로라 광고주센터 숫자와 다를 수 있음. 대상: AD, AD_DETAIL, ADEXTENSION, EXPKEYWORD, CRITERION (`2026-02-11-notice1.md`)
- 03-30: `/stats`에 `purchaseCcnt`, `purchaseConvAmt`(구매완료) 추가. 최근 2년 데이터까지 소급 (`2026-03-20-notice1.md`)
- 05-13: `/stats`에 `purchaseRor`(구매완료 ROAS) 추가 (`2026-05-08-notice1.md`)
- 06-04: `TALKTALK_CONSULTATION` 확장소재 API 등록. 필수 필드는 talkAccountId, url, description (`2026-06-04-release-note.md`)
- 06-10: 캠페인과 확장소재 기간 필드 검증 강화. 한국 자정을 UTC로 쓴 값만 받음 (`2026-06-10-notice.md`)
- 07-15: **ADVoost Max `aiAdsOptIn`**이 광고그룹에 추가됨 (`2026-07-15-release-note.md`)
  - **파워링크 + 확장 검색을 쓰는 그룹만** 설정할 수 있음
  - **값을 안 넣으면 true(켜짐)**
- 07-16: 그룹 마스터 19번 열에 `Using Ai Ads` 추가(네이버 AI 광고) (`2026-06-16-notice1.md`)
- 07-29: **파워링크 품질지수 종료**. Qi 마스터 5번 열과 `nccQi`가 고정값 4로 나옴. 이유는 애드부스트 기술이 모든 검색어에 적용됐기 때문 (`2026-06-30-notice1.md`)
- 09-16: **ADVoost 플레이스** (`2026-09-16-release-note.md`)
  - `LOCAL_AD` 그룹의 `adgroupAttrJson.useAdvoost` 추가. 기본값 false
  - 켜면 연동형 소재 `ADVOOST_PLACE_AD`(type 17)가 자동으로 하나 생김
  - 켜져 있는 동안 소재·확장소재 추가, 제외 검색어, 매체·타깃·입찰 변경이 막힘
  - 신규 오류 코드 15개
- 09-30: 쇼핑 브랜드형 `topImpRto`가 0으로 고정됨 (`2026-08-27-notice1.md`)
- **11-16(예정)**: ADEXTENSION과 ADEXTENSION_CONVERSION 보고서에서 8번 'AD extension Business Channel ID' 열이 **삭제되고 뒤 열이 한 칸씩 당겨짐**(열 15개가 14개로, 14개가 13개로) (`2026-08-14-notice1.md`)
- **11-25(예정)**: 쇼핑몰 상품형과 제품 카탈로그형 품질지수가 고정값 4로 바뀜. 새 지표 '클릭기대지수'로 전환 (`2026-10-29-notice1.md`)

---

## 10. 2026-11 기준: 없어진 것과 새로 생긴 것

### 없어졌거나 곧 없어지는 것
| 대상 | 상태 | 출처 |
|---|---|---|
| `api.naver.com` 도메인 | 2023-03-22 종료 | `2023-03-22-notice1.md` |
| 키워드 확장(keywordplus): `useKeywordPlus`, `keywordPlusWeight`, `useCloseVariant`, **estimate의 `keywordplus` 필드** | 2024-08 삭제 | `2024-07-16-notice1.md` |
| `/stats` breakdown `genderNm`, `ageRangeNm`, `regnR3Nm` | 2024-11-07 삭제 | `2024-11-07-release-note.md` |
| 광고그룹의 지역·요일·성별·연령 필드(옛 Target) | 2022-04 Criterion으로 이전 | `2022-04-26-release-note.md` |
| 쇼핑·카탈로그 마스터의 Price(Mobile) 열 | 2024-12-01 삭제 | `2024-08-26-notice1.md` |
| `PRICE_LINKS` 확장소재 등록 | 2025-02-05 종료 | `2025-02-05-release-note.md` |
| `NAVERPAY_CONVERSION` 보고서 | 2025-05-09 완전 종료 | `2025-04-02-notice1.md` |
| average-position-bid PC 순위 11~15 | 2025-05-13부터 400 | `2025-05-13-notice1.md` |
| Bizmoney `get(cost)` | 2025-08-06 종료 | `2025-06-26-notice.md` |
| 쇼핑 자동입찰 `MAXCONV` | 2025-09-10 NONE으로 변환 | `2025-07-30-notice1.md` |
| ManagedCustomerLink `/customer-links`, Account 마스터 | 2025-09-15 종료 | `2025-08-07-notice1.md`, `2025-08-07-notice2.md` |
| `recentAvgRnk`, `recentAvgCpc` | 2025-10-27부터 항상 0 | `2025-09-26-notice2.md` |
| STAT-REPORT 파일 40일 보관 | 14일로 줄어듦 | `2025-09-26-notice2.md` |
| 파워링크 품질지수(Qi 마스터 5번, `nccQi`) | 2026-07-29부터 4로 고정 | `2026-06-30-notice1.md` |
| 쇼핑 브랜드형 `topImpRto` | 2026-09-30부터 0으로 고정 | `2026-08-27-notice1.md` |
| **ADEXTENSION(_CONVERSION) 8번 열** | **2026-11-16 삭제(일주일 뒤)** | `2026-08-14-notice1.md` |
| **쇼핑몰 상품형·카탈로그형 품질지수** | **2026-11-25부터 4로 고정** | `2026-10-29-notice1.md` |
| ManagedKeyword `PCPLMaxDepth`, `isBrand` | 삭제(2023, 2019) | `2023-08-14-notice1.md`, `2019-01-02` |

### 최근 새로 생긴 것 (2025~2026)
- 광고계정·관리계정 API(`/ad-accounts`, `/manager-accounts`). adAccountNo와 CUSTOMER_ID를 짝지을 때 씀 (2025-09)
- 쇼핑 전환목표 자동입찰 `autobidStrategy` (`MAX_CONV_VALUE`) (2025-10-15)
- 브랜드검색과 신제품검색 계약 조회 API (2025-10-01)
- `/stats`: `pcNxAvgCpc`, `mblNxAvgCpc` (2025-10), `purchaseCcnt`, `purchaseConvAmt` (2026-03), `purchaseRor` (2026-05)
- 검수 이력 조회 `/ncc/inspect-history` (2025-12-03)
- 키워드 `adRelevanceScore`, `expectedClickScore` (2025-12-11)
- 확장소재 API 등록 확대: `WEBSITE_INFO`, `POWER_LINK_IMAGE`, `IMAGE_SUB_LINKS`(Base64), `TALKTALK_CONSULTATION`
- 소재 유형 `MEDICAL_AD`, `HospitalAd` 마스터 (2025-05, 08)
- **ADVoost Max `aiAdsOptIn`**(기본 켜짐, 2026-07-15), 그룹 마스터 `Using Ai Ads` 열
- **ADVoost 플레이스 `useAdvoost`**와 `ADVOOST_PLACE_AD`(2026-09-16), 신규 오류 코드
- 지역 코드 18 '전남광주통합특별시'(FAQ, 시점 ❓)

---

## 11. 광고 예산 코치 앱에 영향 있는 것

1. **`/keywordstool`은 호출 제한이 가장 빡빡함**: 다른 기능의 약 1/5, IP까지 셈. 429가 오면 오래 쉬고, 연속으로 나면 5분 이상 멈출 것. 캐시(지금 `data/interim/naver_cache/`)를 꼭 유지하고, 여러 키워드는 묶어서 적게 부를 것. 키워드 수 초과는 7001, 중복은 7002, 금지 문자는 7003 (`2020-12-18-notice.md`).
2. **`/estimate/performance(-bulk)`에 `keywordplus` 필드를 넣지 말 것**: 2024-08-16부터 무시됨. bulk는 최대 200개. median과 exposure-minimum은 `period`(DAY/MONTH)가 필수 (`2024-07-16-notice1.md`, `2016-07-11`, `2016-05-02`).
3. **average-position-bid PC 순위는 1~10만**: 11~15는 400 (`2025-05-13-notice1.md`).
4. **고객 ID를 헷갈리지 말 것**: 사용자가 광고주센터에서 보는 번호가 adAccountNo일 수 있음. API의 `X-Customer`에는 CUSTOMER_ID가 들어가야 함. 앱 안내 문구에 이 점을 적어야 함 ❓(앱에서 어떤 번호를 받는지 확인 필요).
5. **리포트 열 이름과 순서**:
   - 2026-11-16부터 ADEXTENSION과 ADEXTENSION_CONVERSION의 8번 열이 사라지고 Media code부터 한 칸씩 당겨짐. 열 번호로 읽는 코드는 깨짐 → **열 이름으로 읽어야 함**.
   - Cost는 2026-03-30부터 VAT 포함 정수.
   - Conversion Type은 2024-07부터 문자열(`purchase` 등).
6. **EXPKEYWORD('파워링크 검색어 보고서')의 Search Keyword Type**: 2025-07 이후 0 일치, 1 확장, 2 유사. 검색어가 없을 때 쓰던 '-' 행은 없어짐 (`2025-06-02-notice1.md`).
7. **지표 이름**:
   - 쓸 수 없게 된 것: `recentAvgRnk`, `recentAvgCpc`(0), `topImpRto`(0), 품질지수(4로 고정)
   - ROAS나 예상 CPA를 구매 기준으로 보려면 `purchaseCcnt`, `purchaseConvAmt`, `purchaseRor`를 쓸 것
8. **예산 추천 관련**:
   - 확장 검색 그룹은 하루 예산 중 확장 검색에 쓰는 비율(`expSearchBudgetRatio`, 1~100%)이 있음
   - ADVoost Max(`aiAdsOptIn`)는 **기본 켜짐**이라 입찰가와 예산 안내에 영향 ❓
   - 공유예산은 계정당 20개, 대상 200개까지
9. **오류 처리**: 입찰가 오류는 2102, 3703, 3904, 예산 오류는 3505, 3704, 3720이므로 사용자에게 이해하기 쉬운 문장으로 바꿔 보여 줄 것.

---

## 부록. 읽은 파일

**읽은 파일**
- `site/_posts/*.md` 227개 전부. 장애·점검·복구 공지는 제목만 보고 넘어감. 그 밖의 공지는 본문을 읽었고 영어로 반복된 부분은 걸러냄.
- `wiki/FAQ.asciidoc`, `wiki/FAQ-stat.asciidoc`, `wiki/FAQ-ManagedCustomerLink-Fade‐out.asciidoc`, `wiki/FAQ-검색광고-ID-(CUSTOMER_ID)-와-통합광고-ID-(adAccountNo).md`, `wiki/Home.md`(한 줄짜리 인사말)
- `repo/README.md`, `repo/NaverSA_API_Error_Code_MAP.md`
- `repo/python-sample/README.md`, `examples/signaturehelper.py`, `examples/ad_management_sample.py`(훑어봄)
- `site/assets/i18n/markdown-ko-KR.json`

**못 읽었거나 일부만 읽은 파일**
- 읽지 못한 파일은 없음.
- 2016~2019 릴리즈 노트의 큰 표(마스터 리포트 열 정의 등)는 건너뜀.
- 2023-07-09와 2024-05-21의 이름 변경 표, 2024-03-13 반응형 소재 마스터 표는 일부만 읽음.
- 2022-06-03과 2023-11-13 공지의 매체 ID 목록 전체는 옮기지 않음.
-
