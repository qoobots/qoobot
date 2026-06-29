#!/bin/bash
# ==============================================
# qoocloud — 冒烟测试
# 验证基础设施和微服务健康状态
# ==============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass_count=0
fail_count=0

check() {
  local name="$1"
  local url="$2"
  echo -n "  [$name] "
  if curl -sf --max-time 10 "$url" > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
    ((pass_count++))
  else
    echo -e "${RED}FAIL${NC}"
    ((fail_count++))
  fi
}

echo "================================================"
echo "  qoocloud Smoke Tests"
echo "================================================"

echo ""
echo "--- Infrastructure ---"
check "PostgreSQL  " "http://localhost:5432" || true  # pg_isready via docker
check "Redis       " "http://localhost:6379" || true  # redis-cli ping via docker
check "Nacos       " "http://localhost:8848/nacos/v1/console/health/readiness"
check "Kafka       " "http://localhost:9092" || true
check "MinIO       " "http://localhost:9000/minio/health/live"

echo ""
echo "--- Microservices ---"
check "Gateway     " "http://localhost:8080/actuator/health"
check "Inference   " "http://localhost:8200/actuator/health"
check "Device      " "http://localhost:8201/actuator/health"
check "OTA         " "http://localhost:8202/actuator/health"
check "Data Sync   " "http://localhost:8203/actuator/health"
check "Orchestra   " "http://localhost:8204/actuator/health"
check "Twin        " "http://localhost:8205/actuator/health"
check "Observability" "http://localhost:8206/actuator/health"
check "Infra       " "http://localhost:8207/actuator/health"
check "Teleop      " "http://localhost:8208/actuator/health"

echo ""
echo "================================================"
echo -e "  Results: ${GREEN}${pass_count} passed${NC} / ${RED}${fail_count} failed${NC}"
echo "================================================"

if [ $fail_count -gt 0 ]; then
  exit 1
fi
