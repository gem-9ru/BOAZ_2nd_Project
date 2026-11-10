"""화면 상태 키 선언 하나 + 계획 파일(Plan) + 단계 이동 (MVP 7e 3단계).

키마다 쓰임을 한 번만 적는다:
  persist = 그리지 않은 단계의 위젯 값도 남김 (Streamlit은 그리지 않은 위젯 값을 지움)
  plan    = 계획 파일에 저장 (개인정보 없음: 상품·숫자·검색어·재구매 실측 숫자만)
  reset   = '내 숫자로 시작'에서 지움
화면(app/main.py)은 이 목록과 함수(go_to·begin·reset·apply_plan·clamp_step)만 쓰고 coach_step을 직접 바꾸지 않는다.
"""
import json
import math
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, MutableMapping, Optional, Tuple

from .coach import BUDGET_PICKS, CATEGORIES, MEASURED, REPURCHASE_PRESETS

_P, _L, _R = "persist", "plan", "reset"
KEYS: List[Tuple[str, Tuple[str, ...]]] = [
    # 1 내 가게 (예시 값과 같은 키)
    ("q_category", (_P, _L, _R)), ("q_stores", (_P, _L, _R)), ("q_price", (_P, _L, _R)), ("q_profit", (_P, _L, _R)),
    ("q_repurchase", (_P, _L, _R)), ("q_budget", (_P, _L, _R)), ("q_baseline", (_P, _L, _R)), ("q_keyword", (_P, _L, _R)),
    # 2 답 보기
    ("q_cpc", (_P, _L, _R)), ("q_budget_pick", (_P, _L, _R)),
    # 4 한 달 뒤 (쓴 돈·클릭·쿠폰·리포트 전환·전체 판매)
    ("q_spent", (_P, _L, _R)), ("q_clicks", (_P, _L, _R)), ("q_coupon", (_P, _L, _R)), ("q_report", (_P, _L, _R)),
    ("q_total", (_P, _L, _R)),
    # 주문 내역 재구매 실측 (숫자 dict). '내 숫자로 시작'해도 남김
    ("repurchase_measured", (_L,)),
    # 4 실행 준비 체크·링크 만들기 (v1.0: 3 광고 세팅과 나눔)
    ("prep_1", (_P, _R)), ("prep_2", (_P, _R)), ("prep_3", (_P, _R)),
    ("link_store", (_P, _R)), ("link_ch", (_P, _R)), ("link_url", (_P, _R)), ("link_product", (_P, _R)),
    ("link_detail", (_P, _R)),
    # 3 광고 세팅: 세팅 도우미 매체 고르기 (7d). 고른 값은 단계 이동 때 남기고 '내 숫자로 시작'에서 지움
    ("setup_media", (_P, _R)), ("_setup_media_touched", (_R,)), ("setup_phase", (_R,)), ("setup_last", (_R,)),
    # 단계 진행
    ("coach_started", (_R,)), ("coach_prev_rate", (_R,)), ("coach_seen", (_R,)), ("_budget_touched", (_R,)),
    # 첫 화면 '리포트만 올리기' (v1.0): 가게 숫자만 넣고 바로 최적화로. 계획 때 예측이 없어 예측 오차율을 숨김
    ("report_only", (_R,)),
]
PERSIST = [k for k, t in KEYS if _P in t]
PLAN = [k for k, t in KEYS if _L in t]
RESET = [k for k, t in KEYS if _R in t]


# ── 단계 (v1.0: 화면에서는 ① 세팅 = 0·1·2, ② 실행 = 3, ③ 최적화 = 4) ──────────────
SHOP, ANSWER, SETUP, RUN, RESULT = range(5)
STEP_NAMES = ["내 가게", "답 보기", "광고 세팅", "실행 준비", "한 달 뒤"]
STAGES = [("세팅", (SHOP, ANSWER, SETUP)), ("실행", (RUN,)), ("최적화", (RESULT,))]


def stage_of(step: int) -> int:
    """단계 번호 → 화면 묶음 번호 (0 세팅 · 1 실행 · 2 최적화)."""
    return next(i for i, (_, steps) in enumerate(STAGES) if step in steps)


# ── 단계 이동 (coach_step을 바꾸는 곳은 여기뿐) ─────────────────────────────
def go_to(ss: MutableMapping, step: int) -> None:
    """단계 표시 버튼·'광고를 시작했어요': 지금 단계를 바꾸고, 본 단계는 줄이지 않음."""
    ss["coach_step"] = step
    ss["coach_seen"] = max(ss.get("coach_seen", 0), step)


def begin(ss: MutableMapping, mode: str, step: int) -> None:
    """새로 시작 (예시 고르기·대화 마침): 모드와 단계를 정하고 본 단계도 그 단계로."""
    ss["coach_mode"], ss["coach_step"], ss["coach_seen"] = mode, step, step


def reset(ss: MutableMapping) -> None:
    """'내 숫자로 시작': 선언된 reset 키를 지우고 첫 단계부터."""
    for k in RESET:
        ss.pop(k, None)
    ss["coach_mode"], ss["coach_step"] = "mine", 0


def clamp_step(ss: MutableMapping, has_answer: bool) -> Tuple[int, int]:
    """열린 단계까지로 지금 단계를 줄임 → (지금 단계, 열린 마지막 단계).
    답이 없으면 내 가게만, 답이 있으면 모두 (v1.0: 최적화도 길을 막지 않음. 광고 시작 전이면 화면이 빈 화면 안내)."""
    unlocked = RESULT if has_answer else SHOP
    ss["coach_step"] = min(ss.get("coach_step", 0), unlocked)
    return ss["coach_step"], unlocked


# ── 계획 파일 (가정 A4: 로그인 없이 JSON 내려받기·올리기) ──────────────────────
PLAN_VERSION = 2   # 2: 재구매 실측(B3)·한 달 뒤 입력·세팅값(7d 자리) 추가. 1 파일도 읽음. 새 항목은 모두 있어도 되고 없어도 됨
PLAN_CHOICES = {"q_category": tuple(CATEGORIES), "q_repurchase": tuple(REPURCHASE_PRESETS) + (MEASURED,),
                "q_budget_pick": BUDGET_PICKS}   # 선택지 값은 화면 선택지 상수에서만 (B4)
# 재구매 실측: 숫자 dict (orders.measure 결과 중 화면이 쓰는 것, 고객 식별자 없음)
MEASURED_NUM_KEYS = ("customers", "orders", "observed_months", "repeat_share", "repeats_observed", "repeats_year")
PRED_KEYS = ("budget", "naver", "meta", "clicks", "cpc", "new", "cvr", "wins", "p10", "p90")


def _is_num(v) -> bool:
    """bool이 아닌 유한한 수 (NaN·무한대 제외)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _measured(v) -> Dict:
    if not (isinstance(v, dict) and all(_is_num(v.get(k)) and v[k] >= 0 for k in MEASURED_NUM_KEYS)):
        raise ValueError("재구매 실측 값이 이상해요")
    out = {k: v[k] for k in MEASURED_NUM_KEYS}
    out["extended"] = bool(v.get("extended", out["observed_months"] < 11.5))
    return out


def _input(k: str, v):
    if k == "q_stores":
        if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
            raise ValueError("판매처 값이 이상해요")
        return v
    if k == "repurchase_measured":
        return _measured(v)
    if k in PLAN_CHOICES:
        if v not in PLAN_CHOICES[k]:
            raise ValueError(f"{k} 값이 이상해요")
        return v
    if k == "q_keyword":
        if not isinstance(v, str):
            raise ValueError(f"{k} 값이 이상해요")
        return v
    if not _is_num(v) or v < 0:
        raise ValueError(f"{k} 값이 이상해요")
    return v


def _setting(v) -> bool:
    """세팅값(7d): 글자·숫자·참거짓 또는 그 목록만 (중첩 dict 없음)."""
    scalar = lambda x: x is None or isinstance(x, (str, bool)) or _is_num(x)  # noqa: E731
    return scalar(v) or (isinstance(v, list) and all(scalar(x) for x in v))


def _started(v) -> Optional[str]:
    if v is None:
        return None
    try:
        ok = isinstance(v, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)) and date.fromisoformat(v)
    except ValueError:
        ok = False
    if not ok:
        raise ValueError("시작일 형식이 이상해요")
    return v


@dataclass
class Plan:
    """계획 파일 한 장: 입력(재구매 실측·한 달 뒤 입력 포함), 그때의 예측, 광고 시작일, 세팅값(7d가 채움)."""
    inputs: Dict
    prediction: Dict
    started: Optional[str]
    settings: Dict = field(default_factory=dict)

    @classmethod
    def from_session(cls, ss, prediction: Dict, started: Optional[str], settings: Optional[Dict] = None) -> "Plan":
        return cls({k: ss.get(k) for k in PLAN if ss.get(k) is not None}, dict(prediction), started, dict(settings or {}))

    def to_json(self) -> str:
        body = {"version": PLAN_VERSION, "started": self.started,
                "inputs": {k: self.inputs[k] for k in PLAN if self.inputs.get(k) is not None},
                "prediction": {k: (None if self.prediction.get(k) is None else float(self.prediction[k])) for k in PRED_KEYS},
                "settings": self.settings}
        return json.dumps(body, ensure_ascii=False, indent=1)

    @classmethod
    def from_json(cls, text: str) -> "Plan":
        """정해진 키만 받는다 (다른 키는 버림). 형식이 틀리면 ValueError (화면은 사장님 문장으로 안내)."""
        body = json.loads(text)
        if not isinstance(body, dict) or body.get("version") not in (1, PLAN_VERSION):
            raise ValueError("계획 파일 형식이 아니에요")
        # 버전 변환 1 → 2: 새 항목(재구매 실측·한 달 뒤 입력·세팅값)이 없을 뿐, 나머지 그대로
        raw_in, raw_pred = body.get("inputs") or {}, body.get("prediction") or {}
        if not (isinstance(raw_in, dict) and isinstance(raw_pred, dict)):
            raise ValueError("계획 파일 형식이 아니에요")
        inputs = {k: _input(k, raw_in[k]) for k in PLAN if raw_in.get(k) is not None}
        pred = {}
        for k in PRED_KEYS:
            v = raw_pred.get(k)
            if v is None:
                continue
            if not _is_num(v):
                raise ValueError(f"예측 {k} 값이 이상해요")
            pred[k] = float(v)
        settings = body.get("settings") or {}
        if not (isinstance(settings, dict) and all(isinstance(k, str) and _setting(v) for k, v in settings.items())):
            raise ValueError("세팅값이 이상해요")
        return cls(inputs, pred, _started(body.get("started")), settings)


def apply_plan(ss: MutableMapping, plan: Plan) -> None:
    """불러온 계획을 화면 상태에 넣음. 고른 예산이 있으면 사장님이 고른 것으로, 시작일이 있으면 한 달 뒤(최적화)로."""
    for k, v in plan.inputs.items():
        ss[k] = v
    if "q_budget_pick" in plan.inputs:
        ss["_budget_touched"] = True
    ss["plan_pred"] = plan.prediction
    ss["coach_mode"] = "mine"
    if plan.started:
        ss["coach_started"], ss["coach_step"], ss["coach_seen"] = plan.started, RESULT, RESULT
