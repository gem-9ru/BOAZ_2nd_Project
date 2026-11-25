"""4 판정: B가 나을 확률로 채택·유력·보류 (희수 8장 ④ 90/70% 규칙, 다정 M1 확률 계산).

코드 값(level)은 개발 문서·근거 탭용 확실/유력/보류, 사장님 화면 글(word)은
'확실해요 / ○ 쪽이에요 / 아직 몰라요' 3개만 (설계서 v4.2 AN-TXT). 기준 90% / 70%는 같다.

- 판정 배지 지표: 1,000원당 도착 (11/22 회의 제안, 다정 79%와 같은 계산)
- 일자별 재현: 날마다 누적해서 다시 계산 → 며칠치로 고르면 뒤집힌다 (다정 M3, Lewis & Rao 2015)
- 최소 검증 예산: 기대 효과에서 '90% 확신으로 승자를 고를 확률'이 80% 이상이 되는 그룹당 예산 (희수 8장 ④, Feit & Berman 2019는 근거 인용)
"""
from typing import Dict, List, Optional

import numpy as np

from . import posterior, summary, words
from ..specs import loop as _loop

BADGE = "visits_per_1000won"
METRICS = [  # (키, 사장님 말 이름 (약어), 클수록 좋은가)
    ("visits_per_1000won", "같은 돈으로 온 손님", True),
    ("cpm", "광고 1,000번 보여주는 데 드는 돈 (CPM)", False),
    ("cpc", "클릭 1번에 드는 돈 (CPC)", False),
    ("ctr", "본 사람 중 누른 비율 (CTR)", True),
]
ADOPT, LIKELY = 0.9, 0.7


def level(p: float) -> str:
    return "채택" if p >= ADOPT else "유력" if p >= LIKELY else "보류"


def word(p: float, overlap: bool, better: str) -> str:
    """사이트 전체에서 쓰는 판정 문구 3개 (희수 90/70% + 다정 '말할 수 있음/방향만/말할 수 없음').
    p는 나은 쪽의 확률(0.5 이상). 95% 범위가 안 겹치면 확실."""
    if p >= ADOPT or not overlap:
        return "확실해요"
    return f"{better} 쪽이에요" if p >= LIKELY else "아직 몰라요"


def _q(x: np.ndarray, level_: float = 0.95):
    t = (1 - level_) / 2
    return float(np.quantile(x, t)), float(np.quantile(x, 1 - t))


def compare(a: Dict, b: Dict, seed: int = 0) -> Dict:
    da, db = posterior.draws(a, seed=seed), posterior.draws(b, seed=seed + 1)
    metrics = []
    for key, label, higher in METRICS:
        p = float((db[key] > da[key]).mean() if higher else (db[key] < da[key]).mean())
        ai, bi = _q(da[key]), _q(db[key])
        overlap = not (ai[1] < bi[0] or bi[1] < ai[0])
        better = "B" if p >= 0.5 else "A"
        metrics.append({"key": key, "label": label, "higher_is_better": higher, "prob_b_better": p,
                        "a_interval": ai, "b_interval": bi, "overlap": overlap, "better": better,
                        "word": word(max(p, 1 - p), overlap, better)})
    m = next(x for x in metrics if x["key"] == BADGE)
    conf = max(m["prob_b_better"], 1 - m["prob_b_better"])
    return {"a": a["name"], "b": b["name"], "metrics": metrics,
            "badge": {"metric": BADGE, "label": "손님 1명당 비용", "better": m["better"], "prob": conf,
                      "level": level(conf), "word": m["word"]}}


def _prob_visits(a: Dict, b: Dict, n: int = 50_000, seed: int = 0) -> float:
    rng = np.random.default_rng(seed)
    la = rng.gamma(1 + a["landing_page_views"], 1 / max(a["spend"], 1e-9), n)
    lb = rng.gamma(1 + b["landing_page_views"], 1 / max(b["spend"], 1e-9), n)
    return float((lb > la).mean())


def daily_replay(bundle, a_name: str, b_name: str) -> List[Dict]:
    """날짜마다 그날까지 누적한 숫자로 'B가 나을 확률'을 다시 계산. 두 세트 다 아직 안 나간 날은 뺀다."""
    d = bundle.tables["meta_daily"].df
    cols = [c for c in summary.COUNTS if c in d.columns]
    out = []
    for date in sorted(d["date"].unique()):
        upto = d[d["date"] <= date]
        s = upto.groupby("adset")[cols].sum()
        if a_name not in s.index or b_name not in s.index or s.loc[a_name, "spend"] <= 0 or s.loc[b_name, "spend"] <= 0:
            continue
        a = summary.arm(a_name, *(float(s.loc[a_name].get(c, 0.0)) for c in summary.COUNTS))
        b = summary.arm(b_name, *(float(s.loc[b_name].get(c, 0.0)) for c in summary.COUNTS))
        p = _prob_visits(a, b)
        few = min(a["landing_page_views"], b["landing_page_views"])
        # 그날까지 손님이 세트마다 기준보다 적으면 표본 부족 → '아직 몰라요' (ALT-14와 같은 생각, rules.yaml)
        w = "아직 몰라요" if few < _loop()["alerts"].get("replay_min_visits", 5) else words.word_of(max(p, 1 - p), "B" if p >= 0.5 else "A")
        out.append({"date": str(np.datetime_as_string(np.datetime64(date, "D"))), "prob": p, "min_visits": few, "word": w})
    return out


def min_budget(a: Dict, lift: float = 0.2, confidence: float = ADOPT, power: float = 0.8, seed: int = 0,
               sims: int = 400, n_draws: int = 4000, max_per_group: int = 3_000_000) -> Dict:
    """A의 1,000원당 도착이 그대로이고 B가 lift만큼 좋을 때, 그룹마다 얼마를 써야
    'P(B>A) ≥ confidence'로 B를 고를 확률이 power 이상이 되는지. 1,000원 단위."""
    rate_a = a["landing_page_views"] / a["spend"] if a["spend"] else 0.0
    if rate_a <= 0:
        return {"per_group": None, "total": None, "lift": lift, "confidence": confidence, "power": None, "metric": BADGE}
    rate_b = rate_a * (1 + lift)

    def achieved(x: int) -> float:
        rng = np.random.default_rng(seed)
        ka, kb = rng.poisson(rate_a * x, sims), rng.poisson(rate_b * x, sims)
        la = rng.gamma(1 + ka[:, None], 1 / x, (sims, n_draws))
        lb = rng.gamma(1 + kb[:, None], 1 / x, (sims, n_draws))
        return float(((lb > la).mean(axis=1) >= confidence).mean())

    lo, hi = 1, max_per_group // 1000
    if achieved(hi * 1000) < power:
        return {"per_group": None, "total": None, "lift": lift, "confidence": confidence, "power": None, "metric": BADGE}
    while lo < hi:
        mid = (lo + hi) // 2
        if achieved(mid * 1000) >= power:
            hi = mid
        else:
            lo = mid + 1
    x = lo * 1000
    return {"per_group": x, "total": 2 * x, "lift": lift, "confidence": confidence, "power": achieved(x), "metric": BADGE}


_ORDER = ["보류", "유력", "채택"]


def _word_for(level_: str, better: str) -> str:
    return {"채택": "확실해요", "유력": f"{better} 쪽이에요", "보류": "아직 몰라요"}[level_]


def apply_caps(v: Dict, small_sample: bool, spend_gap: bool) -> Dict:
    """알림에 따라 확실도를 낮춘다: 표본 부족(ALT-14) → 최대 '유력', 지출 쏠림(ALT-13) → 한 단계 낮춤.
    사장님 화면 순서로는 확실해요 → ○ 쪽이에요 → 아직 몰라요."""
    badge = dict(v["badge"])
    i = _ORDER.index(badge["level"])
    reasons = []
    if small_sample and i > 1:
        i, _ = 1, reasons.append(f"클릭이 적어서 '{badge['better']} 쪽이에요'까지만")
    if spend_gap and i > 0:
        i, _ = i - 1, reasons.append("한쪽에 돈이 몰려서 한 단계 낮췄어요")
    if reasons:
        badge.update(level=_ORDER[i], word=_word_for(_ORDER[i], badge["better"]), capped=reasons)
    return dict(v, badge=badge)
