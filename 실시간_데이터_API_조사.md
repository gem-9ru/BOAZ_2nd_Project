# 실시간·실측 데이터 연결 후보 (API 조사)

> 작성 2026-11-05 · 목적: 네이버 검색광고 API처럼 엔진 기본값을 "실제 숫자"로 바꿀 수 있는 데이터 출처를 찾고, 연결에 필요한 키·권한을 정리
> 표기: 체인 단계는 밸류체인 v3(①접촉 ②반응 ③행동 ④구매 ⑤재구매 ⑥추천). 출처는 맨 아래.
> 키·토큰은 `.env`(로컬)와 Streamlit Secrets(배포)에만 넣고, 저장소에는 올리지 않습니다. 주문처럼 개인정보가 있는 데이터는 고객 ID를 해시로만 다룹니다.

---

## 1. 한눈에 보기

| 우선 | 데이터 | 채우는 체인·엔진 값 | 지금 문제 → 바뀌는 것 | 필요한 것 | 난이도 |
|---|---|---|---|---|---|
| ~~**1**~~ → — | ~~네이버 쇼핑 검색 API~~ **(11/6 정정: 사용 불가)** | ④ 객단가 | NAVER API HUB에 쇼핑 검색이 없음(공식 문서 확인, 기획 세션). 2차 자료에 따르면 쇼핑 검색은 HUB로 이관되지 않고 2026-07-31 개발자센터에서도 종료 → **객단가 후보 기능은 다른 출처 필요** | — | 제외 |
| **1** | 네이버 데이터랩 (검색어 트렌드·쇼핑인사이트) | ② 클릭 곡선의 계절성, 연령·성별 | 12개월 같은 광고비·같은 클릭 → 월별 검색 지수로 계절성, 쇼핑 분야 연령·성별 클릭 비중 | NAVER API HUB 키 (위와 같은 키) | 쉬움 |
| **1** | 네이버 검색광고 `/stats` | ①② 실제 노출·클릭·비용·전환 | 지금은 예상 실적만 → 운영 중인 캠페인이 있으면 실적으로 곡선 보정 (검토 화면의 출발점) | **이미 있는 키** + 계정에 집행 중인 캠페인 | 쉬움 |
| 2 | GA4 Data API | ③ 단계 전환율, 매체별 `cvr_mult` | 구글 굿즈 스토어 샘플 → 내 가게 퍼널. 닫힌 퍼널(funnelReport)도 가능 | 서비스 계정을 GA4 속성에 '뷰어'로 추가 + 속성 ID | 보통 |
| 2 | 스마트스토어 커머스API 또는 카페24 API | ④ 객단가·구매 수, **⑤ 재구매(리텐션 곡선)**, ⑥ 추천 | ⑤⑥이 임시값 → 실제 주문 이력으로 리텐션·구매 빈도 적합 (정의상 ⑤⑥은 자사 주문으로만 채움) | 판매자 계정 + 커머스API센터 '내스토어 애플리케이션'(국내 사업자만) / 카페24 앱 | 보통 |
| 2 | Meta Marketing API (Ads Insights) | ①② 실제 CPM·CTR·CPC | 메타 CPC 700원 가정 → 실측 | 광고 계정 + 시스템 사용자 토큰(`ads_read`) | 보통 |
| 3 | YouTube Data API | ① 인플루언서 도달 (공동구매 카드) | 1회 판매량을 감으로 입력 → 채널 구독자·평균 조회수로 범위 제시 | Google Cloud API 키 (하루 10,000 단위 무료) | 쉬움 |
| 3 | KOSIS 온라인쇼핑동향 | 시장 맥락 (발표용) | 업종별 온라인 거래액·모바일 비중 추이 | KOSIS 인증키 (**개인 회원만**) | 쉬움 |
| 4 | Google Ads API (키워드 기록 지표) | ② 구글 검색량·CPC | 네이버만 있음 → 구글 검색 곡선 | 개발자 토큰 Basic 이상 + '키워드 조사' 허용 용도 승인 | 어려움 |
| 4 | 쿠팡 Wing Open API | ④⑤ (쿠팡 판매분) | 오픈마켓 판매 실적 | 쿠팡 판매자 계정 + Access Key | 보통 (공식 문서 확인 못 함) |
| — | Meta Ad Library API | 경쟁 광고 | **한국은 정치·사회 이슈 광고만 반환** → 상업 광고 조사에 못 씀 | 신분 확인 | 제외 |
| — | 카카오모먼트 API | ①② | 별도 승인 필요, 우선순위 낮음 | 제휴 승인 | 제외 |

---

## 2. 항목별 상세

### 2-1. NAVER API HUB: 데이터랩 (검색어 트렌드·쇼핑인사이트)
> **11/6 정정**: 이전 판에 있던 "쇼핑 검색"은 HUB에서 제공되지 않습니다. HUB의 NAVER 검색 카테고리는 뉴스·블로그·지역·지식iN·카페·백과·이미지·성인검색어·오타변환·웹문서뿐입니다 (공식 문서 [HUB 애플리케이션 가이드](https://guide.ncloud-docs.com/docs/apihub-application), 기획 세션 확인). 2차 자료에 따르면 쇼핑·책·전문자료 검색은 이관 없이 2026-07-31에 종료됐습니다 [11][12].
- 2026-07-31 이후 신규 키는 개발자센터가 아니라 **NAVER API HUB**(네이버 클라우드)에서 발급. 인증 헤더 형식이 바뀜(`X-NCP-APIGW-API-KEY-ID` 계열), 도메인은 `naverapihub.apigw.ntruss.com` [1]
- 한도: 검색어 트렌드·쇼핑인사이트 **각 월 50,000건, 키당 50 RPS, 현재 한시 무료(종량제 예정)** (공식 문서, 기획 세션 확인)
- ⚠️ **약관 확인 필요**: 2차 자료에 네이버 검색 API 약관 개정(9월 시행)으로 "AI 입력·학습 금지, 캐시 기간 제한, 출처 표기 의무"가 생겼다는 보도가 있음 [13]. 데이터랩 결과를 앱에 쓰기 전에 HUB 이용약관 원문에서 해당 조항이 데이터랩에도 적용되는지 확인
- **검색어 트렌드**: 검색어 묶음별 월간 상대 지수 → 월별 클릭 배수(계절성). 지금 엔진은 12개월 동일 가정이라 한계 슬라이드에 적힌 문제를 직접 해결
- **쇼핑인사이트**: 쇼핑 분야·키워드별 클릭 추이를 기기·성별·연령으로 → 메타 타깃 가정의 근거

### 2-2. 네이버 검색광고 `/stats` (지금 키 그대로)
- 노출(`impCnt`), 클릭(`clkCnt`), 광고비(`salesAmt`), 평균 노출 순위, 전환 수(`ccnt`)를 캠페인·광고그룹·키워드 단위로 조회. 대용량은 `StatReport`(하루 단위 비동기, TSV) [4]
- 조회 기간은 한 번에 최대 92일이라는 설명이 있음 [4]
- **필요한 것은 키가 아니라 "집행 이력"**: 계정에 실제로 돈을 쓴 캠페인이 있어야 숫자가 나옵니다

### 2-3. GA4 Data API
- 서비스 계정 권한은 두 곳에서 따로 줘야 함: GCP 프로젝트에서 API 사용 설정, **GA4 관리 화면에서 서비스 계정 이메일을 '뷰어'로 추가** [3]
- `runReport`로 매체·기기별 단계 사용자 수, `runFunnelReport`(v1alpha)로 **닫힌 퍼널** — 기능명세 3-2의 "열린/닫힌 퍼널 차이" 확인 과제를 해결 [3]
- 할당량은 프로젝트당 하루 수십만 요청 수준 [3]

### 2-4. 스마트스토어 커머스API / 카페24 API (⑤ 재구매의 유일한 실측 출처)
- 커머스API센터(apicenter.commerce.naver.com) → 애플리케이션 등록 → 주문·판매자 API 그룹 → ID·시크릿 → 토큰 발급 [2]
- **'내스토어 애플리케이션'은 판매자 본인이 직접 쓸 때만, 국내 사업자만 발급.** 다른 판매자 데이터를 받으려면 솔루션 입점·API 대행사 등록이 필요 → 우리 앱은 "판매자 본인이 자기 키로 쓰는" 형태로만 가능 [2]
- 카페24는 개발자센터 앱 + OAuth, Analytics API(베타)도 있음 [5]
- 받은 주문으로: 첫 구매 월 코호트별 재구매율 → `cohort_retention.csv` 형식으로 저장 → 엔진이 이미 자동 적합 (MECE #5 "유지·수익 근거 비어 있음" 해결)

### 2-5. Meta Marketing API
- 권한 `ads_read`면 광고 계정의 인사이트(노출·도달·CPM·CTR·CPC·전환) 읽기 가능 [7]
- 토큰: 그래프 API 탐색기 토큰은 1~2시간, 장기 토큰 약 60일, **비즈니스 관리자 시스템 사용자 토큰**이 서버용 [7]
- 자기 광고 계정만 쓰면 기본(Standard) 접근으로 충분. 남의 계정까지 쓰려면 앱 검수·비즈니스 인증 필요 [7]

### 2-6. YouTube Data API
- 기본 하루 10,000 단위, `channels.list`(구독자·조회수)는 채널 50개까지 1단위 [8]
- 공동구매 카드에서 인플루언서 채널 주소를 넣으면 구독자·최근 영상 평균 조회수 → "1회 예상 판매량" 범위(조회수 × 가정한 구매 전환율)를 제시

### 2-7. KOSIS 온라인쇼핑동향
- kosis.kr/openapi 회원가입 → 활용신청 → 자동 승인 인증키. **개인 회원만 가능, 법인 불가**, 키 유효기간 있음 [9]
- 상품군별 온라인 거래액, 모바일 비중 → 발표의 "시장 크기" 근거

### 2-8. Google Ads API
- 키워드 조사(`KeywordPlanIdeaService`)는 개발자 토큰 **Basic 이상** + "Researching keywords and recommendations" 허용 용도가 있어야 함. Basic은 하루 15,000 작업 [10]
- 승인에 시간이 걸려 중간 발표(11/9) 전에는 어려움

---

## 3. 연결 원칙 (밸류체인 정의와 맞춤)
1. 매체 API(네이버·메타·구글)는 ①② 숫자와 비용→클릭 곡선에만 씀. ③ 이후 비율은 GA4·주문에서 가져옴 (정의 3-2 원칙 1)
2. ⑤⑥은 주문 데이터로만 채움. 없으면 지금처럼 "가정값" 표시 (원칙 4)
3. 실시간 호출 결과는 `data/interim/` 캐시에 저장하고, 키가 없거나 막히면 캐시로 동작 (네이버 API와 같은 방식). 주문 원본은 저장소에 올리지 않음
4. 매체 숫자는 기여 기간·날짜 기준이 달라 합치지 않고 경고 (조사 00-5 규칙 3)

---

## 출처
1. [NAVER API HUB 개요 (네이버 클라우드)](https://guide.ncloud-docs.com/docs/apihub-overview) · [검색어 트렌드 사용 가이드](https://guide.ncloud-docs.com/docs/searchtrend-use) · [데이터랩 API 비개발자용 정리](https://www.digitalmarketer.co.kr/insights/naver-datalab-api-data-for-non-developers) · [데이터랩 API 신규 발급 주의 (socialcrawl)](https://www.socialcrawl.dev/ko/blog/naver-datalab-api)
2. [커머스API 토론: 내스토어 애플리케이션 조건](https://github.com/commerce-api-naver/commerce-api/discussions/3251) · [커머스API 토론 3463](https://github.com/commerce-api-naver/commerce-api/discussions/3463) · [채널톡 스마트스토어 연동 가이드](https://docs.channel.io/help/ko/articles/%EB%84%A4%EC%9D%B4%EB%B2%84-%EC%8A%A4%EB%A7%88%ED%8A%B8%EC%8A%A4%ED%86%A0%EC%96%B4-6d4e4039) · [솔라피: 스마트스토어 확장](https://solapi.com/blog/seumateu-seutoeoyi-muhan-hwagjangyi-gili-yeolryeossda)
3. [GA4 서비스 계정 가이드](https://grandavehousing.calpoly.edu/news/ga4-service-account-a-quick) · [GA4 Data API 커넥터 문서 (flin-ga4-mcp)](https://pypi.org/project/flin-ga4-mcp/) · [서비스 계정 권한 문제 사례](https://community.latenode.com/t/service-account-permissions-issue-when-using-gcloud-to-query-google-analytics-data-api/38492)
4. [네이버 검색광고 API 데이터 정리 (디지털마케터)](https://www.digitalmarketer.co.kr/insights/naver-search-ad-api-data-for-non-developers) · [naver-ad-performance 문서](https://raw.githubusercontent.com/NomaDamas/k-skill/main/docs/features/naver-ad-performance.md) · [naver-searchad-mcp StatReport](https://glama.ai/mcp/servers/PlatAid/naver-searchad-mcp/tools/download_stat_report)
5. [카페24 개발자센터 공지](https://developers.cafe24.com/cs/front/notice?page=18)
6. [네이버 쇼핑 API 예제 (GitHub wiki)](https://github.com/ehdwo0427/study_repository/wiki/AI_NaverShopping_API) · [네이버 크롤링 차단과 공식 API](https://hashscraper.blog.haus/posts/reasons-why-naver-crawling-is-blocked-and-solutions)
7. [Meta Ads API 키 발급 (unified.to)](https://unified.to/blog/how_to_get_your_meta_ads_api_key) · [Meta Ads API 가이드 (admanage)](https://admanage.ai/blog/meta-ads-api) · [Ad Library API 가이드 (admanage)](https://admanage.ai/blog/facebook-ads-library-api) · [Ad Library API 토큰 (gethookd)](https://www.gethookd.ai/learn/how-to-use-meta-ad-library-api-access-token-generation-documentation/)
8. [YouTube Data API Overview (Google)](https://developers.google.com/youtube/v3/getting-started) · [YouTube API 할당량 정리 (ChannelCrawler)](https://channelcrawler.com/insights/youtube-api-daily-limit-quotas-costs-and-how-to-scale-beyond-10000-units-channelcrawler)
9. [KOSIS OpenAPI 매뉴얼](https://kosis.kr/openapi/file/openApi_manual_v1.0.pdf) · [KOSIS Q&A: 개인 회원만](https://kosis.kr/eng/bulletinBoard/qnaView.do?boardIdx=340099) · [PublicDataReader KOSIS](https://wooiljeong.github.io/PublicDataReader/PublicDataReader.kosis.html)
10. [Google Ads API Access Levels and Permissible Use](https://developers.google.com/google-ads/api/docs/api-policy/access-levels?authuser=0) · [KeywordPlanIdeaService 404 사례](https://groups.google.com/g/adwords-api/c/EvQHQKHcoPY/m/4qINhIH3CAAJ)
11. [네이버 검색 API 종료와 HUB 이관 정리 (waffleboard)](https://waffleboard.io/blog/naver-search-api-hub-migration-guide) · [네이버 오픈API의 API HUB 이관 정리 (키워드 랩)](https://keyword-lab-delta.vercel.app/guide/naver-api-hub) (2차 자료)
12. [개발자센터 신규 발급 종료 대응 PR (CoursePilot)](https://github.com/Mode1221/CoursePilot/pull/406) · [API HUB 요금제 변경 (MiniBiz)](https://minibiz.kr/%EB%84%A4%EC%9D%B4%EB%B2%84-api-hub-%EB%84%A4%EC%9D%B4%EB%B2%84-%EA%B0%9C%EB%B0%9C%EC%9E%90%EC%84%BC%ED%84%B0-api-%EB%B0%8F-%EB%AC%B4%EB%A3%8C-%EC%9A%94%EA%B8%88%EC%A0%9C-%EB%B3%80%EA%B2%BD/) (2차 자료)
13. [네이버, 9월부터 검색 API 'AI 활용 금지' (한국데이터경제신문)](https://www.dataeconomy.co.kr/news/articleView.html?idxno=42307) (보도, 약관 원문 미확인)
