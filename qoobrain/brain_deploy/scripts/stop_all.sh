#!/usr/bin/env bash
# stop_all.sh — 停止本地启动的所有 Brain OS 服务
set -euo pipefail

stop_service() {
  local name="$1"
  local pid_file="$2"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
      echo "  ✅ 已停止 $name (PID=$pid)"
    else
      echo "  ⚠️  $name 已不在运行 (PID=$pid)"
    fi
    rm -f "$pid_file"
  else
    echo "  ⚠️  未找到 $name 的 PID 文件"
  fi
}

echo ">>> 停止 Brain OS 服务..."
stop_service "brain_ai"  "/tmp/brain_ai.pid"
stop_service "brain_viz" "/tmp/brain_viz.pid"
echo "✅ 所有服务已停止"
