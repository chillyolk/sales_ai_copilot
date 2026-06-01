#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
ENV_FILE="$APP_DIR/.env.local"

if [ -f "$ENV_FILE" ]; then
  . "$ENV_FILE"
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
MINIMAX_API_URL="${MINIMAX_API_URL:-https://api.minimaxi.com/v1/chat/completions}"
MINIMAX_MODEL="${MINIMAX_MODEL:-MiniMax-M2}"
LOG_FILE="$APP_DIR/server.log"
PID_FILE="$APP_DIR/server.pid"
KEYCHAIN_ACCOUNT="${MINIMAX_KEYCHAIN_ACCOUNT:-sale_mobile_ai_minimax}"
KEYCHAIN_SERVICE="${MINIMAX_KEYCHAIN_SERVICE:-minimax_api_key}"

if [ -z "${MINIMAX_API_KEY:-}" ]; then
  MINIMAX_API_KEY="$(security find-generic-password -a "$KEYCHAIN_ACCOUNT" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null || true)"
fi

if [ -z "${MINIMAX_API_KEY:-}" ] && [ -t 0 ]; then
  printf "请输入 MiniMax API Key："
  read MINIMAX_API_KEY
fi

if [ -z "${MINIMAX_API_KEY:-}" ] || [ "$MINIMAX_API_KEY" = "你的 MiniMax API Key" ]; then
  echo "未找到有效的 MiniMax API Key。请先运行：$APP_DIR/save_minimax_key.sh"
  echo "或临时运行：MINIMAX_API_KEY=你的Key $APP_DIR/start_app.sh"
  exit 1
fi

if python3 - <<PY >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://$HOST:$PORT/api/health', timeout=2).read()
PY
then
  echo "服务已在运行：http://$HOST:$PORT"
  echo "如需使用新的 .env.local，请先运行：$APP_DIR/stop_app.sh"
  open "http://$HOST:$PORT" >/dev/null 2>&1 || true
  exit 0
fi

cd "$APP_DIR"
MINIMAX_API_KEY="$MINIMAX_API_KEY" \
MINIMAX_API_URL="$MINIMAX_API_URL" \
MINIMAX_MODEL="$MINIMAX_MODEL" \
HOST="$HOST" \
PORT="$PORT" \
python3 "$APP_DIR/server.py" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

sleep 1

if python3 - <<PY >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://$HOST:$PORT/api/health', timeout=5).read()
PY
then
  echo "启动成功：http://$HOST:$PORT"
  echo "日志文件：$LOG_FILE"
  open "http://$HOST:$PORT" >/dev/null 2>&1 || true
else
  echo "启动失败，请查看日志：$LOG_FILE"
  exit 1
fi
