"""퍼널: 본 사람 → 누른 사람 → 들어온 사람 (광고 관리자 숫자 기준).

단계 사이 비율은 베타 분포 95% 범위와 함께. 앞 단계 건수가 10 미만이면 '아직 몰라요'.
가장 문제인 단계에 원인 힌트 한 줄.
"""
from typing import Dict, List

import numpy as np

FEW = 10
STAGES = [("impressions", "보여진 횟수"), ("link_clicks", "클릭"), ("landing_page_views", "손님 (페이지 방문)")]
VERB = {"link_clicks": "눌렀어요", "landing_page_views": "들어왔어요"}


def _range(k: float, n: float, seed: int = 0):
    d = np.random.default_rng(seed).beta(1 + k, 1 + max(n - k, 0), 100_000)
    return float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))


def _per100(rate: float, key: str) -> str:
    """비율을 사람 수로 (v4.2): 누르는 정도는 100명 기준으로 차이가 안 보여서 1,000명 기준."""
    base = 1000 if key == "link_clicks" else 100
    n = rate * base
    shown = f"약 {n:.0f}명" if n >= 1 else f"약 {n:.1f}명"
    return f"{base:,}명이 {'보면' if key == 'link_clicks' else '누르면'} {shown}이 {VERB[key]}"


def run(arms: List[Dict]) -> Dict:
    out = []
    for a in arms:
        stages, prev = [], None
        for key, label in STAGES:
            count = float(a.get(key, 0.0))
            st = {"key": key, "label": label, "count": count}
            if prev is not None and prev > 0:
                rate = count / prev
                st.update({"rate": rate, "range": _range(count, prev), "per100": _per100(rate, key), "unknown": prev < FEW})
            stages.append(st)
            prev = count
        out.append({"name": a["name"], "stages": stages})

    hint = None
    clicks = sum(a["link_clicks"] for a in arms)
    imps = sum(a["impressions"] for a in arms)
    visits = sum(a["landing_page_views"] for a in arms)
    if clicks >= 5 and visits / clicks < 0.7:
        hint = f"누른 사람 중 {visits / clicks:.0%}만 들어왔어요. 클릭은 했는데 도착이 적으면 페이지가 늦게 열리는지 점검해 보세요."
    elif imps >= 300 and clicks / imps < 0.01:
        hint = f"1,000명이 보면 {clicks / imps * 1000:.0f}명만 눌러요. 사진과 첫 문장을 바꿔 보는 게 먼저예요."
    return {"arms": out, "hint": hint}
