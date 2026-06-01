#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PID_FILE="$APP_DIR/server.pid"
PORT="${PORT:-8000}"
STOPPED=0

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" >/dev/null 2>&1; then
    kill "$PID"
    STOPPED=1
    echo "已停止 start_app.sh 启动的服务：$PID"
  fi
  rm -f "$PID_FILE"
fi

PIDS="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "$PIDS" ]; then
  for PID in $PIDS; do
    CMD="$(ps -p "$PID" -o command= 2>/dev/null || true)"
    case "$CMD" in
      *"$APP_DIR/server.py"*)
        kill "$PID"
        STOPPED=1
        echo "已停止占用端口 $PORT 的旧服务：$PID"
        ;;
    esac
  done
fi

if [ "$STOPPED" -eq 0 ]; then
  echo "未找到正在运行的本应用服务。"
fi
