"""한 달 뒤 재계산 (노션 Q4): 계획 파일 저장·불러오기, 네이버·메타 리포트 CSV 매핑, 진단 규칙, 과대 집계율·예측 오차율.

리포트 열 이름
- 메타: 광고 관리자 '보고서 내보내기'(한국어) 실제 파일의 열 이름 ✅ (팀 제공 캠페인 내보내기, 2026-11).
  예: 지출 금액 (KRW), 노출, 도달, 빈도, 링크 클릭, CTR(링크 클릭률), 결과, 결과 표시 도구
- 네이버: 검색광고 '다차원 보고서' 항목 이름 △ (대행사 안내 기준, 공식 문서·실제 파일 미확인)
  예: 노출수, 클릭수, 총비용(VAT포함,원), 전환수, 전환매출액(원)
열 이름은 판매처·버전마다 달라 화면에서 사용자가 고칠 수 있게 한다.
"""
import json
import math
import re
from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .coach import BUDGET_PICKS, CATEGORIES, REPURCHASE_PRESETS

PLAN_VERSION = 2          # 2: 재구매 실측(repurchase_measured) 추가 (MVP 7e B3). 버전 1 파일도 그대로 읽음
# 계획 파일에 담는 입력 (개인정보 없음: 상품·숫자·검색어·재구매 실측 숫자만)
PLAN_INPUT_KEYS = ("q_category", "q_stores", "q_price", "q_profit", "q_repurchase", "q_budget", "q_baseline", "q_keyword",
                   "q_cpc", "q_budget_pick", "repurchase_measured")
MEASURED = "실측"         # 재구매 선택지: 주문 내역으로 잰 내 가게 값 (main.py와 같은 값)
# 선택지 값은 화면 선택지 상수에서만 (B4)
PLAN_CHOICES = {"q_category": tuple(CATEGORIES), "q_repurchase": tuple(REPURCHASE_PRESETS) + (MEASURED,),
                "q_budget_pick": BUDGET_PICKS}
# 재구매 실측: 숫자 dict (orders.measure 결과 중 화면이 쓰는 것, 고객 식별자 없음)
MEASURED_NUM_KEYS = ("customers", "orders", "observed_months", "repeat_share", "repeats_observed", "repeats_year")
PLAN_PRED_KEYS = ("budget", "naver", "meta", "clicks", "cpc", "new", "cvr", "wins", "p10", "p90")


# ── 계획 파일 (가정 A4: 로그인 없이 JSON 내려받기·올리기) ──────────────────────
def plan_to_json(inputs: Dict, prediction: Dict, started: Optional[str]) -> str:
    body = {"version": PLAN_VERSION, "started": started,
            "inputs": {k: inputs.get(k) for k in PLAN_INPUT_KEYS if k in inputs and inputs.get(k) is not None},
            "prediction": {k: (None if prediction.get(k) is None else float(prediction[k])) for k in PLAN_PRED_KEYS}}
    return json.dumps(body, ensure_ascii=False, indent=1)


def _is_num(v) -> bool:
    """bool이 아닌 유한한 수 (NaN·무한대 제외)."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _measured(v) -> Dict:
    if not (isinstance(v, dict) and all(_is_num(v.get(k)) and v[k] >= 0 for k in MEASURED_NUM_KEYS)):
        raise ValueError("재구매 실측 값이 이상해요")
    out = {k: v[k] for k in MEASURED_NUM_KEYS}
    out["extended"] = bool(v.get("extended", out["observed_months"] < 11.5))
    return out


def _upgrade(body: Dict) -> Dict:
    """버전 변환 (1 → 2: 재구매 실측 항목이 없을 뿐, 나머지 그대로)."""
    if body.get("version") == 1:
        body = dict(body, version=2)
    return body


def plan_from_json(text: str) -> Tuple[Dict, Dict, Optional[str]]:
    """정해진 키만 받는다 (다른 키는 버림). 형식이 틀리면 ValueError (화면은 사장님 문장으로 안내)."""
    body = json.loads(text)
    if not isinstance(body, dict) or body.get("version") not in (1, PLAN_VERSION):
        raise ValueError("계획 파일 형식이 아니에요")
    body = _upgrade(body)
    raw_in, raw_pred = body.get("inputs") or {}, body.get("prediction") or {}
    inputs = {}
    for k in PLAN_INPUT_KEYS:
        if k not in raw_in or raw_in[k] is None:
            continue
        v = raw_in[k]
        if k == "q_stores":
            if not (isinstance(v, list) and all(isinstance(x, str) for x in v)):
                raise ValueError("판매처 값이 이상해요")
        elif k == "repurchase_measured":
            v = _measured(v)
        elif k in PLAN_CHOICES:
            if v not in PLAN_CHOICES[k]:
                raise ValueError(f"{k} 값이 이상해요")
        elif k == "q_keyword":
            if not isinstance(v, str):
                raise ValueError(f"{k} 값이 이상해요")
        elif not _is_num(v) or v < 0:
            raise ValueError(f"{k} 값이 이상해요")
        inputs[k] = v
    pred = {}
    for k in PLAN_PRED_KEYS:
        v = raw_pred.get(k)
        if v is None:
            continue
        if not _is_num(v):
            raise ValueError(f"예측 {k} 값이 이상해요")
        pred[k] = float(v)
    started = body.get("started")
    if started is not None:
        try:
            ok = isinstance(started, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", started)) and date.fromisoformat(started)
        except ValueError:
            ok = False
        if not ok:
            raise ValueError("시작일 형식이 이상해요")
    return inputs, pred, started


# ── 리포트 열 매핑 ─────────────────────────────────────────────
METRICS = {
    "impressions": "노출", "clicks": "클릭", "cost": "광고비", "conversions": "전환(구매)", "revenue": "전환 매출",
    "reach": "도달", "frequency": "빈도", "objective": "결과 종류(목적)",
}
# 앞에 있는 이름이 먼저 맞으면 그 열. (정확히 같음 = '=', 포함 = 그대로)
WORDS = {
    "naver": {
        "impressions": ["노출수"], "clicks": ["클릭수"], "cost": ["총비용", "비용"], "conversions": ["전환수"],
        "revenue": ["전환매출액", "전환매출"], "reach": [], "frequency": [], "objective": [],
    },
    "meta": {
        "impressions": ["=노출", "노출"], "clicks": ["=링크 클릭", "링크 클릭"], "cost": ["지출 금액", "지출"],
        "conversions": ["=웹사이트 구매", "=구매", "=결과"], "revenue": ["구매 전환값", "전환값"],
        "reach": ["=도달"], "frequency": ["=빈도"], "objective": ["=결과 표시 도구"],
    },
}
EXCLUDE = ("률", "당", "비율", "평균", "CPC", "CPM", "CTR")   # '클릭률', '결과당 비용', '평균클릭비용' 같은 파생 열은 합계 대상 아님
TOTAL_ROW_WORDS = ("합계", "총계")   # 내보내기 맨 아래 합계 행 (더하면 두 번 셈)


def _clean(name) -> str:
    """BOM(엑셀에서 저장한 UTF-8 CSV 첫 열 앞의 \ufeff)과 앞뒤 공백 제거."""
    return str(name).replace("\ufeff", "").strip()


def read_report(f) -> pd.DataFrame:
    """CSV(BOM 있어도)·엑셀 읽기. 열 이름의 BOM·공백도 정리."""
    name = getattr(f, "name", str(f)).lower()
    df = pd.read_csv(f, encoding="utf-8-sig") if name.endswith(".csv") else pd.read_excel(f)
    df.columns = [_clean(c) for c in df.columns]
    return df


def detect_platform(columns: List[str]) -> Optional[str]:
    cols = " ".join(_clean(c) for c in columns)
    if "지출 금액" in cols or "링크 클릭" in cols or "결과 표시 도구" in cols:
        return "meta"
    if "노출수" in cols and "클릭수" in cols:
        return "naver"
    return None


def map_columns(columns: List[str], platform: str) -> Dict[str, Optional[str]]:
    out, used = {}, set()
    for metric in METRICS:
        out[metric] = None
        for w in WORDS[platform][metric]:
            exact = w.startswith("=")
            word = w.lstrip("=")
            for c in columns:
                name = _clean(c)
                if c in used:
                    continue
                if exact and name != word:
                    continue
                if not exact and (word not in name or (metric not in ("objective",) and any(x in name for x in EXCLUDE))):
                    continue
                out[metric] = c
                used.add(c)
                break
            if out[metric] is not None:
                break
    return out


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[,원\s%₩]", "", regex=True), errors="coerce").fillna(0.0)


def totals(df: pd.DataFrame, mapping: Dict[str, Optional[str]], platform: str) -> Dict:
    """합계. 빈도는 노출 ÷ 도달, 목적은 가장 많이 나온 결과 종류. 메타 '결과'가 구매가 아니면 전환으로 세지 않음."""
    out = {"platform": platform}
    text = df.select_dtypes(exclude="number").astype(str).apply(lambda s: s.str.strip())
    if not text.empty:
        df = df[~text.isin(TOTAL_ROW_WORDS).any(axis=1)]
    for m in ("impressions", "clicks", "cost", "conversions", "revenue", "reach"):
        col = mapping.get(m)
        out[m] = float(_num(df[col]).sum()) if col and col in df.columns else None
    obj_col = mapping.get("objective")
    objective = None
    if obj_col and obj_col in df.columns and df[obj_col].notna().any():
        objective = str(df[obj_col].dropna().astype(str).mode().iloc[0])
    out["objective"] = objective
    out["objective_is_purchase"] = objective is None or bool(re.search(r"purchase|구매", objective, re.I))
    if platform == "meta" and mapping.get("conversions") is not None and _clean(mapping["conversions"]) == "결과" \
            and not out["objective_is_purchase"]:
        out["conversions_note"] = f"'결과'가 구매가 아니라 '{objective}'라서 전환으로 세지 않았어요"
        out["conversions"] = 0.0
    if out.get("reach") and out.get("impressions"):
        out["frequency"] = out["impressions"] / out["reach"]
    elif mapping.get("frequency") and mapping["frequency"] in df.columns:
        out["frequency"] = float(_num(df[mapping["frequency"]]).mean())
    else:
        out["frequency"] = None
    return out


# ── 진단 규칙 (노션 Q4) ──────────────────────────────────────────
CTR_HIGH = 0.01          # 링크 클릭률 1% 이상이면 '광고는 눌린다'
FREQ_HIGH = 3.0          # 메타 빈도 3 이상이면 같은 사람이 여러 번 봄
BUY_LOW_RATIO = 0.5      # 실측 구매 비율이 예측의 절반 미만이면 '상세페이지'


def diagnose(rep: Dict, predicted_cvr: Optional[float]) -> List[Dict[str, str]]:
    """규칙 → [{"title", "evidence", "action"}]. 리포트 하나(플랫폼 하나)에 대해."""
    out = []
    name = "네이버" if rep["platform"] == "naver" else "메타"
    imp, clk, conv = rep.get("impressions") or 0, rep.get("clicks") or 0, rep.get("conversions")
    ctr = clk / imp if imp else None
    buy = (conv / clk) if (clk and conv is not None) else None
    if rep["platform"] == "meta" and not rep.get("objective_is_purchase", True):
        out.append({"title": f"{name}: 광고 목적이 구매가 아니에요",
                    "evidence": f"결과 종류가 '{rep.get('objective')}'예요. 이 목적이면 메타는 구매할 사람보다 많이 보거나 누를 사람을 찾아요.",
                    "action": "판매를 늘리려면 캠페인 목적을 '판매(전환)'로 바꾸고 픽셀 구매 이벤트를 최적화 기준으로 고르세요."})
    if ctr is not None and ctr >= CTR_HIGH and buy is not None and predicted_cvr and buy < predicted_cvr * BUY_LOW_RATIO:
        out.append({"title": f"{name}: 누르긴 하는데 사지 않아요 → 상세페이지 먼저",
                    "evidence": f"클릭률 {ctr:.1%}로 광고는 잘 눌리는데, 누른 사람 중 산 비율이 {buy:.2%}로 예상({predicted_cvr:.2%})의 절반도 안 돼요.",
                    "action": "사진·후기·가격·배송 안내를 고치고, 고친 뒤 같은 예산으로 2주 다시 비교하세요."})
    freq = rep.get("frequency")
    if rep["platform"] == "meta" and freq and freq >= FREQ_HIGH and ctr is not None and ctr < CTR_HIGH:
        out.append({"title": "메타: 같은 사람이 너무 자주 봐요 → 소재 피로",
                    "evidence": f"한 사람이 평균 {freq:.1f}번 봤고 클릭률은 {ctr:.1%}예요.",
                    "action": "새 사진·영상(소재) 2~3개를 추가하거나 보여 줄 사람(타깃)을 넓히세요."})
    if conv == 0 and clk > 0 and rep.get("objective_is_purchase", True):
        out.append({"title": f"{name}: 전환이 0건이에요 → 측정부터 확인",
                    "evidence": f"클릭 {clk:,.0f}번에 전환이 한 건도 잡히지 않았어요.",
                    "action": "네이버는 전환 추적 스크립트, 메타는 픽셀 구매 이벤트가 설치돼 있는지 확인하세요. 실제 주문이 있었다면 측정이 빠진 거예요."})
    if rep["platform"] == "naver" and imp and imp < 1_000:
        out.append({"title": "네이버: 광고가 거의 보이지 않았어요",
                    "evidence": f"한 달 노출이 {imp:,.0f}번이에요.",
                    "action": "검색량이 더 많은 검색어를 추가하거나 입찰가를 조금 올리세요."})
    return out


def over_count_rate(report_conversions: float, actual_orders: float) -> Optional[float]:
    """플랫폼 과대 집계율 = (네이버 + 메타 리포트 전환 − 실제 주문) ÷ 실제 주문. 같은 주문을 두 플랫폼이 모두 자기 몫으로 세면 커짐."""
    if not actual_orders:
        return None
    return (report_conversions - actual_orders) / actual_orders


def prediction_error(predicted: Optional[float], actual: Optional[float]) -> Optional[float]:
    """예측 오차율 = |예측 − 실측| ÷ 실측."""
    if predicted is None or not actual:
        return None
    return abs(predicted - actual) / actual


class ScaledCurve:
    """실측 클릭 비용으로 보정한 곡선: 같은 돈이면 클릭이 k배 (k = 예측 CPC ÷ 실측 CPC)."""

    def __init__(self, curve, k: float):
        self.curve, self.k = curve, float(k)
        self.capacity = getattr(curve, "capacity", float("inf"))

    def spendable(self, s: float) -> float:
        return self.curve.spendable(s)

    def clicks(self, s: float) -> float:
        return self.curve.clicks(s) * self.k

    def marginal_cpc(self, s: float):
        m = self.curve.marginal_cpc(s)
        return None if m is None else m / self.k
