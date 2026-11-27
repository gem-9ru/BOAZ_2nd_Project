"""가상 케이스 6개 (v4 4-1장: AN-06 근거 탭·발표 자료만, 판정에는 안 씀).

메타 설정 하나만 다르게 한 A/B 두 세트를 오븐로그 실측(11/17~20) 비율로 만들어, 실제 분석 엔진(loop.run)에
그대로 넣었을 때 결론·판정·알림이 규칙대로 나오는지 보여 준다. 네이버 광고는 돌리지 않으므로 메타만.
- 실측: 오븐로그 A(자동 노출 위치) · B(직접 고르기) 의 광고비(CPM)·누르는 비율(CTR)·도착 비율
- 가정(D): 실측에 없는 값 (주소 잘못일 때 도착 비율, 좁은 지역에서 같은 사람에게 반복될 때 빈도·클릭률 하락)
시드 고정이라 다시 돌려도 같은 숫자. 화면 표는 scripts/virtual_cases.py 가 web/src/steps/cases.ts 로 적는다.
"""
import io
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..meta_export import read_export
from . import run as loop_run

SEED = 20261126
# 오븐로그 실측 (summary 기준): 광고 1,000번 보여주는 데 드는 돈 · 누르는 비율 · 누른 뒤 도착 비율
AUTO = {"cpm": 6342, "ctr": 0.0155, "visit": 0.77}
MANUAL = {"cpm": 5389, "ctr": 0.0173, "visit": 0.82}
PLACES = [("Instagram", "Instagram 릴스", 0.72), ("Instagram", "피드", 0.28)]   # 오븐로그 지출의 72%가 릴스


def _arm(name: str, p: Dict, spends: List[float], freq: float = 1.1, ctr_drop: float = 0.0) -> Dict:
    return {"name": name, "p": p, "spends": spends, "freq": freq, "ctr_drop": ctr_drop}


def _per_set(total: int, days: int) -> List[float]:
    return [total / days] * days


CASES: List[Dict] = [
    {"id": "V1", "setting": "노출 위치: 자동 vs 직접 고르기", "basis": "실측",
     "arms": [_arm("A_자동노출위치", AUTO, _per_set(5000, 4)), _arm("B_수동노출위치", MANUAL, _per_set(5000, 4))]},
    {"id": "V2", "setting": "같은 설정 두 세트 (차이 없음)", "basis": "실측",
     "arms": [_arm("A_수동노출위치", MANUAL, _per_set(5000, 4)), _arm("B_수동노출위치", MANUAL, _per_set(5000, 4))]},
    {"id": "V3", "setting": "총예산이 '하루 최소 × 기간'보다 적음 (두 세트 모두 2,000원)", "basis": "실측 (11/17 안 나간 날)",
     "settings": {"meta.adset.lifetime_budget": "2,000원"},
     "arms": [_arm("A_자동노출위치", AUTO, [0, 300, 300, 300]), _arm("B_수동노출위치", MANUAL, [0, 300, 300, 300])]},
    {"id": "V4", "setting": "예산 공유(최대 20%) 켬 → 한 세트에 돈이 몰림", "basis": "실측 (모닝빈 28 : 72)",
     "arms": [_arm("A_자동노출위치", AUTO, _per_set(2800, 4)), _arm("B_수동노출위치", MANUAL, _per_set(7200, 4))]},
    {"id": "V5", "setting": "B 웹사이트 주소 잘못 (페이지가 늦게 열림)", "basis": "가정: 도착 비율 45%",
     "arms": [_arm("A_수동노출위치", MANUAL, _per_set(5000, 4)), _arm("B_수동노출위치", {**MANUAL, "visit": 0.45}, _per_set(5000, 4))]},
    {"id": "V6", "setting": "좁은 지역 + 14일 (같은 사람에게 반복)", "basis": "가정: 빈도 3번 · 뒤 절반 클릭 30%↓",
     "arms": [_arm("A_수동노출위치", MANUAL, _per_set(20000, 14), freq=3.0, ctr_drop=0.3),
              _arm("B_수동노출위치", MANUAL, _per_set(20000, 14), freq=3.0, ctr_drop=0.3)]},
]


def export_csv(case: Dict, seed: int = SEED) -> bytes:
    """케이스 → 메타 광고 관리자 내보내기 모양 CSV (일 × 노출 위치). 노출·클릭·도착은 실측 비율에서 무작위로 뽑는다."""
    rng = np.random.default_rng(seed)
    rows = []
    days = len(case["arms"][0]["spends"])
    for d in range(days):
        date = (pd.Timestamp("2026-11-17") + pd.Timedelta(days=d)).strftime("%Y-%m-%d")
        for arm in case["arms"]:
            p = arm["p"]
            ctr = p["ctr"] * (1 - arm["ctr_drop"] if d >= days // 2 else 1)
            for plat, place, share in PLACES:
                spend = round(arm["spends"][d] * share)
                imps = int(rng.poisson(spend / p["cpm"] * 1000)) if spend else 0
                clicks = int(rng.binomial(imps, ctr)) if imps else 0
                visits = int(rng.binomial(clicks, p["visit"])) if clicks else 0
                rows.append({"보고 시작": date, "보고 종료": date, "광고 세트 이름": arm["name"], "플랫폼": plat, "노출 위치": place,
                             "지출 금액 (KRW)": spend, "노출": imps, "도달": round(imps / arm["freq"]), "링크 클릭": clicks,
                             "랜딩 페이지 조회": visits})
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8")


def outcome(case: Dict, seed: int = SEED) -> Dict:
    """케이스를 실제 분석 엔진에 넣은 결과: 결론(테스트할 칸) · 판정 · 뜬 주의 알림."""
    r = loop_run.run(read_export(io.BytesIO(export_csv(case, seed))), seed=0, settings=case.get("settings"))
    ch = r["matrix"]["change"] or {}
    badge = (r["verdict"] or {}).get("badge") or {}
    warns = [a["kind"] for a in r["alerts"] if a["level"] in ("block", "warn")]
    return {"id": case["id"], "setting": case["setting"], "basis": case["basis"],
            "conclusion": f"{ch.get('path', '')}: {ch.get('new_short', '')}".strip(": ") or "—",
            "word": badge.get("word"), "prob": round(float(badge["prob"]), 2) if badge.get("prob") is not None else None,
            "better": badge.get("better"), "alerts": warns}


def all_outcomes(seed: int = SEED) -> List[Dict]:
    return [outcome(c, seed) for c in CASES]
