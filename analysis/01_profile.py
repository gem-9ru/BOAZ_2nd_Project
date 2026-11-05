"""데이터셋 4종 프로파일링 (explore-data).

실행: python analysis/01_profile.py
"""
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, INTERIM = ROOT / "data/raw", ROOT / "data/interim"
pd.set_option("display.width", 200, "display.max_columns", 30)


def section(title):
    print(f"\n{'=' * 70}\n## {title}\n{'=' * 70}")


def numeric_profile(s):
    q = s.quantile([.01, .25, .5, .75, .95, .99])
    return (f"min={s.min():,.2f} p25={q[.25]:,.2f} median={q[.5]:,.2f} mean={s.mean():,.2f} "
            f"p75={q[.75]:,.2f} p95={q[.95]:,.2f} p99={q[.99]:,.2f} max={s.max():,.2f} "
            f"zeros={(s == 0).sum():,} neg={(s < 0).sum():,}")


# ---------------------------------------------------------------- UCI
section("UCI Online Retail II (거래 행 단위)")
uci = pd.read_parquet(RAW / "uci/online_retail_II.parquet")
print(f"rows={len(uci):,} cols={uci.shape[1]}  기간 {uci.InvoiceDate.min()} ~ {uci.InvoiceDate.max()}")
print("null rate:", (uci.isna().mean() * 100).round(2).to_dict())
print("distinct:", uci.nunique().to_dict())
print("exact duplicate rows:", uci.duplicated().sum())
print("Quantity:", numeric_profile(uci.Quantity))
print("Price:", numeric_profile(uci.Price))
inv = uci.Invoice.astype(str)
print("invoice prefix:", inv.str[0].where(~inv.str[0].str.isdigit(), "digit").value_counts().to_dict())
print("country top 8:", uci.Country.value_counts(normalize=True).head(8).round(3).to_dict())
monthly = uci.set_index("InvoiceDate").resample("MS").size()
print("월별 행 수 (최소/최대):", monthly.min(), monthly.idxmin().date(), "/", monthly.max(), monthly.idxmax().date())

# ---------------------------------------------------------------- Kaggle
section("Kaggle 페이스북 광고 (광고 단위)")
fb = pd.read_csv(RAW / "kaggle_fb/KAG_conversion_data_hf_copy.csv")
print(f"rows={len(fb):,} cols={fb.shape[1]}  ad_id 고유={fb.ad_id.is_unique}")
for c in ["Impressions", "Clicks", "Spent", "Total_Conversion", "Approved_Conversion"]:
    print(f"{c}:", numeric_profile(fb[c]))
print("approved>total:", (fb.Approved_Conversion > fb.Total_Conversion).sum(),
      " clicks>impressions:", (fb.Clicks > fb.Impressions).sum(),
      " spent>0 & clicks=0:", ((fb.Spent > 0) & (fb.Clicks == 0)).sum())
print("상관(Spent, Impressions, Clicks, Approved):")
print(fb[["Spent", "Impressions", "Clicks", "Approved_Conversion"]].corr().round(2))
print("interest 광고 수 분포:", fb.interest.value_counts().describe().round(1).to_dict())

# ---------------------------------------------------------------- GA4
section("GA4 샘플 (BigQuery 쿼리 결과 4개)")
ev = pd.read_csv(RAW / "ga4/ga4_events.csv")
print("이벤트:", dict(zip(ev.event_name, ev.users)))
fun = pd.read_csv(RAW / "ga4/ga4_funnel.csv")
print(f"\nfunnel rows={len(fun)} (medium × device), 사용자 합={fun.users.sum():,}")
print("medium:", fun.groupby("medium").users.sum().sort_values(ascending=False).to_dict())
print("device:", fun.groupby("device").users.sum().to_dict())
steps = ["visit_users", "view_users", "cart_users", "checkout_users", "purchase_users"]
tot = fun[steps].sum()
print("전체 퍼널:", tot.to_dict())
viol = (fun[steps].diff(axis=1).iloc[:, 1:] > 0).any(axis=1)
print("단계가 늘어나는 행(순서 위반):", int(viol.sum()))
tx = pd.read_csv(RAW / "ga4/ga4_transactions.csv")
print(f"\ntransactions rows={len(tx):,} 고유 거래={tx.transaction_id.nunique():,} 고유 사용자={tx.user_pseudo_id.nunique():,}")
print("revenue:", numeric_profile(tx.revenue))
print("purchase_events 분포:", tx.purchase_events.value_counts().sort_index().to_dict())
print("medium 비중:", tx.medium.value_counts(normalize=True).round(3).to_dict())
per_user = tx.groupby("user_pseudo_id").size()
print("사용자당 거래:", per_user.value_counts().sort_index().head(6).to_dict(),
      " 2회 이상 비율=", round((per_user >= 2).mean(), 3))
print("주문일 범위:", tx.order_date.min(), "~", tx.order_date.max())
ap = pd.read_csv(RAW / "ga4/ga4_attribution_paths.csv")
print(f"\nattribution paths rows={len(ap):,} 세션 합={ap.n_sessions.sum():,} 구매 합={ap.purchases.sum():,}")
ap["touches"] = ap.mpath.str.count(">") + 1
print("경로 길이:", ap.touches.describe().round(1).to_dict())

# ---------------------------------------------------------------- Naver
section("네이버 검색광고 캐시 (키워드 도구 + 입찰가별 예상 실적)")
for f in sorted(glob.glob(str(INTERIM / "naver_cache/keywordstool_*.json"))):
    d = json.load(open(f))
    kw = pd.DataFrame(d["response"]["keywordList"])
    low = kw.monthlyMobileQcCnt.astype(str).str.contains("<").sum()
    print(f"[keywordstool] hint={d['request']['hintKeywords']} fetched={d['fetched_at']} 연관={len(kw)} "
          f"'<10' 모바일={low} compIdx={kw.compIdx.value_counts().to_dict()}")
rows = []
for f in sorted(glob.glob(str(INTERIM / "naver_cache/estimate_*.json"))):
    d = json.load(open(f))
    est = pd.DataFrame(d["response"]["estimate"])
    est = est.sort_values("bid")
    mono = all((est[c].diff().fillna(0) >= 0).all() for c in ["impressions", "clicks", "cost"])
    first = est.loc[est.clicks > 0, "bid"].min() if (est.clicks > 0).any() else np.nan
    rows.append({"keyword": d["request"]["key"], "device": d["request"]["device"], "bids": len(est),
                 "fetched": d["fetched_at"][:10], "first_click_bid": first,
                 "max_clicks": est.clicks.max(), "max_cost": est.cost.max(), "monotonic": mono})
est_df = pd.DataFrame(rows)
print(est_df.to_string(index=False))
for f in ["industry_compare.csv", "industry_compare_beauty.csv"]:
    print(f"\n[{f}]")
    print(pd.read_csv(INTERIM / f).to_string(index=False))
