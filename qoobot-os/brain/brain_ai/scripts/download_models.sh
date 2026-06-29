#!/usr/bin/env bash
# ============================================================================
# Brain AI 模型下载脚本
#
# 委托给 brain_models/scripts/download_models.sh 实现
# 用法: bash download_models.sh [选项...]
# ============================================================================
exec "$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")/brain_models/scripts/download_models.sh" "$@"
