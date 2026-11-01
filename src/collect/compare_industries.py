"""시연 업종 후보를 네이버 키워드 도구 데이터로 비교한다.

실행: python src/collect/compare_industries.py [beauty]
결과: data/interim/industry_compare.csv (beauty 인자를 주면 industry_compare_beauty.csv)
"""
import sys
import time
from pathlib import Path

import pandas as pd

from naver_api_test import call

ROOT = Path(__file__).resolve().parents[2]

CANDIDATES = {
    "반려동물 사료·간식": ["강아지사료", "고양이사료", "강아지간식"],
    "원두커피": ["원두커피", "커피원두", "드립백"],
    "건강기능식품": ["유산균", "종합비타민", "오메가3"],
    "스킨케어": ["수분크림", "선크림", "토너패드"],
    "캠핑용품": ["캠핑용품", "캠핑의자", "텐트"],
    "필라테스복·요가복": ["필라테스복", "요가복", "레깅스"],
}

BEAUTY = {
    "기초 스킨케어": ["토너패드", "수분크림", "앰플"],
    "선케어": ["선크림", "선스틱", "톤업크림"],
    "클렌징": ["클렌징오일", "클렌징폼", "클렌징밤"],
    "색조 (베이스·립)": ["쿠션팩트", "립틴트", "파운데이션"],
    "마스크팩": ["마스크팩", "시트마스크", "모델링팩"],
    "헤어·바디": ["탈모샴푸", "바디로션", "헤어에센스"],
    "올리브영 연관": ["올리브영추천", "올리브영세일", "올리브영"],
}

if len(sys.argv) > 1 and sys.argv[1] == "beauty":
    CANDIDATES, OUT_NAME = BEAUTY, "industry_compare_beauty.csv"
else:
    OUT_NAME = "industry_compare.csv"


def to_num(v):
    if isinstance(v, str):
        v = v.replace("<", "").replace(",", "").strip()
        return float(v) if v else 0.0
    return float(v)


rows = []
for industry, hints in CANDIDATES.items():
    res = call("GET", "/keywordstool", params={"hintKeywords": ",".join(hints), "showDetail": 1})
    df = pd.DataFrame(res["keywordList"])
    for c in ["monthlyPcQcCnt", "monthlyMobileQcCnt", "monthlyAveMobileClkCnt", "monthlyAveMobileCtr"]:
        df[c] = df[c].map(to_num)
    df["qc"] = df.monthlyPcQcCnt + df.monthlyMobileQcCnt
    seeds = df[df.relKeyword.isin(hints)]
    mid = df[df.qc.between(1000, 30000)]
    rows.append({
        "industry": industry,
        "seed_search_total": int(seeds.qc.sum()),
        "related_keywords": len(df),
        "related_qc_ge_1000": int((df.qc >= 1000).sum()),
        "mid_tail_low_mid_comp": int(mid.compIdx.isin(["낮음", "중간"]).sum()),
        "share_high_comp": round((df.compIdx == "높음").mean(), 2),
        "median_mobile_ctr": round(df.loc[df.qc >= 1000, "monthlyAveMobileCtr"].median(), 2),
    })
    time.sleep(1)

out = pd.DataFrame(rows)
(ROOT / "data/interim").mkdir(parents=True, exist_ok=True)
out.to_csv(ROOT / "data/interim" / OUT_NAME, index=False)
print(out.to_string(index=False))
