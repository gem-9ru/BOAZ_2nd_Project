"""광고 코치 v3 서버: 크롬 확장이 부르는 HTTP 창구. 계산은 server/engine에 있다.

- COACH_OFFLINE=1 이면 네이버를 부르지 않고 저장본만 쓴다 (시연장 네트워크 대비).
"""
import datetime
import os
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from server.engine import market

MAX_KEYWORDS = 10

app = FastAPI(title="광고 코치 v3")
app.add_middleware(CORSMiddleware, allow_origin_regex=r"chrome-extension://.*",
                   allow_methods=["*"], allow_headers=["*"])


def _online() -> bool:
    return os.environ.get("COACH_OFFLINE") != "1"


@app.get("/health")
def health() -> dict:
    return {"ok": True}


class ResearchIn(BaseModel):
    product: str
    seeds: Optional[List[str]] = None   # 비우면 상품 이름 하나로 찾음


@app.post("/research")
def research(body: ResearchIn) -> dict:
    seeds = [s for s in (body.seeds or [body.product]) if s.strip()]
    report = market.build(seeds, online=_online())
    if report is None:
        return {"headline": "", "keywords": [], "audience": None, "fetched": "", "source": "cache",
                "notice": "네이버에서 이 상품 검색 자료를 찾지 못했어요. 상품을 다른 말로 적어 보세요."}
    kw = report.keywords.set_index("keyword")["total_qc"]
    keywords = [{"keyword": k, "total_qc": int(kw[k])} for k in report.recommended[:MAX_KEYWORDS] if k in kw]
    audience = None
    if report.audiences:
        name, aud = next(iter(report.audiences.items()))
        audience = {"keyword": name, "female": aud["female"], "ages": aud["ages"], "top_age": market.top_age(aud)}
    live = report.fetched == datetime.date.today().isoformat()
    return {"headline": report.headline, "keywords": keywords, "audience": audience, "fetched": report.fetched,
            "source": "live" if live else "cache", "notice": None}
