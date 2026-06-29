#!/bin/bash
# ============================================================
# qooauth Flyway Migration Runner
# ============================================================
# Runs Flyway database migrations for all qooauth modules.
# Requires: Flyway CLI or Maven/Gradle wrapper
#
# Usage: ./migrate.sh [options]
#   -e, --env       Environment (dev/staging/prod, default: dev)
#   -m, --module    Specific module to migrate (default: all)
#   -c, --clean     Clean database before migration (DANGER!)
#   -r, --repair    Repair Flyway schema history table
#   --help          Show this help message
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QOOAUTH_DIR="$(dirname "${SCRIPT_DIR}")"

# Default values
ENV="${ENV:-dev}"
MODULE="${MODULE:-all}"
CLEAN=false
REPAIR=false

# Module list
MODULES=(
    "qooauth-auth"
    "qooauth-user"
    "qooauth-device"
    "qooauth-api-key"
    "qooauth-security"
    "qooauth-robot-trust"
    "qooauth-developer"
    "qooauth-gateway"
)

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -m|--module)
            MODULE="$2"
            shift 2
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -r|--repair)
            REPAIR=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "  -e, --env     Environment (dev/staging/prod, default: dev)"
            echo "  -m, --module  Specific module to migrate (default: all)"
            echo "  -c, --clean   Clean database before migration (DANGER!)"
            echo "  -r, --repair  Repair Flyway schema history table"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "============================================"
echo "  qooauth Flyway Migration Runner"
echo "============================================"
echo "Environment: ${ENV}"
echo "Module:      ${MODULE}"
echo "Clean:       ${CLEAN}"
echo "Repair:      ${REPAIR}"
echo "============================================"

# Load environment-specific config
CONFIG_FILE="${QOOAUTH_DIR}/.env.${ENV}"
if [ -f "${CONFIG_FILE}" ]; then
    echo "Loading environment config from ${CONFIG_FILE}"
    set -a
    source "${CONFIG_FILE}"
    set +a
else
    echo "WARNING: No .env.${ENV} file found, using defaults"
    export DB_HOST="${DB_HOST:-localhost}"
    export DB_PORT="${DB_PORT:-5432}"
    export DB_NAME="${DB_NAME:-qooauth}"
    export DB_USER="${DB_USER:-qooauth}"
    export DB_PASSWORD="${DB_PASSWORD:-qooauth}"
fi

# Construct JDBC URL
JDBC_URL="jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}"

# Determine which modules to migrate
if [ "${MODULE}" = "all" ]; then
    TARGET_MODULES=("${MODULES[@]}")
else
    TARGET_MODULES=("${MODULE}")
fi

# Function to run flyway for a module
run_flyway() {
    local module_name="$1"
    local module_dir="${QOOAUTH_DIR}/${module_name}"

    if [ ! -d "${module_dir}" ]; then
        echo "  SKIP: Module directory not found: ${module_dir}"
        return 1
    fi

    local migration_dir="${module_dir}/src/main/resources/db/migration"
    if [ ! -d "${migration_dir}" ]; then
        echo "  SKIP: No migration directory for ${module_name}"
        return 0
    fi

    echo ""
    echo "--- Migrating: ${module_name} ---"

    local flyway_cmd="flyway"
    flyway_cmd="${flyway_cmd} -url=${JDBC_URL}"
    flyway_cmd="${flyway_cmd} -user=${DB_USER}"
    flyway_cmd="${flyway_cmd} -password=${DB_PASSWORD}"
    flyway_cmd="${flyway_cmd} -locations=filesystem:${migration_dir}"
    flyway_cmd="${flyway_cmd} -table=${module_name//-/_}_schema_history"
    flyway_cmd="${flyway_cmd} -baselineOnMigrate=true"
    flyway_cmd="${flyway_cmd} -validateOnMigrate=true"
    flyway_cmd="${flyway_cmd} -outOfOrder=false"

    # Check if Flyway CLI is available, otherwise try Maven
    if command -v flyway &> /dev/null; then
        if [ "${CLEAN}" = true ]; then
            echo "  WARNING: Cleaning database schema for ${module_name}..."
            ${flyway_cmd} clean
        fi

        if [ "${REPAIR}" = true ]; then
            echo "  Repairing Flyway schema history..."
            ${flyway_cmd} repair
        fi

        ${flyway_cmd} migrate
        echo "  -> ${module_name} migration complete."

    elif command -v mvn &> /dev/null; then
        echo "  Using Maven Flyway plugin for ${module_name}..."
        cd "${module_dir}"

        if [ "${CLEAN}" = true ]; then
            mvn flyway:clean -Dflyway.url="${JDBC_URL}" \
                -Dflyway.user="${DB_USER}" -Dflyway.password="${DB_PASSWORD}" \
                -Dflyway.table="${module_name//-/_}_schema_history" -q
        fi

        if [ "${REPAIR}" = true ]; then
            mvn flyway:repair -Dflyway.url="${JDBC_URL}" \
                -Dflyway.user="${DB_USER}" -Dflyway.password="${DB_PASSWORD}" \
                -Dflyway.table="${module_name//-/_}_schema_history" -q
        fi

        mvn flyway:migrate -Dflyway.url="${JDBC_URL}" \
            -Dflyway.user="${DB_USER}" -Dflyway.password="${DB_PASSWORD}" \
            -Dflyway.table="${module_name//-/_}_schema_history" \
            -Dflyway.locations="filesystem:${migration_dir}" -q

        cd "${QOOAUTH_DIR}"
        echo "  -> ${module_name} migration complete."

    elif command -v gradle &> /dev/null; then
        echo "  Using Gradle Flyway plugin for ${module_name}..."
        cd "${module_dir}"

        if [ "${CLEAN}" = true ]; then
            gradle flywayClean -Dflyway.url="${JDBC_URL}" \
                -Dflyway.user="${DB_USER}" -Dflyway.password="${DB_PASSWORD}" -q
        fi

        if [ "${REPAIR}" = true ]; then
            gradle flywayRepair -Dflyway.url="${JDBC_URL}" \
                -Dflyway.user="${DB_USER}" -Dflyway.password="${DB_PASSWORD}" -q
        fi

        gradle flywayMigrate -Dflyway.url="${JDBC_URL}" \
            -Dflyway.user="${DB_USER}" -Dflyway.password="${DB_PASSWORD}" -q

        cd "${QOOAUTH_DIR}"
        echo "  -> ${module_name} migration complete."

    else
        echo "  ERROR: Neither Flyway CLI, Maven, nor Gradle found."
        echo "         Please install Flyway: https://flywaydb.org/documentation/usage/commandline/"
        return 1
    fi
}

# Run migrations for each target module
FAILED_MODULES=()
for module in "${TARGET_MODULES[@]}"; do
    if ! run_flyway "${module}"; then
        FAILED_MODULES+=("${module}")
    fi
done

# Summary
echo ""
echo "============================================"
if [ ${#FAILED_MODULES[@]} -eq 0 ]; then
    echo "  All migrations completed successfully!"
else
    echo "  Migration completed with failures:"
    for m in "${FAILED_MODULES[@]}"; do
        echo "    - ${m}"
    done
fi
echo "============================================"
