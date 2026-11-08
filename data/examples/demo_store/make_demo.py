"""시연용 가상 데이터: 스마트스토어 예시 2개, 각 3개월 (2026-08 ~ 2026-10). 10월 한 달만 광고.

실행: .venv/bin/python data/examples/demo_store/make_demo.py   (시드 고정 → 늘 같은 파일)
예시별 폴더 (모두 가짜, 실제 가게·사람과 무관):
- coffee/   예시 1 원두 로스터리 (코치 결론 '준비가 먼저'): 광고 성과가 가정 수준
- protein/  예시 2 단백질 쉐이크 정기구매 (코치 결론 '해 볼 만해요'): 광고 성과가 가정보다 좋아 한 달 뒤 '계속'
폴더마다 만드는 파일:
- orders.csv        커머스API '상품 주문 정보 구조체' 항목 이름 (커머스API_주문데이터_매핑.md). 개인정보 항목 없음, 주문자는 가짜 번호
- store_stats.csv   10월 일별 유입수·상품상세조회수·장바구니수·결제수·결제금액 (스마트스토어 통계처럼, 코치 '판매처 통계 파일')
- naver_report.csv  네이버 검색광고 다차원 보고서 항목 이름 (△ 공식 양식 미확인), 10월 일별
- meta_report.csv   메타 광고 관리자 한국어 내보내기 열 이름 (✅ 실제 내보내기 열, 숫자는 가상), 10월 일별
- plan.json         코치 계획 파일 (10월 1일 시작, 예측값은 코치 계산과 같은 수준)
재구매: 두 예시 모두 '매달(정기)' 프리셋(1년 6번)에 맞춰, 산 적 있는 손님이 하루 6/365 확률로 다시 삼.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
SEED = 20261109
DAYS = pd.date_range("2026-08-01", "2026-10-31", freq="D")
AD_DAYS = pd.date_range("2026-10-01", "2026-10-31", freq="D")
REPEATS_PER_YEAR = 6.0          # '매달(정기)' 프리셋

EXAMPLES = {
    "coffee": dict(
        products=[("1001", "싱글오리진 원두 200g", 20_000), ("1002", "하우스 블렌드 원두 500g", 20_000)],
        price=20_000, profit=7_000, budget_max=300_000, keyword="원두커피", organic_new=1.2,
        naver=68_000, meta=142_000, naver_cpc=1_900, meta_cpc=1_300, cvr=0.015,
        naver_tracking=True,
        meta_overcount=0.7,              # 메타가 자기 광고 주문 1건마다 0.7건을 더 셈(조회 후 구매·다른 경로 구매) → 과대 집계
        meta_reach=(900, 1_400), meta_freq=(2.6, 3.4), coupon_share=0.6,
        prediction=dict(budget=210_000, naver=68_000, meta=142_000, clicks=145.0, cpc=1_450.0, new=1.4, cvr=0.0126,
                        wins=0, p10=-190_000, p90=-110_000),
        campaign=("원두_쇼핑검색", "원두커피_상품", "원두_판매_10월"),
    ),
    "protein": dict(
        products=[("2001", "단백질 쉐이크 초코 2kg (한 달분)", 79_000), ("2002", "단백질 쉐이크 곡물 2kg (한 달분)", 79_000)],
        price=79_000, profit=39_500, budget_max=500_000, keyword="프로틴쉐이크", organic_new=0.6,
        naver=120_600, meta=379_400, naver_cpc=1_450, meta_cpc=1_300, cvr=0.05,   # 실제 광고 성과가 가정(1.26%)보다 좋음
        naver_tracking=True, meta_overcount=0.6,
        meta_reach=(1_800, 2_600), meta_freq=(1.6, 2.2), coupon_share=0.9,
        prediction=dict(budget=500_000, naver=120_600, meta=379_400, clicks=375.0, cpc=1_333.0, new=4.2, cvr=0.0126,
                        wins=85, p10=-63_000, p90=1_010_000),
        campaign=("프로틴_파워링크", "프로틴쉐이크_상품", "프로틴_판매_10월"),
    ),
}


def make(name: str, cfg: dict, rng: np.random.Generator):
    out = OUT / name
    out.mkdir(exist_ok=True)
    buyers, orders, stats, naver_rows, meta_rows = [], [], [], [], []
    oid = {"coffee": 2026080100000, "protein": 2026080200000}[name]
    p_repeat = REPEATS_PER_YEAR / 365
    naver_daily, meta_daily = cfg["naver"] / len(AD_DAYS), cfg["meta"] / len(AD_DAYS)
    # 광고 달의 클릭은 매일 무작위, 광고 주문·메타 리포트 전환 '합계'는 정해진 비율로 (시연 숫자가 늘 같은 이야기를 하게)
    n_clicks = rng.poisson(naver_daily / cfg["naver_cpc"], len(AD_DAYS))
    m_clicks = rng.poisson(meta_daily / cfg["meta_cpc"], len(AD_DAYS))

    def spread(total: int, weights) -> np.ndarray:
        w = np.asarray(weights, dtype=float)
        days = rng.choice(len(w), size=total, p=w / w.sum()) if total and w.sum() else []
        return np.bincount(np.asarray(days, dtype=int), minlength=len(w))

    n_buys = spread(int(round(n_clicks.sum() * cfg["cvr"])), n_clicks)
    m_buys = spread(int(round(m_clicks.sum() * cfg["cvr"])), m_clicks)
    m_results = m_buys + spread(int(round(m_buys.sum() * cfg["meta_overcount"])), np.maximum(m_clicks, 1))
    for day in DAYS:
        ad = day in AD_DAYS
        i = AD_DAYS.get_loc(day) if ad else None
        n_clk, m_clk = (int(n_clicks[i]), int(m_clicks[i])) if ad else (0, 0)
        n_buy, m_buy = (int(n_buys[i]), int(m_buys[i])) if ad else (0, 0)
        repeat = rng.binomial(len(buyers), p_repeat) if buyers else 0
        sources = (["organic"] * rng.poisson(cfg["organic_new"]) + ["repeat"] * repeat
                   + ["naver"] * n_buy + ["meta"] * m_buy)
        day_orders = 0
        for src in sources:
            if src == "repeat":
                cid = buyers[rng.integers(0, len(buyers))]
            else:
                cid = f"DEMO{name[0].upper()}{len(buyers) + 1:05d}"
                buyers.append(cid)
            pid, pname, price = cfg["products"][rng.integers(0, len(cfg["products"]))]
            qty = 1 if rng.random() < 0.9 else 2
            coupon = f"{rng.integers(10**9, 10**10)}" if src in ("naver", "meta") and rng.random() < cfg["coupon_share"] else ""
            discount = round(price * 0.05) * qty if coupon else 0
            inflow, inflow_add = {"organic": (rng.choice(["네이버 쇼핑", "네이버 쇼핑 외"], p=[0.7, 0.3]), ""),
                                  "repeat": ("네이버 쇼핑", ""),
                                  "naver": ("검색광고(SA)", cfg["keyword"]),
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
        if not ad:
            continue
        visits = int(max(day_orders, 1) / 0.03) + n_clk + m_clk + int(rng.integers(0, 15))
        views = int(visits * rng.uniform(0.55, 0.7))
        stats.append({"날짜": day.strftime("%Y-%m-%d"), "유입수": visits, "상품상세조회수": views,
                      "장바구니수": max(int(views * rng.uniform(0.07, 0.11)), day_orders), "결제수": day_orders,
                      "결제금액": day_orders * cfg["price"]})
        n_imp = int(n_clk / rng.uniform(0.008, 0.014)) if n_clk else int(rng.integers(150, 400))
        n_conv = n_buy if cfg["naver_tracking"] else 0
        naver_rows.append({"일자": day.strftime("%Y.%m.%d."), "캠페인": cfg["campaign"][0], "광고그룹": cfg["campaign"][1],
                           "키워드": cfg["keyword"], "노출수": n_imp, "클릭수": n_clk,
                           "클릭률(%)": round(100 * n_clk / n_imp, 2) if n_imp else 0,
                           "평균클릭비용(VAT포함,원)": cfg["naver_cpc"] if n_clk else 0, "총비용(VAT포함,원)": n_clk * cfg["naver_cpc"],
                           "전환수": n_conv, "전환매출액(원)": n_conv * cfg["price"]})
        reach = int(rng.integers(*cfg["meta_reach"]))
        m_imp = int(reach * rng.uniform(*cfg["meta_freq"]))
        results = int(m_results[i])
        spend = m_clk * cfg["meta_cpc"]
        meta_rows.append({
            "보고 시작": day.strftime("%Y-%m-%d"), "보고 종료": day.strftime("%Y-%m-%d"), "캠페인 이름": cfg["campaign"][2],
            "캠페인 게재": "active", "기여 설정": "클릭 후 7일, 조회 후 1일 또는 참여한 조회 후 1일", "결과": results,
            "결과 표시 도구": "actions:offsite_conversion.fb_pixel_purchase", "도달": reach, "빈도": round(m_imp / reach, 2),
            "결과당 비용": round(spend / results) if results else "", "광고 세트 예산": round(meta_daily), "광고 세트 예산 유형": "일일",
            "지출 금액 (KRW)": spend, "종료": "진행 중", "노출": m_imp,
            "CPM(1,000회 노출당 비용) (KRW)": round(1000 * spend / m_imp, 1), "링크 클릭": m_clk, "shop_clicks": "",
            "CPC(링크 클릭당 비용) (KRW)": cfg["meta_cpc"] if m_clk else "", "CTR(링크 클릭률)": round(100 * m_clk / m_imp, 2),
            "클릭(전체)": int(m_clk * 1.6), "CTR(전체)": round(160 * m_clk / m_imp, 2), "CPC(전체) (KRW)": round(spend / max(m_clk * 1.6, 1)),
            "랜딩 페이지 조회": int(m_clk * 0.8), "랜딩 페이지 조회당 비용 (KRW)": round(spend / max(m_clk * 0.8, 1)),
            "결과(초기)": results, "결과(초기) 표시 도구": "actions:offsite_conversion.fb_pixel_purchase",
        })
    pd.DataFrame(orders).to_csv(out / "orders.csv", index=False)
    pd.DataFrame(stats).to_csv(out / "store_stats.csv", index=False)
    pd.DataFrame(naver_rows).to_csv(out / "naver_report.csv", index=False)
    pd.DataFrame(meta_rows).to_csv(out / "meta_report.csv", index=False)
    plan = {"version": 1, "started": "2026-10-01",
            "inputs": {"q_category": "식품", "q_stores": ["스마트스토어"], "q_price": cfg["price"], "q_profit": cfg["profit"],
                       "q_repurchase": "매달(정기)", "q_budget": cfg["budget_max"], "q_keyword": cfg["keyword"],
                       "q_budget_pick": "recommended"},
            "prediction": {k: float(v) for k, v in cfg["prediction"].items()}}
    (out / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    o = pd.DataFrame(orders)
    oct_ad = o[o["order.paymentDate"].str.startswith("2026-10") & (o["productOrder.productOrderStatus"] != "CANCELED")
               & ((o["productOrder.inflowPath"] == "검색광고(SA)") | (o["productOrder.inflowPathAdd"] == "meta_paid_social"))]
    per_buyer = o.groupby("order.ordererNo").size()
    summary = {
        "spend": int(sum(r["총비용(VAT포함,원)"] for r in naver_rows) + sum(r["지출 금액 (KRW)"] for r in meta_rows)),
        "clicks": int(sum(r["클릭수"] for r in naver_rows) + sum(r["링크 클릭"] for r in meta_rows)),
        "ad_orders": int(len(oct_ad)), "coupon_orders": int((oct_ad["productOrder.appliedCoupons.couponPublishNumber"].fillna("") != "").sum()),
        "report_conversions": int(sum(r["전환수"] for r in naver_rows) + sum(r["결과"] for r in meta_rows)),
        "orders_total": int(len(o)), "repeat_share": round(float((per_buyer > 1).mean()), 3),
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def main():
    rng = np.random.default_rng(SEED)
    for name, cfg in EXAMPLES.items():
        print(name, make(name, cfg, rng))


if __name__ == "__main__":
    main()
