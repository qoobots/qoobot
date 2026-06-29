#!/usr/bin/env bash
# ============================================================
# QooChain CI — BOM 成本核算 API 冒烟测试
# 前置: 微服务集群已启动
# ============================================================

set -euo pipefail

BOM_URL="${GATEWAY_URL:-http://localhost:8080}/api/bom"
PASS=0
FAIL=0

log_pass() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
log_fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

echo "=== QooChain BOM API Smoke Test ==="

# 1. Create BOM
echo "[1/3] Create BOM"
BOM_RESP=$(curl -sf -X POST "$BOM_URL/boms" \
    -H "Content-Type: application/json" \
    -d '{"name":"TEST-BOM-001","version":"1.0","type":"EBOM","productName":"QooBot Test"}')
BOM_ID=$(echo "$BOM_RESP" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
if [ -n "$BOM_ID" ]; then
    log_pass "BOM created (id=$BOM_ID)"
else
    log_fail "Failed to create BOM"
fi

# 2. Get BOM
echo "[2/3] Get BOM"
if curl -sf "$BOM_URL/boms/$BOM_ID" > /dev/null; then
    log_pass "BOM retrieved"
else
    log_fail "Failed to retrieve BOM"
fi

# 3. List BOMs
echo "[3/3] List BOMs"
COUNT=$(curl -sf "$BOM_URL/boms" | grep -c '"id"' || echo "0")
if [ "$COUNT" -ge 1 ]; then
    log_pass "BOM list has $COUNT entries"
else
    log_fail "BOM list empty"
fi

echo "=== BOM: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
