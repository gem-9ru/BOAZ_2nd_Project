#!/bin/bash
# 맥미니(hspace-mini, ~/ad-assistant)에 지금 코드를 올리고 서버를 다시 켠다.
# 비밀 파일(.env)은 보내지 않는다 (맥미니에 따로 있음). 분석 페이지를 바꿨으면 먼저 `cd web && npm run build`.
set -euo pipefail
cd "$(dirname "$0")/.."
rsync -a --delete --exclude '.venv/' --exclude 'node_modules/' --exclude '.output/' --exclude '.env' --exclude '.env.*' \
  --exclude '발표자료/' --exclude 'store/*.zip' --exclude '.superpowers/' ./ hspace-mini:ad-assistant/
ssh hspace-mini 'cd ~/ad-assistant && .venv/bin/pip install -q -r server/requirements.txt && launchctl kickstart -k gui/$(id -u)/io.adassistant.server && sleep 4 && curl -s -o /dev/null -w "맥미니 서버 %{http_code}\n" http://127.0.0.1:8001/fields'
