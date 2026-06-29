#!/bin/bash
# ============================================================
# qooauth PostgreSQL Database Initialization Script
# ============================================================
# Creates the qooauth database and user if they don't exist.
# Requires: psql client, PostgreSQL server running
#
# Usage: ./init-db.sh [options]
#   -h, --host      PostgreSQL host (default: localhost)
#   -p, --port      PostgreSQL port (default: 5432)
#   -U, --user      PostgreSQL admin user (default: postgres)
#   -d, --database  Database name (default: qooauth)
#   --help          Show this help message
# ============================================================

set -euo pipefail

# Default values
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_ADMIN_USER="${PG_ADMIN_USER:-postgres}"
DB_NAME="${DB_NAME:-qooauth}"
DB_USER="${DB_USER:-qooauth}"
DB_PASSWORD="${DB_PASSWORD:-qooauth}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            PG_HOST="$2"
            shift 2
            ;;
        -p|--port)
            PG_PORT="$2"
            shift 2
            ;;
        -U|--user)
            PG_ADMIN_USER="$2"
            shift 2
            ;;
        -d|--database)
            DB_NAME="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "  -h, --host      PostgreSQL host (default: localhost)"
            echo "  -p, --port      PostgreSQL port (default: 5432)"
            echo "  -U, --user      PostgreSQL admin user (default: postgres)"
            echo "  -d, --database  Database name (default: qooauth)"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

export PGPASSWORD="${PGPASSWORD:-}"

echo "============================================"
echo "  qooauth Database Initialization"
echo "============================================"
echo "Host:     ${PG_HOST}:${PG_PORT}"
echo "Database: ${DB_NAME}"
echo "User:     ${DB_USER}"
echo "============================================"

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql client not found. Please install PostgreSQL client."
    exit 1
fi

# Test connection to PostgreSQL
echo ""
echo "[1/4] Testing connection to PostgreSQL..."
if ! psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d postgres -c "SELECT 1;" &> /dev/null; then
    echo "ERROR: Cannot connect to PostgreSQL at ${PG_HOST}:${PG_PORT} as ${PG_ADMIN_USER}"
    echo "       Please check that PostgreSQL is running and accessible."
    exit 1
fi
echo "  -> Connection successful."

# Create user if not exists
echo ""
echo "[2/4] Creating database user '${DB_USER}'..."
USER_EXISTS=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d postgres -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}';" 2>/dev/null || echo "0")

if [ "${USER_EXISTS}" = "1" ]; then
    echo "  -> User '${DB_USER}' already exists."
else
    psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d postgres -c \
        "CREATE USER \"${DB_USER}\" WITH PASSWORD '${DB_PASSWORD}';" > /dev/null
    echo "  -> User '${DB_USER}' created."
fi

# Create database if not exists
echo ""
echo "[3/4] Creating database '${DB_NAME}'..."
DB_EXISTS=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}';" 2>/dev/null || echo "0")

if [ "${DB_EXISTS}" = "1" ]; then
    echo "  -> Database '${DB_NAME}' already exists."
else
    psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d postgres -c \
        "CREATE DATABASE \"${DB_NAME}\" OWNER \"${DB_USER}\" ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE template0;" > /dev/null
    echo "  -> Database '${DB_NAME}' created."
fi

# Grant privileges
echo ""
echo "[4/4] Granting privileges..."
psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d "${DB_NAME}" -c \
    "GRANT ALL PRIVILEGES ON DATABASE \"${DB_NAME}\" TO \"${DB_USER}\";" > /dev/null
psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d "${DB_NAME}" -c \
    "GRANT ALL ON SCHEMA public TO \"${DB_USER}\";" > /dev/null
echo "  -> Privileges granted to '${DB_USER}'."

# Enable extensions
echo ""
echo "Enabling extensions..."
psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d "${DB_NAME}" -c \
    "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" > /dev/null 2>&1 || true
psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_ADMIN_USER}" -d "${DB_NAME}" -c \
    "CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";" > /dev/null 2>&1 || true

echo ""
echo "============================================"
echo "  Database initialization complete!"
echo "  Database: ${DB_NAME}"
echo "  User:     ${DB_USER}"
echo "  Host:     ${PG_HOST}:${PG_PORT}"
echo "============================================"

unset PGPASSWORD
