"""집행 전 예산 계획 (T09): 네이버 몫(검색 수요 상한 안) + 남는 돈은 메타 + 예상 도달.

- 예산은 '한 달 광고비'. 네이버는 한 달(30일)에 나눠 쓰고, 메타는 광고 기간(days)에 나눠 쓴다.
- 모든 가정 숫자는 v2/specs/assumptions.yaml에서 읽고, 사장님께 보여 줄 문장에 근거 등급(A~D)을 붙인다.
- 돈은 10원 단위로 반올림한다.
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from . import specs

NAVER_DAYS = 30  # 네이버 하루 예산 = 네이버 월 몫 ÷ 30 (naver_fields.yaml 설명과 같음)


@dataclass
class BudgetPlan:
    budget: int
    days: int
    objective: str                      # "트래픽" | "인지도"
    naver_cap_month: Optional[int]      # 검색 수요로 쓸 수 있는 월 상한 (키워드가 없으면 None)
    naver_month: int
    meta_month: int
    naver_daily: int
    meta_daily: int
    naver_bid: int                      # 10원 단위
    demand_capped: bool                 # 네이버 수요가 예산 몫보다 작음
    meta_forecast: Dict[str, float] = field(default_factory=dict)
    naver_forecast: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


def round10(x: float) -> int:
    """10원 단위 반올림 (0.5는 올림)."""
    return int(math.floor(x / 10.0 + 0.5)) * 10


def _mid(d: dict) -> float:
    return (d["low"] + d["high"]) / 2.0


def _won(x: float) -> str:
    return "{:,}원".format(int(x))


def naver_demand_cap(keywords: Optional[pd.DataFrame], cpc: float, ctr: float) -> Optional[float]:
    """고른 키워드의 월 검색수 × 클릭률 × 클릭당 비용 = 네이버에서 한 달에 쓸 수 있는 돈의 위쪽 한계.

    키워드 표가 없거나 비어 있으면 None. 'intent'가 '제외…'인 줄은 빼고, 숫자가 아닌 검색수는 0으로 본다.
    """
    if keywords is None or len(keywords) == 0 or "total_qc" not in keywords:
        return None
    df = keywords
    if "intent" in df:
        df = df[~df["intent"].astype(str).str.startswith("제외")]
    searches = pd.to_numeric(df["total_qc"], errors="coerce").fillna(0).clip(lower=0).sum()
    return float(searches) * ctr * cpc


def meta_cpm_range(objective: str, target_key: str) -> Dict:
    """목표·타겟에 맞는 CPM 가정 (low, high, grade). 인지도는 넓은 타겟이면 싸고 좁으면 비싸다."""
    cpm = specs.assumptions()["meta"]["cpm"]
    if objective == "트래픽":
        return cpm["traffic"]
    return cpm["awareness_broad"] if target_key == "넓게" else cpm["awareness_narrow"]


def reach_from_impressions(impressions: float, target: float) -> float:
    """메타 도달 = T·(1 − e^(−노출/T)). 타겟 T를 넘을 수 없다."""
    if target <= 0 or impressions <= 0:
        return 0.0
    return target * (1.0 - math.exp(-impressions / target))


def meta_forecast(meta_month: float, days: int, objective: str, target_key: str) -> Dict[str, float]:
    a = specs.assumptions()["meta"]
    targets = a["effective_target"]
    if target_key not in targets:
        raise ValueError("타겟 '{}'은(는) 아직 예측에 쓸 수 없어요. 가능한 타겟: {}".format(
            target_key, ", ".join(targets)))
    target = float(targets[target_key]["value"])
    cpm = meta_cpm_range(objective, target_key)
    impressions = meta_month / _mid(cpm) * 1000.0
    reach = reach_from_impressions(impressions, target)
    freq = impressions / reach if reach > 0 else 0.0
    weeks = max(days, 7) / 7.0  # 7일보다 짧아도 '주당'은 기간 전체로 본다
    clicks = impressions * a["link_ctr"]["value"] if objective == "트래픽" else 0.0
    return {
        "impressions": impressions, "reach": reach, "frequency": freq,
        "weekly_frequency": freq / weeks, "link_clicks": clicks,
        "cpm_low": float(cpm["low"]), "cpm_high": float(cpm["high"]),
    }


def naver_forecast(naver_month: float, cpc: float, ctr: float) -> Dict[str, float]:
    clicks = naver_month / cpc if cpc > 0 else 0.0
    return {"clicks": clicks, "impressions": clicks / ctr if ctr > 0 else 0.0}


def _notes(plan: BudgetPlan, target_key: str, cpc: float, cpc_given: bool, ctr: dict) -> List[str]:
    a = specs.assumptions()
    cpm = meta_cpm_range(plan.objective, target_key)
    notes = []
    if plan.naver_cap_month is None:
        notes.append("키워드를 아직 고르지 않아서, 네이버에는 예산의 {}%까지만 잡았어요. 키워드를 고르면 검색하는 사람 수만큼으로 다시 계산해요."
                     .format(int(round(plan.naver_month * 100.0 / plan.budget)) if plan.budget else 0))
    elif plan.demand_capped:
        notes.append("네이버는 검색하는 사람이 적어서 한 달에 약 {} 이상은 쓰기 어려워요. 남는 돈까지 합쳐 메타에 {}을 쓰도록 했어요. (근거 C: 클릭률·클릭당 비용은 공개 자료)"
                     .format(_won(plan.naver_cap_month), _won(plan.meta_month)))
    else:
        notes.append("네이버 검색 수요는 한 달에 약 {}까지 받쳐 줘서, 예산 몫만큼 쓸 수 있어요. (근거 C)"
                     .format(_won(plan.naver_cap_month)))
    cpc_grade = "D 직접 입력" if cpc_given else a["naver"]["cpc"]["grade"]
    notes.append("네이버는 클릭 1번에 약 {}, 한 달 클릭 약 {}번을 예상해요. (근거 {})"
                 .format(_won(cpc), int(plan.naver_forecast["clicks"]), cpc_grade))
    mf = plan.meta_forecast
    notes.append("메타는 노출 1,000번에 {}~{} 정도로 보고, 약 {:,}명에게 평균 {:.1f}번 보여 줄 수 있어요. (근거 {}: CPM, 도달은 {}: 메타가 실제로 보여 주는 사람 수 추정)"
                 .format(_won(cpm["low"]), _won(cpm["high"]), int(mf["reach"]), mf["frequency"],
                         cpm["grade"], a["meta"]["effective_target"][target_key]["grade"]))
    if plan.objective == "트래픽":
        notes.append("가게로 들어오는 클릭은 한 달에 약 {}번으로 예상해요. (근거 {}: 링크 클릭률 {:.1f}%)"
                     .format(int(mf["link_clicks"]), a["meta"]["link_ctr"]["grade"], a["meta"]["link_ctr"]["value"] * 100))
    else:
        notes.append("인지도 목표라서 클릭 수는 예측하지 않아요. 광고를 본 사람이 나중에 브랜드를 검색하는지로 확인해요.")
    if plan.days < 7:
        notes.append("메타 기간이 7일보다 짧으면 광고가 자리를 잡기 어려워요. 7~14일을 권해요.")
    return notes


def plan_budget(budget: int, keywords: Optional[pd.DataFrame] = None, objective: str = "트래픽",
                days: int = 14, target_key: str = "넓게", naver_share_max: float = 0.5,
                cpc: Optional[int] = None) -> BudgetPlan:
    """한 달 예산을 네이버·메타로 나누고 예상 결과를 계산한다.

    네이버 상한 = Σ(월 검색수 × 클릭률 중간값) × 클릭당 비용. 네이버 몫 = min(상한, 예산 × naver_share_max). 남는 돈은 메타.
    """
    if objective not in ("트래픽", "인지도"):
        raise ValueError("목표는 '트래픽' 또는 '인지도' 중에서 골라 주세요.")
    if days < 1:
        raise ValueError("광고 기간은 1일 이상이어야 해요.")
    share = min(max(float(naver_share_max), 0.0), 1.0)
    total = max(round10(budget), 0)

    naver_a = specs.assumptions()["naver"]
    ctr_mid = _mid(naver_a["ctr"])
    cpc_used = float(cpc) if cpc else float(naver_a["cpc"]["value"])
    bid = round10(float(cpc) if cpc else float(naver_a["cpc"]["high"]))

    cap = naver_demand_cap(keywords, cpc_used, ctr_mid)
    share_money = total * share
    capped = cap is not None and cap < share_money
    naver_month = round10(min(cap, share_money)) if cap is not None else round10(share_money)
    naver_month = min(naver_month, total)
    meta_month = total - naver_month

    plan = BudgetPlan(
        budget=total, days=days, objective=objective,
        naver_cap_month=None if cap is None else round10(cap),
        naver_month=naver_month, meta_month=meta_month,
        naver_daily=round10(naver_month / float(NAVER_DAYS)),
        meta_daily=round10(meta_month / float(days)),
        naver_bid=bid, demand_capped=capped,
        meta_forecast=meta_forecast(meta_month, days, objective, target_key),
        naver_forecast=naver_forecast(naver_month, cpc_used, ctr_mid),
    )
    plan.notes = _notes(plan, target_key, cpc_used, bool(cpc), naver_a["ctr"])
    return plan
