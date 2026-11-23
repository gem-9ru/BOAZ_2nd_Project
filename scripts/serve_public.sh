#!/usr/bin/env bash
# Ad assistant를 이 맥에서 띄우고 Cloudflare Tunnel로 https://boaz-ad-assistant.gem-9ru.com 에 공개한다.
#   시작: scripts/serve_public.sh        멈춤: scripts/serve_public.sh stop
# 이 맥과 이 스크립트가 켜져 있을 때만 접속된다. 로그: logs/server.log, logs/tunnel.log
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
TUNNEL_CFG="$HOME/.cloudflared/ad-assistant.yml"
# 이 프로젝트 서버 = 8000번 포트를 듣고 있는 'server.app:app' 프로세스 (다른 폴더·포트의 uvicorn은 건드리지 않음)
server_pid() {
  for pid in $(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null); do
    ps -o command= -p "$pid" | grep -q "server.app:app" && echo "$pid"
  done
}
tunnel_pid() { pgrep -f "cloudflared tunnel --config $TUNNEL_CFG" || true; }

if [ "${1:-}" = "stop" ]; then
  p="$(server_pid)"; [ -n "$p" ] && kill $p && echo "서버를 껐어요" || echo "서버는 이미 꺼져 있어요"
  p="$(tunnel_pid)"; [ -n "$p" ] && kill $p && echo "터널을 껐어요" || echo "터널은 이미 꺼져 있어요"
  exit 0
fi
# 분석 페이지가 빌드돼 있어야 /analysis가 뜬다
[ -f web/dist/index.html ] || (cd web && mise exec node@22 -- npx vite build)
if [ -z "$(server_pid)" ]; then
  nohup .venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 >> logs/server.log 2>&1 &
  echo "서버를 켰어요 (127.0.0.1:8000)"
else
  echo "서버는 이미 켜져 있어요 (127.0.0.1:8000)"
fi
if [ -z "$(tunnel_pid)" ]; then
  nohup cloudflared tunnel --config "$TUNNEL_CFG" run ad-assistant >> logs/tunnel.log 2>&1 &
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
