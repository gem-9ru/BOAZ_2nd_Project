"""광고 코치 v3 서버: 크롬 확장이 부르는 HTTP 창구. 계산은 server/engine에 있다."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="광고 코치 v3")
app.add_middleware(CORSMiddleware, allow_origin_regex=r"chrome-extension://.*",
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health() -> dict:
    return {"ok": True}
