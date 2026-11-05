"""분석 질문 Q1~Q4 (statistical-analysis).

실행: python analysis/03_analysis.py
결과: analysis/out/03_analysis.txt (콘솔 출력), analysis/out/*.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from scipy.optimize import curve_fit
from statsmodels.stats.proportion import proportion_confint, proportions_ztest

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data/raw", ROOT / "analysis/out"
pd.set_option("display.width", 200, "display.max_columns", 30)


def section(title):
    print(f"\n{'=' * 70}\n## {title}\n{'=' * 70}")


# =================================================================== Q1
section("Q1. 네이버: 대표(검색 1만+) vs 세부(검색 300~3천) 키워드의 클릭 단가와 포화")
est = pd.read_csv(OUT / "naver_q1/estimates.csv")


CURVE_KEYS = ["has_clicks", "max_clicks", "min_click_bid", "cpc_at_50pct", "marginal_cpc_50_90", "saturation_ratio"]


def curve_metrics(g):
    g = g.sort_values("bid")
    g = g[g.clicks > 0]
    out = dict.fromkeys(CURVE_KEYS, np.nan)
    out["has_clicks"], out["max_clicks"] = len(g) > 0, (g.clicks.max() if len(g) else 0)
    if len(g) < 2:
        return out
    mx = g.clicks.max()
    at = lambda share: g[g.clicks >= share * mx].iloc[0]
    p50, p90 = at(0.5), at(0.9)
    cpc50 = p50.cost / p50.clicks
    marginal = (p90.cost - p50.cost) / max(p90.clicks - p50.clicks, 1)
    out.update(min_click_bid=g.bid.iloc[0], cpc_at_50pct=cpc50, marginal_cpc_50_90=marginal,
               saturation_ratio=marginal / cpc50)
    return out


kc = pd.DataFrame([{"industry": i, "tier": t, "keyword": k, "qc": q, **curve_metrics(g)}
                   for (i, t, k, q), g in est.groupby(["industry", "tier", "keyword", "qc"])])
print(f"키워드 {kc.keyword.nunique()}개 (업종 4개). 예상 클릭이 한 번도 안 나온 키워드: "
      f"{(~kc.has_clicks.astype(bool)).sum()}개 → {kc[~kc.has_clicks.astype(bool)].groupby('tier').size().to_dict()}")
ok = kc[kc.has_clicks.astype(bool) & kc.cpc_at_50pct.notna()]
summ = ok.groupby("tier")[["cpc_at_50pct", "marginal_cpc_50_90", "saturation_ratio", "max_clicks", "min_click_bid"]].median()
print("\n[중앙값] tier별")
print(summ.round(1))
for m in ["cpc_at_50pct", "saturation_ratio"]:
    a, b = ok[ok.tier == "대표"][m], ok[ok.tier == "세부"][m]
    u = stats.mannwhitneyu(a, b, alternative="two-sided")
    print(f"Mann-Whitney {m}: 대표 n={len(a)} 중앙값={a.median():.1f} / 세부 n={len(b)} 중앙값={b.median():.1f} / p={u.pvalue:.3f}")
by_ind = ok.groupby(["industry", "tier"]).cpc_at_50pct.median().unstack()
print("\n업종별 CPC(최대 클릭의 50% 지점) 중앙값:")
print(by_ind.round(0))
print("세부가 대표보다 CPC가 낮은 업종 수:", int((by_ind["세부"] < by_ind["대표"]).sum()), "/", len(by_ind))
print("\n포화 비율(=50→90% 구간의 한계 CPC ÷ 50% 지점 평균 CPC) 분포:", ok.saturation_ratio.describe().round(2).to_dict())
kc.to_csv(OUT / "q1_keyword_curves.csv", index=False)

# =================================================================== Q2
section("Q2. Kaggle: 타깃(연령·성별)별 구매당 비용(CPA), 캠페인 통제")
fb = pd.read_csv(RAW / "kaggle_fb/KAG_conversion_data_hf_copy.csv")
fb = fb[fb.Spent > 0].copy()
fb["campaign"] = fb.xyz_campaign_id.astype(str)


def seg_table(df, by):
    g = df.groupby(by).agg(ads=("ad_id", "size"), spend=("Spent", "sum"), conv=("Approved_Conversion", "sum"),
                           clicks=("Clicks", "sum"))
    g["CPA"] = g.spend / g.conv
    g["CVR_click"] = g.conv / g.clicks
    lo, hi = proportion_confint(g.conv, g.clicks, method="wilson")
    g["CVR_lo"], g["CVR_hi"] = lo, hi
    return g


print("[합계 기준] 연령")
print(seg_table(fb, "age").round(3))
print("\n[합계 기준] 성별")
print(seg_table(fb, "gender").round(3))
# 준포아송 GLM: 구매 수 ~ 연령 + 성별 + 캠페인, offset = log(비용)
m = smf.glm("Approved_Conversion ~ C(age) + C(gender) + C(campaign)", data=fb,
            family=sm.families.Poisson(), offset=np.log(fb.Spent)).fit(scale="X2")
coef = m.params.filter(like="C(age)").to_frame("coef").join(m.conf_int().rename(columns={0: "lo", 1: "hi"}))
coef = pd.concat([coef, m.params.filter(like="C(gender)").to_frame("coef").join(
    m.conf_int().rename(columns={0: "lo", 1: "hi"}))])
coef["CPA_배수"] = np.exp(-coef.coef)
coef["CPA_배수_95CI"] = [f"{np.exp(-h):.2f}~{np.exp(-l):.2f}" for l, h in zip(coef.lo, coef.hi)]
print("\n[준포아송 GLM, 캠페인 통제] 기준 = 30-34세, 여성 대비 CPA 배수")
print(coef[["CPA_배수", "CPA_배수_95CI"]].round(2))
print("과대산포 scale =", round(m.scale, 2))
print("\n[심슨 점검] 캠페인별 성별 CPA")
print(seg_table(fb, ["campaign", "gender"])[["ads", "conv", "CPA"]].round(1))

# =================================================================== Q3
section("Q3. GA4: 퍼널 단계별 이탈, 기기·유입 매체별 전환율 차이")
fun = pd.read_csv(RAW / "ga4/ga4_funnel.csv")
steps = ["visit_users", "view_users", "cart_users", "checkout_users", "purchase_users"]
names = ["방문", "상품 조회", "장바구니", "결제 시작", "구매"]
tot = fun[steps].sum()
print("전체 퍼널 (사용자 기준, 단계 도달 여부)")
for i, (s, n) in enumerate(zip(steps, names)):
    prev = tot.iloc[i - 1] if i else np.nan
    print(f"  {n:6s} {tot[s]:>8,}  이전 단계 대비 {tot[s] / prev:6.1%}" if i else f"  {n:6s} {tot[s]:>8,}")
print(f"  방문→구매 전체 {tot.purchase_users / tot.visit_users:.2%}")
drop = {f"{names[i]}→{names[i + 1]}": 1 - tot[steps[i + 1]] / tot[steps[i]] for i in range(4)}
print("  단계별 이탈률:", {k: f"{v:.1%}" for k, v in drop.items()}, "→ 가장 큰 이탈:", max(drop, key=drop.get))

dev = fun.groupby("device")[steps].sum()
dev["visit→purchase"] = dev.purchase_users / dev.visit_users
dev["cart→purchase"] = dev.purchase_users / dev.cart_users
print("\n기기별"); print(dev[["visit_users", "purchase_users", "visit→purchase", "cart→purchase"]].round(4))
z, p = proportions_ztest(dev.loc[["desktop", "mobile"], "purchase_users"], dev.loc[["desktop", "mobile"], "visit_users"])
print(f"desktop vs mobile 방문→구매 z={z:.2f} p={p:.3g}")

med = fun.groupby("medium")[steps].sum()
med["visit→purchase"] = med.purchase_users / med.visit_users
med["view→cart"] = med.cart_users / med.view_users
med["cart→purchase"] = med.purchase_users / med.cart_users
print("\n유입 매체별 (첫 유입 기준)"); print(med[["visit_users", "purchase_users", "visit→purchase", "view→cart", "cart→purchase"]].round(4))
clean = med.drop(index=["<Other>", "(data deleted)"], errors="ignore")
chi = stats.chi2_contingency(np.c_[clean.purchase_users, clean.visit_users - clean.purchase_users])
print(f"마스킹 제외 매체 4개 방문→구매 차이 카이제곱 p={chi[1]:.3g} (매체 {len(clean)}개)")
z, p = proportions_ztest(med.loc[["cpc", "organic"], "purchase_users"], med.loc[["cpc", "organic"], "visit_users"])
print(f"cpc vs organic 방문→구매 z={z:.2f} p={p:.3g}")
tx = pd.read_csv(RAW / "ga4/ga4_transactions.csv")
per_user = tx.groupby("user_pseudo_id").size()
print(f"\n3개월 내 2회 이상 구매 고객 비율 {(per_user >= 2).mean():.1%} (구매 고객 {len(per_user):,}명)")
print("구매 이벤트가 2번 이상 찍힌 거래:", int((tx.purchase_events > 1).sum()), "건 → 이벤트 수로 세면 구매가 부풀려짐")
pd.DataFrame({"step": names, "users": tot.values}).to_csv(OUT / "q3_funnel_overall.csv", index=False)

# =================================================================== Q4
section("Q4. UCI: 코호트 리텐션 곡선, 12개월 LTV, 첫 구매액 vs 12개월 가치")
u = pd.read_parquet(RAW / "uci/online_retail_II.parquet").drop_duplicates()
u["Invoice"] = u.Invoice.astype(str)
u["StockCode"] = u.StockCode.astype(str)
NON_PRODUCT = {"POST", "DOT", "M", "D", "S", "B", "C2", "PADS", "ADJUST", "ADJUST2", "BANK CHARGES",
               "AMAZONFEE", "TEST001", "TEST002", "CRUK"}
sc = u.StockCode.str.upper()
u = u[~u.Invoice.str[0].isin(["C", "A"]) & (u.Quantity > 0) & (u.Price > 0)
      & ~sc.isin(NON_PRODUCT) & ~sc.str.startswith("GIFT_")].dropna(subset=["Customer ID"])
u["amount"] = u.Quantity * u.Price
orders = u.groupby("Invoice").agg(cid=("Customer ID", "first"), dt=("InvoiceDate", "min"), amount=("amount", "sum")).reset_index()
first = orders.groupby("cid").agg(first_dt=("dt", "min"))
orders = orders.join(first, on="cid")
orders["cohort"] = orders.first_dt.dt.to_period("M")
orders["age_m"] = (orders.dt.dt.to_period("M") - orders.cohort).apply(lambda x: x.n)
print(f"정제 후 주문 {len(orders):,}건, 고객 {orders.cid.nunique():,}명")

# 월 범위 리텐션: 첫 코호트(2009-12, 기존 고객 섞임) 제외, 12개월 관측 가능한 코호트(2010-01~2010-11)만
coh = orders[(orders.cohort >= pd.Period("2010-01", "M")) & (orders.cohort <= pd.Period("2010-11", "M"))]
size = coh.groupby("cohort").cid.nunique()
active = coh[coh.age_m.between(1, 12)].groupby(["cohort", "age_m"]).cid.nunique().unstack(fill_value=0)
ret = active.div(size, axis=0)
pooled = active.sum() / size.sum()
print(f"\n코호트 {len(size)}개 (2010-01~2010-11), 고객 {size.sum():,}명")
print("가중 평균 월 범위 리텐션 (t=1..12):", (pooled * 100).round(1).to_dict())


def curve(t, floor, k):
    return floor + (1 - floor) * np.exp(-k * t)


t = np.arange(0, 13)
y = np.r_[1.0, pooled.values]
(floor, k), cov = curve_fit(curve, t, y, p0=[0.2, 1.0], bounds=([0, 0], [1, 10]))
se = np.sqrt(np.diag(cov))
resid = y - curve(t, floor, k)
print(f"적합: 리텐션(t) = {floor:.3f} + (1-{floor:.3f})·e^(-{k:.2f}t)  바닥값 SE={se[0]:.3f}, RMSE={np.sqrt((resid[1:] ** 2).mean()):.4f}")
# 앞 6개월로 맞추고 뒤 6개월로 검증
(f6, k6), _ = curve_fit(curve, t[:7], y[:7], p0=[0.2, 1.0], bounds=([0, 0], [1, 10]))
mape = np.mean(np.abs(curve(t[7:], f6, k6) - y[7:]) / y[7:])
print(f"홀드아웃 검증: 1~6개월로 적합 → 7~12개월 예측 MAPE {mape:.1%} (바닥값 {f6:.3f})")

# 첫 주문액 대량 구매(도매 추정) 분리
first_order = orders[orders.dt == orders.first_dt].groupby("cid").amount.sum()
thr = first_order.quantile(0.9)
seg = np.where(first_order.reindex(size.index.map(lambda _: None)).isna(), None, None)  # placeholder
coh_c = coh[["cid", "cohort"]].drop_duplicates().set_index("cid")
coh_c["bulk"] = first_order.reindex(coh_c.index) > thr
for flag, name in [(True, f"첫 주문 상위 10% (£{thr:,.0f} 초과)"), (False, "나머지 90%")]:
    ids = coh_c.index[coh_c.bulk == flag]
    sub = coh[coh.cid.isin(ids)]
    act = sub[sub.age_m.between(1, 12)].groupby("age_m").cid.nunique()
    r = act / len(ids)
    print(f"  {name}: n={len(ids):,} 1개월 {r.get(1, 0):.1%} 3개월 {r.get(3, 0):.1%} 12개월 {r.get(12, 0):.1%}")

# 12개월 LTV (첫 구매 포함, 365일 이내), 첫 구매 2010-12-09 이전 & 첫 코호트 제외
elig = first[(first.first_dt >= "2010-01-01") & (first.first_dt <= "2010-12-09")].index
o12 = orders[orders.cid.isin(elig) & (orders.dt < orders.first_dt + pd.Timedelta(days=365))]
ltv = o12.groupby("cid").amount.sum()
fo = first_order.reindex(elig)
repeat_share = 1 - fo.sum() / ltv.sum()
print(f"\n12개월 LTV (매출, 고객 {len(ltv):,}명): 평균 £{ltv.mean():,.0f} / 중앙값 £{ltv.median():,.0f} / p90 £{ltv.quantile(.9):,.0f}")
print(f"첫 주문액: 평균 £{fo.mean():,.0f} / 중앙값 £{fo.median():,.0f}")
print(f"12개월 매출 중 재구매 비중 {repeat_share:.1%}  (중앙값 고객 기준 LTV ÷ 첫 주문 = {ltv.median() / fo.median():.2f}배)")
rho = stats.spearmanr(fo, ltv.reindex(fo.index))
print(f"첫 주문액 vs 12개월 LTV 스피어만 ρ={rho.correlation:.2f} (p={rho.pvalue:.2g})")
q = pd.qcut(fo, 5, labels=["Q1 최소", "Q2", "Q3", "Q4", "Q5 최대"])
tab = pd.DataFrame({"첫주문_중앙값": fo.groupby(q).median(), "LTV12_중앙값": ltv.reindex(fo.index).groupby(q).median()})
tab["LTV÷첫주문"] = tab.LTV12_중앙값 / tab.첫주문_중앙값
tab["재구매율_12m"] = (o12.groupby("cid").size().reindex(fo.index) >= 2).groupby(q).mean()
print("\n첫 주문액 5분위별"); print(tab.round(2))
top_first = set(fo.nlargest(int(len(fo) * .2)).index)
top_ltv = set(ltv.nlargest(int(len(ltv) * .2)).index)
print(f"첫 주문 상위 20% 고객 중 12개월 LTV 상위 20%에도 드는 비율: {len(top_first & top_ltv) / len(top_first):.1%}")
pd.DataFrame({"t": t, "observed": y, "fitted": curve(t, floor, k)}).to_csv(OUT / "q4_retention_curve.csv", index=False)
ret.to_csv(OUT / "q4_cohort_retention.csv")
