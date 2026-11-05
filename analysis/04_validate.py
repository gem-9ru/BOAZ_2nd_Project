"""03_analysis 결과 독립 재계산 (validate-data). 다른 방법으로 같은 숫자를 다시 구한다.

실행: python analysis/04_validate.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data/raw", ROOT / "analysis/out"
checks = []


def check(name, expected, actual, tol=1e-6):
    ok = abs(expected - actual) <= tol * max(1, abs(expected))
    checks.append((name, expected, actual, "OK" if ok else "MISMATCH"))


# ---- Q2: 연령별 CPA를 numpy로 다시 계산
fb = pd.read_csv(RAW / "kaggle_fb/KAG_conversion_data_hf_copy.csv")
for age, exp in [("30-34", 34.430), ("45-49", 104.275)]:
    m = (fb.age.values == age) & (fb.Spent.values > 0)
    check(f"Q2 CPA {age}", exp, fb.Spent.values[m].sum() / fb.Approved_Conversion.values[m].sum(), tol=1e-4)
check("Q2 Spent>0 행 수 = 연령 합계 광고 수", 307 + 211 + 187 + 231, int((fb.Spent > 0).sum()))
check("Q2 Spent=0 광고의 구매 수 (제외해도 되는지)", 0, int(fb.loc[fb.Spent == 0, "Approved_Conversion"].sum()))

# ---- Q3: 퍼널 합계 = 이벤트 파일 사용자 수 (서로 다른 쿼리)
ev = pd.read_csv(RAW / "ga4/ga4_events.csv").set_index("event_name").users
fun = pd.read_csv(RAW / "ga4/ga4_funnel.csv")
for col, e in [("visit_users", "session_start"), ("view_users", "view_item"), ("cart_users", "add_to_cart"),
               ("checkout_users", "begin_checkout"), ("purchase_users", "purchase")]:
    check(f"Q3 {col} 합 = events.{e}", ev[e], fun[col].sum())
check("Q3 전체 사용자 = events 고유 사용자(page_view 근사)", 270154, fun.users.sum())
tx = pd.read_csv(RAW / "ga4/ga4_transactions.csv")
check("Q3 구매 사용자(퍼널) vs 거래 고유 사용자", 4419, tx.user_pseudo_id.nunique(), tol=0.2)
masked = fun[fun.medium.isin(["<Other>", "(data deleted)"])].users.sum() / fun.users.sum()
checks.append(("Q3 마스킹 매체 비중 (참고)", np.nan, round(masked, 3), "INFO"))

# ---- Q4: 고객 1명을 원본 행으로 손계산
u = pd.read_parquet(RAW / "uci/online_retail_II.parquet").drop_duplicates()
u["Invoice"] = u.Invoice.astype(str)
u = u[~u.Invoice.str[0].isin(["C", "A"]) & (u.Quantity > 0) & (u.Price > 0)].dropna(subset=["Customer ID"])
cid = 13047.0
c = u[u["Customer ID"] == cid].copy()
c["amount"] = c.Quantity * c.Price
first_dt = c.InvoiceDate.min()
ltv_hand = c.loc[c.InvoiceDate < first_dt + pd.Timedelta(days=365)].query(
    "StockCode.astype('str').str.upper() not in ['POST','DOT','M','D','C2','BANK CHARGES']", engine="python").amount.sum()
checks.append((f"Q4 고객 {int(cid)} 첫 구매일·12개월 매출 (손계산)", np.nan, f"{first_dt.date()} / £{ltv_hand:,.2f}", "INFO"))
ret = pd.read_csv(OUT / "q4_cohort_retention.csv", index_col=0)
check("Q4 리텐션 값 범위 0~1", 1, int(((ret >= 0) & (ret <= 1)).all().all()))
# 관측 기간: 마지막 코호트(2010-11)의 12개월 차 = 2011-11 (데이터 끝 2011-12-09 이전, 완전한 달)
check("Q4 마지막 코호트 12개월 차 달이 완전한 달", 1, int(pd.Period("2010-11", "M") + 12 <= pd.Period("2011-11", "M")))
# 12월 계절성: 12개월 차 반등이 특정 달에 몰리는지
coh_m = ret.index.astype(str)
checks.append(("Q4 12개월 차 리텐션 코호트별 (계절성 확인)", np.nan, dict(zip(coh_m, ret["12"].round(3))), "INFO"))

# ---- Q1: 표본 크기와 클릭 수
kc = pd.read_csv(OUT / "q1_keyword_curves.csv")
checks.append(("Q1 tier별 키워드 수 / 최대 클릭 30 미만 비율", np.nan,
               kc.groupby("tier").apply(lambda g: f"{len(g)}개 / {(g.max_clicks < 30).mean():.0%}").to_dict(), "INFO"))

for row in checks:
    print(" | ".join(map(str, row)))
