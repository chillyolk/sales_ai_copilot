#!/bin/sh
set -eu

ACCOUNT="${MINIMAX_KEYCHAIN_ACCOUNT:-sale_mobile_ai_minimax}"
SERVICE="${MINIMAX_KEYCHAIN_SERVICE:-minimax_api_key}"

printf "请输入新的 MiniMax API Key，将保存到 macOS Keychain："
read KEY

if [ -z "$KEY" ]; then
  echo "未输入 Key，已退出。"
  exit 1
fi

security add-generic-password -U -a "$ACCOUNT" -s "$SERVICE" -w "$KEY"
echo "已保存到 Keychain。之后可直接运行 ./start_app.sh。"
