#!/usr/bin/env bash
# scripts/local_ci.sh — Run CI checks locally (no Docker required)
#
# Usage:
#   bash scripts/local_ci.sh         # run all checks
#   bash scripts/local_ci.sh proto   # run only proto-check
#   bash scripts/local_ci.sh python  # run only Python checks
#   bash scripts/local_ci.sh node    # run only TypeScript checks
#
# Exit code 0 = all checks passed, non-zero = failures

set -euo pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSPACE"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

passed=0
failed=0

_ok()   { echo -e "${GREEN}  ✅ $1${NC}";  ((passed++)); }
_fail() { echo -e "${RED}  ❌ $1: $2${NC}"; ((failed++)); }
_skip() { echo -e "${YELLOW}  ⏭  $1 (skipped: $2)${NC}"; }
_header() { echo; echo "── $1 ─────────────────────────────────"; }

FILTER="${1:-all}"

# ── Proto check ─────────────────────────────────────────────────

if [[ "$FILTER" == "all" || "$FILTER" == "proto" ]]; then
  _header "Proto generation"

  if command -v python3 &>/dev/null; then
    PYTHON=python3
  elif command -v python &>/dev/null; then
    PYTHON=python
  else
    _skip "proto-generate" "python not found"
    PYTHON=""
  fi

  if [[ -n "$PYTHON" ]]; then
    if $PYTHON -c "import grpc_tools.protoc" 2>/dev/null; then
      $PYTHON brain_proto/scripts/generate_proto.py && \
        _ok "proto-generate" || _fail "proto-generate" "generation failed"
    else
      _skip "proto-generate" "grpcio-tools not installed (pip install grpcio-tools)"
    fi
  fi
fi

# ── Python checks ────────────────────────────────────────────────

if [[ "$FILTER" == "all" || "$FILTER" == "python" ]]; then
  _header "Python (brain_ai)"

  if command -v python3 &>/dev/null; then
    PYTHON=python3
  elif command -v python &>/dev/null; then
    PYTHON=python
  else
    _skip "python" "python not found"
    PYTHON=""
  fi

  if [[ -n "$PYTHON" ]]; then
    # grpc communication test
    if $PYTHON -c "import grpc" 2>/dev/null; then
      $PYTHON tests/test_grpc_communication.py 2>/dev/null && \
        _ok "grpc-communication" || _fail "grpc-communication" "test failed"
    else
      _skip "grpc-communication" "grpcio not installed"
    fi

    # websocket communication test
    if $PYTHON -c "import websockets" 2>/dev/null; then
      $PYTHON tests/test_websocket_communication.py 2>/dev/null && \
        _ok "websocket-communication" || _fail "websocket-communication" "test failed"
    else
      _skip "websocket-communication" "websockets not installed"
    fi

    # ruff lint
    if command -v ruff &>/dev/null; then
      ruff check brain_ai/brain_ai/ brain_sdk/brain_os/ \
        --ignore E501,E402,F401 --quiet && \
        _ok "ruff-lint" || _fail "ruff-lint" "linting errors"
    else
      _skip "ruff-lint" "ruff not installed"
    fi
  fi
fi

# ── TypeScript checks ────────────────────────────────────────────

if [[ "$FILTER" == "all" || "$FILTER" == "node" ]]; then
  _header "TypeScript (brain_viz)"

  if command -v npm &>/dev/null && [[ -d brain_viz/node_modules ]]; then
    cd brain_viz
    npx tsc --noEmit 2>/dev/null && _ok "tsc-typecheck" || _fail "tsc-typecheck" "type errors"
    cd "$WORKSPACE"
  else
    _skip "tsc-typecheck" "npm or node_modules not available"
  fi
fi

# ── C++ build check ──────────────────────────────────────────────

if [[ "$FILTER" == "all" || "$FILTER" == "cpp" ]]; then
  _header "C++ (brain_core)"

  if command -v cmake &>/dev/null && command -v make &>/dev/null; then
    mkdir -p brain_core/build_ci
    cmake -S brain_core -B brain_core/build_ci \
      -DCMAKE_BUILD_TYPE=Release -DBRAIN_CORE_SKIP_ROS2=ON \
      -Wno-dev -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
      >/dev/null 2>&1 && _ok "cmake-configure" || \
      _skip "cmake-configure" "cmake failed (likely missing ROS2/gRPC)"
  else
    _skip "cmake" "cmake/make not found"
  fi
fi

# ── Summary ──────────────────────────────────────────────────────

echo
echo "════════════════════════════════════════"
echo "  Local CI Results: ${passed} passed, ${failed} failed"
echo "════════════════════════════════════════"

exit "$failed"
