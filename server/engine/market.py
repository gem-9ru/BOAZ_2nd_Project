"""내 손님이 찾는 말 찾기 (v2): 연관 키워드 → 묶음 분류 → 추천 키워드 → 누가·언제 찾는지.

- 숫자의 근거 등급: 월 검색수·클릭률은 네이버 검색광고 키워드 도구(B 매체 추산),
  성별·연령·기기·월별은 데이터랩 쇼핑 인사이트 클릭 추이(B 매체 추산, 상대값이라 절대 인원이 아님).
- 네트워크가 안 되거나 키가 없으면 저장본(cache_examples)으로, 그것도 없으면 None. 앱을 멈추지 않는다.
"""
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set, Tuple

import pandas as pd

from . import naver_api as api, specs

log = logging.getLogger("coach.market")

DEFAULT_CATEGORY = "50000006"  # 쇼핑 인사이트 분야: 식품
HUB = "/shopping/v1/category"
AGE_GROUPS = ("10", "20", "30", "40", "50", "60")
MIN_AGE_SHARE = 0.25           # 헤드라인에 쓸 연령은 비중이 이 이상일 때만 (작은 집단의 큰 배수는 잡음)
HIGH_INDEX = 1.2               # 이 배수 이상일 때만 "분야 평균의 N배"라고 말함
SEASON_PEAK = 1.2              # 최고 달이 평균의 이 배수 이상이면 "N월에 가장 많이"라고 말함

# ── 분류 낱말: 분야에 묶이지 않는 공통 낱말만 사양(rules.yaml find:)에서 읽는다. 상품 낱말은 사장님이 입력한 말 ──
_FIND = specs.find()
CATEGORIES: List[dict] = [dict(c) for c in _FIND["categories"]]
MAKING_WORDS = tuple(_FIND["common"]["making"])
PLACE_WORDS = tuple(_FIND["common"]["place"])
GIFT_WORDS = tuple(_FIND["common"]["gift"])
SEASON_WORDS = tuple(_FIND["common"]["season"])
MODIFIER_GROUPS = {g: tuple(w) for g, w in _FIND["modifier_groups"].items()}
MODIFIER_SKIP = tuple(_FIND["modifier_skip"])
MODIFIER_SKIP_EXACT = tuple(_FIND.get("modifier_skip_exact", []))
GUESS_MIN_POINTS = 6           # 분야 추정: 지난 12개월 중 이 달 수 이상 자료가 있어야 함
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
    # 네이버는 10 미만을 "< 10" 글자로 준다 (데이터_수집_전처리_가이드.md 응답 필드 표). 그 칸 수 0·1·2 → 화면이 '20번 미만'·'약 N번'으로
    is_few = lambda v: str(v).strip().startswith("<")   # noqa: E731
    out["under"] = df["monthlyPcQcCnt"].map(is_few).astype(int) + df["monthlyMobileQcCnt"].map(is_few).astype(int)
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
    return df[["keyword", "total_qc", "mobile_qc", "pc_qc", "mobile_clicks", "mobile_ctr", "comp", "tier", "under"]]


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


def product_words(product: str, seeds: List[str]) -> List[str]:
    """내 상품인지 맞춰 볼 낱말: 상품 이름(띄어쓰기 없앰), 마지막 조각(머리 명사, 2글자 이상), seeds(띄어쓰기 없앰). 중복 없음.
    앞 조각(캠핑 의자의 '캠핑')은 넣지 않는다: '캠핑카대여'·'캠핑텐트'가 내 상품으로 잡히지 않게."""
    pieces = product.split()
    head = [pieces[-1]] if pieces and len(pieces[-1]) >= 2 else []
    words = [product.replace(" ", "")] + head + [s.replace(" ", "") for s in seeds]
    return [w for w in dict.fromkeys(words) if w]


def strip_words(product: str, seeds: List[str]) -> List[str]:
    """꾸밈말을 뽑을 때 키워드에서 지울 낱말: 상품 이름, 띄어쓰기로 나눈 2글자 이상 조각 전부, seeds. 중복 없음.
    ('경량캠핑의자'에서 '캠핑'까지 지워 '경량'만 남게)"""
    words = [product.replace(" ", "")] + [p for p in product.split() if len(p) >= 2] + [s.replace(" ", "") for s in seeds]
    return [w for w in dict.fromkeys(words) if w]


def has_product(keyword: str, seeds: List[str]) -> bool:
    """내가 입력한 낱말(seeds)이나 그 오타·변형이 들어 있는가. 분야별 상품 낱말 목록은 쓰지 않는다.
    검색어가 내 낱말보다 짧으면 끝부분(머리 명사, 2글자 이상)일 때만 상품: '의자'⊂'캠핑의자'는 상품, '캠핑'·'립'은 아님."""
    k = keyword.replace(" ", "")
    clean = [s.replace(" ", "") for s in seeds if s]
    return any(s in k or (len(k) >= 2 and s.endswith(k)) for s in clean) or is_variant(k, clean)


PEAK_MAX = 50                  # 분야 추정: 최고 달 검색 수를 1~이 값 안에서 찾는다 (못 찾으면 그보다 많은 것으로 봄)
PEAK_TOLERANCE = 0.02          # ratio×n/100이 정수에서 이만큼 안이면 정수로 봄 (응답의 반올림)


def _category_ratios(product: str, online: bool) -> Dict[str, List[float]]:
    """분야 12개별 달별 상대값 목록 (값이 없거나 못 받으면 빈 목록). 분야마다 한 번씩만 조회."""
    name = product.replace(" ", "")
    if not name:
        return {}
    return {c["code"]: api.category_keyword_ratios(c["code"], name, online) or [] for c in CATEGORIES}


def peak_count(ratios: List[float]) -> Optional[int]:
    """가장 많은 달의 검색(클릭) 수 추정: ratio는 (그 달 수 ÷ 최고 달 수 × 100)이라, 최고 달 수 n이 작으면
    모든 ratio×n/100이 정수에 가깝다. 그런 가장 작은 n(1~PEAK_MAX). 없으면 None (= PEAK_MAX보다 많음)."""
    vals = [r for r in ratios if r > 0]
    if not vals:
        return None
    for n in range(1, PEAK_MAX + 1):
        if all(abs(r * n / 100 - round(r * n / 100)) <= PEAK_TOLERANCE for r in vals):
            return n
    return None


def category_guess(product: str, online: bool = True) -> Tuple[Optional[str], List[str]]:
    """분야 12개를 한 번만 조회해 (추정 code, 후보 code들)를 함께 돌려줌.
    순위: 자료가 있는 달 수가 많은 순 → 같으면 최고 달 검색 수 추정(peak_count, None은 아주 많음)이 큰 순.
    추정: 1위가 2위보다 그 순위에서 확실히 앞서고 달 수가 6 이상일 때만, 아니면 None(사장님께 묻는다).
    후보: 달 수가 6 이상이고 가장 많은 달 수와 같은 분야를 순위대로 최대 3개 (같으면 분야 목록 순서)."""
    ratios = _category_ratios(product, online)
    if not ratios:
        return None, []
    order = {c["code"]: i for i, c in enumerate(CATEGORIES)}
    peaks = {c: peak_count(r) for c, r in ratios.items()}
    points = {c: len(r) for c, r in ratios.items()}
    key = {c: (points[c], float("inf") if peaks[c] is None else peaks[c]) for c in ratios}
    ranked = sorted(ratios, key=lambda c: (-key[c][0], -key[c][1], order[c]))
    lead = ranked[0]
    clear = len(ranked) == 1 or key[lead] > key[ranked[1]]
    code = lead if clear and points[lead] >= GUESS_MIN_POINTS else None
    top = points[lead]
    cands = [c for c in ranked if points[c] >= GUESS_MIN_POINTS and points[c] == top][:3]
    names = {c["code"]: c["name"] for c in CATEGORIES}
    log.info("category guess product=%s code=%s candidates=%s top=%s", product, code, ",".join(cands) or "-",
             ",".join(f"{names[c]}:{points[c]}/{peaks[c] or 'many'}" for c in ranked[:3]))
    return code, cands


def guess_category(product: str, online: bool = True) -> Optional[str]:
    return category_guess(product, online)[0]


def category_candidates(product: str, online: bool = True) -> List[str]:
    return category_guess(product, online)[1]


def classify(df: pd.DataFrame, seeds: List[str]) -> pd.DataFrame:
    """키워드 표에 intent 열을 붙임: 선물·답례 | 시즌 | 상품 | 제외: 만들기 | 제외: 매장·지역 | 관련 낮음."""
    out = df.copy()
    out["intent"] = out["keyword"].map(lambda k: intent_of(k, seeds))
    return out


def _modifier_of(keyword: str, seeds: List[str], strip: Optional[List[str]] = None) -> Optional[str]:
    """키워드에서 상품 낱말(seeds + strip)·선물·시즌·지역·군더더기(추천 등)를 지우고 남은 말.
    seeds(맞추기 낱말)가 안 들어 있거나 2~6자가 아니거나 숫자뿐이면 None."""
    k = keyword.replace(" ", "")
    if not any(s.replace(" ", "") in k for s in seeds if s):
        return None
    mine = sorted({s.replace(" ", "") for s in list(seeds) + list(strip or []) if s}, key=len, reverse=True)
    for w in mine:
        k = k.replace(w, "")
    for w in sorted(GIFT_WORDS + SEASON_WORDS + PLACE_WORDS + MODIFIER_SKIP, key=len, reverse=True):
        k = k.replace(w, "")
    return k if 2 <= len(k) <= 6 and not k.isdigit() and k not in MODIFIER_SKIP_EXACT else None


MODIFIER_POOL = 30   # build가 뽑는 꾸밈말 수. 서버가 브랜드를 거르고 MAX_MODIFIERS개만 보낸다


def modifiers(kw: pd.DataFrame, seeds: List[str], limit: int = 15, strip: Optional[List[str]] = None) -> List[dict]:
    """손님이 상품과 함께 검색하는 꾸밈말(좋은 점 후보). 뜻이 '상품'인 키워드만 보고, 같은 꾸밈말은 검색수를 더해
    검색수 순 limit개. strip은 더 지울 상품 낱말(strip_words). 각 항목: word, group(포장|맛·재료|배송|양|그 밖), total_qc, examples(최대 3)."""
    found: Dict[str, dict] = {}
    for row in kw[kw["intent"] == "상품"].sort_values("total_qc", ascending=False).itertuples():
        word = _modifier_of(row.keyword, seeds, strip)
        if word is None:
            continue
        item = found.setdefault(word, {"word": word, "total_qc": 0, "examples": []})
        item["total_qc"] += int(row.total_qc)
        if len(item["examples"]) < 3:
            item["examples"].append(row.keyword)
    # 오타·다른 표기(앤드그레인 ← 엔드그레인, 소세지 ← 소시지)는 많이 찾는 쪽 하나로 합친다 (3글자 이상만: 짧은 말은 엉뚱하게 붙음)
    merged: Dict[str, dict] = {}
    for item in sorted(found.values(), key=lambda m: m["total_qc"], reverse=True):
        host = next((m for w, m in merged.items() if is_variant(item["word"], [w])), None)
        if host:
            host["total_qc"] += item["total_qc"]
            host["examples"] = (host["examples"] + item["examples"])[:3]
        else:
            merged[item["word"]] = item
    found = merged
    for item in found.values():
        item["group"] = next((g for g, ws in MODIFIER_GROUPS.items() if any(w in item["word"] for w in ws)), "그 밖")
    ranked = sorted(found.values(), key=lambda m: m["total_qc"], reverse=True)[:max(limit, 0)]
    return [{"word": m["word"], "group": m["group"], "total_qc": m["total_qc"], "examples": m["examples"]} for m in ranked]


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


BY_AGE_MIN = 0.05   # 이보다 적게 찾는 나이대는 성별을 따로 묻지 않음 (호출 수를 줄임)


def female_by_age(keyword: str, category: str, ages: Dict[str, float], online: bool = True) -> Dict[str, float]:
    """나이대마다 그 안의 여성 비중 (쇼핑인사이트 성별 + ages 필터). 막대를 여성·남성으로 나눠 그리는 데 씀. 못 받은 나이대는 빠짐.
    /research에서는 부르지 않는다 (호출 수 한도): 화면에 그림이 열릴 때 /audience/split으로 따로 받는다."""
    out: Dict[str, float] = {}
    for age, share in ages.items():
        if share < BY_AGE_MIN:
            continue
        g = _shares(_sums(api.shopping_insight(f"{HUB}/keyword/gender", category, keyword, online, ages=[age])), ("f", "m"))
        if g:
            out[age] = round(g["f"], 3)
    return out


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


def top_age(aud: dict) -> str:
    """대표 연령대: 비중이 MIN_AGE_SHARE 이상인 연령대 중 분야 평균 대비 배수가 가장 큰 것 (한 줄 요약과 같은 기준)."""
    ages = {a: s for a, s in aud["ages"].items() if s >= MIN_AGE_SHARE}
    idx = aud.get("index", {})
    return max(ages, key=lambda a: (idx.get(a, 0), ages[a])) if ages else max(aud["ages"], key=aud["ages"].get)


def lead_audience(auds: Dict[str, dict]) -> Optional[str]:
    """대표 키워드: 대표 연령대의 분야 평균 대비 배수가 가장 큰 것 (같으면 앞 순서). 손님이 가장 뚜렷한 말."""
    if not auds:
        return None
    def score(k: str) -> float:
        a = auds[k]
        return float(a.get("index", {}).get(top_age(a), 0))
    return max(auds, key=lambda k: (score(k), -list(auds).index(k)))


def headline(keyword: str, aud: Optional[dict], fallback_qc: Optional[float] = None) -> str:
    """한 줄 요약. 예: "답례품쿠키를 찾는 사람은 30대 여성이 분야 평균의 2.8배, 11월에 가장 많이 찾아요"."""
    if not aud:
        if fallback_qc:
            return f"'{keyword}'은(는) 한 달에 약 {int(fallback_qc):,}번 검색돼요"
        return f"'{keyword}'를 찾는 사람 정보는 아직 못 가져왔어요"
    return f"{keyword}{_obj(keyword)} 찾는 사람은 {segment_line(aud)}"


def _seasonal(monthly: Dict[str, float]) -> bool:
    """최고 달이 평균의 SEASON_PEAK배 이상인가."""
    return bool(monthly and max(monthly.values()) >= SEASON_PEAK * (sum(monthly.values()) / len(monthly)))


def segment_line(aud: Optional[dict]) -> str:
    """손님 무리 한 줄. 예: "30대 여성이 분야 평균의 2.8배, 12월에 가장 많이 찾아요"."""
    if not aud:
        return "누가 찾는지 자료가 아직 없어요"
    idx = aud.get("index", {})
    best = top_age(aud)
    sex = "여성" if aud["female"] >= 0.6 else "남성" if aud["female"] <= 0.4 else ""
    who = f"{best}대 {sex}".strip() + ("이" if sex else "가")
    mult = idx.get(best)
    strong = bool(mult and mult >= HIGH_INDEX)
    seasonal = bool(aud.get("peak_month") and _seasonal(aud.get("monthly") or {}))
    when = f", {aud['peak_month']}월에 가장 많이 찾아요" if seasonal else ""
    if strong:
        return f"{who} 분야 평균의 {mult:g}배" + (when or "예요")
    return f"{who} 가장 많고{when}" if seasonal else f"{who} 가장 많아요"


SEGMENT_LABEL: Dict[str, str] = {"선물·답례": "선물로 찾는 손님", "시즌": "시즌에 찾는 손님", "상품": "상품 자체로 찾는 손님"}


def _trend_of(monthly: Dict[str, float]) -> dict:
    peak = max(monthly, key=monthly.get) if monthly else None
    return {"monthly": monthly, "peak_month": int(peak[5:7]) if peak else None, "seasonal": _seasonal(monthly)}


def trend_by_group(groups: Dict[str, List[str]], online: bool = True) -> Dict[str, dict]:
    """데이터랩 검색어 트렌드를 무리별 달 곡선으로. 무리마다 최고 달 = 100. 응답이 없으면 {}."""
    data = api.search_trend(groups, online)
    out: Dict[str, dict] = {}
    try:
        for res in data["results"]:
            by = {str(r["period"])[:7]: float(r["ratio"]) for r in res["data"]}
            top = max(by.values()) if by else 0
            if top > 0:
                out[res["title"]] = _trend_of({m: round(v / top * 100, 1) for m, v in sorted(by.items())})
    except (TypeError, KeyError, ValueError):
        return {}
    return out


def lead_of(kws: List[str], name: str = "") -> str:
    """무리의 대표 검색어: 상품 이름 전체(띄어쓰기 없앰)가 든 말 중 검색이 가장 많은 것, 없으면 그냥 가장 많은 것.
    ('캠핑 의자'에서 '낚시의자'처럼 끝 낱말만 같은 다른 상품이 대표가 되어 손님 나이·성별이 엉뚱해지는 것을 막는다.)
    kws는 검색이 많은 순."""
    me = name.replace(" ", "")
    return next((k for k in kws if me and me in k.replace(" ", "")), kws[0])


def segments(kw: pd.DataFrame, rec: List[str], category: Optional[str], online: bool = True,
             keep: Optional[List[str]] = None, name: str = "") -> List[dict]:
    """추천 검색어를 뜻(선물·답례/시즌/상품)으로 묶은 손님 무리 최대 3개 (검색수 합이 큰 순). 대표 검색어는 lead_of."""
    chosen = [k for k in rec if keep is None or k in keep]
    sub = kw[kw["keyword"].isin(chosen)].sort_values("total_qc", ascending=False)
    groups = []
    for intent, g in sub.groupby("intent", sort=False):
        groups.append((intent, list(g["keyword"]), int(g["total_qc"].sum())))
    groups = sorted(groups, key=lambda x: -x[2])[:3]
    if not groups:
        return []
    trends = trend_by_group({i: kws[:5] for i, kws, _ in groups}, online)
    out = []
    for intent, kws, total in groups:
        lead = lead_of(kws, name)
        aud = audience(lead, category, online) if category else None
        trend, source = trends.get(intent), "search" if intent in trends else None
        if trend is None and aud and aud.get("monthly"):
            trend, source = _trend_of(aud["monthly"]), "shopping"
        if aud and trend:
            aud = {**aud, "monthly": trend["monthly"], "peak_month": trend["peak_month"]}
        out.append({"intent": intent, "label": SEGMENT_LABEL.get(intent, intent), "keywords": kws,
                    "total_qc": total, "lead": lead,
                    "audience": {k: aud[k] for k in ("female", "ages", "index")} | {"top_age": top_age(aud)} if aud else None,
                    "trend": trend, "trend_source": source, "line": segment_line(aud)})
    log.info("segments done n=%d intents=%s trend=%s", len(out), ",".join(o["intent"] for o in out),
             ",".join(str(o["trend_source"]) for o in out) or "-")
    return out


def _obj(word: str) -> str:
    """목적격 조사 (을/를)."""
    last = word[-1]
    if "가" <= last <= "힣":
        return "을" if (ord(last) - 0xAC00) % 28 else "를"
    return "을(를)"


def _product_trend(word: str, aud: Optional[dict], online: bool) -> dict:
    """몇 월에 많이 찾나: 손님 무리 카드와 같은 기준(검색어 트렌드)을 먼저 쓰고, 못 받으면 쇼핑인사이트 클릭.
    (같은 화면에서 상품 카드는 1월·무리 카드는 4월처럼 기준이 달라 서로 다른 달이 나오던 문제)"""
    t = trend_by_group({"상품": [word]}, online).get("상품")
    if t:
        return {"trend": t, "trend_source": "search"}
    if aud and aud.get("monthly"):
        return {"trend": _trend_of(aud["monthly"]), "trend_source": "shopping"}
    return {"trend": None, "trend_source": None}


def product_stats(kw: pd.DataFrame, name: str, category: Optional[str], online: bool = True) -> Optional[dict]:
    """상품 이름 그대로(띄어쓰기 없앰)의 월 검색 수와, 분야가 있으면 그 말을 찾는 사람의 성별·연령.
    키워드 표에 그 말이 없으면 None. 연령·성별을 못 받으면 audience만 None."""
    word = name.replace(" ", "")
    row = kw[kw["keyword"] == word]
    if not word or row.empty:
        return None
    r = row.iloc[0]
    total = int(r["total_qc"])
    aud = audience(word, category, online) if category else None
    under = int(r["under"]) if "under" in row else 0
    out = {"keyword": word, "total_qc": total, **({"under": under} if under else {}),
           "mobile": round(float(r["mobile_qc"]) / total, 3) if total > 0 and "mobile_qc" in row else None,
           "audience": {k: aud[k] for k in ("female", "ages", "index")} | {"top_age": top_age(aud)} if aud else None,
           **_product_trend(word, aud, online)}
    log.info("product stats keyword=%s qc=%d audience=%s", word, total, "yes" if aud else "no")
    return out


@dataclass
class MarketReport:
    seeds: List[str]
    groups: pd.DataFrame
    keywords: pd.DataFrame
    recommended: List[str] = field(default_factory=list)
    negatives: List[str] = field(default_factory=list)
    audiences: Dict[str, dict] = field(default_factory=dict)
    headline: str = ""
    fetched: str = ""          # 쓴 응답 중 가장 오래된 받은 날 'YYYY-MM-DD' (화면의 조회일)
    fetched_parts: Dict[str, str] = field(default_factory=dict)   # 부분별 받은 날 (product·baseline)
    category: Optional[str] = None                                # 쇼핑인사이트 분야 code (없으면 None)
    segments: List[dict] = field(default_factory=list)            # 손님 무리 (분야가 없으면 비어 있음)
    modifiers: List[dict] = field(default_factory=list)           # 꾸밈말
    product_stats: Optional[dict] = None                          # 상품 이름 그대로의 검색 수·찾는 사람


def build(seeds: List[str], online: bool = True, category: Optional[str] = None,
          keep: Optional[List[str]] = None, *, product: Optional[str] = None,
          drop_words: Optional[Callable[[List[str]], Set[str]]] = None) -> Optional[MarketReport]:
    """한 번에: 키워드 표 → 분류 → 추천·제외·꾸밈말 → (분야가 있으면) 손님 무리 → 한 줄 요약. 키워드를 못 받으면 None.
    분야가 없거나 손님 무리가 비면 손님(쇼핑 인사이트) 조회 없이 첫 추천 검색어의 검색수 한 줄.
    product가 있으면 그 이름으로 사장님 낱말을 만들고, 없으면 첫 seed를 상품 이름으로 본다."""
    api.reset_fetched()
    table = keyword_table(seeds, online)
    if table is None:
        return None
    name = product if product else (seeds[0] if seeds else "")
    words = product_words(name, seeds)
    kw = classify(table, words)
    rec = recommend(kw, seeds=words)
    mods = modifiers(kw, words, limit=MODIFIER_POOL, strip=strip_words(name, seeds))   # 넉넉히: 브랜드를 거른 뒤 화면에 15개
    if drop_words:   # 다른 가게·브랜드 이름이 든 검색어(아트릭스핸드크림·스탠리텀블러)는 추천·손님 무리에서 뺀다
        bad = drop_words([m["word"] for m in mods])
        if bad:
            rec = [k for k in rec if not any(b in k.replace(" ", "") for b in bad)]
    segs = segments(kw, rec, category, online, keep, name) if category else []
    stats = product_stats(kw, name, category, online)
    common = dict(seeds=list(seeds), groups=group_summary(kw), keywords=kw, recommended=rec,
                  negatives=negative_list(kw), category=category, segments=segs, modifiers=mods, product_stats=stats)
    stamp = lambda: dict(fetched=api.oldest_fetched() or "", fetched_parts=api.fetched_parts())
    if segs:   # 무리의 대표 검색어가 손님 조회의 대표 (첫 무리가 대표)
        auds = {s["lead"]: {**s["audience"]} for s in segs if s["audience"]}
        first = next((s for s in segs if s["audience"]), segs[0])   # 손님을 아는 첫 무리 (응답의 audience와 같은 키워드)
        if first["audience"]:
            head = f"{first['lead']}{_obj(first['lead'])} 찾는 사람은 {first['line']}"
        else:
            qc = float(kw.loc[kw["keyword"] == first["lead"], "total_qc"].iloc[0])
            head = headline(first["lead"], None, qc)
        return MarketReport(audiences=auds, headline=head, **common, **stamp())
    # 분야를 모르거나 고른 검색어가 없으면 손님 조회를 하지 않는다 (기본 분야로 조회하면 엉뚱한 분야 평균과 비교하게 됨)
    top = rec[0] if rec else None
    qc = float(kw.loc[kw["keyword"] == top, "total_qc"].iloc[0]) if top else None
    return MarketReport(audiences={}, headline=headline(top, None, qc) if top else "", **common, **stamp())
