"""노션 중간 발표용 차트 5개 (PNG). 03_analysis와 같은 데이터·정의를 쓴다.

실행: python analysis/05_charts.py
결과: 시각화/분석_*.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT, FIG = ROOT / "data/raw", ROOT / "analysis/out", ROOT / "시각화"

# 참조 팔레트 (dataviz references/palette.md, 라이트 모드)
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S1, S2 = "#2a78d6", "#eb6834"  # 범주 1·2번 슬롯 (파랑, 주황)
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#eef4fc", "#9cc3ef", "#2a78d6", "#123f7a"])

for path in ["/System/Library/Fonts/Supplemental/AppleGothic.ttf", "/Library/Fonts/NanumGothic.ttf"]:
    if Path(path).exists():
        font_manager.fontManager.addfont(path)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=path).get_name()
        break
plt.rcParams.update({
    "axes.unicode_minus": False, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "font.size": 11,
    "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 14,
})


def save(fig, name, note):
    fig.text(0.01, -0.02, note, fontsize=9, color=INK2, ha="left", va="top")
    fig.savefig(FIG / f"분석_{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("saved", name)


# ------------------------------------------------------------------ 1. 네이버 입찰가 곡선
est = pd.read_csv(OUT / "naver_q1/estimates.csv")
kc = pd.read_csv(OUT / "q1_keyword_curves.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.4, 1]})
p = est[(est.keyword == "필라테스") & (est.clicks > 0)].sort_values("bid")
a1.plot(p.cost / 1e4, p.clicks, color=S1, lw=2, marker="o", ms=5)
for _, r in p.iloc[[0, len(p) // 2, -1]].iterrows():
    a1.annotate(f"입찰 {r.bid:,.0f}원\n클릭당 {r.cost / r.clicks:,.0f}원", (r.cost / 1e4, r.clicks),
                textcoords="offset points", xytext=(8, -28), fontsize=9, color=INK2)
a1.set_title("'필라테스' 광고비를 늘릴수록 클릭은 덜 늘어난다")
a1.set_xlabel("예상 월 광고비 (만 원)"); a1.set_ylabel("예상 월 클릭 수")
a1.set_ylim(bottom=0); a1.set_xlim(left=0)
ok = kc.dropna(subset=["saturation_ratio"])
for i, (tier, color) in enumerate([("대표", S1), ("세부", S2)]):
    v = ok[ok.tier == tier].saturation_ratio.clip(upper=5)
    jitter = np.random.default_rng(0).uniform(-0.12, 0.12, len(v))
    a2.scatter(np.full(len(v), i) + jitter, v, s=40, color=color, alpha=0.75, edgecolor=SURFACE, linewidth=1.5)
    med = ok[ok.tier == tier].saturation_ratio.median()
    a2.hlines(med, i - 0.3, i + 0.3, color=INK, lw=2)
    a2.text(i + 0.33, med, f"중앙값 {med:.1f}배", va="center", fontsize=10, color=INK)
a2.set_xticks([0, 1], [f"대표\n월 검색 1만+\nn={(ok.tier == '대표').sum()}", f"세부\n월 검색 300~3천\nn={(ok.tier == '세부').sum()}"])
a2.set_xlim(-0.6, 1.9); a2.set_ylim(0, 5.3)
a2.set_title("대표 키워드가 더 빨리 포화된다")
a2.set_ylabel("포화 비율 (한계 CPC ÷ 평균 CPC)")
a2.grid(axis="x", visible=False)
save(fig, "Q1_네이버_입찰가곡선",
     "자료: 네이버 검색광고 API 입찰가별 예상 실적(모바일), 2026-11-06 수집, 업종 4개 키워드 63개. 포화 비율 5배 초과는 5로 표시. 대표 vs 세부 Mann-Whitney p=0.002")

# ------------------------------------------------------------------ 2. UCI 전처리 단계
u = pd.read_parquet(RAW / "uci/online_retail_II.parquet")
NON_PRODUCT = {"POST", "DOT", "M", "D", "S", "B", "C2", "PADS", "ADJUST", "ADJUST2", "BANK CHARGES",
               "AMAZONFEE", "TEST001", "TEST002", "CRUK"}
steps = [("원본", u)]
u = u.drop_duplicates(); steps.append(("완전 중복 제거", u))
inv = u.Invoice.astype(str)
u = u[~inv.str[0].isin(["C", "A"]) & (u.Quantity > 0)]; steps.append(("취소·조정·음수 수량 제거", u))
sc = u.StockCode.astype(str).str.upper()
u = u[~sc.isin(NON_PRODUCT) & ~sc.str.startswith("GIFT_")]; steps.append(("배송비·수수료 등 비상품 제거", u))
u = u[u.Price > 0]; steps.append(("단가 0 이하 제거", u))
u = u.dropna(subset=["Customer ID"]); steps.append(("고객 ID 없는 행 제거", u))
rows = [len(d) for _, d in steps]
fig, ax = plt.subplots(figsize=(11, 4.6))
y = np.arange(len(steps))[::-1]
ax.barh(y, rows, color=S1, height=0.6)
for yi, (name, d), r in zip(y, steps, rows):
    ax.text(r + 1.2e4, yi, f"{r:,}행 · 고객 {d['Customer ID'].nunique():,}명", va="center", fontsize=10, color=INK)
ax.set_yticks(y, [n for n, _ in steps]); ax.set_xlim(0, 1.45e6)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1e4:,.0f}만"))
ax.grid(axis="y", visible=False)
ax.set_title(f"UCI 거래 {rows[0]:,}행 → 고객 분석용 {rows[-1]:,}행 ({rows[-1] / rows[0]:.0%})")
save(fig, "UCI_전처리단계",
     "자료: UCI Online Retail II (2009-12-01~2011-12-09). 고객 ID 결측은 행의 22.8%. 고객 분석에서만 제외")

# ------------------------------------------------------------------ 3. 코호트 리텐션 히트맵
ret = pd.read_csv(OUT / "q4_cohort_retention.csv", index_col=0)
fig, ax = plt.subplots(figsize=(11, 5.4))
im = ax.imshow(ret.values * 100, cmap=SEQ, vmin=0, vmax=35, aspect="auto")
for i in range(ret.shape[0]):
    for j in range(ret.shape[1]):
        v = ret.values[i, j] * 100
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=9, color="white" if v > 22 else INK)
ax.set_xticks(range(12), [f"{m}" for m in range(1, 13)]); ax.set_yticks(range(len(ret)), ret.index)
ax.set_xlabel("첫 구매 후 경과 개월"); ax.set_ylabel("첫 구매 월 (코호트)")
ax.grid(False)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.set_label("그 달에 다시 구매한 고객 비율 (%)", color=INK2)
cb.outline.set_visible(False)
ax.set_title("첫 달에 약 20%로 떨어진 뒤 평평하게 유지된다 (12개월 차는 연말 성수기 반등)")
save(fig, "Q4_코호트리텐션",
     "자료: UCI 정제 데이터, 코호트 2010-01~2010-11 (3,288명). 월 범위 리텐션. 2009-12 코호트는 기존 고객이 섞여 제외. 도매 비중이 커서 일반 쇼핑몰보다 높음")

# ------------------------------------------------------------------ 4. Kaggle 타깃 CPA 배수
fb = pd.read_csv(RAW / "kaggle_fb/KAG_conversion_data_hf_copy.csv")
fb = fb[fb.Spent > 0].assign(campaign=lambda d: d.xyz_campaign_id.astype(str))
m = smf.glm("Approved_Conversion ~ C(age) + C(gender) + C(campaign)", data=fb,
            family=sm.families.Poisson(), offset=np.log(fb.Spent)).fit(scale="X2")
ci = m.conf_int()
rows = [("30-34세 (기준)", 1, 1, 1)]
for age in ["35-39", "40-44", "45-49"]:
    k = f"C(age)[T.{age}]"
    rows.append((f"{age}세", np.exp(-m.params[k]), np.exp(-ci.loc[k, 1]), np.exp(-ci.loc[k, 0])))
rows.append(("여성 (기준)", 1, 1, 1))
k = "C(gender)[T.M]"
rows.append(("남성", np.exp(-m.params[k]), np.exp(-ci.loc[k, 1]), np.exp(-ci.loc[k, 0])))
fig, ax = plt.subplots(figsize=(10, 4.8))
yy = np.arange(len(rows))[::-1]
for yi, (name, est_, lo, hi) in zip(yy, rows):
    base = lo == hi == 1
    color = INK2 if base else (S1 if "세" in name else S2)
    ax.plot([lo, hi], [yi, yi], color=color, lw=2.5, solid_capstyle="round")
    ax.plot(est_, yi, "o", ms=9, color=color, markeredgecolor=SURFACE, markeredgewidth=2)
    ax.text(max(hi, 1) + 0.08, yi, "기준" if base else f"{est_:.2f}배 ({lo:.2f}~{hi:.2f})", va="center", fontsize=10, color=INK)
ax.axvline(1, color=INK2, lw=1, ls="--")
ax.set_yticks(yy, [r[0] for r in rows]); ax.set_xlim(0, 4.9)
ax.set_xlabel("구매당 비용(CPA) 배수, 95% 신뢰구간 (캠페인 통제)")
ax.grid(axis="y", visible=False)
ax.set_title("45-49세는 30-34세보다 구매당 비용이 약 3배, 남성은 여성의 0.63배")
save(fig, "Q2_타깃별CPA",
     "자료: Kaggle 'Sales Conversion Optimization' 광고비 0원 초과 광고 936개. 준포아송 회귀(구매 수 ~ 연령 + 성별 + 캠페인, 광고비 보정). 관찰 데이터라 인과 해석 불가")

# ------------------------------------------------------------------ 5. GA4 퍼널
fun = pd.read_csv(OUT / "q3_funnel_overall.csv")
fig, ax = plt.subplots(figsize=(10, 4.6))
y = np.arange(len(fun))[::-1]
ax.barh(y, fun.users, color=S1, height=0.6)
for i, (yi, r) in enumerate(zip(y, fun.itertuples())):
    label = f"{r.users:,}명"
    if i:
        rate = r.users / fun.users.iloc[i - 1]
        label += f"  (이전 단계의 {rate:.1%})"
    ax.text(r.users + 3000, yi, label, va="center", fontsize=10, color=INK)
worst = (fun.users / fun.users.shift()).idxmin()
ax.barh(y[worst], fun.users.iloc[worst], color=S2, height=0.6)
ax.set_yticks(y, fun.step); ax.set_xlim(0, 3.6e5)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v / 1e4:,.0f}만"))
ax.grid(axis="y", visible=False)
ax.set_title("상품을 본 사람의 79.5%가 장바구니에 담지 않는다 (방문 → 구매 1.65%)")
save(fig, "Q3_GA4퍼널",
     "자료: GA4 공개 샘플 (구글 굿즈몰, 2020-11~2021-01), 사용자 기준 단계 도달 여부. 주황 = 이탈이 가장 큰 단계")
