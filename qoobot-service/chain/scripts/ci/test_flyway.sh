#!/usr/bin/env bash
# ============================================================
# QooChain CI — 数据库迁移验证
# 验证 Flyway 迁移脚本完整性
# ============================================================

set -euo pipefail

SQL_DIR="qoochain-cloud/sql"
PASS=0
FAIL=0

log_pass() { echo "  ✅ $1"; PASS=$((PASS + 1)); }
log_fail() { echo "  ❌ $1"; FAIL=$((FAIL + 1)); }

echo "=== QooChain Flyway Migration Verification ==="

# 1. Check V1__init_schema.sql exists and non-empty
echo "[1/4] V1__init_schema.sql"
V1_SIZE=$(wc -c < "$SQL_DIR/V1__init_schema.sql" 2>/dev/null || echo "0")
if [ "$V1_SIZE" -gt 1000 ]; then
    log_pass "V1__init_schema.sql: $V1_SIZE bytes"
else
    log_fail "V1__init_schema.sql: too small or missing ($V1_SIZE bytes)"
fi

# 2. Check for SQL syntax markers
echo "[2/4] Table definitions"
TABLE_COUNT=$(grep -c "CREATE TABLE" "$SQL_DIR/V1__init_schema.sql" 2>/dev/null || echo "0")
if [ "$TABLE_COUNT" -ge 15 ]; then
    log_pass "Found $TABLE_COUNT CREATE TABLE statements (expected >=15)"
else
    log_fail "Only $TABLE_COUNT CREATE TABLE statements (expected >=15)"
fi

# 3. Check seed data files
echo "[3/4] Seed data files"
SEED_FILES=$(ls "$SQL_DIR"/V[2-9]*.sql 2>/dev/null | wc -l || echo "0")
if [ "$SEED_FILES" -ge 1 ]; then
    log_pass "Found $SEED_FILES seed data migration files"
else
    log_fail "No seed data migration files found (V2+)"
fi

# 4. Check migration naming convention
echo "[4/4] Naming convention"
INVALID=$(ls "$SQL_DIR"/*.sql 2>/dev/null | grep -vP '^.*/V\d+__[a-z_]+\.sql$' | wc -l || echo "0")
if [ "$INVALID" -eq 0 ]; then
    log_pass "All SQL files follow Flyway naming convention"
else
    log_fail "$INVALID files with invalid naming convention"
fi

echo "=== Flyway: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
