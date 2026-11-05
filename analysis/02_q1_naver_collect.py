"""Q1 수집: 업종 4개에서 검색량 상위(대표) / 롱테일(세부) 키워드를 뽑아 입찰가별 예상 실적을 받는다.

실행: python analysis/02_q1_naver_collect.py
결과: analysis/out/naver_q1/keywords.csv, estimates.csv (원본 JSON은 같은 폴더)
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/collect"))
from naver_api_test import call  # noqa: E402

OUT = ROOT / "analysis/out/naver_q1"
OUT.mkdir(parents=True, exist_ok=True)

SEEDS = {"원두커피": "커피", "필라테스": "운동", "수분크림": "화장품", "강아지사료": "반려동물"}
HEAD_MIN, TAIL_RANGE = 10_000, (300, 3_000)
N_HEAD, N_TAIL = 6, 10
BIDS = [70, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600, 1800,
        2000, 2300, 2600, 3000, 3500, 4000, 5000, 6000, 8000, 10000]


def num(v):
    return 5.0 if isinstance(v, str) and "<" in v else float(v)


kw_rows, est_rows = [], []
for seed, industry in SEEDS.items():
    res = call("GET", "/keywordstool", params={"hintKeywords": seed, "showDetail": 1})
    (OUT / f"keywordstool_{seed}.json").write_text(json.dumps(res, ensure_ascii=False))
    kw = pd.DataFrame(res["keywordList"])
    for c in ["monthlyPcQcCnt", "monthlyMobileQcCnt", "monthlyAveMobileClkCnt", "monthlyAveMobileCtr"]:
        kw[c] = kw[c].map(num)
    kw["qc"] = kw.monthlyPcQcCnt + kw.monthlyMobileQcCnt
    head = kw[kw.qc >= HEAD_MIN].nlargest(N_HEAD, "qc").assign(tier="대표")
    tail_pool = kw[kw.qc.between(*TAIL_RANGE)]
    tail = tail_pool.sample(min(N_TAIL, len(tail_pool)), random_state=42).assign(tier="세부")
    picked = pd.concat([head, tail]).assign(seed=seed, industry=industry)
    kw_rows.append(kw.assign(seed=seed, industry=industry))
    time.sleep(1)
    for _, r in picked.iterrows():
        est = call("POST", "/estimate/performance/keyword",
                   body={"device": "MOBILE", "keywordplus": True, "key": r.relKeyword, "bids": BIDS})
        if isinstance(est, dict) and "estimate" in est:
            for e in est["estimate"]:
                est_rows.append({**e, "keyword": r.relKeyword, "tier": r.tier, "seed": seed,
                                 "industry": industry, "qc": r.qc, "compIdx": r.compIdx})
        time.sleep(0.8)

pd.concat(kw_rows).to_csv(OUT / "keywords.csv", index=False)
pd.DataFrame(est_rows).to_csv(OUT / "estimates.csv", index=False)
print("keywords:", sum(len(k) for k in kw_rows), "estimate rows:", len(est_rows))
