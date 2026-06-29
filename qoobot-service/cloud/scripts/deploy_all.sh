#!/bin/bash
# ==============================================
# qoocloud — 一键部署脚本
# 启动基础设施 + 构建并运行所有微服务
# ==============================================

set -e

echo "================================================"
echo "  qoocloud — Deploy All"
echo "================================================"

# 1. 启动基础设施
echo ""
echo "--- Step 1: Start infrastructure ---"
docker compose up -d postgres redis nacos kafka minio sentinel
echo "Waiting for infrastructure to be healthy..."
sleep 15

# 2. 构建所有模块
echo ""
echo "--- Step 2: Build all modules ---"
bash scripts/build_all.sh package

# 3. 启动所有微服务
echo ""
echo "--- Step 3: Start all microservices ---"
docker compose up -d --build

# 4. 等待健康检查
echo ""
echo "--- Step 4: Health check ---"
sleep 30
bash scripts/smoke_test.sh

echo ""
echo "✅ qoocloud deployment complete!"
echo ""
echo "Endpoints:"
echo "  Gateway:       http://localhost:8080"
echo "  Inference:     http://localhost:8200"
echo "  Device:        http://localhost:8201"
echo "  OTA:           http://localhost:8202"
echo "  Data:          http://localhost:8203"
echo "  Orchestra:     http://localhost:8204"
echo "  Twin:          http://localhost:8205"
echo "  Observability: http://localhost:8206"
echo "  Infra:         http://localhost:8207"
echo "  Teleop:        http://localhost:8208"
echo "  Nacos:         http://localhost:8848/nacos"
echo "  MinIO:         http://localhost:9001"
