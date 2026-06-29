#!/bin/bash
# ==============================================
# qoocloud CI — 冒烟测试 (精简版)
# 仅验证 Gateway 和基础设施健康
# ==============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass=0
fail=0

check() {
  local name="$1"
  local url="$2"
  echo -n "  [$name] "
  if curl -sf --max-time 10 "$url" > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
    ((pass++))
  else
    echo -e "${RED}FAIL${NC}"
    ((fail++))
  fi
}

echo "================================================"
echo "  qoocloud CI Smoke Tests"
echo "================================================"

echo ""
echo "--- Infrastructure ---"
check "PostgreSQL" "http://localhost:5432" || true
check "Redis     " "http://localhost:6379" || true
check "Nacos     " "http://localhost:8848/nacos/v1/console/health/readiness"
check "MinIO     " "http://localhost:9000/minio/health/live"

echo ""
echo "--- Gateway ---"
check "Gateway   " "http://localhost:8080/actuator/health"

# Gateway API 基础连通性测试
if curl -sf --max-time 5 http://localhost:8080/actuator/health > /tmp/health.json 2>&1; then
  echo "  [Gateway API] $(cat /tmp/health.json)"
  ((pass++))
else
  echo -e "  [Gateway API] ${RED}FAIL${NC}"
  ((fail++))
fi

echo ""
echo "================================================"
echo -e "  Results: ${GREEN}${pass} passed${NC} / ${RED}${fail} failed${NC}"
echo "================================================"

if [ $fail -gt 0 ]; then
  exit 1
fi
