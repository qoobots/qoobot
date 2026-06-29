#!/bin/bash
# ==============================================
# qoocloud — 数据备份脚本
# 备份 PostgreSQL 数据库到 MinIO
# ==============================================

set -e

BACKUP_DIR="${BACKUP_DIR:-/tmp/qoocloud_backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-7}"

DATABASES=(
  "qoocloud_inference"
  "qoocloud_device"
  "qoocloud_ota"
  "qoocloud_data"
  "qoocloud_orchestra"
  "qoocloud_twin"
  "qoocloud_teleop"
)

mkdir -p "$BACKUP_DIR"

echo "================================================"
echo "  qoocloud Database Backup"
echo "  Timestamp: ${TIMESTAMP}"
echo "================================================"

for db in "${DATABASES[@]}"; do
  FILE="${BACKUP_DIR}/${db}_${TIMESTAMP}.sql.gz"
  echo "Backing up: ${db} → ${FILE}"
  PGPASSWORD="${DB_PASSWORD:-qoobot}" pg_dump \
    -h "${DB_HOST:-localhost}" \
    -U "${DB_USERNAME:-qoobot}" \
    -d "$db" \
    --no-owner --no-acl \
    | gzip > "$FILE"
  echo "  ✅ $(du -h "$FILE" | cut -f1)"
done

# 清理旧备份
echo ""
echo "Cleaning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo ""
echo "✅ Backup complete: ${BACKUP_DIR}"
ls -lh "$BACKUP_DIR"/*"${TIMESTAMP}"*.sql.gz
