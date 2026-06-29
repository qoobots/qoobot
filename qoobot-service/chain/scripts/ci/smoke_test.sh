#!/usr/bin/env bash
# ============================================================
# QooChain CI — 微服务健康检查冒烟测试
# 前置: docker-compose.ci.yml 已启动
# ============================================================

set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
TIMEOUT=5
PASS=0
FAIL=0

log_pass() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
log_fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

echo "========================================="
echo " QooChain Smoke Test Suite"
echo " Gateway: $GATEWAY_URL"
echo "========================================="
echo ""

# --- Gateway ---
echo "[1/9] Gateway Health"
if curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/actuator/health" > /dev/null; then
    log_pass "Gateway reachable"
else
    log_fail "Gateway not reachable"
fi

# --- BOM Service ---
echo "[2/9] BOM Service"
if curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/api/bom/health" > /dev/null 2>&1; then
    log_pass "BOM service healthy"
else
    log_fail "BOM service not healthy"
fi

# --- Line Service ---
echo "[3/9] Line Service"
if curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/api/line/health" > /dev/null 2>&1; then
    log_pass "Line service healthy"
else
    log_fail "Line service not healthy"
fi

# --- Calibration Service ---
echo "[4/9] Calibration Service"
if curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/api/calibration/health" > /dev/null 2>&1; then
    log_pass "Calibration service healthy"
else
    log_fail "Calibration service not healthy"
fi

# --- Quality Service ---
echo "[5/9] Quality Service"
if curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/api/quality/health" > /dev/null 2>&1; then
    log_pass "Quality service healthy"
else
    log_fail "Quality service not healthy"
fi

# --- Trace Service ---
echo "[6/9] Trace Service"
if curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/api/trace/health" > /dev/null 2>&1; then
    log_pass "Trace service healthy"
else
    log_fail "Trace service not healthy"
fi

# --- Logistics Service ---
echo "[7/9] Logistics Service"
if curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/api/logistics/health" > /dev/null 2>&1; then
    log_pass "Logistics service healthy"
else
    log_fail "Logistics service not healthy"
fi

# --- Aftermarket Service ---
echo "[8/9] Aftermarket Service"
if curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/api/aftermarket/health" > /dev/null 2>&1; then
    log_pass "Aftermarket service healthy"
else
    log_fail "Aftermarket service not healthy"
fi

# --- Gateway Routes ---
echo "[9/9] Gateway Routes"
ROUTES_COUNT=$(curl -sf --max-time "$TIMEOUT" "$GATEWAY_URL/actuator/gateway/routes" 2>/dev/null | grep -c '"route_id"' || echo "0")
if [ "$ROUTES_COUNT" -ge 7 ]; then
    log_pass "Gateway has $ROUTES_COUNT routes (expected >= 7)"
else
    log_fail "Gateway routes: $ROUTES_COUNT (expected >= 7)"
fi

echo ""
echo "========================================="
echo " Results: $PASS passed, $FAIL failed"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
