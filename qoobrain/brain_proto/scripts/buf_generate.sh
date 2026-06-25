#!/usr/bin/env bash
# buf_generate.sh — 生成 Python / C++ gRPC 存根
# 需要安装：buf (>= 1.28), protoc-gen-grpc-python, protoc-gen-grpc-cpp
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROTO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "[buf] 切换到 brain_proto 目录..."
cd "$PROTO_ROOT"

# 创建输出目录
mkdir -p ../brain_ai/brain_ai/proto_gen
mkdir -p ../brain_sdk/brain_os/proto_gen
mkdir -p ../brain_core/src/proto_gen

# 添加 __init__.py（确保 Python 包可导入）
touch ../brain_ai/brain_ai/proto_gen/__init__.py
touch ../brain_sdk/brain_os/proto_gen/__init__.py

echo "[buf] 更新依赖..."
buf dep update

echo "[buf] 生成代码..."
buf generate

echo "[buf] ✅ 代码生成完成"
echo "  → brain_ai/brain_ai/proto_gen/"
echo "  → brain_sdk/brain_os/proto_gen/"
echo "  → brain_core/src/proto_gen/"
