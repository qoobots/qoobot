#!/bin/bash
# ==============================================
# qoocloud — 全模块构建脚本
# 按依赖顺序编译所有 Maven 模块
# ==============================================

set -e

MODULES_ORDERED=(
  "qoocloud-common"
  "qoocloud-gateway"
  "qoocloud-inference"
  "qoocloud-device"
  "qoocloud-ota"
  "qoocloud-data"
  "qoocloud-orchestra"
  "qoocloud-twin"
  "qoocloud-observability"
  "qoocloud-infra"
  "qoocloud-teleop"
)

BUILD_MODE="${1:-compile}"  # compile | package | test

echo "================================================"
echo "  qoocloud — Build All Modules"
echo "  Mode: ${BUILD_MODE}"
echo "================================================"

case "$BUILD_MODE" in
  compile)
    GOAL="compile"
    ;;
  package)
    GOAL="package -DskipTests"
    ;;
  test)
    GOAL="test"
    ;;
  *)
    echo "Usage: $0 [compile|package|test]"
    exit 1
    ;;
esac

for module in "${MODULES_ORDERED[@]}"; do
  echo ""
  echo "--- Building: ${module} ---"
  mvn $GOAL -pl "${module}" -am -B
  echo "  ${module} ✅"
done

echo ""
echo "================================================"
echo "  All modules: ${BUILD_MODE} completed ✅"
echo "================================================"
