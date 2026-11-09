"""광고 세팅값 (MVP 7d 3단계): 코치 답(Answer) → 네이버·메타 광고 관리자에 넣을 값을 단계별로 한 곳에서 만든다.

- 단계 = 광고 관리자에서 누르는 순서. 단계마다 세팅값(항목)·근거 카드 id·대량 등록 안내.
- 값마다 출처: 🧮 코치 계산 / 🙋 사장님 답(고칠 수 있음) / ✍️ 초안(고쳐 쓰세요).
- 숫자는 엔진·guide가 이미 정한 규칙만 씀 (하루 예산 = 월 ÷ 30.4, 쇼핑검색 최소 50원, 메타 권장 = 결과 1개 비용 × 10 등).
- '스마트스토어인가'는 is_smartstore / own_site 두 함수 하나씩 (체크리스트·메타 목적·세팅 도우미가 같이 씀).
- 메타 손님 1명 비용(CPA)은 meta_cpa 하나: 메타 예산 ÷ 메타가 데려온 새 손님 (검수 A3 사용자 결정 11/10).
- 이 앱은 광고 계정에 쓰지 않는다. 세팅값은 사장님이 화면이나 대량 관리 파일로 직접 넣는다.
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from .defaults import DAYS_PER_MONTH

Value = Union[str, int, float, bool, List[str]]
CALC, OWNER, DRAFT = "🧮", "🙋", "✍️"
SOURCE_WORDS = {CALC: "코치 계산", OWNER: "사장님 답", DRAFT: "초안"}
SHOPPING_MIN_BID = 50          # ✅ 쇼핑검색 최소 입찰가 [naver-setup-011]
POWERLINK_MIN_BID = 70         # ✅ 파워링크 최소 입찰가 [naver-setup-011]
NAVER_TITLE_MAX = 15           # ✅ 파워링크 단일형 제목 최대 15자 [naver-setup-014]
NAVER_DESC_RANGE = (20, 45)    # ✅ 설명 20~45자 [naver-setup-014]
NAVER_PROMO1_MAX = 10         # ✅ 쇼핑검색 추가 홍보 문구 1 최대 10자 (문구 2는 30자) [naver-setup-018]
META_TITLE_REC = 27            # ✅ 페이스북 피드 제목 권장 27자 (제한 아님) [meta-crv-002]
META_TEXT_REC = (50, 150)      # ✅ 기본 문구 권장 50~150자 [meta-crv-002]
# 제외 키워드 제안 (사지 않고 정보만 찾는 검색). 사장님이 고쳐 씀 ✍️ [naver-kw-008]
NEGATIVE_SUGGEST = ["레시피", "만들기", "만드는법", "만드는 법", "무료", "중고", "칼로리", "도안"]


# ── 스마트스토어 규칙 하나 ──────────────────────────────────────
def is_smartstore(stores: Optional[List[str]]) -> bool:
    """네이버 쇼핑검색(쇼핑몰 상품형)이 맞는 가게: 스마트스토어에서 팔거나 판매처를 아직 안 고름."""
    return not stores or "스마트스토어" in stores


def own_site(stores: Optional[List[str]]) -> bool:
    """메타 픽셀을 달 수 있는 내 사이트(자사몰)가 있는가. 없으면 메타는 '트래픽' 기본 (스마트스토어 픽셀 ❓)."""
    return bool(stores) and "자사몰" in stores


# ── 메타 손님 1명 비용 (A3) ─────────────────────────────────────
def meta_new_customers(split, params) -> float:
    """메타 예산만으로 한 달에 오는 새 손님 (엔진 one_month, 흔들기 없이)."""
    from .montecarlo import one_month
    if split.meta.spend <= 0:
        return 0.0
    return one_month([split.channels[-1]], [split.meta.spend], params)["new"]


def meta_cpa(split, params) -> Optional[float]:
    """메타 손님 1명 비용 = 메타 예산 ÷ 메타 새 손님 (A3 결정: 네이버와 섞지 않음)."""
    new = meta_new_customers(split, params)
    return split.meta.spend / new if new > 0 else None


# ── 세팅값 묶음 ────────────────────────────────────────────────
@dataclass
class Item:
    key: str
    label: str
    value: Value
    source: str                 # 🧮 / 🙋 / ✍️
    note: str = ""
    editable: bool = True       # 🧮도 사장님이 바꿀 수 있음 (바꾸면 🙋로 표시)


@dataclass
class Step:
    media: str                  # "naver" / "meta"
    key: str
    title: str
    where: str                  # 광고 관리자에서 찾을 곳
    cards: List[str]
    items: List[Item]
    bulk: str = ""              # 대량 등록 파일 안내 (있으면)
    note: str = ""


@dataclass
class SettingsPlan:
    steps: List[Step]
    smartstore: bool
    own_site: bool
    no_ad: bool
    meta_cpa: Optional[float]
    powerlink: bool = False
    warnings: List[str] = field(default_factory=list)
    meta_plan: Dict = field(default_factory=dict)      # guide.meta_plan 결과 (목적·이유·권장 하루 예산·머신 러닝 점검)
    numbers: Dict = field(default_factory=dict)        # 세팅 카드 '내 숫자'·챗봇 문맥이 읽는 값 (setup_rag.my_numbers)

    def for_media(self, media: str) -> List[Step]:
        return [s for s in self.steps if s.media == media]

    def item(self, media: str, key: str) -> Optional[Item]:
        return next((it for s in self.for_media(media) for it in s.items if it.key == key), None)

    def value(self, media: str, key: str, default=None):
        it = self.item(media, key)
        return default if it is None else it.value

    def to_settings(self) -> Dict[str, Value]:
        """계획 파일 Plan.settings에 넣을 값 (글자·숫자·참거짓·글자 목록만, 키 = '매체.항목')."""
        out: Dict[str, Value] = {}
        for s in self.steps:
            for it in s.items:
                v = it.value
                if isinstance(v, (str, bool, int, float)) or (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                    out[f"{s.media}.{it.key}"] = v
        return out

    def rows(self, media: Optional[str] = None) -> List[Dict[str, str]]:
        """'광고 세팅값' 시트 한 줄씩 (광고 관리자에서 누르는 순서)."""
        rows = []
        for n, s in enumerate(self.steps if media is None else self.for_media(media), 1):
            for it in s.items:
                rows.append({"매체": "네이버" if s.media == "naver" else "메타", "단계": f"{n}. {s.title}", "항목": it.label,
                             "값": show(it.value), "출처": f"{it.source} {SOURCE_WORDS[it.source]}", "메모": it.note,
                             "찾을 곳": s.where})
        return rows


def show(v: Value) -> str:
    if isinstance(v, bool):
        return "켜기" if v else "끄기"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, list):
        return ", ".join(v)
    return str(v)


def _won(v: float) -> int:
    return int(round(v / 10.0) * 10) if v else 0      # 광고 관리자에 넣기 좋게 10원 단위


# ── 만들기 ─────────────────────────────────────────────────────
def build_settings(answer, stores: Optional[List[str]], pixel_ready: bool = False, media: str = "both", keyword: str = "",
                   product: str = "", month: str = "", powerlink: bool = False, owner: Optional[Dict[str, Value]] = None,
                   naver_link: str = "", meta_link: str = "") -> SettingsPlan:
    """answer: coach.Answer. media: both / naver / meta. owner: 사장님이 고친 값 {"매체.항목": 값} (🙋로 표시).
    product: 상품 이름(캠페인 이름·문구 초안), month: yymm. 링크는 화면의 '링크 만들기' 결과(없으면 빈칸)."""
    from . import guide as GD
    sp = answer.split
    ss_, site = is_smartstore(stores), own_site(stores)
    no_ad = answer.default_pick == "none"
    cpa_meta = meta_cpa(sp, answer.params)
    mp = GD.meta_plan(sp.meta.spend, cpa_meta or 0.0, pixel_ready, stores, sp.meta.cpc)
    steps: List[Step] = []
    prod = product or keyword or "상품"
    name = f"{month}_{prod}" if month else prod
    if media in ("both", "naver") and sp.naver_spend > 0:
        steps += _naver_steps(sp, ss_, keyword, name, powerlink, naver_link)
    if media in ("both", "meta") and sp.meta.spend > 0:
        steps += _meta_steps(sp, mp, name, meta_link)
    plan = SettingsPlan(steps=steps, smartstore=ss_, own_site=site, no_ad=no_ad, meta_cpa=cpa_meta, powerlink=powerlink,
                        meta_plan=mp)
    if no_ad:
        plan.warnings.append("코치는 지금 '광고 안 함'을 추천해요. 시작한다면 아래 값대로 넣으세요.")
    for pre in ("", "pl_"):          # 입찰가가 하루 예산에 비해 크면 클릭 몇 번에 예산이 끝남 [naver-setup-009]
        bid_v, day_v = plan.value("naver", pre + "bid"), plan.value("naver", pre + "daily_budget")
        if isinstance(bid_v, (int, float)) and isinstance(day_v, (int, float)) and day_v > 0 and bid_v * 3 > day_v:
            n = int(day_v // max(bid_v, 1))
            plan.warnings.append(f"{'파워링크 ' if pre else ''}입찰가 {bid_v:,.0f}원이면 하루 예산 {day_v:,.0f}원이 "
                                 + ("클릭 1번 값도 안 돼요. " if n < 1 else f"클릭 약 {n}번에 끝나요. ")
                                 + "하루 예산을 늘리거나 입찰가를 낮춰 시작하세요.")
    for k, v in (owner or {}).items():
        m, _, key = k.partition(".")
        it = plan.item(m, key)
        if it is not None and v != it.value:
            it.value = v
            it.source = DRAFT if it.source == DRAFT else OWNER      # 고친 초안은 여전히 초안 ✍️
    plan.numbers = {
        "naver": sp.naver_spend, "naver_daily": plan.value("naver", "daily_budget", 0) or plan.value("naver", "pl_daily_budget", 0),
        "meta": sp.meta.spend, "meta_daily": plan.value("meta", "daily_budget", _won(mp["daily"])),
        "meta_rec_daily": mp["recommended_daily"], "meta_objective": mp["objective"],
        "bid": GD.naver_bid_at(sp.naver.curve, sp.naver_spend) if sp.has_naver else None,
        "shopping_min": SHOPPING_MIN_BID, "smartstore": ss_, "keyword": keyword, "cpa": cpa_meta,
        "be_first": answer.be.first, "no_ad": no_ad}
    return plan


def context_lines(plan: SettingsPlan, media: str, limit: int = 14) -> List[str]:
    """챗봇(LLM) 문맥에 붙일 지금 매체의 세팅값 몇 줄 (개인정보 없음: 숫자·이름 규칙·고른 값)."""
    out = []
    for s in plan.for_media(media):
        for it in s.items:
            if it.value not in ("", [], None):
                out.append(f"{s.title} · {it.label}: {show(it.value)} ({SOURCE_WORDS[it.source]})")
    return out[:limit]


def _naver_steps(sp, smartstore: bool, keyword: str, name: str, powerlink: bool, link: str) -> List[Step]:
    """스마트스토어면 쇼핑검색(쇼핑몰 상품형)이 기본, '파워링크도 할래요'면 파워링크 캠페인을 하나 더 (사용자 결정 11/9).
    자사몰만이면 파워링크가 기본."""
    from . import guide as GD
    monthly = sp.naver_spend
    daily = _won(GD.daily_budget(monthly))
    bid = GD.naver_bid_at(sp.naver.curve, monthly) if sp.has_naver else None
    both = smartstore and powerlink
    if both and sp.has_naver:
        bid = GD.naver_bid_at(sp.naver.curve, monthly / 2)      # 파워링크 몫(반)을 쓰게 되는 입찰가
    steps = [Step("naver", "account", "광고주 가입·비즈머니", "네이버애즈 > 광고주 가입 → 비즈머니 충전", ["naver-setup-001", "naver-setup-002"],
                  [Item("bizmoney", "비즈머니 충전 (첫 달)", _won(monthly), CALC, "네이버 월 배분만큼. 잔액이 0원이면 검토도 시작되지 않아요.")])]
    if smartstore:
        steps += _shopping_steps(name, daily // 2 if both else daily, monthly, keyword, bid, both)
    if powerlink or not smartstore:
        steps += _powerlink_steps(name, daily - daily // 2 if both else daily, monthly, keyword, bid, link, both)
    steps.append(Step("naver", "tracking", "전환 추적", "도구 > 전환 추적 관리 > 웹사이트 → 캠페인 설정에서 선택", ["naver-setup-016"],
                      [Item("conversion", "전환 추적 대상", "스마트스토어 (신청하면 바로 설치 완료)" if smartstore else "자사몰 (안내 메일대로 스크립트 설치)",
                            CALC, "신청한 뒤 캠페인 설정에서 꼭 골라야 리포트에 전환이 잡혀요"),
                       Item("link", "광고 링크 (꼬리표)", link, OWNER, "판매처 통계에서 광고 손님을 따로 세는 링크. 3단계 '링크 만들기'에서 만들어요")]))
    return steps


_RANK_NOTE = ("노출 순위는 입찰가만으로 정해지지 않아요. 검색어와 광고·사이트의 연관성, 광고 품질을 함께 봐요(파워링크는 광고 연관지수·"
              "클릭 기대지수 1~10). 입찰가를 올려도 순위는 보장되지 않으니 다음 날 보고서의 노출수로 확인하세요")


def _daily_note(monthly: float, both: bool) -> str:
    base = f"네이버 월 {monthly:,.0f}원 ÷ {DAYS_PER_MONTH}일"
    return base + (" 을 쇼핑검색·파워링크에 반씩 (합계가 넘지 않게 고쳐 써도 돼요)" if both else "")


def _shopping_steps(name: str, daily: int, monthly: float, keyword: str, bid: Optional[float], both: bool) -> List[Step]:
    return [
        Step("naver", "campaign", "캠페인 (쇼핑검색)", "광고 관리 > [+ 새 캠페인] → 쇼핑검색",
             ["naver-setup-005", "naver-setup-008", "naver-setup-009", "naver-setup-007"],
             [Item("campaign_type", "캠페인 유형", "쇼핑검색광고 (쇼핑몰 상품형)", CALC, "스마트스토어 상품이 네이버 쇼핑 영역에 보이는 광고 (코치 기본)"),
              Item("campaign_name", "캠페인 이름", f"{name}_쇼핑", OWNER, "월_상품_유형 규칙이면 나중에 합쳐 보기 쉬워요"),
              Item("daily_budget", "하루 예산 (원)", daily, CALC, _daily_note(monthly, both)),
              Item("even_spend", "예산 균등 배분", True, CALC, "아침에 예산이 다 써져 광고가 일찍 꺼지는 일을 줄여요")],
             note="이런 상품도 있어요: ADVoost 쇼핑·스마트스토어 광고는 예산만 정하면 AI가 상품·지면·입찰을 정해요(둘 중 하나만). "
                  "입찰가를 직접 정해 숫자를 배우려면 쇼핑검색광고가 맞아요"),
        Step("naver", "adgroup", "광고그룹 (입찰가·노출 대상)", "캠페인 > [+ 새 광고그룹] (쇼핑몰 상품형) → 타겟팅 탭",
             ["naver-setup-006", "naver-setup-011", "naver-setup-017", "naver-setup-012"],
             [Item("adgroup_name", "광고그룹 이름", f"{name}_1", OWNER),
              Item("bid", "기본 입찰가 (원)", SHOPPING_MIN_BID, CALC,
                   f"쇼핑검색은 상품 단위, 최소 {SHOPPING_MIN_BID}원부터 보고서를 보며 올려요"
                   + (f" (참고: '{keyword}' 파워링크 예상 입찰가 약 {bid:,.0f}원)" if bid else "")),
              Item("region_exclude", "노출 제외 지역", "없음 (모든 지역)", OWNER,
                   "쇼핑검색은 '노출 제외 지역'만 정해요. 배송지가 아니라 검색한 사람 위치 기준이라 배송 지역은 상세페이지에 밝혀요"),
              Item("age_gender", "연령·성별", "모두", OWNER, "처음엔 모두, 성과를 본 뒤 조정")],
             note=_RANK_NOTE),
        Step("naver", "creative", "소재 (상품 연결·확장소재)", "광고그룹 > 소재 탭 > [+ 새 소재] / 확장 소재 탭",
             ["naver-setup-006", "naver-setup-018", "naver-setup-019"],
             [Item("product", "광고할 상품", "스마트스토어 대표 상품 1개", OWNER, "상품명·이미지가 상품과 맞아야 검토에 좋아요"),
              Item("promo1", "추가 홍보 문구 1 (10자 이하)", "", DRAFT, "상세페이지에 있는 사실 혜택만 (예: 당일 제작)"),
              Item("negatives", "제외 검색어", list(NEGATIVE_SUGGEST[:4]), DRAFT, "광고그룹 소재 목록 > 제외검색어 탭 (최대 70개)")],
             bulk="쇼핑검색 상품 연결은 화면에서만 해요 (대량 등록 파일로 안 됨)."),
    ]


def _powerlink_steps(name: str, daily: int, monthly: float, keyword: str, bid: Optional[float], link: str, both: bool) -> List[Step]:
    p = "pl_" if both else ""          # 쇼핑검색과 함께면 항목 이름이 겹치지 않게
    t = " (파워링크 추가)" if both else ""
    return [
        Step("naver", p + "campaign", "캠페인" + (t or " (파워링크)"), "광고 관리 > [+ 새 캠페인] → 파워링크", ["naver-setup-005", "naver-setup-009"],
             [Item("campaign_type" if not p else "pl_campaign_type", "캠페인 유형", "파워링크 (사이트검색광고)", CALC, "키워드 검색 결과에 문구와 함께 보이는 광고"),
              Item(p + "campaign_name", "캠페인 이름", f"{name}_파워링크", OWNER),
              Item(p + "daily_budget", "하루 예산 (원)", daily, DRAFT if both else CALC, _daily_note(monthly, both))]),
        Step("naver", p + "adgroup", "광고그룹 (입찰가·노출 대상)" + t, "캠페인 > [+ 새 광고그룹] → 고급옵션·타겟팅 탭",
             ["naver-setup-010", "naver-setup-011", "naver-setup-017", "naver-setup-021", "naver-setup-012"],
             [Item(p + "adgroup_name", "광고그룹 이름", f"{name}_PL1", OWNER),
              Item(p + "bid", "기본 입찰가 (원)", _won(max(bid or POWERLINK_MIN_BID, POWERLINK_MIN_BID)), CALC,
                   f"'{keyword}' 예상 실적에서 이 예산을 쓰게 되는 입찰가 (최소 {POWERLINK_MIN_BID}원)" if bid else f"최소 {POWERLINK_MIN_BID}원부터"),
              Item(p + "exp_search", "확장 검색", False, CALC, "기본은 켜져 있어요. 작은 예산은 '일치 검색'으로 시작하고 검색어 보고서를 본 뒤 켜기 (코치 판단 △)"),
              Item(p + "advoost_max", "ADVoost Max", False, CALC, "확장 검색 그룹에서 기본 켜짐. 첫 달엔 끄기 권장 (코치 판단 △)"),
              Item(p + "region", "지역", "모든 지역", OWNER, "배송 안 되는 곳이 있으면 '광고 노출 지역 설정'으로 좁혀요"),
              Item(p + "schedule", "요일·시간", "모든 요일·시간", OWNER, "성과를 본 뒤 시간대별 입찰 가중치로 조정"),
              Item(p + "device", "PC·모바일", "모두", OWNER, "[고급옵션] 매체에서 한쪽만, 또는 PC/모바일 입찰가 가중치")],
             note=_RANK_NOTE),
        Step("naver", p + "keywords", "키워드·제외 키워드" + t, "광고그룹 > 키워드 탭 / 제외 검색어 탭", ["naver-kw-004", "naver-kw-008"],
             [Item(p + "keywords", "키워드", [keyword] if keyword else [], OWNER, "키워드 도구에서 월 검색수 300~1만 세부 키워드를 더해요"),
              Item(p + "negatives", "제외 키워드", list(NEGATIVE_SUGGEST[:4]), DRAFT)],
             bulk="키워드가 많으면: 광고그룹을 먼저 만들고 → 광고그룹 ID를 복사해 → 대량 관리에서 키워드 파일을 올려요."),
        Step("naver", p + "creative", "소재 (광고 문구)" + t, "광고그룹 > 소재 탭 > [+ 새 소재] / 확장 소재 탭",
             ["naver-setup-014", "naver-setup-018", "naver-setup-019"],
             [Item(p + "title", f"제목 ({NAVER_TITLE_MAX}자 이하)", "", DRAFT),
              Item(p + "description", f"설명 ({NAVER_DESC_RANGE[0]}~{NAVER_DESC_RANGE[1]}자)", "", DRAFT),
              Item(p + "url", "연결 URL", link, OWNER, "코치 '링크 만들기'의 꼬리표 링크")],
             bulk="소재가 많으면 대량 관리의 소재 파일로 올려요 (광고그룹 ID 필요)."),
    ]


def _meta_steps(sp, mp: Dict, name: str, link: str) -> List[Step]:
    daily = _won(mp["daily"])
    rec = _won(mp["recommended_daily"]) if mp.get("recommended_daily") else None
    return [
        Step("meta", "objective", "캠페인 목표", "광고 관리자 > [+ 만들기] → 캠페인 목표", ["meta-obj-001", "meta-obj-004", "meta-obj-003"],
             [Item("objective", "캠페인 목표", mp["objective"] or "트래픽", CALC, mp["why"].split(". ")[0] + "."),
              Item("campaign_name", "캠페인 이름", f"{name}_메타", OWNER)]),
        Step("meta", "budget", "예산·입찰", "캠페인 또는 광고 세트 > 예산 및 일정", ["meta-bud-001", "meta-bud-004", "meta-bud-003", "meta-auto-002"],
             [Item("daily_budget", "일일 예산 (원)", daily, CALC, f"메타 월 {sp.meta.spend:,.0f}원 ÷ {DAYS_PER_MONTH}일. 어떤 날은 최대 75% 더 쓸 수 있어요"),
              Item("bid_strategy", "입찰 전략", "최고 볼륨", CALC, "기본 자동 입찰 (예전 이름 '최저 비용')")]
             + ([Item("recommended_daily", "메타 권장 하루 예산 (참고)", rec, CALC,
                      "결과 1개 평균 비용 × 10. 지금 예산이 이보다 작으면 결과가 고르지 않을 수 있어요", editable=False)] if rec else [])),
        Step("meta", "audience", "타겟", "광고 세트 > 타겟", ["meta-tgt-001", "meta-tgt-002"],
             [Item("advantage_audience", "어드밴티지+ 타겟", True, CALC, "처음엔 넓게. 예산이 작을수록 좁히면 결과가 늦게 모여요 (△)"),
              Item("location", "위치", "대한민국", OWNER, "배송 안 되는 곳이 있으면 '수정'으로 빼요"),
              Item("age", "최소 연령", "18", OWNER)]),
        Step("meta", "placement", "노출 위치", "광고 세트 > 노출 위치", ["meta-plc-001"],
             [Item("placement", "노출 위치", "어드밴티지+ 노출 위치 (자동)", CALC, "판매 목표에서는 수동 선택이 단계적으로 없어지는 중이라 그대로 두세요")]),
        Step("meta", "creative", "광고 (이미지·문구)", "광고 > 광고 설정·크리에이티브", ["meta-crv-001", "meta-crv-002", "meta-crv-003"],
             [Item("image_ratio", "이미지 비율", ["4:5 (피드)", "9:16 (릴스·스토리)"], OWNER, "비율별로 하나씩 만들면 대부분의 위치를 채워요"),
              Item("primary_text", f"기본 문구 (권장 {META_TEXT_REC[0]}~{META_TEXT_REC[1]}자)", "", DRAFT),
              Item("headline", f"제목 (권장 {META_TITLE_REC}자)", "", DRAFT),
              Item("url", "웹사이트 URL", link, OWNER, "코치 '링크 만들기'의 UTM/NT 링크")],
             bulk="광고가 여러 개면: 이미지·영상을 계정에 먼저 올리고 → 일괄 가져오기 파일을 내려받아 채운 뒤 → 올리고 미리 보기에서 개수를 확인해요."),
        Step("meta", "measure", "측정", "이벤트 관리자 / 광고 세트 > 기여 설정", ["meta-msr-001", "meta-msr-003"],
             [Item("attribution", "기여 설정", "기본값 (클릭 후 7일·조회 후 1일·참여한 조회 후 1일)", CALC,
                   "보기만 한 사람의 구매도 잡혀 실제 주문보다 많을 수 있어요")]),
    ]


# ── 광고 문구 초안·검사 ─────────────────────────────────────────
# 심사에서 문제 되기 쉬운 표현 (근거 없는 최상급·순위·보장). 공식 기준: naver-setup-019 카드
REVIEW_WORDS = ["최고", "최상", "최초", "최대", "최저", "1위", "1등", "넘버원", "No.1", "유일", "100%", "완벽", "무조건", "가장", "제일", "국내 최고",
                "세계 최고", "보장"]
_PRICE = re.compile(r"\d[\d,]*\s*원|\d+\s*%\s*(할인|세일|off)|무료\s*배송|공짜", re.I)


def check_copy(text: str, kind: str) -> List[str]:
    """광고 문구 검사 → 고칠 점 목록 (없으면 빈 목록). kind: naver_title / naver_desc / meta_text / meta_headline."""
    t = (text or "").strip()
    out = []
    n = len(t)
    if kind == "naver_promo1" and n > NAVER_PROMO1_MAX:
        out.append(f"추가 홍보 문구 1이 {n}자예요. {NAVER_PROMO1_MAX}자 이하로 줄여 주세요.")
    if kind == "naver_title" and n > NAVER_TITLE_MAX:
        out.append(f"제목이 {n}자예요. {NAVER_TITLE_MAX}자 이하로 줄여 주세요.")
    if kind == "naver_desc" and not (NAVER_DESC_RANGE[0] <= n <= NAVER_DESC_RANGE[1]):
        out.append(f"설명이 {n}자예요. {NAVER_DESC_RANGE[0]}~{NAVER_DESC_RANGE[1]}자로 맞춰 주세요.")
    if kind == "naver_desc" and n > 10 and " " not in t:
        out.append("설명에 띄어쓰기가 없으면 등록이 안 돼요.")
    if kind == "meta_headline" and n > META_TITLE_REC:
        out.append(f"제목이 {n}자예요. 메타 권장은 {META_TITLE_REC}자예요 (넘으면 잘려 보일 수 있어요).")
    if kind == "meta_text" and n and not (META_TEXT_REC[0] <= n <= META_TEXT_REC[1]):
        out.append(f"기본 문구가 {n}자예요. 메타 권장은 {META_TEXT_REC[0]}~{META_TEXT_REC[1]}자예요.")
    hits = [w for w in REVIEW_WORDS if w.lower() in t.lower()]
    if hits:
        out.append(f"'{', '.join(hits)}' 같은 최상급·순위·보장 표현은 객관적 근거(출처·기준일)가 없으면 심사에서 막힐 수 있어요.")
    if _PRICE.search(t):
        out.append("가격·할인·무료배송을 쓰면 상세페이지와 똑같아야 해요 (다르면 심사에서 막히거나 손님이 떠나요).")
    if re.search(r"[!?~★♥]{2,}|[^\w\s.,()·%/~!?:'\"-]{3,}", t):
        out.append("특수문자를 여러 개 이어 쓰면 등록이 안 될 수 있어요.")
    return out


def draft_copy(product: str, strength: str = "", benefit: str = "") -> Dict[str, str]:
    """키가 없을 때 틀 채우기 ✍️ (사장님이 준 상품명·강점·혜택만 씀, 지어내지 않음)."""
    p = (product or "우리 상품").strip()
    s = (strength or "").strip()
    b = (benefit or "").strip()
    title = p[:NAVER_TITLE_MAX]
    desc = " ".join(x for x in (f"{p}," if s else p, s, b) if x).strip()
    if len(desc) < NAVER_DESC_RANGE[0]:
        desc = (desc + " 스마트스토어에서 만나 보세요.").strip()
    desc = desc[:NAVER_DESC_RANGE[1]]
    meta_text = " ".join(x for x in (f"{p}." if not s else f"{p}, {s}.", b + "." if b else "", "지금 스토어에서 확인해 보세요.") if x)
    return {"naver_title": title, "naver_desc": desc, "meta_text": meta_text, "meta_headline": p[:META_TITLE_REC]}
