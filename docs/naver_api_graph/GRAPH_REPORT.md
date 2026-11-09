# Graph Report - corpus  (2026-11-09)

## Corpus Check
- 49 files · ~75,410 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1096 nodes · 1843 edges · 63 communities (52 shown, 11 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 140 edges (avg confidence: 0.83)
- Token cost: 574,047 input · 0 output

## Community Hubs (Navigation)
- 광고그룹·입찰·예산 오류 코드
- 소재·반응형 소재·전환 리포트
- 광고그룹 API·확장 검색·예산 마스터
- 확장소재·성과 리포트·비즈머니
- 전환·확장소재 리포트 열 변경
- 소재·확장소재·공통 오류 코드
- 호출 제한·점검·키워드 도구 오류
- 비즈채널 API와 오류
- 캠페인 API와 오류
- 예상 실적·입찰가 API
- 확장소재 유형 변천
- 성과 통계 지표 (/stats)
- 광고 유형 계층 (캠페인·그룹·마스터)
- 마스터 리포트 API
- 마스터 리포트 열 변경 (2016)
- 키워드 API와 오류
- 광고계정 API (atower)
- 대용량 리포트 유형·COST 변경
- 초기 광고관리 API 변경 (2016)
- 타기팅 개편 2022 (Criterion)
- 구매완료 지표 (purchase*)
- 쇼핑검색 입찰가 추정 (NPLA)
- 쇼핑 브랜드형·상품 그룹
- ADVoost (Max·플레이스)
- 옛 타깃 API (Target)
- 계정 통합·관리계정 대체
- 비즈머니 비용 조회 변천
- 옛 Target·카탈로그 (2016~2018)
- 파워컨텐츠 (NPC)
- 2026 AI 광고·품질지수 종료
- 키워드 플러스·유사검색어 → 검색어 보고서
- 타기팅 기준 API (Criterion)
- 위키 FAQ: 인증·상태·공유예산
- 캠페인·그룹 유형 코드
- 인증 서명 (파이썬 샘플)
- 전환 리포트 초기 (2016~2017)
- 키워드 플러스·예상 실적 bulk
- 네이버페이 전환·검색어 보고서
- /stats 조회 규칙 변천
- 쇼핑 전환목표 자동입찰
- 기간 필드 검증·톡톡상담
- 타기팅 리포트 (CRITERION)
- 이용자 세그먼트·쇼핑 지역 타기팅
- 리포트·마스터 이름 변경 (2023)
- 관리 키워드 초기 필드
- API 도메인 이전
- 스마트블록 매체
- 파워링크 최적화 지표 (연관·클릭 기대)
- 최소 노출 입찰가 (period)
- 키워드 확장 Beta
- 관리 키워드 API
- 키워드 도구 호출 제한 (429)
- 관리 키워드 필드 삭제
- 라벨
- 2016 릴리스 노트
- Java 6 지원 종료
- 2017 공지
- 2018 공지
- api.naver.com SSL
- 2019 공지
- 2020 공지
- 2021 공지
- 위키 Home

## God Nodes (most connected - your core abstractions)
1. `Adgroup 정의` - 39 edges
2. `예상 실적·입찰가 API (Estimate)` - 34 edges
3. `Campaign 정의` - 22 edges
4. `AdgroupRequest 정의` - 22 edges
5. `네이버 검색광고 API 오류 코드표` - 22 edges
6. `도구 API (Tool)` - 21 edges
7. `성과 통계 API (Report)` - 21 edges
8. `AdKeyword 정의` - 20 edges
9. `계정 API (atower)` - 20 edges
10. `광고그룹 API (Adgroup)` - 18 edges

## Surprising Connections (you probably didn't know these)
- `recentAvgRnk (최근통검평균노출순위, 0 반환)` --semantically_similar_to--> `recentAvgRnk (최근 통검 평균노출순위)`  [INFERRED] [semantically similar]
  notices/notices_2025b.md → wiki/FAQ-stat.md
- `쇼핑몰 상품형 광고그룹 (SHOPPING)` --semantically_similar_to--> `SHOPPING(2) 쇼핑몰 상품형 그룹`  [INFERRED] [semantically similar]
  notices/notices_2025b.md → wiki/FAQ.md
- `LOCAL_AD (플레이스광고 광고그룹)` --semantically_similar_to--> `LOCAL_AD(10) 플레이스 검색 그룹`  [INFERRED] [semantically similar]
  notices/notices_2026.md → wiki/FAQ.md
- `<API_KEY>·<SECRET_KEY>·<CUSTOMER_ID> 설정` --semantically_similar_to--> `apiKey / secretKey`  [INFERRED] [semantically similar]
  repo/python-sample/README.md → specs/atower.md
- `purchaseCcnt (구매완료 전환수)` --semantically_similar_to--> `ccnt (전환수)`  [INFERRED] [semantically similar]
  notices/notices_2026.md → wiki/FAQ-stat.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **2021 쇼핑검색 브랜드형 출시 구성요소** — notices_notices_2021_shopping_brand_adgroup, notices_notices_2021_product_group, notices_notices_2021_nccproductgroupid, notices_notices_2021_shopping_brand_keyword_type, notices_notices_2021_shopping_brand_ad, notices_notices_2021_topimprto, notices_notices_2021_shoppingbrandproduct_report, notices_notices_2021_master_report_brandad [EXTRACTED 0.95]
- **광고그룹 자동입찰 (systemBiddingType) 체계** — notices_notices_2019_systembiddingtype, notices_notices_2019_systembiddingtype_ml, notices_notices_2019_systembiddingtype_maxconv, notices_notices_2019_daily_budget [EXTRACTED 0.95]
- **입찰가 추정(Estimate) 서비스 계열** — notices_notices_2016_estimate_exposure_minimum_bid, notices_notices_2016_estimate_performance_bulk, notices_notices_2017_npla_estimate_exposure_minimum_bid, notices_notices_2017_npc_estimate_average_position_bid, notices_notices_2018_npc_estimate_performance, notices_notices_2021_shopping_brand_estimate_pc_mobile_mins [INFERRED 0.85]
- **2022-04 Criterion 타겟팅 API 묶음** — notices_notices_2022_criterion, notices_notices_2022_ep_criterion_get, notices_notices_2022_ep_criterion_bidweight, notices_notices_2022_ep_criterion_put_type, notices_notices_2022_ep_criterion_dictionary, notices_notices_2022_criterion_master, notices_notices_2022_criterion_report [EXTRACTED 1.00]
- **2023-04 공유예산 기능(객체·API·마스터)** — notices_notices_2023a_shared_budget, notices_notices_2023a_ep_shared_budgets, notices_notices_2023a_shared_budget_master, notices_notices_2023a_shared_budget_id, notices_notices_2023a_campaign_master, notices_notices_2023a_adgroup_master [EXTRACTED 1.00]
- **파워링크 검색어 보고서(EXPKEYWORD) 검색어 타입 변천** — notices_notices_2023a_event_2023_07_10_expkeyword_change, notices_notices_2023b_event_2023_08_15_expkeyword_extend, notices_notices_2023b_event_2023_11_14_exact_match_type, notices_notices_2023b_search_keyword_type, notices_notices_2023b_expkeyword [INFERRED 0.85]
- **키워드 확장(Beta) 종료로 제거된 필드 묶음** — notices_notices_2024a_키워드_확장_beta_종료, notices_notices_2024a_usekeywordplus, notices_notices_2024a_keywordplusweight, notices_notices_2024a_useclosevariant, notices_notices_2024a_keywordplus, notices_notices_2024a_using_keywordplus, notices_notices_2024a_keywordplus_bidding_weight, notices_notices_2024a_using_closevariant [EXTRACTED 1.00]
- **확장 검색 도입으로 추가된 필드·유형** — notices_notices_2024b_확장_검색, notices_notices_2024b_useexpsearch, notices_notices_2024b_expsearchbudgetratio, notices_notices_2024b_sharedexpsearchbudgetratio, notices_notices_2024b_using_expanded_search, notices_notices_2024b_expanded_search_budget_ratio, notices_notices_2024b_exp_search [EXTRACTED 1.00]
- **광고계정 통합에 따른 API·리포트 교체** — notices_notices_2025a_광고계정_통합, notices_notices_2025a_account_master, notices_notices_2025a_managedcustomerlink, notices_notices_2025a_get__ad_accounts, notices_notices_2025a_get__ad_accounts__adaccountno__members, notices_notices_2025a_get__manager_accounts, notices_notices_2025a_get__manager_accounts__manageraccountno__child_ad_accounts [EXTRACTED 1.00]
- **2026년 ADVoost 확대 (파워링크 QI 종료·ADVoost Max·ADVoost 플레이스)** — notices_notices_2026_파워링크_qi_항목_종료_20260729, notices_notices_2026_광고그룹_advoost_max_aiadsoptin_추가_20260715, notices_notices_2026_플레이스광고_advoost_플레이스_20260916, notices_notices_2026_advoost [INFERRED 0.85]
- **'구매완료' 전환유형 STATS 지표 (purchaseCcnt·purchaseConvAmt·purchaseRor)** — notices_notices_2026_purchaseccnt, notices_notices_2026_purchaseconvamt, notices_notices_2026_purchaseror, notices_notices_2026_구매완료_전환유형 [EXTRACTED 1.00]
- **통합광고 계정 체계 전환 (ManagedCustomerLink 대체·CUSTOMER_ID 유지)** — wiki_faq_managedcustomerlink_fade_out_managedcustomerlink, wiki_faq_managedcustomerlink_fade_out_ad_accounts, wiki_faq_managedcustomerlink_fade_out_manager_accounts, wiki_faq_managedcustomerlink_fade_out_child_ad_accounts, wiki_faq_검색광고_id__customer_id__와_통합광고_id__adaccountno__customer_id, wiki_faq_검색광고_id__customer_id__와_통합광고_id__adaccountno__adaccountno [INFERRED 0.85]
- **캠페인 → 광고그룹 → 키워드·소재·확장소재 계층** — specs_ncc_heroes_ncc__campaign_campaign, specs_ncc_heroes_ncc__adgroup_adgroup, specs_ncc_heroes_ncc__adkeyword_adkeyword, specs_ncc_heroes_ncc__ad_ad, specs_ncc_heroes_ncc__adextension_adextension, specs_ncc_heroes_ncc__businesschannel_businesschannel [EXTRACTED 1.00]
- **키워드 수요 → 입찰가별 예상 실적 → 쇼핑검색 입찰가 추정** — specs_ncc_keywordstool_api_group, specs_estimate_post_estimate_performance_type, specs_estimate_post_npla_estimate_average_position_bid_type, 네이버_검색광고_api_종합_키워드_도구_사용_중, 네이버_검색광고_api_종합_쇼핑검색_입찰가_추정_후보 [INFERRED 0.85]
- **API 키 발급과 인증 설정** — repo_readme_api_license_and_secret_key, repo_python_sample_readme_api_key_secret_key_customer_id, repo_python_sample_readme_ad_management_sample_py, specs_atower_apikey, repo_readme_naver_search_advertiser_center [INFERRED 0.75]

## Communities (63 total, 11 thin omitted)

### Community 0 - "광고그룹·입찰·예산 오류 코드"
Cohesion: 0.06
Nodes (59): 3703 광고그룹 입찰가 오류, 3704 광고그룹 하루 예산 오류, 3709 키워드 플러스(확장) 사용 여부 오류, 3714 캠페인당 광고그룹 최대 개수 초과, 3716 광고그룹 제외 키워드 최대 개수 초과, 3911 그룹당 키워드 수 초과, 광고그룹 오류 3701~3732, 입찰가·이름 중복 2102 / 2023 / 2024 (+51 more)

### Community 1 - "소재·반응형 소재·전환 리포트"
Cohesion: 0.07
Nodes (53): Ad (소재), AD AssetLink Master 수정: Asset Link Inspect Status 항목 제외 (2024-03-20), Conversion Report (AD_CONVERSION), Conversion Detail Report (AD_CONVERSION_DETAIL), 키워드 확장 종료에 따른 Ad group Master 11·12·20번 필드 빈스트링 처리 (2024-08-19), Powerlink Single Ad Master (item=Ad), 반응형 소재 연결 마스터 (item=ADASSETLINK / Powerlink Responsive Ad AssetLink Master), Ad Extension Conversion Report (ADEXTENSION_CONVERSION) (+45 more)

### Community 2 - "광고그룹 API·확장 검색·예산 마스터"
Cohesion: 0.07
Nodes (52): Adgroup API, 광고그룹 마스터 (item=Adgroup), 광고그룹 예산 마스터 (item=AdgroupBudget), breakdown 파라미터, Campaign (캠페인), Shopping Catalog Product Master (item=CatalogAd), Estimate: get (performance / performance-bulk), EXP_SEARCH (제외검색어 type: 확장 검색) (+44 more)

### Community 3 - "확장소재·성과 리포트·비즈머니"
Cohesion: 0.06
Nodes (51): /ncc/ad-extensions (확장소재 API), Account Master (item=Account), Ad Performance Report (AD), Ad Performance Detail Report (AD_DETAIL), Ad Extension Performance Report (ADEXTENSION), Adgroup: create / update / update (by fields), Bizmoney API (get, charge, period, exhaust 계속 제공), 비즈머니 사용 조회 Bizmoney(cost) API 지원 중단 (2025-08-06) (+43 more)

### Community 4 - "전환·확장소재 리포트 열 변경"
Cohesion: 0.06
Nodes (49): AD_CONVERSION (광고 전환 보고서), AD_CONVERSION_DETAIL (전환 상세 보고서), AD extension Business Channel ID (보고서 열), AD extension ID (보고서 열), Ad Media Master (item = media), ADEXTENSION (확장소재 광고 성과 보고서), ADEXTENSION_CONVERSION (확장소재 전환 보고서), BrandNewContract API (신제품 검색 계약) (+41 more)

### Community 5 - "소재·확장소재·공통 오류 코드"
Cohesion: 0.07
Nodes (49): 1018 접근 권한 없음, 3819 키워드 삽입 과다, 3822 같은 내용 소재 중복, 4003 확장소재 타입 오류, 4011 확장소재 기간 노출 설정 오류, 소재 오류 3801~3828, 확장소재 오류 4001~4014, 공통 오류 1001~1018 (자원 없음, 잘못된 요청, 중복, 한도 초과, 권한) (+41 more)

### Community 6 - "호출 제한·점검·키워드 도구 오류"
Cohesion: 0.06
Nodes (47): 1016 너무 많은 접속, 429 요청 과다, 4601 잘못된 보고서 ID, 503 정기 점검, 네이버 검색광고 API 오류 코드표, 광고그룹 전략 없음 3001~3005, 광고 템플릿 오류 4801~4803, 키워드 입력 오류 7001~7003 (+39 more)

### Community 7 - "비즈채널 API와 오류"
Cohesion: 0.07
Nodes (43): 3725 캠페인 유형에서 쓸 수 없는 채널 타입, 비즈채널 오류 3601~3608, 노출 제한 IP 오류 5501~5503, 비즈채널 API (BusinessChannel), BusinessChannel 정의 (비즈채널), channelTp (SITE, PHONE, ADDRESS, BOOKING, TALK, CONTENTS, PLACE, CATALOG), DELETE /api/ncc/channels/{businessChannelId} (delete), DELETE /api/ncc/channels{?ids} (delete by ids) (+35 more)

### Community 8 - "캠페인 API와 오류"
Cohesion: 0.09
Nodes (40): 3502 캠페인 안에 그룹 존재, 3505 캠페인 하루 예산값 오류, 3506 같은 이름의 캠페인, 3728 키워드 확장 제외 키워드 미지원 캠페인 유형, 3923 캠페인 유형상 키워드 생성 불가, 캠페인 오류 3501~3506, 캠페인 API (Campaign), Campaign 정의 (+32 more)

### Community 9 - "예상 실적·입찰가 API"
Cohesion: 0.10
Nodes (39): 예상 실적·입찰가 API (Estimate), Bid 정의, bids (입찰가 목록, 최대 100), device (PC, MOBILE, BOTH), Error 정의, EstimateBid 정의, EstimateBidByPosition 정의, EstimateBidWithPostion 정의 (+31 more)

### Community 10 - "확장소재 유형 변천"
Cohesion: 0.09
Nodes (34): Ad-extension (확장소재), 2017-03 확장소재 기간설정·WEB_SITE 신규 유형(HEADLINE/DESCRIPTION/SUB_LINKS/PRICE_LINKS) 추가, 2017-12 WEB_SITE 확장소재 POWER_LINK_IMAGE, IMAGE_SUB_LINKS 추가, DESCRIPTION 확장소재, HEADLINE 확장소재, IMAGE_SUB_LINKS 확장소재, POWER_LINK_IMAGE 확장소재, PRICE_LINKS 확장소재 (+26 more)

### Community 11 - "성과 통계 지표 (/stats)"
Cohesion: 0.14
Nodes (31): 성과 통계 API (Report), avgRnk (평균 노출 순위, 파워링크만), breakdown (pcMblTp, dayw, hh24, regnNo 분할), BreakdownStat 정의, ccnt (전환수), clkCnt (클릭수), cpc (클릭당 비용), ctr (클릭률) (+23 more)

### Community 12 - "광고 유형 계층 (캠페인·그룹·마스터)"
Cohesion: 0.09
Nodes (31): 광고그룹 (Adgroup), adgroupAttrJson, Ad group Master (Adgroup), 신제품검색광고 (BRAND_NEW), 브랜드검색, BRAND_SEARCH_NEW_AD 신제품검색 소재 유형, 캠페인 (Campaign), Campaign Master (Campaign) (+23 more)

### Community 13 - "마스터 리포트 API"
Cohesion: 0.12
Nodes (27): 5001 실명인증 미완료로 충전 불가, 충전(비즈머니) 오류 5001~5002, 마스터 리포트 API (Master Report), DELETE /master-reports (delete all), DELETE /master-reports/{id} (delete by id), Error 정의, fromTime (Delta 시작 시각), GET /master-reports (list (최대 100 jobs)) (+19 more)

### Community 14 - "마스터 리포트 열 변경 (2016)"
Cohesion: 0.10
Nodes (26): 2016-05 Adgroup 마스터 9번 필드 PC 네트워크 입찰 가중치로 변경, 2016-05 SeasonalEvent 마스터 보고서 추가, 2016-07 Media 마스터 Group Id 필드 추가, 2016-11 ShoppingProduct 마스터 추가 및 BusinessChannel 유형 변경, 2016-12 ShoppingProduct 마스터 Delta(fromTime) 지원, Master Report (마스터 보고서), Adgroup 마스터 보고서, BusinessChannel 마스터 보고서 (+18 more)

### Community 15 - "키워드 API와 오류"
Cohesion: 0.15
Nodes (24): 3904 키워드 입찰가 오류, 3905 광고그룹에 이미 있는 키워드, 3909 광고 노출 금지 키워드, 3916 기본 입찰가 사용 여부·입찰가 누락, 키워드 오류 3901~3924, AdKeyword 정의, 키워드 API (AdKeyword), DELETE /api/ncc/keywords{?ids} (delete-items) (+16 more)

### Community 16 - "광고계정 API (atower)"
Cohesion: 0.15
Nodes (24): AdAccount 정의, AdAccountDetail 정의, AdAccountMember 정의, adAccountNo (광고 계정 번호), AdAccountsResponse 정의, 계정 API (atower), ApiCredentials 정의, apiKey / secretKey (+16 more)

### Community 17 - "대용량 리포트 유형·COST 변경"
Cohesion: 0.17
Nodes (20): AD (광고 성과 보고서), AD_CONVERSION, AD_CONVERSION_DETAIL, AD_DETAIL, AD extension Business Channel ID (보고서 열), ADEXTENSION (확장 소재 광고 성과 보고서), ADEXTENSION_CONVERSION, 리포트 상태 '데이터 변경됨 (CHANGED)' (+12 more)

### Community 18 - "초기 광고관리 API 변경 (2016)"
Cohesion: 0.13
Nodes (19): 2016-05 광고관리 JSON 타입 Integer→boolean/Enum 변경, 2016-05 캠페인·광고그룹·키워드 목록 페이징 적용, 2016-06 GET /ncc/campaigns·adgroups·keywords selector 파라미터 추가, Ad (소재), Ad Keyword, AdGroup, Campaign, deliveryMethod (+11 more)

### Community 19 - "타기팅 개편 2022 (Criterion)"
Cohesion: 0.18
Nodes (17): 광고그룹 (Adgroup), bidWeight 입찰가 가중치 (50~500), Criterion 광고 객체 (타겟팅), Criteria Master (item=Criterion) 타게팅 대상 마스터, Criterion Dictionary, dictionaryCode 타겟팅 코드 생성 규칙, DictionaryType (SD/GN/AG/RL/RP/ALL_REGIONAL), PUT /ncc/criterion/{adgroupId}/bidWeight (+9 more)

### Community 20 - "구매완료 지표 (purchase*)"
Cohesion: 0.15
Nodes (17): purchaseCcnt (구매완료 전환수), purchaseConvAmt (구매완료 전환매출액), purchaseRor (구매완료 광고수익률 %), STATS API (/stats), STATS API 구매완료 광고수익률 purchaseRor 신규 제공 (2026-05-13), STATS API 구매완료 전환지표 신규 제공 (2026-03-30), topImpRto (검색상단노출률 %), '구매완료' 전환유형 (+9 more)

### Community 21 - "쇼핑검색 입찰가 추정 (NPLA)"
Cohesion: 0.16
Nodes (15): 2016-10 /stats statType=NPLA_SCH_KEYWORD 추가 (쇼핑 검색어별 클릭·전환), statType NPLA_SCH_KEYWORD, 쇼핑검색광고 (SHOPPING 캠페인), 2017-01 쇼핑검색(NPLA) 입찰가 추정 서비스 추가, 2017-09 NPLA_SCH_KEYWORD 집계기준 클릭→노출 변경, impCnt 추가, impCnt, /npla-estimate/average-position-bid/{type}, /npla-estimate/exposure-minimum-bid/{type} (+7 more)

### Community 22 - "쇼핑 브랜드형·상품 그룹"
Cohesion: 0.20
Nodes (15): 2021-03 마스터 보고서 변경 (BusinessChannel·Adgroup·Keyword 타입 추가, ProductGroup·ProductGroupRel 신규), 2021-03 쇼핑검색 브랜드형 상품별 광고효과·전환 보고서 추가 (NV_MID 기준, 365일), 2021-04 SHOPPINGBRANDPRODUCT 보고서 Business Channel ID 누락, GET /api/ncc/product-groups, 비즈채널 SHOPPING_BRAND, ProductGroup / ProductGroupRel 마스터 보고서, nccProductGroupId, NV_MID (네이버쇼핑 상품 ID) (+7 more)

### Community 23 - "ADVoost (Max·플레이스)"
Cohesion: 0.19
Nodes (15): adgroupAttrJson, ADVoost (애드부스트), ADVoost Max, ADVOOST_PLACE_AD (연동형 소재, type 17), ADVoost 플레이스 신규 오류 코드 (3749·3752~3756·3837~3840·4029·4420~4422·5117), aiAdsOptIn (ADVoost Max 설정), LOCAL_AD (플레이스광고 광고그룹), /ncc/adgroups (광고그룹 API) (+7 more)

### Community 24 - "옛 타깃 API (Target)"
Cohesion: 0.14
Nodes (15): AD_TAG (광고 태그), GENDER_TARGET, MEDIA_TARGET (매체 타겟팅), NON_SEARCH_KEYWORD_TARGET (검색어 없는 경우 노출 제외), PC_MOBILE_TARGET, REGIONAL_TARGET (지역 타겟팅), RESTRICT_KEYWORD_TARGET (노출 제한 키워드), Schedules.java (java 샘플 시간 타겟팅 유틸) (+7 more)

### Community 25 - "계정 통합·관리계정 대체"
Cohesion: 0.21
Nodes (15): /ad-accounts (내가 구성원인 광고계정 목록), /ad-accounts/{adAccountNo}/members (광고계정 구성원), /manager-accounts/{managerAccountNo}/child-ad-accounts (하위 광고계정), FAQ - ManagedCustomerLink Fade-out, ManagedCustomerLink API (지원 종료), /manager-accounts (관리계정 목록), 관리계정 (ManagerAccount), MYCLIENTS 조회 대체 절차 (+7 more)

### Community 26 - "비즈머니 비용 조회 변천"
Cohesion: 0.18
Nodes (14): 2016-06 AD_COST 보고서 폐지 (getCost로 대체), 2016-07 getCost 조정 비즈머니 컬럼 추가 (adjustedNonRefundableAmt, adjustedRefundableAmt), 2016-08 getCost BRND 기간인식 광고비 PC/모바일 제공, AD_COST 보고서, Bizmoney, Bizmoney: getCost, productCode=BRND (브랜드검색), 2017-10 getCost 신규 브랜드검색(BRAND_SEARCH) 광고비 조회 추가 (+6 more)

### Community 27 - "옛 Target·카탈로그 (2016~2018)"
Cohesion: 0.21
Nodes (14): 2016-06 Target target 필드 String→Object, 2016-06 Target nccAdgroupId → ownerId 이름 변경, 2016-10 /ncc/targets 조회·수정 오퍼레이션 추가, GET/PUT /ncc/targets, ownerId, Target, 2018-09 쇼핑검색 CATALOG 그룹·CATALOG_AD 소재·카탈로그 확장소재 추가, CATALOG_AD 소재 (+6 more)

### Community 28 - "파워컨텐츠 (NPC)"
Cohesion: 0.20
Nodes (14): 2017-02 파워컨텐츠(NPC) 입찰가 추정 서비스 추가, 2017-02 POWER_CONTENTS 캠페인·CONTENTS 채널·컨텐츠 소재 유형 추가, adgroupAttrJson (contentsType), CONTENTS_AD_INFORMATION, CONTENTS_AD_PRODUCT, 비즈채널 CONTENTS 유형 (BLOG/CAFE/POST), 키워드플러스 노출제한 키워드 API, /npc-estimate/average-position-bid/{type} (+6 more)

### Community 29 - "2026 AI 광고·품질지수 종료"
Cohesion: 0.18
Nodes (14): Ad group Master Report (item = Adgroup), 확장소재 마스터 (item = AdExtension), AI 광고 출시로 Ad group Master Report에 'Using Ai Ads' 열 추가 (2026-07-16), 검색광고 API 비밀키 (Secret Key), 네이버 검색광고 API 공지·릴리스 노트 2026년, MASTER-REPORT (마스터 보고서), nccQi (AdKeyword 응답), 품질지수 마스터 (item = Qi, 5번 Quality Index) (+6 more)

### Community 30 - "키워드 플러스·유사검색어 → 검색어 보고서"
Cohesion: 0.26
Nodes (12): 2023-06-28 파워링크 유사검색어(Close Variant) beta 추가, 2023-07-10 키워드 플러스 성과 보고서 변경(검색어 타입 추가·중복행 제거·명칭 변경), EXPKEYWORD 키워드 플러스 성과 보고서 → 파워링크검색어보고서, Search Keyword Type (1:확장, 2:유사검색어), STAT-REPORT 대용량 보고서, useCloseVariant 일치(유사검색어) 노출 여부, useKeywordPlus 키워드 확장, 2023-07-11 파워링크 검색어 보고서 재생성 (+4 more)

### Community 31 - "타기팅 기준 API (Criterion)"
Cohesion: 0.32
Nodes (12): 타게팅 기준 API (Criterion), bidWeight (입찰 가중치 50~500), Criterion 정의 (타게팅), CriterionDictionary 정의, CriterionRequest 정의, GET /api/ncc/criterion-dictionary/{type} (타게팅 코드 사전), GET /api/ncc/criterion/{ownerId}{?type} (list by id), negative (노출 제외 여부) (+4 more)

### Community 32 - "위키 FAQ: 인증·상태·공유예산"
Cohesion: 0.18
Nodes (12): adAttr bidAmt / useGroupBidAmt (쇼핑 상품형·카탈로그형), 검색광고 API 위키 FAQ, Invalid Timestamp 403 오류 (X-Timestamp), RSA_AD (파워링크 반응형 소재, 14), statusReason (ELIGIBLE, CAMPAIGN_LIMITED_BY_BUDGET 등), X-Timestamp 헤더, 공유예산 한도 (캠페인용·광고그룹용 각 20개, 포함 최대 200개), 하나의 액세스 라이선스/비밀키로 여러 애플리케이션 구축 (+4 more)

### Community 33 - "캠페인·그룹 유형 코드"
Cohesion: 0.29
Nodes (12): BRAND_NEW(11) 신제품 검색 그룹, CATALOG(7) 제품 카탈로그 그룹, LOCAL_AD(10) 플레이스 검색 그룹, SHOPPING(2) 쇼핑몰 상품형 그룹, SHOPPING_BRAND(9) 쇼핑 브랜드 그룹, 광고 관리 문자열 코드 ↔ Master Report 숫자 코드 매핑, 캠페인 유형별 등록 가능한 그룹·비즈채널 유형, BRAND_SEARCH(4) 브랜드검색 (+4 more)

### Community 35 - "전환 리포트 초기 (2016~2017)"
Cohesion: 0.22
Nodes (11): 2016-06 모든 Stat Report에 PC Mobile Type 필드 추가, 2016-07 AD_CONVERSION_DETAIL 제공기간 7일→30일, AD_CONVERSION_DETAIL 보고서, Stat Report (대용량 보고서), 2017-01 AD_CONVERSION_DETAIL 제공기간 30일→45일, 2017-03 Master/Stat Report zip 압축 다운로드 지원, 2017-06 생성 30일 지난 보고서 파일 자동 삭제, 2017-08 브랜드검색 전환 지표 제공 (+3 more)

### Community 36 - "키워드 플러스·예상 실적 bulk"
Cohesion: 0.20
Nodes (11): 2016-07 /estimate/performance-bulk 추가 (최대 200개), /estimate/performance-bulk, keywordplus (요청 파라미터), useKeywordPlus, 2017-09 EXPKEYWORD 보고서 컨텐츠 네트워크 문맥매칭 지표 제공 중단, 2017-03~06 AD_DETAIL 제공기간 7→14→21→30일 확장, AD_DETAIL 보고서, EXPKEYWORD (키워드확장/키워드플러스 보고서) (+3 more)

### Community 37 - "네이버페이 전환·검색어 보고서"
Cohesion: 0.22
Nodes (11): 2022-04-27 네이버페이 전환 보고서 반영 시점 정정(08시→16시), 2022-04-28 네이버페이 전환 보고서 검색어 항목 추가, 2022-06-03 쇼핑 검색어 보고서 검색어 제공 매체 확대, 2022-10-26 STAT-REPORT 에러코드 변경(11001→10004), NAVERPAY_CONVERSION 네이버페이 전환 보고서, 파워컨텐츠, Search keyword (검색어) 필드, 쇼핑검색광고 (+3 more)

### Community 38 - "/stats 조회 규칙 변천"
Cohesion: 0.24
Nodes (10): GET /stats, 2017-05 /stats nccAdExtensionId 지표 조회 추가, 2017-07 브랜드검색 소재 상세 항목 통계 (eventCode breakdown), 2017-11 STAT 브랜드검색 breakdown 90일 확장 및 ids 동일 캠페인 유형 제약, 브랜드검색, 에러 11003 (ids 혼합 캠페인 유형), breakdown=eventCode (브랜드검색 소재 상세), 2021-03 STAT 성별/연령 breakdown(쇼핑 한정) 및 topImpRto 지표 추가 (+2 more)

### Community 39 - "쇼핑 전환목표 자동입찰"
Cohesion: 0.20
Nodes (10): autobidBidGoal (NONE/MAX_CONV_VALUE), autobidBidStrategy (NO_CAP 고정), autobidStrategy (자동입찰 전략 객체), autobidTargetType (GRP 고정), isAutobidActive, /ncc/adgroups (광고그룹 생성·수정 API), nccAutobidStrategyId, 쇼핑검색광고 전환목표 자동입찰(Beta) 오픈 (2025-10-15) (+2 more)

### Community 40 - "기간 필드 검증·톡톡상담"
Cohesion: 0.27
Nodes (10): Campaign/AdExtension 기간 필드 검증 강화 (2026-06-10), /ncc/ad-extensions (확장소재 API), /ncc/campaigns (Campaign API), periodStartDt / periodEndDt (노출 기간), talkAccountId (톡톡상담 필수 필드), TALKTALK_CONSULTATION (톡톡상담 확장소재), 사이트검색광고 '톡톡상담' 확장소재 등록 지원 (2026-06-04), PERIOD_TARGET (+2 more)

### Community 41 - "타기팅 리포트 (CRITERION)"
Cohesion: 0.28
Nodes (9): CRITERION_CONVERSION 타게팅 전환 보고서, Criterion id (ownerId~dictionaryCode), CRITERION 타게팅 성과 보고서, 2022-04-19 Stat API에 Criterion id 조회 추가, 2022-07-21 타게팅 신규 대용량 보고서 추가, Stat API (/stats), CRITERION_CONVERSION 타게팅 전환 보고서, CRITERION 타게팅 성과 보고서 (+1 more)

### Community 42 - "이용자 세그먼트·쇼핑 지역 타기팅"
Cohesion: 0.33
Nodes (9): 이용자 세그먼트 / 잠재고객타게팅 (AUDIENCE='AD', Beta), Criterion 광고 객체, DictionaryType (+AUDIENCE 'AD'), PUT /ncc/criterion/{ownerId}/negative, PUT /ncc/criterion/{adgroupId}/{dictionaryType}, 2023-08-23 파워링크 이용자 세그먼트(잠재고객) 타겟팅 Beta 추가, 2023-10-18 쇼핑검색 광고그룹 지역 타겟팅 추가, 파워링크 (+1 more)

### Community 43 - "리포트·마스터 이름 변경 (2023)"
Cohesion: 0.36
Nodes (8): Criterion Master (Criterion), 2023-07-09 STAT-REPORT·MASTER 보고서 이름 변경(코드 유지), 2023-11-13 검색어 제공 대용량 보고서 지표 제공 매체 통합 수정, MASTER-REPORT 마스터 보고서, NAVERPAY_CONVERSION 네이버페이 전환 보고서, Shopping shopping mall product Master (ShoppingProduct), SHOPPINGKEYWORD_CONVERSION_DETAIL 쇼핑 검색어 전환 상세 보고서, SHOPPINGKEYWORD_DETAIL 쇼핑 검색어 성과 상세 보고서

### Community 44 - "관리 키워드 초기 필드"
Cohesion: 0.48
Nodes (7): 2016-06 ManagedKeyword is* 필드 boolean 변경, isBrand, isShoppingMall, ManagedKeyword, 2017-02 AdKeyword managedKeyword 제거, pCPLMaxDepth→PCPLMaxDepth, isShoppingMall 제거·expUiType 추가, expUiType (SHOPPING_MALL), 2019-01 ManagedKeyword isBrand 응답 속성 삭제

### Community 45 - "API 도메인 이전"
Cohesion: 0.38
Nodes (7): api.naver.com (구 도메인), api.searchad.naver.com (신규 도메인), 2022-09-20 API 접속 도메인 변경 공지, 2022-12-22 api.searchad.naver.com 정식 서비스 시작, api.naver.com (구 도메인), api.searchad.naver.com (신규 도메인), 2023-03-22 api.naver.com 서비스 종료

### Community 46 - "스마트블록 매체"
Cohesion: 0.33
Nodes (6): 2022-12-12 매체명 변경(함께 찾은 파워링크→스마트블록), 매체 마스터 (Media), 파워링크, 네이버 통합검색 파워링크 스마트블록 매체(447344/447349), 파워링크 (WEB_SITE 광고그룹), 스마트블록 매체 (media_id 447344, 447349)

### Community 47 - "파워링크 최적화 지표 (연관·클릭 기대)"
Cohesion: 0.47
Nodes (6): adRelevanceScore (광고 연관 지수), bidAmt, expectedClickScore (클릭 기대 지수), Keyword 응답 객체 (파워링크), 파워링크 '최적화 신규 지표' Keyword 응답 필드 추가 (2025-12-11), 파워링크

### Community 48 - "최소 노출 입찰가 (period)"
Cohesion: 0.50
Nodes (5): 2016-05 first-page-bid → exposure-minimum-bid URI 이동 및 period 필수화, /estimate/exposure-minimum-bid, /estimate/first-page-bid, /estimate/median-bid, period 파라미터 (DAY/MONTH)

### Community 49 - "키워드 확장 Beta"
Cohesion: 0.40
Nodes (5): /ncc/adgroups/{adgroupId}/restricted-keywords (제외 검색어), keywordPlusWeight (1~999999 %), /ncc/adgroups/{adgroupId}/restricted-keywords (KEYWORD_PLUS_RESTRICT), useKeywordPlus, 키워드 확장 Beta (useKeywordPlus, keywordPlusWeight)

### Community 50 - "관리 키워드 API"
Cohesion: 0.70
Nodes (5): 관리 키워드 API (ManagedKeyword), GET /api/ncc/managedKeyword{?keywords} (list by keywords), ManagedKeywordRequest 정의, ManagedKeywordResponse 정의, POST /api/ncc/managedKeyword (list by keywords POST)

### Community 51 - "키워드 도구 호출 제한 (429)"
Cohesion: 0.67
Nodes (4): 2020-09-10 RelKwdStat 과도 요청으로 API 응답 지연 및 요청 제한, 2020-12 키워드 도구 429 에러 가이드 (호출속도 1/5~1/6, IP당 제한), HTTP 429 Too Many Requests, 키워드 도구 (RelKwdStat)

### Community 52 - "관리 키워드 필드 삭제"
Cohesion: 1.00
Nodes (3): 2023-09-13 ManagedKeyword PCPLMaxDepth 제거, ManagedKeyword API, PCPLMaxDepth 필드

## Knowledge Gaps
- **194 isolated node(s):** `네이버 검색광고 API 릴리스 노트 2016`, `/estimate/first-page-bid`, `/estimate/median-bid`, `2016-05 SeasonalEvent 마스터 보고서 추가`, `2016-05 Adgroup 마스터 9번 필드 PC 네트워크 입찰 가중치로 변경` (+189 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 201 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `네이버 검색광고 API 종합 (기획 문서)` connect `호출 제한·점검·키워드 도구 오류` to `광고그룹·입찰·예산 오류 코드`, `소재·확장소재·공통 오류 코드`, `예상 실적·입찰가 API`, `성과 통계 지표 (/stats)`, `마스터 리포트 API`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Adgroup 정의` (e.g. with `광고그룹 오류 3701~3732` and `광고그룹 전략 없음 3001~3005`) actually correct?**
  _`Adgroup 정의` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `네이버 검색광고 API 릴리스 노트 2016`, `/estimate/first-page-bid`, `/estimate/median-bid` to the rest of the system?**
  _194 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `광고그룹·입찰·예산 오류 코드` be split into smaller, more focused modules?**
  _Cohesion score 0.06187202538339503 - nodes in this community are weakly interconnected._
- **Why does `네이버 검색광고 API 오류 코드표` connect `호출 제한·점검·키워드 도구 오류` to `광고그룹·입찰·예산 오류 코드`, `소재·확장소재·공통 오류 코드`, `비즈채널 API와 오류`, `캠페인 API와 오류`, `예상 실적·입찰가 API`, `마스터 리포트 API`, `키워드 API와 오류`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `Campaign 정의` (e.g. with `캠페인 오류 3501~3506` and `MasterReportJob 정의`) actually correct?**
  _`Campaign 정의` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Should `소재·반응형 소재·전환 리포트` be split into smaller, more focused modules?**
  _Cohesion score 0.07474600870827286 - nodes in this community are weakly interconnected._