"""M3 어트리뷰션: 전환 경로 → 규칙 기반 5개 모델의 채널별 기여 → 채널 전환율 보정계수.

기여는 관측된 접점에 전환을 '배분'한 것이지, 그 채널이 '만든' 전환(인과·증분)이 아니다 (명세 10-3).
이 모듈은 정답 모델을 고르는 기능이 아니라 '기준을 바꾸면 결론이 흔들리는가'를 보는 민감도 점검이다.

입력 형식
- GA4 샘플: data/raw/ga4/ga4_attribution_paths.csv (mpath, srcpath, n_sessions, purchases, revenue; 접점은 " > "로 연결)
- 사용자 업로드: path, conversions, [revenue] (접점 = 채널 이름 또는 도메인)
"""
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GA4_PATHS = ROOT / "data" / "raw" / "ga4" / "ga4_attribution_paths.csv"
SEP = " > "
SELF_DOMAINS = ("shop.googlemerchandisestore.com", "googlemerchandisestore.com")  # GA4 샘플 스토어 (사용자 입력으로 교체)
DIRECT = "direct"
UNKNOWN = "식별 불가"
_UNKNOWN_TOKENS = {"(data deleted)", "<Other>", "(unknown)", "(not set)", ""}
MODELS = {
    "first": "첫 클릭",
    "last": "마지막 클릭",
    "last_non_direct": "마지막 비직접 클릭",
    "linear": "선형",
    "u_shape": "U자형",
}
SPREAD_THRESHOLD = 5.0  # %p. 모든 채널의 모델 간 변동폭이 이보다 작으면 "결론 같음" (명세 9장 #2, 팀 결정 대기)


def load_ga4_paths(path: Path = GA4_PATHS) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    return pd.DataFrame({"path": df["mpath"], "source_path": df["srcpath"],
                         "conversions": df["purchases"].astype(float), "revenue": df["revenue"].fillna(0.0)})


def from_upload(df: pd.DataFrame) -> pd.DataFrame:
    """업로드 CSV(path, conversions, [revenue]) → 내부 형식. 소스 경로가 없으면 접점 이름으로 자기 참조를 판정."""
    out = pd.DataFrame({"path": df["path"].astype(str),
                        "conversions": pd.to_numeric(df["conversions"], errors="coerce").fillna(0.0)})
    out["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0.0) if "revenue" in df.columns else 0.0
    out["source_path"] = df["source_path"].astype(str) if "source_path" in df.columns else out["path"]
    return out[out["conversions"] > 0].reset_index(drop=True)


def _channel(token: str) -> str:
    token = token.strip()
    if token in ("(none)", "(direct)"):
        return DIRECT
    if token in _UNKNOWN_TOKENS:
        return UNKNOWN
    return token


def clean_paths(df: pd.DataFrame, self_domains: Iterable[str] = SELF_DOMAINS, clean: bool = True,
                lookback_days: Optional[int] = None) -> pd.DataFrame:
    """접점 목록(touches) 컬럼을 만든다.

    clean=True: 자기 도메인에서 온 접점(결제·로그인 페이지 복귀) 삭제 = GA4 '원치 않는 추천' 처리.
    접점이 모두 지워진 경로는 GA4처럼 direct 한 접점으로 남긴다 (전환 수 보존).
    lookback_days: 전환 인정 기간. 경로 CSV에 접점 시각이 없어 지금은 적용하지 않는다 (GA4 샘플은 3개월치).
    """
    domains = {d.strip().lower() for d in self_domains if d.strip()}
    touches = []
    for path, src in zip(df["path"].astype(str), df["source_path"].astype(str)):
        meds, srcs = path.split(SEP), src.split(SEP)
        if len(srcs) != len(meds):
            srcs = meds
        t = [_channel(m) for m, s in zip(meds, srcs)
             if not (clean and (s.strip().lower() in domains or m.strip().lower() in domains))]
        touches.append(t or [DIRECT])
    out = df.copy()
    out["touches"] = touches
    out["n_touches"] = out["touches"].map(len)
    return out


def _weights(n: int, model: str, touches: Sequence[str]) -> np.ndarray:
    w = np.zeros(n)
    if model == "first":
        w[0] = 1
    elif model == "last":
        w[-1] = 1
    elif model == "last_non_direct":
        idx = [i for i, c in enumerate(touches) if c != DIRECT]
        w[idx[-1] if idx else -1] = 1
    elif model == "linear":
        w[:] = 1 / n
    elif model == "u_shape":
        if n == 1:
            w[0] = 1
        elif n == 2:
            w[:] = 0.5
        else:
            w[0] = w[-1] = 0.4
            w[1:-1] = 0.2 / (n - 2)
    else:
        raise ValueError(model)
    return w


def credit(df: pd.DataFrame, model: str) -> pd.Series:
    """채널별로 배분된 전환 수 (합 = 전체 전환 수)."""
    acc: Dict[str, float] = {}
    for t, conv in zip(df["touches"], df["conversions"]):
        for c, w in zip(t, _weights(len(t), model, t)):
            acc[c] = acc.get(c, 0.0) + w * conv
    return pd.Series(acc, dtype=float).sort_values(ascending=False)


def credit_table(df: pd.DataFrame) -> pd.DataFrame:
    """행 = 채널, 열 = 모델, 값 = 기여 비중(%). 마지막 클릭 기준 내림차순, 식별 불가는 맨 아래."""
    tab = pd.DataFrame({m: credit(df, m) for m in MODELS}).fillna(0.0)
    tab = tab / df["conversions"].sum() * 100
    order = [c for c in tab.sort_values("last", ascending=False).index if c != UNKNOWN]
    return tab.loc[order + ([UNKNOWN] if UNKNOWN in tab.index else [])]


def spread(table: pd.DataFrame) -> pd.Series:
    """채널별 모델 간 변동폭 (최댓값 − 최솟값, %p)."""
    return (table.max(axis=1) - table.min(axis=1)).sort_values(ascending=False)


def verdict(table: pd.DataFrame, threshold: float = SPREAD_THRESHOLD) -> str:
    sp = spread(table.drop(index=UNKNOWN, errors="ignore"))
    if sp.empty:
        return "경로 데이터가 없습니다."
    top, width = sp.index[0], float(sp.iloc[0])
    if width < threshold:
        return (f"이 데이터에서는 어떤 모델을 써도 채널별 기여가 {threshold:.0f}%p 안에서만 움직입니다 (최대 {width:.1f}%p, {top}). "
                "모델보다 데이터 정제가 중요합니다.")
    row = table.loc[top]
    under = "과소평가" if row["last"] < row.drop("last").mean() else "과대평가"
    return f"마지막 클릭 기준은 '{top}' 채널을 {under}합니다 (모델 간 {width:.1f}%p 차이). 보정 후 배분을 확인하세요."


def correction_factors(table: pd.DataFrame, model: str, base: str = "last",
                       channels: Optional[List[str]] = None) -> pd.Series:
    """k_c = 선택 모델 기여 ÷ 기준(마지막 클릭) 기여. 총 전환 보존: Σ base_c·k_c = Σ base_c (channels 안에서).

    어트리뷰션은 전환을 새로 만들지 않고 채널 사이에 나눌 뿐이라, 보정 후에도 전체 전환 수가 같아야 한다.
    기본 channels = 식별 불가를 뺀 모든 채널.
    """
    chans = channels if channels is not None else [c for c in table.index if c != UNKNOWN]
    t = table.loc[[c for c in chans if c in table.index]]
    t = t[t[base] > 0]
    k = t[model] / t[base]
    k = k * t[base].sum() / (t[base] * k).sum()
    return k


def self_ref_share(df: pd.DataFrame, domain: str = SELF_DOMAINS[0], medium: str = "referral") -> float:
    """정제 전 referral 접점(전환 가중) 중 자기 도메인 비율."""
    tot = hit = 0.0
    for path, src, conv in zip(df["path"], df["source_path"], df["conversions"]):
        for m, s in zip(path.split(SEP), src.split(SEP)):
            if m == medium:
                tot += conv
                hit += conv * (s == domain)
    return hit / tot if tot else 0.0


def single_touch_share(cleaned: pd.DataFrame) -> float:
    w = cleaned["conversions"]
    return float(w[cleaned["n_touches"] == 1].sum() / w.sum()) if w.sum() else 0.0


# 매체 보고 vs 분석 도구 차이 체크리스트 (명세 4-4 4번)
REPORT_GAP_CHECKLIST = [
    "매체는 광고를 **본 것(조회)** 도 전환으로 인정하고, GA4는 **클릭해 들어온 세션**만 봅니다. 메타 API의 조회 후 기간은 2026-01-12부터 1일뿐입니다.",
    "전환 인정 기간이 다릅니다. 메타 광고 세트 기본은 '클릭 후 7일 또는 조회 후 1일'(메타 도움말 검색 요약 기준), GA4는 유입 전환 30일·그 밖의 주요 이벤트 90일이 기본입니다.",
    "같은 구매를 여러 매체가 각자 자기 것으로 보고합니다 (매체 합계 > 실제 구매).",
    "날짜 기준이 다릅니다. 매체는 광고 노출·클릭 날짜, GA4는 전환 날짜로 잡는 경우가 많습니다.",
    "추적 누락: 광고 차단, 쿠키 동의 거부, UTM 누락.",
]
