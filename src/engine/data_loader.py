"""엔진 기본값 로더: data/processed/ 산출물이 있으면 그것을, 없으면 defaults.py 값을 쓴다.

| 파일 | 기대 컬럼 | 담당 |
|---|---|---|
| data/processed/ga4_funnel.csv (없으면 data/raw/ga4/ga4_funnel.csv) | medium, visit_users, view_users, cart_users, checkout_users, purchase_users | B |
| data/processed/fb_target_metrics.csv | target, rel_cpa, purchases | A |
| data/processed/cohort_retention.csv | months_since, retention (0~1), [customers], [segment] | B |
"""
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from . import defaults as D

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
GA4_ALL = "전체"


@lru_cache(maxsize=1)
def _read_ga4_table() -> Optional[pd.DataFrame]:
    for path in (PROCESSED / "ga4_funnel.csv", ROOT / "data" / "raw" / "ga4" / "ga4_funnel.csv"):
        if path.exists():
            df = pd.read_csv(path)
            if set(D.GA4_EVENTS) <= set(df.columns):
                return df
    return None


def _ga4_table() -> Optional[pd.DataFrame]:
    """GA4 공개 샘플 퍼널 표 (파일은 한 번만 읽고, 부를 때마다 복사본을 줌: 한 곳에서 고쳐도 다른 곳에 번지지 않게)."""
    df = _read_ga4_table()
    return None if df is None else df.copy()


def ga4_mediums() -> List[str]:
    df = _ga4_table()
    if df is None or "medium" not in df.columns:
        return []
    # 마스킹 매체 '(data deleted)'는 계산에서 늘 빼므로 선택지에서도 뺌 (고르면 말없이 기본값이 되던 것, 검수 A18)
    return [GA4_ALL] + sorted(m for m in df["medium"].dropna().unique().tolist() if m != D.GA4_MASKED_MEDIUM)


def funnel_steps(medium: str = GA4_ALL) -> Tuple[List[Tuple[str, float]], str]:
    """(단계 목록, 출처 설명). 첫 단계 '③ 방문'(광고 클릭 → 방문)은 GA4에 없어 기본값 유지."""
    df = _ga4_table()
    if df is None:
        return list(D.FUNNEL_STEPS), "기본값 (GA4 파일 없음)"
    if medium != GA4_ALL and "medium" in df.columns:
        df = df[df["medium"] == medium]
    elif "medium" in df.columns:   # 전체 = 마스킹 매체 제외 (코치 참고 기준 1.49%와 같은 범위)
        df = df[df["medium"] != D.GA4_MASKED_MEDIUM]
    s = df[D.GA4_EVENTS].sum()
    if s.iloc[0] <= 0:
        return list(D.FUNNEL_STEPS), "기본값"
    rates = [float(s.iloc[i + 1] / s.iloc[i]) if s.iloc[i] > 0 else 0.0 for i in range(len(D.GA4_EVENTS) - 1)]
    steps = [D.FUNNEL_STEPS[0]] + [(name, r) for (name, _), r in zip(D.FUNNEL_STEPS[1:], rates)]
    return steps, f"GA4 샘플 ({medium}, 사용자 {int(s.iloc[0]):,}명)"


def meta_targets() -> pd.DataFrame:
    """타깃별 상대 CPA 배수 + 95% 구간 (구매 건수를 포아송으로 보고 근사)."""
    path = PROCESSED / "fb_target_metrics.csv"
    if path.exists():
        df = pd.read_csv(path)[["target", "rel_cpa", "purchases"]]
        source = "fb_target_metrics.csv"
    else:
        df = pd.DataFrame([(k, v[0], v[1]) for k, v in D.META_TARGETS.items()],
                          columns=["target", "rel_cpa", "purchases"])
        source = "Kaggle (defaults.py)"
    half = 1.96 / np.sqrt(df["purchases"].clip(lower=1))
    df["low"] = df["rel_cpa"] * np.exp(-half)
    df["high"] = df["rel_cpa"] * np.exp(half)
    df["source"] = source
    return df.reset_index(drop=True)


def target_multiplier(targets: List[str]) -> float:
    """고른 타깃들의 상대 CPA 배수 (구매 건수 가중). 아무것도 안 고르면 1.0 (전체 평균)."""
    if not targets:
        return 1.0
    df = meta_targets()
    d = df[df["target"].isin(targets)]
    if d.empty:
        return 1.0
    return float(np.average(d["rel_cpa"], weights=d["purchases"]))


def keyword_tier(monthly_qc: float) -> str:
    for threshold, name in D.KEYWORD_TIERS:
        if monthly_qc >= threshold:
            return name
    return D.KEYWORD_TIERS[-1][1]



# ── 유지: 코호트 리텐션 → r(t) = floor + (1 − floor)·e^(−decay·t) 적합 ──────────────
def _retention_model(t, floor, decay):
    return floor + (1 - floor) * np.exp(-decay * t)


def retention_curve_table(df: Optional[pd.DataFrame] = None, segment: Optional[str] = None) -> Optional[pd.DataFrame]:
    """경과 개월별 평균 리텐션 (코호트 고객 수 가중). t ≥ 1만."""
    if df is None:
        path = PROCESSED / "cohort_retention.csv"
        if not path.exists():
            return None
        df = pd.read_csv(path)
    if segment is not None and "segment" in df.columns:
        df = df[df["segment"] == segment]
    df = df[df["months_since"] >= 1].dropna(subset=["retention"])
    if df.empty:
        return None
    w = df["customers"] if "customers" in df.columns else pd.Series(1.0, index=df.index)
    g = (df.assign(w=w, wr=df["retention"] * w).groupby("months_since")[["w", "wr"]].sum())
    return pd.DataFrame({"months_since": g.index.astype(int), "retention": (g["wr"] / g["w"]).values, "weight": g["w"].values})


def retention_segments() -> List[str]:
    path = PROCESSED / "cohort_retention.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    return sorted(df["segment"].dropna().unique().tolist()) if "segment" in df.columns else []


def fit_retention(table: pd.DataFrame, fit_months: Optional[int] = None) -> Dict[str, float]:
    """floor·decay 적합. fit_months를 주면 앞 기간만으로 맞추고 뒤 기간 오차(MAE)를 함께 돌려준다 (기획안 7-3 검증)."""
    train = table if fit_months is None else table[table["months_since"] <= fit_months]
    (floor, decay), _ = curve_fit(_retention_model, train["months_since"].values, train["retention"].values,
                                  p0=[0.05, 1.0], bounds=([0.0, 0.01], [1.0, 10.0]),
                                  sigma=1 / np.sqrt(train["weight"].clip(lower=1e-9).values))
    out = {"floor": float(floor), "decay": float(decay)}
    if fit_months is not None:
        test = table[table["months_since"] > fit_months]
        if len(test):
            pred = _retention_model(test["months_since"].values, floor, decay)
            out["holdout_mae"] = float(np.mean(np.abs(pred - test["retention"].values)))
    return out


# ── 채널 전환율 배수(cvr_mult) 소유권 (MECE #4) ─────────────────────────────
# 하나만 채택: 사용자 성과 CSV > GA4 매체별 배수 > 기본값. 어트리뷰션 보정은 그 위에 한 번만 곱한다.
GA4_CHANNEL_MEDIUM = {"naver": "cpc", "meta": None}  # GA4 샘플에는 소셜 유료 매체가 없음


def ga4_medium_cvr(medium: str = GA4_ALL) -> Optional[float]:
    """방문 → 구매 전환율. (data deleted)는 마스킹 편향으로 '전체'에서도 제외."""
    df = _ga4_table()
    if df is None or "medium" not in df.columns:
        return None
    df = df[df["medium"] != D.GA4_MASKED_MEDIUM]
    if medium != GA4_ALL:
        df = df[df["medium"] == medium]
    visit = float(df["visit_users"].sum())
    return float(df["purchase_users"].sum()) / visit if visit > 0 else None


def resolve_cvr_mult(channel: str, default: float, funnel_cvr: float, funnel_medium: str = GA4_ALL,
                     upload: Optional[pd.DataFrame] = None, use_ga4: bool = True,
                     seg_cvr=None, seg_label: str = "GA4 매체별") -> Tuple[float, str]:
    """(배수, 출처). 퍼널 자체가 그 매체 기준이면 GA4 배수는 1 (이중 계산 방지).
    seg_cvr: 세그먼트 이름 → 방문→구매 전환율 함수. 기본은 GA4 샘플, 내 퍼널 CSV를 올리면 그 표."""
    seg_cvr = seg_cvr or ga4_medium_cvr
    if upload is not None and channel in upload.index and funnel_cvr > 0:
        cvr = float(upload.loc[channel, "CVR"])
        if cvr == cvr and cvr > 0:
            return cvr / funnel_cvr, "내 광고 성과 CSV"
    medium = GA4_CHANNEL_MEDIUM.get(channel)
    if use_ga4 and medium:
        if funnel_medium == medium:
            return 1.0, f"'{medium}' 퍼널을 이미 사용 중"
        num, den = seg_cvr(medium), seg_cvr(funnel_medium)
        if num and den:
            return num / den, f"{seg_label} ('{medium}' ÷ '{funnel_medium}' 방문→구매)"
    return default, "기본값" if default == 1.0 else "가정값 (근거 데이터 없음)"


# ── M2 세그먼트 비교 (명세 3-2) ───────────────────────────────────
SEGMENT_MIN_USERS = 1_000  # 이보다 방문자가 적으면 비교에서 회색 처리 (명세 9장 #3, 팀 결정 대기)
STEP_LABELS = ["방문→상품 조회", "상품 조회→장바구니", "장바구니→결제 시작", "결제 시작→구매", "방문→구매"]


def segment_rates(df: pd.DataFrame, seg_col: Optional[str], step_cols: List[str],
                  labels: Optional[List[str]] = None) -> pd.DataFrame:
    """세그먼트별 단계 전환율 표. 행 = 세그먼트 + '전체', 열 = visitors, 단계 전환율들, 첫→끝, purchases, small."""
    if seg_col:   # 묶음 값이 빈 행은 빼고, 묶음 값이 합계 행 이름('전체')과 같으면 이름을 바꿔 겹치지 않게 (검수 A20)
        seg = df[seg_col]
        df = df[seg.notna() & (seg.astype(str).str.strip() != "")]
        seg = df[seg_col].astype(str).str.strip().replace({GA4_ALL: f"{GA4_ALL} (묶음 값)"})
    counts = df[step_cols].apply(lambda c: pd.to_numeric(c.astype(str).str.replace(",", ""), errors="coerce")).fillna(0)
    g = counts.groupby(seg).sum() if seg_col else pd.DataFrame(columns=step_cols)
    g.loc[GA4_ALL] = counts.sum()
    labels = labels or [f"{a}→{b}" for a, b in zip(step_cols, step_cols[1:])] + [f"{step_cols[0]}→{step_cols[-1]}"]
    out = pd.DataFrame({"visitors": g[step_cols[0]]}, index=g.index)
    for i, lab in enumerate(labels[:-1]):
        out[lab] = g[step_cols[i + 1]] / g[step_cols[i]].where(g[step_cols[i]] > 0)
    out[labels[-1]] = g[step_cols[-1]] / g[step_cols[0]].where(g[step_cols[0]] > 0)
    out["purchases"] = g[step_cols[-1]]
    out["small"] = out["visitors"] < SEGMENT_MIN_USERS
    return out.sort_values("visitors", ascending=False)


def segment_table(dim: str = "medium") -> Optional[pd.DataFrame]:
    """GA4 샘플 매체·기기별 단계 전환율. (data deleted)는 마스킹 편향으로 제외."""
    df = _ga4_table()
    if df is None or dim not in df.columns:
        return None
    if "medium" in df.columns:   # medium 열이 없는 표도 (기기만 있는 표)
        df = df[df["medium"] != D.GA4_MASKED_MEDIUM]
    return segment_rates(df, dim, D.GA4_EVENTS, STEP_LABELS)


def upload_funnel(df: pd.DataFrame, step_cols: List[str], seg_col: Optional[str] = None,
                  segment: str = GA4_ALL) -> Tuple[List[Tuple[str, float]], str]:
    """내 GA4 유입경로 CSV(명세 3-1: segment, step_1_users, …, step_n_users) → 퍼널 단계.

    단계 열이 5개(방문·상품 조회·장바구니·결제 시작·구매)면 엔진의 일반 단계 이름을 쓰고, 아니면 열 이름을 쓴다.
    첫 단계 '③ 방문'(광고 클릭 → 방문)은 분석 도구에 없어 기본값을 유지한다.
    """
    if len(step_cols) < 2:
        raise ValueError("단계 열을 2개 이상 골라 주세요.")
    tab = segment_rates(df, seg_col, step_cols)
    row = tab.loc[segment] if segment in tab.index else tab.loc[GA4_ALL]
    rates = [float(row.iloc[1 + i]) if row.iloc[1 + i] == row.iloc[1 + i] else 0.0 for i in range(len(step_cols) - 1)]
    names = [n for n, _ in D.FUNNEL_STEPS[1:]] if len(step_cols) == len(D.FUNNEL_STEPS) else list(step_cols[1:])
    return [D.FUNNEL_STEPS[0]] + list(zip(names, rates)), f"내 퍼널 CSV ({segment}, 첫 단계 {int(row['visitors']):,}명)"


def two_prop_z(x1: float, n1: float, x2: float, n2: float) -> Tuple[float, float]:
    """두 비율 차이 z-검정 (양측). (z, p)."""
    from scipy.stats import norm
    if min(n1, n2) <= 0:
        return float("nan"), float("nan")
    p = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (x1 / n1 - x2 / n2) / se
    return float(z), float(2 * (1 - norm.cdf(abs(z))))
