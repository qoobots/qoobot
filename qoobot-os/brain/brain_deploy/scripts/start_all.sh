#!/usr/bin/env bash
# start_all.sh — 本地（非 Docker）启动所有服务
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo ">>> 启动 Brain OS 所有服务..."

# 1. 启动 brain_ai
echo "[1/2] 启动 brain_ai gRPC 服务..."
cd "$ROOT"
nohup python -m brain_ai.server --host 0.0.0.0 --port 50051 \
  > /tmp/brain_ai.log 2>&1 &
echo $! > /tmp/brain_ai.pid
echo "  ✅ brain_ai PID=$(cat /tmp/brain_ai.pid) → localhost:50051"

# 等待 brain_ai 就绪
sleep 2

# 2. 启动 brain_viz
echo "[2/2] 启动 brain_viz 开发服务器..."
cd "$ROOT/brain_viz"
nohup npm run dev > /tmp/brain_viz.log 2>&1 &
echo $! > /tmp/brain_viz.pid
echo "  ✅ brain_viz PID=$(cat /tmp/brain_viz.pid) → http://localhost:3000"

echo ""
echo "✅ 所有服务已启动"
echo "   日志：tail -f /tmp/brain_ai.log /tmp/brain_viz.log"
echo "   停止：bash brain_deploy/scripts/stop_all.sh"
