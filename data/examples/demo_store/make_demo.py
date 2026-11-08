"""시연용 가상 데이터: 스마트스토어 원두 로스터리 3개월 (2026-08 ~ 2026-10).

실행: .venv/bin/python data/examples/demo_store/make_demo.py   (시드 고정 → 늘 같은 파일)
만드는 파일 (모두 가짜, 실제 가게·사람과 무관):
- orders.csv        커머스API '상품 주문 정보 구조체' 항목 이름 (커머스API_주문데이터_매핑.md). 개인정보 항목 없음, 주문자는 가짜 번호
- store_stats.csv   스마트스토어 통계처럼 일별 유입·상세 조회·장바구니·결제 (코치 '한 달 뒤'의 판매처 통계 파일)
- naver_report.csv  네이버 검색광고 다차원 보고서 항목 이름 (△ 공식 양식 미확인), 10월 일별
- meta_report.csv   메타 광고 관리자 한국어 내보내기 열 이름 (✅ 실제 내보내기 열), 10월 일별
- plan.json         코치 계획 파일 (원두 예시, 권장 예산 21만 원, 10월 1일 시작)

가정 (README에 같은 내용):
- 판매가 2만 원, 남는 돈 7천 원(마진 35%). 광고 없이 하루 평균 3.5건, 재구매 손님 비율 약 25%
- 10월에 권장 예산 21만 원: 네이버 6.8만 · 메타 14.2만 (코치 배분 그대로)
- 네이버 클릭 1번 약 1,900원, 메타 약 1,300원 (코치 가정과 같은 수준)
- 광고로 온 손님 중 산 비율 약 1.3% (GA4 공개 샘플 수준), 메타 리포트는 조회 후 구매까지 세서 실제보다 많게 잡힘
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
SEED = 20261109
PRICE, PROFIT = 20_000, 7_000
DAYS = pd.date_range("2026-08-01", "2026-10-31", freq="D")
AD_DAYS = pd.date_range("2026-10-01", "2026-10-31", freq="D")
NAVER_MONTH, META_MONTH = 68_000, 142_000
NAVER_CPC, META_CPC, AD_CVR = 1_900, 1_300, 0.013
PRODUCTS = [("1001", "싱글오리진 원두 200g", 20_000), ("1002", "하우스 블렌드 원두 500g", 20_000)]


def main():
    rng = np.random.default_rng(SEED)
    customers, orders, stats = [], [], []
    oid = 2026080100000

    def new_customer():
        cid = f"DEMO{len(customers) + 1:05d}"
        customers.append(cid)
        return cid

    naver_daily = NAVER_MONTH / len(AD_DAYS)
    meta_daily = META_MONTH / len(AD_DAYS)
    naver_rows, meta_rows = [], []
    for day in DAYS:
        ad = day in AD_DAYS
        organic = rng.poisson(3.5)
        n_clk = rng.poisson(naver_daily / NAVER_CPC) if ad else 0
        m_clk = rng.poisson(meta_daily / META_CPC) if ad else 0
        n_buy = rng.binomial(n_clk, AD_CVR) if n_clk else 0
        m_buy = rng.binomial(m_clk, AD_CVR) if m_clk else 0
        visits = int(organic / 0.03) + n_clk + m_clk + rng.integers(0, 15)
        day_orders = 0
        for src, k in (("organic", organic), ("naver", n_buy), ("meta", m_buy)):
            for _ in range(k):
                repeat = src == "organic" and customers and rng.random() < 0.25
                cid = rng.choice(customers) if repeat else new_customer()
                pid, pname, price = PRODUCTS[rng.integers(0, len(PRODUCTS))]
                qty = 1 if rng.random() < 0.85 else 2
                coupon = f"{rng.integers(10**9, 10**10)}" if src == "meta" and rng.random() < 0.6 else ""
                discount = 2_000 * qty if coupon else 0
                inflow, inflow_add = {"organic": (rng.choice(["네이버 쇼핑", "네이버 쇼핑 외"], p=[0.7, 0.3]), ""),
                                      "naver": ("검색광고(SA)", "원두커피"),
                                      "meta": ("네이버 쇼핑 외", "meta_paid_social")}[src]
                status = "CANCELED" if rng.random() < 0.03 else rng.choice(["PURCHASE_DECIDED", "DELIVERED"], p=[0.8, 0.2])
                oid += 1
                pay_time = day + pd.Timedelta(minutes=int(rng.integers(8 * 60, 23 * 60)))
                orders.append({
                    "order.orderId": str(oid), "order.ordererNo": cid, "order.paymentDate": pay_time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
                    "productOrder.productOrderId": f"{oid}01", "productOrder.productId": pid, "productOrder.productName": pname,
                    "productOrder.unitPrice": price, "productOrder.quantity": qty,
                    "productOrder.totalProductAmount": price * qty, "productOrder.totalPaymentAmount": price * qty - discount,
                    "productOrder.productOrderStatus": status, "productOrder.inflowPath": inflow,
                    "productOrder.inflowPathAdd": inflow_add, "productOrder.appliedCoupons.couponPublishNumber": coupon,
                })
                if status != "CANCELED":
                    day_orders += 1
        views = int(visits * rng.uniform(0.55, 0.7))
        cart = int(views * rng.uniform(0.07, 0.11))
        stats.append({"날짜": day.strftime("%Y-%m-%d"), "유입수": visits, "상품상세조회수": views, "장바구니수": max(cart, day_orders),
                      "결제수": day_orders, "결제금액": day_orders * PRICE})
        if ad:
            n_imp = int(n_clk / rng.uniform(0.008, 0.014)) if n_clk else int(rng.integers(150, 400))
            naver_rows.append({"일자": day.strftime("%Y.%m.%d."), "캠페인": "원두_쇼핑검색", "광고그룹": "원두커피_상품", "키워드": "원두커피",
                               "노출수": n_imp, "클릭수": n_clk, "클릭률(%)": round(100 * n_clk / n_imp, 2) if n_imp else 0,
                               "평균클릭비용(VAT포함,원)": NAVER_CPC if n_clk else 0, "총비용(VAT포함,원)": n_clk * NAVER_CPC,
                               "전환수": n_buy, "전환매출액(원)": n_buy * PRICE})
            reach = int(rng.integers(900, 1_400))
            m_imp = int(reach * rng.uniform(2.6, 3.4))
            results = m_buy + rng.binomial(2, 0.25)          # 조회 후 구매·다른 경로 구매까지 세서 많게 잡힘
            spend = m_clk * META_CPC
            meta_rows.append({
                "보고 시작": day.strftime("%Y-%m-%d"), "보고 종료": day.strftime("%Y-%m-%d"), "캠페인 이름": "원두_판매_10월", "캠페인 게재": "active",
                "기여 설정": "클릭 후 7일 또는 조회 후 1일", "결과": results, "결과 표시 도구": "actions:offsite_conversion.fb_pixel_purchase",
                "도달": reach, "빈도": round(m_imp / reach, 2), "결과당 비용": round(spend / results) if results else "",
                "광고 세트 예산": 4_600, "광고 세트 예산 유형": "일일", "지출 금액 (KRW)": spend, "종료": "진행 중", "노출": m_imp,
                "CPM(1,000회 노출당 비용) (KRW)": round(1000 * spend / m_imp, 1), "링크 클릭": m_clk, "shop_clicks": "",
                "CPC(링크 클릭당 비용) (KRW)": META_CPC if m_clk else "", "CTR(링크 클릭률)": round(100 * m_clk / m_imp, 2),
                "클릭(전체)": int(m_clk * 1.6), "CTR(전체)": round(160 * m_clk / m_imp, 2), "CPC(전체) (KRW)": round(spend / max(m_clk * 1.6, 1)),
                "랜딩 페이지 조회": int(m_clk * 0.8), "랜딩 페이지 조회당 비용 (KRW)": round(spend / max(m_clk * 0.8, 1)),
                "결과(초기)": results, "결과(초기) 표시 도구": "actions:offsite_conversion.fb_pixel_purchase",
            })
    pd.DataFrame(orders).to_csv(OUT / "orders.csv", index=False)
    pd.DataFrame(stats).to_csv(OUT / "store_stats.csv", index=False)
    pd.DataFrame(naver_rows).to_csv(OUT / "naver_report.csv", index=False)
    pd.DataFrame(meta_rows).to_csv(OUT / "meta_report.csv", index=False)
    plan = {"version": 1, "started": "2026-10-01",
            "inputs": {"q_category": "식품", "q_stores": ["스마트스토어"], "q_price": PRICE, "q_profit": PROFIT, "q_repurchase": "가끔",
                       "q_budget": 300_000, "q_keyword": "원두커피", "q_budget_pick": "recommended"},
            "prediction": {"budget": 210_000.0, "naver": float(NAVER_MONTH), "meta": float(META_MONTH),
                           "clicks": round(NAVER_MONTH / NAVER_CPC + META_MONTH / META_CPC, 1), "cpc": 1_500.0,
                           "new": round((NAVER_MONTH / NAVER_CPC + META_MONTH / META_CPC) * 0.0126, 2), "cvr": 0.0126,
                           "wins": 0.0, "p10": -202_000.0, "p90": -179_000.0}}
    (OUT / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    ad_orders = [o for o in orders if o["productOrder.inflowPath"] == "검색광고(SA)" or o["productOrder.inflowPathAdd"] == "meta_paid_social"]
    print(f"주문 {len(orders)}건 (광고 {len(ad_orders)}건), 네이버 클릭 {sum(r['클릭수'] for r in naver_rows)}, "
          f"메타 클릭 {sum(r['링크 클릭'] for r in meta_rows)}, 메타 결과 {sum(r['결과'] for r in meta_rows)}, "
          f"네이버 전환 {sum(r['전환수'] for r in naver_rows)}")


if __name__ == "__main__":
    main()
