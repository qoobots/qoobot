#!/bin/bash
# ============================================================
# CI Smoke Test — 验证所有容器健康状态
# Usage: bash scripts/ci/smoke_test.sh
# ============================================================
set -euo pipefail

echo "=== Smoke Test: Checking service health ==="

TIMEOUT=120
ELAPSED=0
INTERVAL=5

# Wait for brain_ai gRPC endpoint
echo "Waiting for brain_ai gRPC server..."
while ! grpcurl -plaintext localhost:50051 list >/dev/null 2>&1; do
  sleep $INTERVAL
  ELAPSED=$((ELAPSED + INTERVAL))
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "ERROR: brain_ai gRPC not healthy after ${TIMEOUT}s"
    exit 1
  fi
done

# Wait for brain_viz HTTP endpoint
echo "Waiting for brain_viz HTTP server..."
ELAPSED=0
while ! curl -sf http://localhost:3000/api/health >/dev/null 2>&1; do
  sleep $INTERVAL
  ELAPSED=$((ELAPSED + INTERVAL))
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "ERROR: brain_viz not healthy after ${TIMEOUT}s"
    exit 1
  fi
done

echo "=== Smoke Test: All services healthy ==="
