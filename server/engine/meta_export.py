"""메타 결과 파일 1개 → 일별 표(meta_daily) + 노출 위치별 표(meta_placement).

받는 형식 두 가지:
1. 광고 관리자 내보내기 (분석 기준 '일 × 노출 위치'): 머리글 한 줄, 행 = 날짜·광고 세트·노출 위치.
   일별 표는 날짜·광고 세트로 더해서 만든다 (도달은 더할 수 없어 뺀다 → 빈도 규칙은 '데이터 없음').
2. 팀 실측 정리본 (오븐로그, 세로형): section·ad_set·date·platform·position·metric·value 열.
   '5_부록_일자별' → 일별 표, '3_노출위치' → 노출 위치별 표.
캠페인 목표 열이 없으면 이번 범위(트래픽)로 채운다.
"""
import io
from pathlib import Path
from typing import Union

import pandas as pd

from .ingest import Bundle, clean

OBJECTIVE = "트래픽"
LONG_COLUMNS = {"section", "ad_set", "metric", "value"}
NEED_CLICKS = "링크 클릭 열이 없어요. 광고 관리자에서 열에 '링크 클릭'을 넣어 다시 내보내 주세요."
METRIC_NAMES = {"지출(원)": "spend", "노출": "impressions", "링크 클릭": "link_clicks", "랜딩 페이지 조회": "landing_page_views",
                "오픈 알림(Lead)": "actions"}   # 들어온 뒤 행동 (알림 신청)
PLATFORM_NAMES = {"facebook": "Facebook", "instagram": "Instagram", "audience_network": "Audience Network", "messenger": "Messenger"}
SUMMABLE = ["spend", "impressions", "link_clicks", "landing_page_views"]

Source = Union[str, Path, io.IOBase, bytes]


def _read_csv(src: Source) -> pd.DataFrame:
    raw = src if isinstance(src, bytes) else (src.read() if hasattr(src, "read") else Path(src).read_bytes())
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(raw), encoding="utf-8", encoding_errors="replace")


def _short(name: str) -> str:
    """'A_자동노출위치 (어드밴티지+ …)' → 'A_자동노출위치' (괄호 설명은 화면에 길어서 뺀다)."""
    return str(name).split(" (")[0].strip()


def _from_long(df: pd.DataFrame) -> Bundle:
    b = Bundle()
    df = df[df["metric"].isin(METRIC_NAMES)].copy()
    df["metric"] = df["metric"].map(METRIC_NAMES)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["adset"] = df["ad_set"].map(_short)

    daily = df[df["section"] == "5_부록_일자별"].pivot_table(index=["date", "adset"], columns="metric",
                                                           values="value", aggfunc="sum").reset_index()
    daily = daily.fillna({c: 0 for c in SUMMABLE if c in daily.columns})
    daily["campaign_objective"] = OBJECTIVE
    t, problems = clean(daily, "meta_daily")
    b.problems += problems
    if t is not None and len(t.df):
        b.tables["meta_daily"] = t

    place = df[df["section"] == "3_노출위치"].copy()
    if len(place):
        place["placement"] = place["platform"].map(lambda p: PLATFORM_NAMES.get(str(p), str(p))) + " " + place["position"].astype(str)
        wide = place.pivot_table(index=["adset", "placement"], columns="metric", values="value", aggfunc="sum").reset_index()
        t, problems = clean(wide, "meta_placement")
        b.problems += problems
        if t is not None and len(t.df):
            b.tables["meta_placement"] = t
    return b


def _with_platform(df: pd.DataFrame) -> pd.DataFrame:
    """한국어 내보내기의 '노출 위치'는 '피드'처럼 플랫폼이 빠진 값이 있다 → '플랫폼 노출 위치'로 합친다.
    ('Instagram 릴스'처럼 이미 플랫폼으로 시작하면 그대로.) 진단은 'Audience Network'·'Instagram' 글자로 노출 위치를 구분한다."""
    plat = next((c for c in ("플랫폼", "Platform") if c in df.columns), None)
    pos = next((c for c in ("노출 위치", "Placement") if c in df.columns), None)
    if not plat or not pos:
        return df
    def join(p, q):
        if pd.isna(q) or pd.isna(p):
            return q
        p, q = str(p).strip(), str(q).strip()
        return q if q.lower().startswith(p.lower()) else f"{p} {q}"
    out = df.copy()
    out[pos] = [join(p, q) for p, q in zip(out[plat], out[pos])]
    return out


def _from_export(df: pd.DataFrame) -> Bundle:
    b = Bundle()
    df = _with_platform(df)
    placed, problems = clean(df.assign(**{"캠페인 목표": OBJECTIVE}) if "캠페인 목표" not in df.columns else df, "meta_placement")
    if placed is not None:   # 맨 아래 '합계' 행처럼 광고 세트·노출 위치가 빈 행은 뺀다
        placed.df = placed.df[placed.df["adset"].notna() & placed.df["placement"].notna()].reset_index(drop=True)
    has_placement = placed is not None and len(placed.df) > 0
    if has_placement:
        b.tables["meta_placement"] = placed
    base = df.copy()
    if not any(c in base.columns for c in ("캠페인 목표", "목표", "Objective")):
        base["캠페인 목표"] = OBJECTIVE
    daily, daily_problems = clean(base, "meta_daily")
    b.problems += daily_problems
    if daily is not None:   # 합계 행처럼 광고 세트가 빈 행은 뺀다 (날짜가 있어도)
        daily.df = daily.df[daily.df["adset"].notna()].reset_index(drop=True)
    if daily is not None and len(daily.df):
        if has_placement:   # 일×노출 위치 → 날짜·광고 세트로 더함 (비율·도달은 다시 계산하거나 뺀다)
            keep = ["date", "adset", "campaign_objective"] + [c for c in SUMMABLE + ["actions"] if c in daily.df.columns]
            daily.df = daily.df[keep].groupby(["date", "adset", "campaign_objective"], as_index=False).sum()
        b.tables["meta_daily"] = daily
    return b


def read_export(src: Source) -> Bundle:
    try:
        df = _read_csv(src)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return Bundle(problems=["파일이 비어 있거나 CSV가 아니에요. 광고 관리자에서 CSV로 내보내 주세요."])
    if LONG_COLUMNS <= set(df.columns):
        if "date" not in df.columns:
            return Bundle(problems=["날짜(date) 열이 없어요. 일별 숫자가 든 파일을 올려 주세요."])
        b = _from_long(df)
    else:
        b = _from_export(df)
    daily = b.tables.get("meta_daily")
    if daily is not None and "link_clicks" not in daily.df.columns:   # 모든 진단이 링크 클릭에 기댄다
        del b.tables["meta_daily"]
        b.problems.append(NEED_CLICKS)
    return b
