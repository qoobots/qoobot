#!/usr/bin/env bash
# setup_dev.sh — 一键初始化本地开发环境
# 用法：bash brain_deploy/scripts/setup_dev.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo ">>> Brain OS 开发环境初始化 (root: $ROOT)"

# 1. 检查 Python
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
if [[ "$(echo "$PYTHON_VERSION < 3.11" | bc)" == "1" ]]; then
  echo "❌ 需要 Python >= 3.11，当前 $PYTHON_VERSION"
  exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# 2. 安装 Python 依赖
echo ">>> 安装根级 Python 依赖..."
cd "$ROOT" && pip install -e ".[dev]" -q

echo ">>> 安装 brain_sdk 依赖..."
cd "$ROOT/brain_sdk" && pip install -e ".[dev]" -q

# 3. 检查 Node.js
NODE_VERSION=$(node --version 2>&1 | grep -oP '\d+' | head -1)
if [[ "$NODE_VERSION" -lt 20 ]]; then
  echo "❌ 需要 Node.js >= 20，当前 $NODE_VERSION"
  exit 1
fi
echo "✅ Node.js $NODE_VERSION"

# 4. 安装前端依赖
echo ">>> 安装 brain_viz 依赖..."
cd "$ROOT/brain_viz" && npm install -q

# 5. 生成 Protobuf 存根（若 buf 已安装）
if command -v buf &>/dev/null; then
  echo ">>> 生成 Protobuf 存根..."
  cd "$ROOT" && bash brain_proto/scripts/buf_generate.sh
else
  echo "⚠️  未找到 buf，跳过 Protobuf 生成（安装：https://buf.build/docs/installation）"
fi

echo ""
echo "✅ 开发环境初始化完成！"
echo ""
echo "常用命令："
echo "  make dev-ai    # 启动 brain_ai gRPC 服务器"
echo "  make dev-viz   # 启动 brain_viz 开发服务器"
echo "  make docker-up # 一键启动所有容器"
echo "  make test      # 运行全部测试"
