#!/usr/bin/env bash
# Ad assistant를 이 맥에서 띄우고 Cloudflare Tunnel로 https://boaz-ad-assistant.gem-9ru.com 에 공개한다.
#   시작: scripts/serve_public.sh        멈춤: scripts/serve_public.sh stop
# 이 맥과 이 스크립트가 켜져 있을 때만 접속된다. 로그: logs/server.log, logs/tunnel.log
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
if [ "${1:-}" = "stop" ]; then
  pkill -f "uvicorn server.app:app" && echo "서버를 껐어요" || echo "서버는 이미 꺼져 있어요"
  pkill -f "cloudflared tunnel --config $HOME/.cloudflared/ad-assistant.yml" && echo "터널을 껐어요" || echo "터널은 이미 꺼져 있어요"
  exit 0
fi
# 분석 페이지가 빌드돼 있어야 /analysis가 뜬다
[ -f web/dist/index.html ] || (cd web && mise exec node@22 -- npx vite build)
if ! pgrep -f "uvicorn server.app:app" >/dev/null; then
  nohup .venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 >> logs/server.log 2>&1 &
  echo "서버를 켰어요 (127.0.0.1:8000)"
else
  echo "서버는 이미 켜져 있어요 (127.0.0.1:8000)"
fi
if ! pgrep -f "cloudflared tunnel --config $HOME/.cloudflared/ad-assistant.yml" >/dev/null; then
  nohup cloudflared tunnel --config "$HOME/.cloudflared/ad-assistant.yml" run ad-assistant >> logs/tunnel.log 2>&1 &
  echo "터널을 켰어요 → https://boaz-ad-assistant.gem-9ru.com"
else
  echo "터널은 이미 켜져 있어요 → https://boaz-ad-assistant.gem-9ru.com"
fi
# 공개 주소로 실제 접속되는지 한 번 확인 (터널이 막 켜졌으면 몇 초 걸릴 수 있음)
for i in 1 2 3 4 5; do
  code="$(curl -s -o /dev/null -w '%{http_code}' https://boaz-ad-assistant.gem-9ru.com/health || true)"
  [ "$code" = "200" ] && { echo "접속 확인: https://boaz-ad-assistant.gem-9ru.com/analysis"; exit 0; }
  sleep 2
done
echo "아직 공개 주소로 접속되지 않아요 (응답 $code). logs/server.log, logs/tunnel.log를 확인해 주세요." >&2
exit 1
