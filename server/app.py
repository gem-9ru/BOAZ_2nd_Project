"""광고 코치 v3 서버: 크롬 확장이 부르는 HTTP 창구. 계산은 server/engine에 있다.

- COACH_OFFLINE=1 이면 네이버를 부르지 않고 저장본만 쓴다 (시연장 네트워크 대비).
- COACH_NO_LLM=1 이면 Claude를 부르지 않고 문장 틀로 문구를 만든다.
"""
import datetime
import os
from typing import List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from server.engine import copywriter, market, specs

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


ASKED_KINDS = ("question", "precheck")
SET_KINDS = ("default", "auto", "next_cycle")


class CopiesIn(BaseModel):
    product: str
    strengths: List[str] = []
    keywords: List[str] = []


@app.post("/copies")
def copies(body: CopiesIn) -> dict:
    client = None if os.environ.get("COACH_NO_LLM") == "1" else copywriter.make_client()
    made = copywriter.meta_copies(body.product, list(body.strengths) + list(body.keywords), n=3,
                                  client=client or False)
    return {"copies": [{"primary_text": c["text"], "headline": c["headline"]} for c in made],
            "source": "claude" if client else "template"}


@app.get("/fields")
def fields() -> dict:
    """묻는 칸(질문·사전 점검)과, 묻지 않고 기본값으로 두는 칸(이유 한 줄)."""
    all_meta = specs.fields("meta")["fields"]
    asked = [{"id": f["id"], "kind": f["kind"], "label": f["label"], "ask": f["ask"],
              "options": f.get("options"), "default": f.get("default"), "why": f.get("why", "")}
             for f in all_meta if f.get("kind") in ASKED_KINDS]
    preset = [{"id": f["id"], "label": f["label"], "default": str(f["default"]), "why": f["why"]}
              for f in all_meta if f.get("kind") in SET_KINDS and f.get("default") is not None and f.get("why")]
    return {"fields": asked, "defaults": preset}
