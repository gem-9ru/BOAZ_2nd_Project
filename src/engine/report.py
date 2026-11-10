"""한 달 뒤 재계산 (노션 Q4): 네이버·메타 리포트 CSV 매핑, 진단 규칙, 과대 집계율·예측 오차율.

리포트 열 이름
- 메타: 광고 관리자 '보고서 내보내기'(한국어) 실제 파일의 열 이름 ✅ (팀 제공 캠페인 내보내기, 2026-11).
  예: 지출 금액 (KRW), 노출, 도달, 빈도, 링크 클릭, CTR(링크 클릭률), 결과, 결과 표시 도구
- 네이버: 검색광고 '다차원 보고서' 항목 이름 △ (대행사 안내 기준, 공식 문서·실제 파일 미확인)
  예: 노출수, 클릭수, 총비용(VAT포함,원), 전환수, 전환매출액(원)
열 이름은 판매처·버전마다 달라 화면에서 사용자가 고칠 수 있게 한다.
"""
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .uploads import guess_columns

# ── 리포트 열 매핑 ─────────────────────────────────────────────
METRICS = {
    "impressions": "노출", "clicks": "클릭", "cost": "광고비", "conversions": "전환(구매)", "revenue": "전환 매출",
    "reach": "도달", "frequency": "빈도", "objective": "결과 종류(목적)", "landing": "랜딩 페이지 조회",
}
# 앞에 있는 이름이 먼저 맞으면 그 열. (정확히 같음 = '=', 포함 = 그대로)
WORDS = {
    "naver": {
        "impressions": ["노출수"], "clicks": ["클릭수"], "cost": ["총비용", "비용"], "conversions": ["전환수"],
        "revenue": ["전환매출액", "전환매출"], "reach": [], "frequency": [], "objective": [], "landing": [],
    },
    "meta": {
        "impressions": ["=노출", "노출"], "clicks": ["=링크 클릭", "링크 클릭"], "cost": ["지출 금액", "지출"],
        "conversions": ["=웹사이트 구매", "=구매", "=결과"], "revenue": ["구매 전환값", "전환값"],
        "reach": ["=도달"], "frequency": ["=빈도"], "objective": ["=결과 표시 도구"],
        "landing": ["=랜딩 페이지 조회"],   # 실제 메타 내보내기 열 (v1.0 랜딩 도달률)
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
    """열 이름 → 지표 (uploads.guess_columns 규칙 하나). 이름은 BOM·앞뒤 공백만 정리하고 비교, 파생 열(EXCLUDE)은 뺌."""
    return guess_columns(((m, WORDS[platform][m]) for m in METRICS), columns, norm=_clean,
                         exclude=EXCLUDE, exclude_except=("objective",))


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[,원\s%₩]", "", regex=True), errors="coerce").fillna(0.0)


def totals(df: pd.DataFrame, mapping: Dict[str, Optional[str]], platform: str) -> Dict:
    """합계. 빈도는 노출 ÷ 도달, 목적은 가장 많이 나온 결과 종류. 메타 '결과'가 구매가 아니면 전환으로 세지 않음."""
    out = {"platform": platform}
    text = df.select_dtypes(exclude="number").astype(str).apply(lambda s: s.str.strip())
    if not text.empty:
        df = df[~text.isin(TOTAL_ROW_WORDS).any(axis=1)]
    for m in ("impressions", "clicks", "cost", "conversions", "revenue", "reach", "landing"):
        col = mapping.get(m)
        out[m] = float(_num(df[col]).sum()) if col and col in df.columns else None
        if m == "landing" and col and col in df.columns and df[col].replace("", None).isna().all():
            out[m] = None   # 메타는 랜딩 추적을 안 켜면 이 열을 비워 둠. 빈칸 = 모름이지 0번이 아님 (실제 내보내기 파일에서 확인)
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
LANDING_LOW = 0.8        # 링크 클릭 중 랜딩 페이지가 열린 비율 80% 미만이면 '페이지가 늦게 열림' (D 가정, v1.0)


# 가장 많이 빠지는 단계 → 결론 한 문장 (차트 아래, 화면 읽기 프로그램도 같은 결론에 닿게)
STEP_SENTENCE = {
    "클릭률": "광고가 잘 안 눌려요. 메타는 문구·사진, 네이버는 검색어·제목부터 바꿔 보세요.",
    "랜딩 도달": "눌렀는데 페이지가 열리기 전에 나가요. 링크와 휴대폰에서 페이지가 열리는 속도를 확인하세요.",
    "구매 비율": "광고는 눌리는데 상세페이지에서 빠져요. 광고비를 늘리기 전에 사진·후기·가격부터 고치세요.",
}


def step_rates(rep: Dict, predicted_cvr: Optional[float]) -> Dict:
    """매체 하나의 단계별 남는 비율 (v1.0 퍼널 막대). 건수가 수천 배 차이 나서 건수 대신 '단계 사이 비율 ÷ 기준'으로 그린다.
    → {"rows": [{name, rate, base, base_label, ratio}], "counts": [(이름, 건수)], "worst": 기준보다 가장 낮은 행 또는 None}"""
    imp, clk = rep.get("impressions") or 0, rep.get("clicks") or 0
    land, conv = rep.get("landing"), rep.get("conversions")
    rows, counts = [], [("노출", imp), ("클릭", clk)]
    if imp:
        rows.append({"name": "클릭률", "rate": clk / imp, "base": CTR_HIGH, "base_label": f"기준 {CTR_HIGH:.0%}"})
    if land and clk:      # 네이버 리포트에는 랜딩 페이지 조회가 없음 → 그 단계를 건너뜀
        rows.append({"name": "랜딩 도달", "rate": land / clk, "base": LANDING_LOW, "base_label": f"기준 {LANDING_LOW:.0%} (가정)"})
        counts.append(("랜딩", land))
    if conv is not None and clk and rep.get("objective_is_purchase", True) and predicted_cvr:
        rows.append({"name": "구매 비율", "rate": conv / clk, "base": predicted_cvr, "base_label": f"예상 {predicted_cvr:.1%}"})
        counts.append(("구매", conv))
    for r in rows:
        r["ratio"] = r["rate"] / r["base"] if r["base"] else None
    below = [r for r in rows if r["ratio"] is not None and r["ratio"] < 1]
    return {"rows": rows, "counts": counts, "worst": min(below, key=lambda r: r["ratio"]) if below else None}


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
    land = rep.get("landing")
    if land is not None and clk and land / clk < LANDING_LOW:
        out.append({"title": f"{name}: 눌렀는데 페이지가 열리기 전에 나가요",
                    "evidence": f"링크 클릭 {clk:,.0f}번 중 페이지가 열린 건 {land:,.0f}번({land / clk:.0%})이에요 (기준 {LANDING_LOW:.0%}, 가정).",
                    "action": "광고 링크가 맞는 상품 페이지로 가는지, 휴대폰에서 페이지가 빨리 열리는지 확인하세요."})
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
