#!/bin/bash
# ==============================================
# qoocloud — 多数据库初始化脚本
# 用于 docker-compose PostgreSQL 首次启动
# ==============================================

set -e

DATABASES=(
  "qoocloud_inference"
  "qoocloud_device"
  "qoocloud_ota"
  "qoocloud_data"
  "qoocloud_orchestra"
  "qoocloud_twin"
  "qoocloud_teleop"
  "qoocloud_test"
)

for db in "${DATABASES[@]}"; do
  echo "Creating database: $db"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE "$db";
    GRANT ALL PRIVILEGES ON DATABASE "$db" TO $POSTGRES_USER;
EOSQL
done

echo "✅ All databases initialized."
