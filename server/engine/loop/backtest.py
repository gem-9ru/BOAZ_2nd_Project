"""백테스트: 앞 날짜로 맞춘 모델이 마지막 날을 80% 범위 안에 맞히는지 (v4 4-1·9장).

광고가 나간 날만 쓴다. 마지막 날 실제 지출로 노출(포아송) → 클릭(이항) → 도착(이항)을 뽑는다.
"""
from typing import Dict

import numpy as np

from . import posterior, summary

RUNS = 20_000


def _band(x: np.ndarray, actual: float) -> Dict:
    lo, hi = int(np.quantile(x, 0.1)), int(np.ceil(np.quantile(x, 0.9)))
    return {"lo": lo, "hi": hi, "median": float(np.median(x)), "actual": int(actual), "inside": bool(lo <= actual <= hi)}


def run(bundle, seed: int = 0) -> Dict:
    daily = bundle.tables["meta_daily"].df
    per_day = daily.groupby("date")["spend"].sum()
    days = sorted(per_day[per_day > 0].index)
    if len(days) < 3:
        return {"ok": False, "note": "광고가 나간 날이 3일보다 적어서 백테스트를 못 해요."}
    train, test = days[:-1], days[-1]
    rng = np.random.default_rng(seed)
    arms = []
    for name, g in daily.groupby("adset"):
        tr = g[g["date"].isin(train)]
        te = g[g["date"] == test]
        fit = summary.arm(str(name), tr["spend"].sum(), tr["impressions"].sum(), tr["link_clicks"].sum(), tr["landing_page_views"].sum())
        d = posterior.draws(fit, n=RUNS, seed=seed)
        budget = float(te["spend"].sum())
        imps = rng.poisson(budget / d["cpm"] * 1000)
        clicks = rng.binomial(imps, d["ctr"])
        visits = rng.binomial(clicks, d["click_to_visit"])
        arms.append({"name": str(name), "budget": budget,
                     "link_clicks": _band(clicks, float(te["link_clicks"].sum())),
                     "visits": _band(visits, float(te["landing_page_views"].sum()))})
    return {"ok": True, "train_days": [str(x.date()) for x in train], "test_day": str(test.date()), "arms": arms,
            "note": "하루치로 1번만 확인한 결과라 표본이 작아요. 기간이 길수록 더 믿을 만해져요."}
