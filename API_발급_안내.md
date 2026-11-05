# API 발급 단계 안내 (개인 계정)

> 작성 2026-11-06 · 공식 문서 본문으로 확인한 절차 기준 (✅ 본문 확인 / △ 검색 요약·2차 자료 / ❓ 미확인)
> 목적: 예측값·샘플 대신 **우리 가게의 실제 숫자**로 코치와 다음 단계 계산을 돌리기 위해, 개인 계정으로 받을 수 있는 API를 순서대로 발급합니다.
> 관련: [실시간_데이터_API_조사.md](실시간_데이터_API_조사.md) (후보 조사), [서비스_종합_진단.md](서비스_종합_진단.md) 6-2 (신호등 검증)

---

## 0. 시작 전에: 꼭 지킬 것

1. **키·시크릿·토큰은 대화창에 붙여 넣지 않습니다.**
   - 직접 아래 파일에 넣고, 저에게는 "넣었어요"라고만 알려 주세요.
   - 저는 키 값을 출력하지 않는 연결 테스트(성공·실패만 표시)로 확인합니다.
2. **로컬에서는 프로젝트 루트의 `.env`에 넣습니다.**
   - 이미 `.gitignore`에 있어서 git에 올라가지 않습니다.
3. **배포 앱(Streamlit Cloud)에서는** 앱 설정의 Secrets 칸에 같은 이름으로 넣습니다. 로컬의 `.streamlit/secrets.toml`도 gitignore 대상입니다.
4. **권한은 읽기 전용으로** 받습니다. 광고 집행, 상품 수정 같은 쓰기 권한은 필요 없습니다.
5. **키가 노출됐다면** 바로 재발급합니다. 네이버 검색광고 키는 예전에 스크린샷으로 공유된 이력이 있어 재발급을 권장합니다(결정 #7).

**넣을 이름** (앱 코드가 읽는 이름. 새 항목은 연결할 때 이 이름으로 맞춥니다)

| API | `.env` / Secrets 이름 | 상태 |
|---|---|---|
| 네이버 검색광고 | `NAVER_AD_API_KEY`, `NAVER_AD_SECRET_KEY`, `NAVER_AD_CUSTOMER_ID` | 코드 있음 |
| NAVER API HUB | `NAVER_HUB_CLIENT_ID`, `NAVER_HUB_CLIENT_SECRET` | 코드 있음 (앱 미연결) |
| 네이버 커머스API | `NAVER_COMMERCE_CLIENT_ID`, `NAVER_COMMERCE_CLIENT_SECRET` | 새로 만듦 |
| 메타 Marketing API | `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID` (`act_` 뒤 숫자) | 새로 만듦 |
| GA4 Data API | `GA4_PROPERTY_ID`, `GOOGLE_APPLICATION_CREDENTIALS` (JSON 키 파일 경로) | 새로 만듦 |

**권장 순서**: ① 검색광고 실적(이미 키 있음) → ② API HUB(누구나, 5분) → ③ 커머스API(스마트스토어가 있을 때) → ④ 메타(광고 계정이 있을 때) → ⑤ GA4(사이트에 GA4가 있을 때)

---

## ① 네이버 검색광고 실적 조회 (`/stats`) — 지금 키 그대로

**필요한 것**: 검색광고 광고주 계정. 그리고 **실제로 돈을 쓴 캠페인 이력**이 있어야 숫자가 나옵니다.

| 단계 | 할 일 | 확인 |
|---|---|---|
| 1 | searchad.naver.com 광고주 가입 (이미 있으면 생략) | ✅ |
| 2 | manage.searchad.naver.com 접속 → **도구 → API 사용 관리** | ✅ |
| 3 | API 라이선스 확인 또는 생성 → 액세스라이선스(API_KEY), 비밀키(SECRET_KEY), CUSTOMER_ID 확인 | ✅ |
| 4 | 키를 재발급했다면 `.env`의 세 값을 바꿈 | — |

- 같은 라이선스로 예상 실적(지금 쓰는 것)과 실적 조회 `GET /stats`, 대용량 리포트 `/stat-reports`를 함께 쓸 수 있습니다 ✅.
  - 별도 신청이 필요 없다는 명시 문장은 찾지 못했습니다 ❓.
  - 호출해 보면 바로 확인됩니다.
- 승인 대기 없이 즉시 쓸 수 있습니다.
- 참고 공지:
  - 2026-11-25부터 쇼핑검색 쇼핑몰상품형·카탈로그형 품질지수가 고정값 4로 나옵니다 ✅.
- 출처: [searchad-apidoc (GitHub)](https://github.com/naver/searchad-apidoc), [API 문서](https://naver.github.io/searchad-apidoc/)

**열리는 것**: 코치 "한 달 뒤"의 쓴 돈·클릭·전환을 직접 입력하지 않고 자동으로 채움. 예상 곡선을 실제 실적으로 보정.

---

## ② NAVER API HUB (데이터랩 검색어 트렌드·쇼핑인사이트) — 누구나

**필요한 것**: 네이버 클라우드(NCP) 계정. 결제수단 등록이 필요한지는 문서에 없습니다 ❓. 가입할 때 요구되면 등록하세요. 현재는 한시적 무료입니다 ✅.

| 단계 | 할 일 | 확인 |
|---|---|---|
| 1 | 네이버 클라우드 가입 → 콘솔 로그인 | ✅ |
| 2 | Menu → All Services → Application Services → **NAVER API HUB** | ✅ |
| 3 | **Subscription** → [서비스 이용 신청] → 약관·개인정보 제3자 제공 동의 | ✅ |
| 4 | **Application** → [Application 등록] → Data Lab의 **검색어 트렌드**, **쇼핑 인사이트** 선택 → 이름(영문·숫자·하이픈 20자 이내) → [완료] | ✅ |
| 5 | Application 목록 → [인증 정보] → **Client ID, Client Secret** 확인 → `.env`에 `NAVER_HUB_CLIENT_ID`, `NAVER_HUB_CLIENT_SECRET` | ✅ |

**한도와 주의**
- 월 한도: 검색어 트렌드·쇼핑 인사이트 각 50,000건. 초당 50건까지입니다. 한도에 닿으면 차단되고 메일 알림이 옵니다 ✅.
- **예전 developers.naver.com 키는 HUB에서 쓸 수 없습니다** ✅.
- **쇼핑 검색(상품 가격) API는 HUB 목록에 없습니다** ✅. 그래서 "검색어별 판매가 분포로 객단가 후보 제시" 아이디어는 지금 방법으로는 막혀 있습니다. 개발자센터에서도 2026-07-31 종료된 것으로 보여(2차 자료 △), 다른 경로로도 쓸 수 없습니다. 이 안내에서는 발급 대상에서 뺐습니다.
- **약관 확인 필요** ❓: 네이버 검색 API 약관 개정(9월 시행) 보도에 따르면 AI 입력·학습 금지, 캐시 기간 제한, 출처 표기 의무가 생겼습니다. 데이터랩(검색어 트렌드)에도 적용되는지 HUB 약관 원문을 발급 화면에서 꼭 읽어 주세요. 우리 앱은 값을 캐시하고 화면에 보여 주므로 캐시 기간과 출처 표기 조건이 중요합니다.
- 개발자센터의 신규 등록 차단 일정은 2차 자료로만 확인했습니다 △.
- 승인 대기 없이 등록하면 바로 키가 나옵니다.
- 출처: [API HUB 개요](https://guide.ncloud-docs.com/docs/apihub-overview), [이용 절차](https://guide.ncloud-docs.com/docs/apihub-procedure), [Application](https://guide.ncloud-docs.com/docs/apihub-application), [이전 안내](https://guide.ncloud-docs.com/docs/apihub-migration)

**열리는 것**: 월별 검색 지수로 계절성 반영. 지금 엔진은 12개월 내내 같은 클릭을 가정합니다. 클라이언트 코드(`src/engine/naver_hub.py`)는 이미 있어서 앱에 연결만 하면 됩니다.

---

## ③ 네이버 커머스API (스마트스토어 주문) — 스마트스토어 판매자만

**필요한 것** (공식 담당자 답변 ✅)
- **국내 사업자**인 스마트스토어 판매자
- 스마트스토어 **통합매니저** 권한
- 판매자 본인이 직접 쓰는 "내 스토어 애플리케이션"만 가능합니다. ID·시크릿을 다른 사람에게 넘기면 약관 위반 소지가 있습니다.

| 단계 | 할 일 | 확인 |
|---|---|---|
| 1 | apicenter.commerce.naver.com 가입 (통합매니저 계정으로) | ✅ |
| 2 | 애플리케이션 등록 → **API 그룹**에서 **주문**(필요하면 판매자정보) 선택 | ✅ 그룹 지정 / ❓ 화면의 버튼·그룹 이름 |
| 3 | 호출할 컴퓨터의 **IP 허용** 설정 (허용되지 않은 IP에서 부르면 `403 GW.IP_NOT_ALLOWED`) | ✅ 오류 / ❓ 입력 위치 |
| 4 | **애플리케이션 ID, 시크릿** 확인 → `.env`에 `NAVER_COMMERCE_CLIENT_ID`, `NAVER_COMMERCE_CLIENT_SECRET` | ✅ |

- 토큰은 코드가 알아서 받습니다 ✅. 3시간짜리이고, `client_id_타임스탬프`를 시크릿으로 bcrypt 서명하는 방식입니다.
- 주문 조회 API: 조건형 상품 주문 조회, 변경 주문 조회(24시간 범위, 최대 300건) ✅
- **IP 허용 때문에** 배포 앱(Streamlit Cloud, IP가 고정되지 않음)에서 직접 부르기는 어렵습니다. 그래서 **집 컴퓨터에서 주문을 받아 파일로 저장 → 앱이 그 파일을 읽는 방식**으로 연결합니다. 주문 원본은 git에 올리지 않습니다.
- 심사·대기 여부는 확인하지 못했습니다 ❓.
- 출처: [인증](https://apicenter.commerce.naver.com/docs/auth), [제한 사항](https://apicenter.commerce.naver.com/docs/restriction), [트러블슈팅](https://apicenter.commerce.naver.com/docs/trouble-shooting), [담당자 답변 #3251](https://github.com/commerce-api-naver/commerce-api/discussions/3251)

**열리는 것**: 실제 판매 수와 **재구매**(⑤)를 잴 수 있습니다. 재구매를 실제로 잴 수 있는 거의 유일한 출처라서, 코치의 재구매 가정값(0 / 0.5 / 2회)과 1년 손익분기를 우리 가게 숫자로 바꿀 수 있습니다.

> 자사몰(카페24)이면 카페24 개발자센터 앱 + OAuth 방식입니다. 이 문서에서는 절차를 확인하지 않았습니다 ❓.

---

## ④ 메타 Marketing API (광고 성과 읽기) — 메타 광고 계정이 있을 때

**필요한 것**: 활성 광고 계정, 비즈니스 관리자(비즈니스 포트폴리오), Meta 개발자 계정

| 단계 | 할 일 | 확인 |
|---|---|---|
| 1 | 광고관리자 → 설정에서 **광고 계정 번호** 확인 | ✅ |
| 2 | developers.facebook.com에서 개발자 등록 → 앱 만들기 → use case **"Measure ad performance data with Marketing API"** (나중에 삭제 불가) | ✅ |
| 3 | 앱에 비즈니스 포트폴리오 연결 (시스템 사용자와 같은 비즈니스 소속이어야 함) | ✅ |
| 4 | business.facebook.com/settings → 사용자 → **시스템 사용자** → 추가 | ✅ |
| 5 | 시스템 사용자에게 [자산 추가]로 앱과 광고 계정 할당 | ✅ 앱 / ❓ 광고 계정 화면 |
| 6 | [새 토큰 생성] → 앱 선택 → **`ads_read`만 체크** → 만료 **60일** 선택(권장) → 토큰 복사 (다시 볼 수 없음) | ✅ |
| 7 | `.env`에 `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID` | — |

- 내 광고 계정만 읽으면 **기본(Standard) 접근으로 충분하고 앱 심사가 없습니다**. 즉시 쓸 수 있습니다 ✅.
- 60일 토큰은 기간 안에 갱신해야 합니다. 그래프 API 탐색기에서 받은 토큰은 1~2시간이면 만료됩니다 ✅.
- 출처: [인증](https://developers.facebook.com/documentation/ads-commerce/marketing-api/get-started/authentication.md), [권한](https://developers.facebook.com/documentation/ads-commerce/marketing-api/get-started/authorization.md), [시스템 사용자 토큰](https://developers.facebook.com/docs/marketing-api/system-users/install-apps-and-generate-tokens)

**열리는 것**: 실제 CPM·CTR·클릭 비용. 지금 쓰는 메타 클릭 비용 가정값(700원)과 메타 포화 노브를 실측으로 바꿉니다.

---

## ⑤ GA4 Data API — 사이트에 GA4가 설치돼 있을 때

**필요한 것**: Google 계정, 그 GA4 속성의 **관리자** 권한(사용자를 추가해야 하므로)

| 단계 | 할 일 | 확인 |
|---|---|---|
| 1 | console.cloud.google.com에서 프로젝트 만들기 → **Google Analytics Data API** 사용 설정 | ✅ |
| 2 | IAM 및 관리자 → **서비스 계정** 만들기 | ✅ |
| 3 | 서비스 계정 → 키 → 키 추가 → 새 키 → **JSON** (한 번만 내려받을 수 있음) → **프로젝트 폴더 밖**에 저장 | ✅ |
| 4 | GA4 → 관리 → 속성 → **속성 액세스 관리** → + → 사용자 추가 → 서비스 계정 이메일(JSON의 `client_email`) → 역할 **뷰어** | ✅ |
| 5 | GA4 → 관리 → 속성 설정 → **속성 ID**(숫자) 확인 | ✅ |
| 6 | `.env`에 `GA4_PROPERTY_ID`, `GOOGLE_APPLICATION_CREDENTIALS=JSON 파일 경로` | ✅ |

- 무료 한도: 속성당 하루 20만 토큰. 우리가 쓰는 양으로는 충분합니다 ✅.
- 회사·학교 조직의 Google Cloud(2024-05 이후 생성)는 JSON 키 생성이 막혀 있을 수 있습니다. 개인 Gmail 프로젝트는 보통 괜찮습니다 △.
- 배포 앱에 넣을 때는 JSON 내용을 Secrets에 표 형식으로 넣습니다(연결할 때 안내).
- 출처: [빠른 시작](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart-client-libraries), [할당량](https://developers.google.com/analytics/devguides/reporting/data/v1/quotas), [속성 ID](https://developers.google.com/analytics/devguides/reporting/data/v1/property-id)

**열리는 것**: 구글 굿즈몰 샘플 대신 **우리 사이트의 퍼널**(방문 → 상품 조회 → 장바구니 → 구매). 열린 퍼널과 닫힌 퍼널의 차이도 확인할 수 있습니다.

---

## 6. 발급한 뒤의 흐름

1. `.env`에 넣고 저에게 **어떤 API를 넣었는지만** 알려 주세요.
2. 연결 테스트를 돌립니다. 키는 출력하지 않고, 성공·실패와 받은 행 수만 보여 줍니다.
3. 프로토타입 세션에 연결을 요청합니다.
   - 실시간 호출이 되는 API(검색광고·HUB·메타·GA4)는 앱에서 바로 부르고 캐시합니다.
   - 커머스API는 로컬에서 받아 파일로 넘깁니다.
4. 받은 실제 숫자로 **코치 신호등 검증**을 먼저 합니다(종합 진단 6-2 #2): 우리 가게에서 코치가 내린 판정과 실제 결과를 나란히 비교합니다.
