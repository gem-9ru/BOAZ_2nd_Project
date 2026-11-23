# Ad assistant 서버 + 분석 페이지 (Cloud Run)
# 1) 분석 페이지(web/)를 빌드하고 2) FastAPI 서버가 /analysis로 함께 띄운다.
# API 키는 이미지에 넣지 않는다 → Cloud Run의 Secret Manager 환경 변수로 주입.

FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npx vite build

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
COPY server/requirements.txt server/requirements.txt
RUN grep -v '^pytest' server/requirements.txt > /tmp/req.txt && pip install --no-cache-dir -r /tmp/req.txt
COPY server/ server/
COPY --from=web /web/dist web/dist
CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${PORT}"]
