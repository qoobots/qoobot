#!/usr/bin/env bash
# ============================================================================
# Isaac Lab Training — Pick Red Cup Skill
# ============================================================================
# Launches RL training for the pick-and-place skill on Kinova Gen3.
#
# Prerequisites:
#   1. Isaac Sim 2023.1.1+ installed
#   2. Isaac Lab installed: pip install isaacsim (or Docker)
#   3. CUDA 11.8+ with compatible NVIDIA driver
#   4. Brain OS model directory with USD assets
#
# Usage:
#   ./isaac_lab_train.sh                     # Train with default config
#   ./isaac_lab_train.sh --num-envs 2048      # Custom env count
#   ./isaac_lab_train.sh --resume checkpoint  # Resume from checkpoint
#   ./isaac_lab_train.sh --eval               # Evaluation only
# ============================================================================

set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_SIM_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
PROJECT_ROOT="$(dirname "$BRAIN_SIM_DIR")"

# Default paths
ISAAC_SIM_PATH="${ISAAC_SIM_PATH:-/isaac-sim}"
ISAAC_LAB_PATH="${ISAAC_LAB_PATH:-${PROJECT_ROOT}/isaac_lab}"
PYTHON_EXE="${ISAAC_SIM_PATH}/python.sh"
CHECKPOINT_DIR="${BRAIN_SIM_DIR}/models/checkpoints"
LOG_DIR="${BRAIN_SIM_DIR}/models/logs"

# Training defaults
TASK_NAME="BrainOS-PickAndPlace-v0"
NUM_ENVS=4096
TOTAL_TIMESTEPS=100000000
HEADLESS=true
RESUME=""
EVAL_ONLY=false

# ── Argument Parsing ───────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --num-envs)
            NUM_ENVS="$2"; shift 2 ;;
        --total-steps)
            TOTAL_TIMESTEPS="$2"; shift 2 ;;
        --headless)
            HEADLESS=true; shift ;;
        --gui)
            HEADLESS=false; shift ;;
        --resume)
            RESUME="$2"; shift 2 ;;
        --eval)
            EVAL_ONLY=true; shift ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --num-envs N     Number of parallel environments (default: 4096)"
            echo "  --total-steps N  Total training timesteps (default: 100M)"
            echo "  --headless       Run without GUI (default)"
            echo "  --gui            Run with GUI for visualization"
            echo "  --resume PATH    Resume from checkpoint"
            echo "  --eval           Evaluation only (no training)"
            echo "  --help, -h       Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Preflight Checks ────────────────────────────────────────────────────────

echo "=============================================="
echo "  Brain OS — Isaac Lab Training"
echo "  Skill: pick_red_cup"
echo "=============================================="
echo ""

# Check Isaac Sim
if [ ! -d "${ISAAC_SIM_PATH}" ]; then
    echo "[WARN] Isaac Sim not found at ${ISAAC_SIM_PATH}"
    echo "[INFO] Set ISAAC_SIM_PATH environment variable to Isaac Sim install dir"
    echo "[INFO] Or run: export ISAAC_SIM_PATH=/path/to/isaac-sim"
    echo ""
    echo "Download Isaac Sim: https://developer.nvidia.com/isaac-sim"
    echo ""
    
    # Check if we're in a CI or dev environment without GPU
    if command -v nvidia-smi &>/dev/null; then
        echo "[ERROR] GPU detected but Isaac Sim not installed. Aborting."
        exit 1
    else
        echo "[WARN] No GPU detected. This is expected in CI/dev."
        echo "[INFO] Isaac Lab training requires an NVIDIA GPU with CUDA."
        echo "[INFO] Skipping actual training — printing config only."
        SKIP_TRAINING=true
    fi
else
    SKIP_TRAINING=false
    echo "[OK] Isaac Sim found: ${ISAAC_SIM_PATH}"
fi

# Check Python
if [ "${SKIP_TRAINING:-false}" = false ]; then
    if [ ! -f "${PYTHON_EXE}" ]; then
        echo "[ERROR] Isaac Sim Python not found: ${PYTHON_EXE}"
        exit 1
    fi
    echo "[OK] Isaac Sim Python: ${PYTHON_EXE}"
fi

# Create directories
mkdir -p "${CHECKPOINT_DIR}"
mkdir -p "${LOG_DIR}"

# ── Environment Variables ───────────────────────────────────────────────────

export ISAAC_SIM_PATH
export TASK_DIR="${BRAIN_SIM_DIR}/isaac_sim/tasks"
export ENV_DIR="${BRAIN_SIM_DIR}/isaac_sim/environments"

# Brain OS integration
export BRAIN_OS_GRPC="localhost:50051"
export BRAIN_OS_SIM_MODE=true

# ── Build Training Command ──────────────────────────────────────────────────

if [ "${SKIP_TRAINING:-false}" = true ]; then
    echo ""
    echo "=============================================="
    echo "  Training Configuration (Simulated)"
    echo "=============================================="
    echo "  Task:        ${TASK_NAME}"
    echo "  Algorithm:   PPO"
    echo "  Num Envs:    ${NUM_ENVS}"
    echo "  Total Steps: ${TOTAL_TIMESTEPS}"
    echo "  Headless:    ${HEADLESS}"
    echo "  Checkpoints: ${CHECKPOINT_DIR}"
    echo "  Logs:        ${LOG_DIR}"
    echo ""
    echo "[INFO] Training skipped — no GPU available."
    echo "[INFO] On a GPU machine, run this script to start actual training."
    echo ""
    
    # Print task manifest for reference
    echo "------------------------------------------------"
    echo "  Skill Manifest"
    echo "------------------------------------------------"
    ${PYTHON_EXE:-python3} -c "
import sys
sys.path.insert(0, '${BRAIN_SIM_DIR}')
sys.path.insert(0, '${BRAIN_SIM_DIR}/isaac_sim/tasks')
from pick_red_cup import register_with_brain_os, get_subtasks, PickRedCupConfig
import json

manifest = register_with_brain_os()
print(json.dumps(manifest, indent=2, ensure_ascii=False))
print()
print('Sub-tasks:')
for i, st in enumerate(get_subtasks(PickRedCupConfig())):
    print(f'  {i+1}. {st.name}: {st.description}')
" 2>&1 || echo "[INFO] Could not print skill manifest (expected in CI)"
    
    exit 0
fi

# Full training command
CMD=(
    "${PYTHON_EXE}" -m isaac_lab.train
    --task "${TASK_NAME}"
    --task-entry "${ENV_DIR}/pick_and_place.py:PickAndPlaceEnv"
    --task-config "${TASK_DIR}/pick_red_cup.py"
    --headless "${HEADLESS}"
    --num-envs "${NUM_ENVS}"
    --total-timesteps "${TOTAL_TIMESTEPS}"
    --checkpoint-dir "${CHECKPOINT_DIR}"
    --log-dir "${LOG_DIR}"
    --seed 42
)

if [ -n "${RESUME}" ]; then
    CMD+=(--resume "${RESUME}")
fi

if [ "${EVAL_ONLY}" = true ]; then
    CMD+=(--eval)
fi

# ── Launch Training ─────────────────────────────────────────────────────────

echo ""
echo "=============================================="
echo "  Starting Training..."
echo "=============================================="
echo "  Command: ${CMD[*]}"
echo ""

# Run the training
"${CMD[@]}" 2>&1 | tee "${LOG_DIR}/training_$(date +%Y%m%d_%H%M%S).log"

# ── Post-Training: Register Model ───────────────────────────────────────────

echo ""
echo "=============================================="
echo "  Training Complete"
echo "=============================================="
echo ""

# Find the latest checkpoint
LATEST_CKPT=$(ls -t "${CHECKPOINT_DIR}"/checkpoint_*.pt 2>/dev/null | head -1)

if [ -n "${LATEST_CKPT}" ]; then
    echo "  Latest checkpoint: ${LATEST_CKPT}"
    
    # Copy to Brain OS models directory
    MODEL_DEST="${PROJECT_ROOT}/brain_models/pick_red_cup/policy.pt"
    mkdir -p "$(dirname "${MODEL_DEST}")"
    cp "${LATEST_CKPT}" "${MODEL_DEST}"
    echo "  Model exported to: ${MODEL_DEST}"
else
    echo "  [WARN] No checkpoint found. Training may have failed."
fi

echo ""
echo "  Done."
