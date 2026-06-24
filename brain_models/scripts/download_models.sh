#!/usr/bin/env bash
# ============================================================================
# Brain OS 模型下载 Shell 入口脚本
#
# 这是 brain_ai/scripts/download_models.sh 的主要入口，
# 内部调用 Python 下载脚本完成实际下载。
#
# Usage:
#   bash download_models.sh --group minimal
#   bash download_models.sh --llm --cv --mirror
#   bash download_models.sh --list
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DOWNLOAD_PY="$PROJECT_ROOT/brain_models/scripts/download_models.py"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[*]${NC} $*"; }
ok()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }

# 检查 Python 环境
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    error "未找到 Python 3 运行环境"
    exit 1
fi

PYTHON="$(command -v python3 || command -v python)"

# 检查 pip 依赖
check_deps() {
    info "检查 Python 依赖..."
    # download_models.py 仅使用标准库 (urllib, hashlib, json, argparse)
    # 无需额外安装，直接可用
    ok "依赖检查通过"
}

# 检查 Git LFS 状态
check_lfs() {
    if command -v git-lfs &> /dev/null; then
        if git lfs env 2>/dev/null | grep -q "git config filter.lfs"; then
            ok "Git LFS 已配置"
        else
            warn "Git LFS 已安装但未初始化，运行: git lfs install"
        fi
    else
        warn "Git LFS 未安装，大型模型文件将通过 HTTP 直接下载"
    fi
}

# 检查磁盘空间 (brain_models 目录所在分区)
check_disk() {
    local dir="$PROJECT_ROOT/brain_models"
    if [ -d "$dir" ]; then
        local available_kb
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
            # Windows Git Bash
            available_kb=$(df "$dir" 2>/dev/null | awk 'NR==2 {print $4}')
        else
            available_kb=$(df "$dir" 2>/dev/null | awk 'NR==2 {print $4}')
        fi
        if [ -n "$available_kb" ]; then
            local available_gb=$((available_kb / 1024 / 1024))
            if [ "$available_gb" -lt 10 ]; then
                warn "可用磁盘空间不足 ${available_gb}GB，完整下载需要 ~10GB"
            else
                ok "可用磁盘空间: ${available_gb}GB"
            fi
        fi
    fi
}

# 主入口
main() {
    echo ""
    echo "  ╔══════════════════════════════════════════════╗"
    echo "  ║        Brain OS 模型下载脚本 v1.0.0          ║"
    echo "  ║  从 HuggingFace Hub 下载模型权重到本地       ║"
    echo "  ╚══════════════════════════════════════════════╝"
    echo ""

    # 预检查
    check_deps
    check_lfs
    check_disk
    echo ""

    # 如果没有参数，显示帮助
    if [ $# -eq 0 ]; then
        warn "请指定下载范围"
        echo ""
        echo "  快速开始:"
        echo "    bash download_models.sh --group minimal   # 最小部署 (LLM+检测+SLAM)"
        echo "    bash download_models.sh --group standard  # 标准部署 (全部核心模型)"
        echo "    bash download_models.sh --list            # 列出所有可用模型"
        echo "    bash download_models.sh --llm --cv        # 仅 LLM + CV"
        echo ""
        echo "  所有选项:"
        $PYTHON "$DOWNLOAD_PY" --help 2>/dev/null || echo "    (请运行 python download_models.py --help)"
        exit 0
    fi

    # 调用 Python 下载脚本
    info "开始下载..."
    $PYTHON "$DOWNLOAD_PY" "$@"
    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo ""
        ok "模型下载完成!"
        echo ""
        echo "  下一步:"
        echo "    1. 运行 python convert_models.py --check     # 检查转换需求"
        echo "    2. 运行 python -m pytest tests/test_models.py # 验证模型完整性"
        echo "    3. 运行 python scripts/benchmark_models.py   # 推理基准测试"
    else
        error "下载过程中发生错误 (exit code: $exit_code)"
    fi

    exit $exit_code
}

main "$@"
