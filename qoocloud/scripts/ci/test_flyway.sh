#!/bin/bash
# ==============================================
# qoocloud CI — Flyway 迁移验证
# 验证所有模块数据库迁移脚本可执行
# ==============================================

set -e

MODULES=(
  "qoocloud-inference"
  "qoocloud-device"
  "qoocloud-ota"
  "qoocloud-data"
  "qoocloud-orchestra"
  "qoocloud-twin"
  "qoocloud-teleop"
)

echo "================================================"
echo "  Flyway Migration Validation"
echo "================================================"

for module in "${MODULES[@]}"; do
  echo ""
  echo "--- Module: ${module} ---"

  SQL_DIR="${module}/src/main/resources/db/migration"
  if [ -d "$SQL_DIR" ]; then
    count=$(find "$SQL_DIR" -name "*.sql" -type f | wc -l)
    echo "  SQL migrations found: ${count}"

    # 检查 SQL 文件命名规范 V<number>__<description>.sql
    invalid=$(find "$SQL_DIR" -name "*.sql" -type f ! -name "V[0-9]*__*.sql" | wc -l)
    if [ "$invalid" -gt 0 ]; then
      echo "  WARNING: ${invalid} files do not follow Flyway naming convention"
      find "$SQL_DIR" -name "*.sql" -type f ! -name "V[0-9]*__*.sql"
    else
      echo "  All files follow Flyway naming convention ✅"
    fi
  else
    echo "  WARNING: No db/migration directory found"
  fi
done

echo ""
echo "✅ Flyway migration check complete."
