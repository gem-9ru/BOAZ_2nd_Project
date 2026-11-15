"""내 손님이 찾는 말 찾기 (v2): 연관 키워드 → 묶음 분류 → 추천 키워드 → 누가·언제 찾는지.

- 숫자의 근거 등급: 월 검색수·클릭률은 네이버 검색광고 키워드 도구(B 매체 추산),
  성별·연령·기기·월별은 데이터랩 쇼핑 인사이트 클릭 추이(B 매체 추산, 상대값이라 절대 인원이 아님).
- 네트워크가 안 되거나 키가 없으면 저장본(cache_examples)으로, 그것도 없으면 None. 앱을 멈추지 않는다.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from . import naver_api as api

DEFAULT_CATEGORY = "50000006"  # 쇼핑 인사이트 분야: 식품
HUB = "/shopping/v1/category"
AGE_GROUPS = ("10", "20", "30", "40", "50", "60")
MIN_AGE_SHARE = 0.25           # 헤드라인에 쓸 연령은 비중이 이 이상일 때만 (작은 집단의 큰 배수는 잡음)
HIGH_INDEX = 1.2               # 이 배수 이상일 때만 "분야 평균의 N배"라고 말함
SEASON_PEAK = 1.2              # 최고 달이 평균의 이 배수 이상이면 "N월에 가장 많이"라고 말함

# ── 분류 낱말 ──────────────────────────────────────────────────────────────
MAKING_WORDS = ("만들기", "만드는", "레시피", "키트", "베이킹", "클래스", "원데이", "반죽", "밀키트", "diy", "DIY", "창업", "장사", "재료", "도매", "납품", "학원")
PLACE_WORDS = ("맛집", "근처", "가볼만", "카페", "빵집", "베이커리", "매장", "지점", "주변", "핫플", "데이트", "여행",
               "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "제주", "수원", "성남", "성수", "강남",
               "홍대", "송도", "분당", "일산", "경기", "강원", "전주", "경주", "속초", "여수", "판교", "잠실")
GIFT_WORDS = ("선물", "답례", "기프트", "감사", "축하", "집들이", "상견례", "돌잔치", "하객", "생일", "기념일")
SEASON_WORDS = ("크리스마스", "발렌타인", "밸런타인", "화이트데이", "빼빼로", "할로윈", "핼러윈", "추석", "설날", "명절",
                "어버이날", "스승의날", "어린이날", "연말", "수능", "새해", "시즌", "설선물", "설연휴")
PRODUCT_WORDS = ("쿠키", "휘낭시에", "마들렌", "구움과자", "디저트", "케이크", "스콘", "까눌레", "타르트", "브라우니",
                 "파운드", "마카롱", "테린느", "샌드위치쿠키")
BUYABLE = ("선물·답례", "시즌", "상품")
EXCLUDED = ("제외: 만들기", "제외: 매장·지역")


def _num(value) -> float:
    """숫자·문자 섞인 값을 숫자로. 키워드 도구의 "< 10"은 5로 근사."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text.startswith("<"):
        return 5.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def tier_of(total_qc: float) -> str:
    """월 검색수로 키워드 크기: 대표(1만 이상) · 세부(300~1만) · 롱테일."""
    return "대표" if total_qc >= 10_000 else "세부" if total_qc >= 300 else "롱테일"


def _frame(data: dict) -> pd.DataFrame:
    """keywordstool 응답 → 표."""
    df = pd.DataFrame(data.get("keywordList", []))
    cols = ("relKeyword", "monthlyPcQcCnt", "monthlyMobileQcCnt", "monthlyAveMobileClkCnt", "monthlyAveMobileCtr", "compIdx")
    if df.empty or not set(cols) <= set(df.columns):
        return pd.DataFrame()
    out = pd.DataFrame({
        "keyword": df["relKeyword"],
        "pc_qc": df["monthlyPcQcCnt"].map(_num),
        "mobile_qc": df["monthlyMobileQcCnt"].map(_num),
        "mobile_clicks": df["monthlyAveMobileClkCnt"].map(_num),
        "mobile_ctr": df["monthlyAveMobileCtr"].map(_num),
        "comp": df["compIdx"],
    })
    out["total_qc"] = out["pc_qc"] + out["mobile_qc"]
    out["tier"] = out["total_qc"].map(tier_of)
    return out


def keyword_table(seeds: List[str], online: bool = True) -> Optional[pd.DataFrame]:
    """연관 키워드 표. 열: keyword, total_qc, mobile_qc, pc_qc, mobile_clicks, mobile_ctr(%), comp, tier.
    seeds가 5개를 넘으면 5개씩 나눠 받음. 하나도 못 받으면 None."""
    seeds = [s for s in dict.fromkeys(x.strip().replace(" ", "") for x in seeds if x and x.strip())]
    frames = []
    for i in range(0, len(seeds), 5):
        data = api.keyword_tool(seeds[i:i + 5], online=online)
        if data:
            f = _frame(data)
            if len(f):
                frames.append(f)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True).drop_duplicates("keyword")
    df = df.sort_values("total_qc", ascending=False).reset_index(drop=True)
    return df[["keyword", "total_qc", "mobile_qc", "pc_qc", "mobile_clicks", "mobile_ctr", "comp", "tier"]]


def intent_of(keyword: str, seeds: List[str]) -> str:
    """키워드 하나의 뜻 분류. 제외 낱말이 먼저, 그다음 선물·답례 → 시즌 → 상품 → 관련 낮음."""
    k = keyword.replace(" ", "")
    if any(w in k for w in MAKING_WORDS):
        return "제외: 만들기"
    if any(w in k for w in PLACE_WORDS):
        return "제외: 매장·지역"
    if any(w in k for w in SEASON_WORDS):     # 수능선물처럼 시즌 낱말이 든 말은 선물 낱말보다 먼저 시즌으로
        return "시즌"
    if any(w in k for w in GIFT_WORDS):
        return "선물·답례"
    return "상품" if has_product(k, seeds) else "관련 낮음"


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def is_variant(keyword: str, cores: List[str]) -> bool:
    """내 상품 말의 오타·변형 표기인가 (빼낭시에 ← 휘낭시에). 글자 수가 비슷하고,
    편집 거리 1 이하이거나 끝 세 글자(낭시에)가 같은 경우. 같은 말은 제외."""
    k = keyword.replace(" ", "")
    for c in cores:
        if len(c) < 3 or k == c or abs(len(k) - len(c)) > 1:
            continue
        if _edit_distance(k, c) <= 1 or (len(c) >= 4 and len(k) >= 4 and k[-3:] == c[-3:] and _edit_distance(k, c) <= 2):
            return True
    return False


def has_product(keyword: str, seeds: List[str]) -> bool:
    """상품 낱말(쿠키·휘낭시에 …)이나 내가 입력한 말(오타·변형 포함)이 들어 있는가."""
    k = keyword.replace(" ", "")
    clean = [s.replace(" ", "") for s in seeds if s]
    return (any(w in k for w in PRODUCT_WORDS) or any(s in k or k in s for s in clean)
            or is_variant(k, clean + list(PRODUCT_WORDS)))


def classify(df: pd.DataFrame, seeds: List[str]) -> pd.DataFrame:
    """키워드 표에 intent 열을 붙임: 선물·답례 | 시즌 | 상품 | 제외: 만들기 | 제외: 매장·지역 | 관련 낮음."""
    out = df.copy()
    out["intent"] = out["keyword"].map(lambda k: intent_of(k, seeds))
    return out


def group_summary(kw: pd.DataFrame) -> pd.DataFrame:
    """뜻별 요약: intent, count(키워드 수), total_qc(검색수 합), mobile_ctr(평균 클릭률 %), top_keyword(대표 키워드)."""
    rows = []
    for intent, g in kw.groupby("intent", sort=False):
        ctr = g.loc[g["mobile_ctr"] > 0, "mobile_ctr"]
        rows.append({"intent": intent, "count": len(g), "total_qc": float(g["total_qc"].sum()),
                     "mobile_ctr": round(float(ctr.mean()), 2) if len(ctr) else 0.0,
                     "top_keyword": g.sort_values("total_qc", ascending=False).iloc[0]["keyword"]})
    return pd.DataFrame(rows, columns=["intent", "count", "total_qc", "mobile_ctr", "top_keyword"]) \
        .sort_values("total_qc", ascending=False).reset_index(drop=True)


def recommend(kw: pd.DataFrame, limit: int = 10, seeds: Optional[List[str]] = None) -> List[str]:
    """살 만한 키워드(선물·답례·시즌·상품, 내 상품 낱말이 들어간 것만) 중 세부(300~1만)를 검색수 순으로, 모자라면 대표·작은 키워드로 채움 (검색수 100 이상)."""
    pool = kw[kw["intent"].isin(BUYABLE) & kw["keyword"].map(lambda k: has_product(k, seeds or []))].sort_values("total_qc", ascending=False)
    detail = pool[pool["tier"] == "세부"]
    rest = pool[(pool["tier"] != "세부") & (pool["total_qc"] >= 100)]
    return list(pd.concat([detail, rest])["keyword"].head(limit))


def negative_list(kw: pd.DataFrame, limit: int = 20) -> List[str]:
    """빼야 할 키워드: 제외 묶음 상위 + 관련 낮음 상위 (관련 낮음 자리를 따로 남겨 두고, 검색수 순으로 합침)."""
    low_n = 5
    low = kw[kw["intent"] == "관련 낮음"].sort_values("total_qc", ascending=False).head(low_n)
    ex = kw[kw["intent"].isin(EXCLUDED)].sort_values("total_qc", ascending=False).head(max(limit - len(low), 0))
    both = pd.concat([ex, low]).sort_values("total_qc", ascending=False)
    return list(both["keyword"].head(limit))


# ── 누가·언제 찾나 (쇼핑 인사이트) ────────────────────────────────────────
def _sums(data: Optional[dict]) -> Dict[str, float]:
    """응답 results[0].data[]의 group별 ratio 합."""
    out: Dict[str, float] = {}
    try:
        for row in data["results"][0]["data"]:
            out[str(row["group"])] = out.get(str(row["group"]), 0.0) + float(row["ratio"])
    except (TypeError, KeyError, IndexError, ValueError):
        return {}
    return out


def _shares(sums: Dict[str, float], groups) -> Dict[str, float]:
    total = sum(sums.get(g, 0.0) for g in groups)
    return {g: sums.get(g, 0.0) / total for g in groups} if total > 0 else {}


def _monthly(data: Optional[dict]) -> Dict[str, float]:
    """월별 상대 검색량 (가장 많은 달 = 100). 같은 달의 group(기기·성별)을 더함."""
    by: Dict[str, float] = {}
    try:
        for row in data["results"][0]["data"]:
            month = str(row["period"])[:7]
            by[month] = by.get(month, 0.0) + float(row["ratio"])
    except (TypeError, KeyError, IndexError, ValueError):
        return {}
    top = max(by.values()) if by else 0
    return {m: round(v / top * 100, 1) for m, v in sorted(by.items())} if top > 0 else {}


def category_baseline(category: str = DEFAULT_CATEGORY, online: bool = True) -> Optional[dict]:
    """분야 전체의 성별·연령 비중 {"female", "male", "ages": {...}}. 못 받으면 None."""
    g = _shares(_sums(api.shopping_insight(f"{HUB}/gender", category, None, online)), ("f", "m"))
    a = _shares(_sums(api.shopping_insight(f"{HUB}/age", category, None, online)), AGE_GROUPS)
    if not g or not a:
        return None
    return {"female": g["f"], "male": g["m"], "ages": a}


def audience_index(female: float, ages: Dict[str, float], baseline: Optional[dict]) -> Dict[str, float]:
    """키워드 비중 ÷ 분야 전체 비중. baseline이 없으면 빈 dict."""
    if not baseline:
        return {}
    idx = {}
    if baseline.get("female"):
        idx["female"] = round(female / baseline["female"], 2)
    if baseline.get("male"):
        idx["male"] = round((1 - female) / baseline["male"], 2)
    for age, share in ages.items():
        base = baseline["ages"].get(age, 0)
        if base > 0:
            idx[age] = round(share / base, 2)
    return idx


def audience(keyword: str, category: str = DEFAULT_CATEGORY, online: bool = True) -> Optional[dict]:
    """키워드를 찾는 사람의 성별·연령·기기·월별. 성별이나 연령을 못 받으면 None. 근거 등급 B."""
    g = _shares(_sums(api.shopping_insight(f"{HUB}/keyword/gender", category, keyword, online)), ("f", "m"))
    a = _shares(_sums(api.shopping_insight(f"{HUB}/keyword/age", category, keyword, online)), AGE_GROUPS)
    if not g or not a:
        return None
    device = api.shopping_insight(f"{HUB}/keyword/device", category, keyword, online)
    dev = _shares(_sums(device), ("mo", "pc"))
    monthly = _monthly(device) or _monthly(api.shopping_insight(f"{HUB}/keyword/gender", category, keyword, online))
    peak = max(monthly, key=monthly.get) if monthly else None
    return {"female": round(g["f"], 3), "ages": {k: round(v, 3) for k, v in a.items()},
            "mobile": round(dev["mo"], 3) if dev else None,
            "monthly": monthly, "peak_month": int(peak[5:7]) if peak else None,
            "index": audience_index(g["f"], a, category_baseline(category, online)), "grade": "B"}


def headline(keyword: str, aud: Optional[dict], fallback_qc: Optional[float] = None) -> str:
    """한 줄 요약. 예: "답례품쿠키를 찾는 사람은 30대 여성이 분야 평균의 2.8배, 11월에 가장 많이 찾아요"."""
    if not aud:
        if fallback_qc:
            return f"'{keyword}'은(는) 한 달에 약 {int(fallback_qc):,}번 검색돼요"
        return f"'{keyword}'를 찾는 사람 정보는 아직 못 가져왔어요"
    ages = {a: s for a, s in aud["ages"].items() if s >= MIN_AGE_SHARE}
    idx = aud.get("index", {})
    best = max(ages, key=lambda a: (idx.get(a, 0), ages[a])) if ages else max(aud["ages"], key=aud["ages"].get)
    sex = "여성" if aud["female"] >= 0.6 else "남성" if aud["female"] <= 0.4 else ""
    who = f"{best}대 {sex}".strip() + ("이" if sex else "가")
    mult = idx.get(best)
    strong = bool(mult and mult >= HIGH_INDEX)
    monthly = aud.get("monthly") or {}
    seasonal = bool(aud.get("peak_month") and monthly
                    and max(monthly.values()) >= SEASON_PEAK * (sum(monthly.values()) / len(monthly)))
    head = f"{keyword}{_obj(keyword)} 찾는 사람은 {who}"
    when = f", {aud['peak_month']}월에 가장 많이 찾아요" if seasonal else ""
    if strong:
        return f"{head} 분야 평균의 {mult:g}배" + (when or "예요")
    return f"{head} 가장 많고{when}" if seasonal else f"{head} 가장 많아요"


def _obj(word: str) -> str:
    """목적격 조사 (을/를)."""
    last = word[-1]
    if "가" <= last <= "힣":
        return "을" if (ord(last) - 0xAC00) % 28 else "를"
    return "을(를)"


def audience_targets(kw: pd.DataFrame, rec: List[str], n: int = 3) -> List[str]:
    """손님을 조회할 키워드 n개: 추천 중 선물·답례 → 시즌 → 상품 순 (같은 묶음 안에서는 추천 순서)."""
    rank = {"선물·답례": 0, "시즌": 1, "상품": 2}
    intent = dict(zip(kw["keyword"], kw["intent"]))
    return sorted(rec, key=lambda k: rank.get(intent.get(k), 3))[:n]


@dataclass
class MarketReport:
    seeds: List[str]
    groups: pd.DataFrame
    keywords: pd.DataFrame
    recommended: List[str] = field(default_factory=list)
    negatives: List[str] = field(default_factory=list)
    audiences: Dict[str, dict] = field(default_factory=dict)
    headline: str = ""


def build(seeds: List[str], online: bool = True) -> Optional[MarketReport]:
    """한 번에: 키워드 표 → 분류 → 추천·제외 → 추천 상위 3개의 손님 → 한 줄 요약. 키워드를 못 받으면 None."""
    table = keyword_table(seeds, online)
    if table is None:
        return None
    kw = classify(table, seeds)
    rec = recommend(kw, seeds=seeds)
    auds = {}
    for k in audience_targets(kw, rec):
        a = audience(k, online=online)
        if a:
            auds[k] = a
    top = next(iter(auds), rec[0] if rec else None)
    qc = float(kw.loc[kw["keyword"] == top, "total_qc"].iloc[0]) if top else None
    return MarketReport(seeds=list(seeds), groups=group_summary(kw), keywords=kw, recommended=rec,
                        negatives=negative_list(kw), audiences=auds,
                        headline=headline(top, auds.get(top), qc) if top else "")
