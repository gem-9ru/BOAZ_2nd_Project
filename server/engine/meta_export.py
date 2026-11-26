"""메타 결과 파일 1개 → 일별 표(meta_daily) + 노출 위치별 표(meta_placement).

받는 형식 두 가지:
1. 광고 관리자 내보내기 (분석 기준 '일 × 노출 위치'): 머리글 한 줄, 행 = 날짜·광고 세트·노출 위치.
   일별 표는 날짜·광고 세트로 더해서 만든다 (도달도 더한다 → 겹치는 사람을 두 번 세므로 빈도는 '적어도 ○번'으로만 쓴다).
   광고 세트 예산·유형 열이 있으면 기간 총예산도 읽는다 (Bundle.budget → ALT-12 예산 덜 씀).
2. 팀 실측 정리본 (오븐로그, 세로형): section·ad_set·date·platform·position·metric·value 열.
   '5_부록_일자별' → 일별 표, '3_노출위치' → 노출 위치별 표.
캠페인 목표 열이 없으면 이번 범위(트래픽)로 채운다.
"""
import io
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from .ingest import Bundle, clean

OBJECTIVE = "트래픽"
LONG_COLUMNS = {"section", "ad_set", "metric", "value"}
NO_DATA = "이 파일에는 광고 결과가 없어요 (메타가 'No data available'로 내보냈어요). 광고가 실제로 나간 기간을 골라 다시 내보내 주세요."
NEED_CLICKS = "링크 클릭 열이 없어요. 광고 관리자에서 열에 '링크 클릭'을 넣어 다시 내보내 주세요."
METRIC_NAMES = {"지출(원)": "spend", "노출": "impressions", "링크 클릭": "link_clicks", "랜딩 페이지 조회": "landing_page_views",
                "오픈 알림(Lead)": "actions"}   # 들어온 뒤 행동 (알림 신청)
PLATFORM_NAMES = {"facebook": "Facebook", "instagram": "Instagram", "audience_network": "Audience Network", "messenger": "Messenger"}
SUMMABLE = ["spend", "impressions", "link_clicks", "landing_page_views"]

Source = Union[str, Path, io.IOBase, bytes]


def _read_csv(src: Source) -> pd.DataFrame:
    raw = src if isinstance(src, bytes) else (src.read() if hasattr(src, "read") else Path(src).read_bytes())
    if raw[:2] == b"PK":   # 엑셀(.xlsx)은 zip이라 'PK'로 시작 (화면설계서 v4.2 AN-00: .csv / .xlsx 허용)
        return pd.read_excel(io.BytesIO(raw))
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
        if has_placement:   # 일×노출 위치 → 날짜·광고 세트로 더함 (비율은 다시 계산하므로 뺀다)
            # 도달(reach_daily)도 더한다: 겹치는 사람을 두 번 세므로 '본 사람 수'의 최댓값이 된다
            # → 노출 ÷ 이 합 = 빈도의 최솟값 ('적어도 ○번'). 이 값이 기준을 넘으면 실제 빈도도 넘는다.
            keep = ["date", "adset", "campaign_objective"] + [c for c in SUMMABLE + ["actions", "reach_daily"] if c in daily.df.columns]
            daily.df = daily.df[keep].groupby(["date", "adset", "campaign_objective"], as_index=False).sum()
        b.tables["meta_daily"] = daily
        b.budget = _budget(df, daily.df)
        b.rankings = _rankings(df)
    return b


# 메타 광고 관련성 진단 (광고 관리자 열: 품질 순위 · 참여율 순위 · 전환율 순위). 같은 타깃을 두고 경쟁하는 광고 대비 순위.
# 노출이 적으면 '-'로 비어 있다 → 건너뛴다 (v4 2장: 있으면 퍼널 진단의 보조 신호, 없으면 건너뜀)
RANKING_COLUMNS = {"quality": ["품질 순위", "Quality ranking"],
                   "engagement": ["참여율 순위", "Engagement rate ranking"],
                   "conversion": ["전환율 순위", "Conversion rate ranking"]}


def _rank(text) -> Optional[str]:
    """'평균 이하 - 하위 35%' → below, '평균 이상' → above, '평균' → average. '-'·빈칸·모르는 글자 → None."""
    t = str(text).strip().lower()
    if not t or t in ("-", "nan", "none") or "알 수 없" in t or "unknown" in t:
        return None
    if "이하" in t or "below" in t:
        return "below"
    if "이상" in t or "above" in t:
        return "above"
    if "평균" in t or "average" in t:
        return "average"
    return None


def _rankings(raw: pd.DataFrame) -> dict:
    """광고 세트마다 순위 3개 (그 세트 줄에서 가장 많이 나온 값). 열이 없거나 다 비었으면 빈 dict."""
    set_col = next((c for c in ("광고 세트 이름", "광고 세트", "Ad set name") if c in raw.columns), None)
    if not set_col:
        return {}
    out: dict = {}
    for key, names in RANKING_COLUMNS.items():
        col = next((c for c in names if c in raw.columns), None)
        if not col:
            continue
        rows = raw[[set_col, col]].dropna(subset=[set_col])
        for aset, vals in rows.groupby(set_col)[col]:
            got = [r for r in map(_rank, vals) if r]
            if got:
                out.setdefault(_short(aset), {})[key] = max(set(got), key=got.count)
    return out


BUDGET_COLUMNS = [("광고 세트 예산", "광고 세트 예산 유형", "adset"), ("Ad set budget", "Ad set budget type", "adset"),
                  ("캠페인 예산", "캠페인 예산 유형", "campaign"), ("Campaign budget", "Campaign budget type", "campaign")]


def _budget_kind(text) -> Optional[str]:
    """예산 유형 글자 → 'daily'(하루 예산) / 'lifetime'(기간 총예산). 모르는 글자면 None (추측하지 않음)."""
    t = str(text).strip().lower()
    if any(w in t for w in ("일일", "하루", "daily")):
        return "daily"
    if any(w in t for w in ("총", "기간", "lifetime")):
        return "lifetime"
    return None


def _budget(raw: pd.DataFrame, daily: pd.DataFrame) -> Optional[dict]:
    """메타 내보내기에 들어 있는 예산 열 → 이 기간에 쓰기로 한 총예산 (ALT-12 예산 덜 씀).
    광고 세트 예산이 세트마다 있으면 그 합, 없으면(캠페인 예산 사용) 캠페인 예산. 금액·유형을 못 읽으면 None."""
    days = int(daily["date"].nunique()) if "date" in daily.columns else 0
    set_col = next((c for c in ("광고 세트 이름", "광고 세트", "Ad set name") if c in raw.columns), None)
    for amount_col, kind_col, level in BUDGET_COLUMNS:
        if amount_col not in raw.columns or kind_col not in raw.columns:
            continue
        rows = raw[[amount_col, kind_col] + ([set_col] if set_col and level == "adset" else [])].copy()
        rows["amount"] = pd.to_numeric(rows[amount_col].astype(str).str.replace(",", "").str.replace("원", ""), errors="coerce")
        rows["kind"] = rows[kind_col].map(_budget_kind)
        rows = rows[(rows["amount"] > 0) & rows["kind"].notna()]
        if level == "adset":
            if not set_col or rows.empty:
                continue
            per_set = rows.groupby(set_col).first()
            if len(per_set) < int(daily["adset"].nunique()):   # 예산을 못 읽은 세트가 있으면 합이 틀려진다
                continue
        else:
            if rows.empty:
                continue
            per_set = rows.head(1)
        total = float(sum(a * (days if k == "daily" else 1) for a, k in zip(per_set["amount"], per_set["kind"])))
        if total > 0 and (days or set(per_set["kind"]) == {"lifetime"}):
            return {"total": total, "level": level, "kinds": sorted(set(per_set["kind"]))}
    return None


def read_export(src: Source) -> Bundle:
    try:
        df = _read_csv(src)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return Bundle(problems=["파일이 비어 있거나 CSV가 아니에요. 광고 관리자에서 CSV로 내보내 주세요."])
    if df.empty or df.iloc[:, 0].astype(str).str.contains("No data available", case=False).all():
        return Bundle(problems=[NO_DATA])
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
