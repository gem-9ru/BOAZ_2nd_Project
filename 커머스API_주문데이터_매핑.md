# 스마트스토어 커머스API 주문 데이터 → 우리 엔진 매핑

> 작성 2026-11-06 · 근거: 커머스API 공식 문서 v2.91.0 (2026-10-28) "주문 > 주문 조회 > **상품 주문 정보 구조체**" 본문 ✅
> - 출처: https://apicenter.commerce.naver.com/docs/commerce-api/current/schemas/상품-주문-정보-구조체
> - 조회 API: `GET /v1/pay-order/seller/product-orders` (조건형 상품 주문 상세 내역 조회) ✅
> - 목적: API를 실제로 발급받지 않아도, 스마트스토어 주문 데이터가 **어떤 항목으로 오는지** 알고 우리 업로드 양식과 엔진 입력을 그 구조에 맞춥니다.

---

## 1. 구조 요약

응답의 `data[]` 한 개 = **상품 주문 1건**(상품주문번호 1개). 그 안이 두 덩어리로 나뉩니다.
- `order`: 주문 전체 단위 (주문번호, 주문자, 결제 일시·수단)
- `productOrder`: 상품 주문 단위 (상품, 수량, 금액, 상태, 클레임, **유입 경로**, 쿠폰, 수수료, 배송지)

## 2. 우리가 쓰는 항목 (✅ 문서 본문 확인)

| 커머스API 항목 | 뜻 (문서 표현) | 우리 엔진에서 | 밸류체인 |
|---|---|---|---|
| `order.orderId` / `productOrder.productOrderId` | 주문 번호 / 상품 주문 번호 | 거래 ID (중복 제거) | ④ |
| `order.ordererNo` | 주문자 번호 | **고객 ID** (해시해서 저장) → 첫 구매·재구매 구분 | ④⑤ |
| `order.paymentDate` | 결제 일시(최종 결제) | 주문일 → 월 코호트 | ④⑤ |
| `productOrder.inflowPath` | **유입 경로(검색광고(SA)/공동구매/밴드/네이버 쇼핑/네이버 쇼핑 외)** | **첫 구매 채널** → 채널별 재구매 배수(`retention_mult`) | ①②→④ |
| `productOrder.inflowPathAdd` | 유입 경로 추가 정보 | 채널 세부 (확인 필요) | — |
| `productOrder.appliedCoupons[].couponPublishNumber` | 쿠폰 발행 번호 | 쿠폰으로 팔린 수 (코치 판매 수 출처 1순위) | ④ |
| `productOrder.totalPaymentAmount` | 최초 결제 금액(할인 적용 후) | 순매출, 객단가 | 돈 축 |
| `productOrder.totalProductAmount` | 최초 주문 금액(할인 적용 전) | 할인율 = 1 − 결제 ÷ 주문 금액 (혜택비) | 돈 축 |
| `productOrder.unitPrice`, `quantity` | 상품 가격, 수량 | 판매가 | 돈 축 |
| `productOrder.expectedSettlementAmount` | 정산 예정 금액 | **실제 남는 돈 계산의 시작점** | 돈 축 |
| `paymentCommission`, `knowledgeShoppingSellingInterlockCommission`, `channelCommission` | 결제 수수료, 네이버 쇼핑 매출 연동 수수료, 채널 수수료 | 판매처 수수료 (코치 "남는 돈"의 근거) | 돈 축 |
| `productOrder.productOrderStatus` | 상품 주문 상태 (`PAYED`, `DELIVERED`, `PURCHASE_DECIDED`, `CANCELED`, `RETURNED` 등) | 취소·반품 빼고 **순매출** | ④ |
| `productOrder.claimType` / `claimStatus` | 취소·반품·교환 구분과 상태 | 반품률 | ④ |
| `productOrder.decisionDate` | 구매 확정일 | 확정 매출 기준일 | ④ |
| `productOrder.productId`, `productName` | 채널 상품 번호, 상품명 | 상품별 분석 | — |

## 3. 쓰지 않는 항목 (개인정보 — 받지도 저장하지도 않음)

`ordererName`, `ordererTel`, `ordererId`, `shippingAddress`(이름·주소·연락처·위경도), `pickupLocationContent`, `entryMethodContent` 등.
- 고객 구분은 `ordererNo`를 **해시**해서만 씁니다.
- 원본 주문 파일은 git에 올리지 않습니다.

## 4. 이 구조로 할 수 있는 것

1. **재구매를 실제로 잽니다(⑤).** `ordererNo` + `paymentDate`로 첫 구매 월 코호트별 재구매율을 계산합니다. 코치의 재구매 가정값(0 / 0.5 / 2회)과 1년 손익분기를 우리 가게 숫자로 바꿉니다. 지금 가장 약한 근거입니다.
2. **UTM 없이도 첫 구매 채널을 압니다.** `inflowPath`가 검색광고(SA), 공동구매, 밴드, 네이버 쇼핑, 그 밖을 구분합니다. 그래서 스마트스토어 판매자는 **채널별 재구매 차이**를 바로 볼 수 있습니다.
   - 한계: 메타·인스타 광고는 "네이버 쇼핑 외"로 뭉칩니다. 그래서 NT 꼬리표와 쿠폰이 여전히 필요합니다.
3. **"1개 팔면 남는 돈"을 실측합니다.** 정산 예정 금액과 수수료 항목으로 판매처 수수료를 뺀 금액을 구할 수 있습니다. 원가·배송비는 사장님이 입력합니다.
4. **순매출과 반품률**: 주문 상태와 클레임으로 취소·반품을 빼서 계산합니다.

## 5. 제안: API 발급 전에 할 수 있는 것

| 단계 | 내용 |
|---|---|
| A | **주문 업로드 양식을 이 구조에 맞춤**: 조사/00 7장의 "(3) 주문" 양식 열 이름을 위 항목에 대응시킨 표를 앱에 내장. 사장님이 스마트스토어에서 받은 주문 파일(또는 API 결과)을 그대로 올리면 자동 매핑 |
| B | **이 구조를 따르는 가상 주문 데이터**를 만들어 시연·테스트에 사용: 재구매·유입 경로·쿠폰·취소가 섞인 3~6개월치 |
| C | 엔진 연결: 주문 → 코호트 리텐션 → `retention_mult`(채널별), 코치의 "가끔" 프리셋 자리에 "내 가게 실측" 선택지 추가 |
| D | 실제 키가 생기면 같은 매핑으로 API 호출만 붙임 (로컬에서 받아 파일로 넘김, IP 허용 문제 때문) |

## 6. 확인하지 못한 것 ❓

- **스마트스토어 판매자센터에서 내려받는 주문 엑셀의 열 이름**이 API 항목과 같은지 (한글 열 이름일 가능성이 큼). A단계에서 짐작 규칙과 사용자 수정 방식(측정 키트의 통계 파일 읽기와 같은 방식)으로 대응합니다.
- `inflowPathAdd`에 실제로 어떤 값이 오는지, NT 꼬리표 값이 주문에 남는지.
- 조회 기간·건수 제한의 세부 (변경 주문 조회는 24시간 범위·최대 300건 ✅, 조건형 조회의 제한은 이 문서에서 확인 안 함).
