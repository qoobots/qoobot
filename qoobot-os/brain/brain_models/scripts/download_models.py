#!/usr/bin/env python3
"""
Brain OS 模型下载脚本

从 HuggingFace Hub 批量下载模型权重，支持：
  - 按下载组批量下载 (minimal/standard/full/llm_only/cv_only)
  - 按类别下载 (--llm / --cv / --asr / --slam / --vla)
  - 单模型下载 (--model qwen2.5-7b-instruct-int4)
  - SHA256 校验和验证
  - 断点续传 (resume/overwrite/skip)
  - 镜像源自动切换 (HF ↔ hf-mirror.com)
  - 下载速度 / 进度条显示
  - 空 LFS 占位符检测与替换

Usage:
  python download_models.py --group minimal
  python download_models.py --llm --cv
  python download_models.py --model yolov11n
  python download_models.py --all --verify-only     # 仅校验不下载
  python download_models.py --group standard --mirror
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent          # brain_models/scripts/
BRAIN_MODELS_DIR = SCRIPT_DIR.parent                  # brain_models/
PROJECT_ROOT = BRAIN_MODELS_DIR.parent                # qoobot/
MODELS_DIR = BRAIN_MODELS_DIR
REGISTRY_FILE = MODELS_DIR / "model_registry.json"
VERSIONS_FILE = MODELS_DIR / "model_versions.yaml"
DOWNLOAD_CACHE = Path.home() / ".cache" / "brain_models"

PRIMARY_HF = "https://huggingface.co"
MIRROR_HF = "https://hf-mirror.com"

# 大文件阈值 (超过此大小显示显式进度条)
PROGRESS_THRESHOLD_MB = 10


# ============================================================================
# 工具函数
# ============================================================================

def load_registry() -> dict:
    """加载模型注册表"""
    if not REGISTRY_FILE.exists():
        print(f"[ERROR] 未找到模型注册表: {REGISTRY_FILE}")
        sys.exit(1)
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def human_size(size_bytes: int) -> str:
    """字节转人类可读大小"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def compute_sha256(filepath: Path) -> str:
    """计算文件 SHA256 校验和"""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()


def check_lfs_stub(filepath: Path) -> bool:
    """检测是否为 Git LFS 空占位符 (小于 200 字节的指针文件)"""
    if not filepath.exists():
        return False
    size = filepath.stat().st_size
    if size < 200:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(130)
        return "oid sha256:" in content
    return False


def ensure_dir(path: Path) -> None:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)


def get_hf_endpoint(use_mirror: bool) -> str:
    """获取 HuggingFace API 端点"""
    return MIRROR_HF if use_mirror else PRIMARY_HF


# ============================================================================
# 下载引擎
# ============================================================================

class ModelDownloader:
    """模型下载器"""

    def __init__(
        self,
        use_mirror: bool = False,
        verify: bool = True,
        overwrite: str = "resume",
        verbose: bool = True,
    ):
        self.use_mirror = use_mirror
        self.verify = verify
        self.overwrite = overwrite  # resume | overwrite | skip
        self.verbose = verbose
        self.registry = load_registry()
        self.endpoint = get_hf_endpoint(use_mirror)
        self.stats = {
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "verified": 0,
            "total_bytes": 0,
            "start_time": time.time(),
            "models": {}
        }

    def log(self, msg: str, level: str = "INFO") -> None:
        """统一日志输出"""
        if self.verbose or level == "ERROR":
            prefix = {"INFO": "  [*]", "OK": "  [✅]", "WARN": "  [⚠️]", "ERROR": "  [❌]", "SKIP": "  [⏭️]"}
            print(f"{prefix.get(level, '  [ ]')} {msg}")

    def download_file(
        self,
        model_id: str,
        repo_id: str,
        filename: str,
        dest: Path,
        revision: str = "main",
    ) -> bool:
        """从 HuggingFace Hub 下载单个文件"""
        url = f"{self.endpoint}/{repo_id}/resolve/{revision}/{filename}"
        dest.parent.mkdir(parents=True, exist_ok=True)

        # 检查是否已存在且有效
        if dest.exists():
            if self.overwrite == "skip":
                self.log(f"跳过 (已存在): {filename}", "SKIP")
                self.stats["skipped"] += 1
                return True
            elif self.overwrite == "resume" and not check_lfs_stub(dest):
                self.log(f"已存在有效文件: {filename}", "SKIP")
                self.stats["skipped"] += 1
                return True
            elif self.overwrite == "overwrite":
                self.log(f"覆盖已存在文件: {filename}", "WARN")

        self.log(f"下载: {repo_id}/{filename}", "INFO")

        try:
            import urllib.request
            import ssl

            ssl_context = ssl.create_default_context()

            req = urllib.request.Request(url)
            req.add_header("User-Agent", "BrainOS-ModelDownloader/1.0")
            req.add_header("Accept", "application/octet-stream")

            # 断点续传
            existing_size = 0
            if self.overwrite == "resume" and dest.exists():
                existing_size = dest.stat().st_size
                req.add_header("Range", f"bytes={existing_size}-")

            response = urllib.request.urlopen(req, context=ssl_context, timeout=60)

            # 检查重定向
            if response.geturl() != url and "cdn-lfs" not in response.geturl():
                self.log(f"重定向到: {response.geturl()}", "INFO")

            content_length = response.headers.get("Content-Length")
            total_size = int(content_length) if content_length else 0
            if existing_size > 0:
                total_size += existing_size

            mode = "ab" if existing_size > 0 else "wb"
            downloaded = existing_size

            with open(dest, mode) as f:
                chunk_size = 8192
                last_report = time.time()
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    # 进度报告 (每 0.5 秒或文件大于阈值时)
                    now = time.time()
                    if total_size > 0 and (now - last_report > 0.5):
                        pct = downloaded / total_size * 100
                        speed = (downloaded - existing_size) / max(now - last_report + 0.5, 0.001)
                        bar_len = 30
                        filled = int(bar_len * downloaded / total_size)
                        bar = "█" * filled + "░" * (bar_len - filled)
                        print(
                            f"\r    {bar} {pct:5.1f}%  {human_size(downloaded)}/{human_size(total_size)}  "
                            f"{human_size(int(speed))}/s",
                            end="",
                            flush=True,
                        )
                        last_report = now

            if total_size > 0:
                print()  # 换行

            file_size = dest.stat().st_size
            self.stats["total_bytes"] += file_size
            self.log(f"完成: {filename} ({human_size(file_size)})", "OK")
            return True

        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.log(f"文件不存在: {filename} (HTTP 404)", "ERROR")
            elif e.code == 401:
                self.log(f"需要认证: {filename} (可能是私有仓库或需要 HF token)", "ERROR")
            elif e.code == 416:
                # Range Not Satisfiable — 文件已完整下载
                self.log(f"已完整 (HTTP 416): {filename}", "SKIP")
                self.stats["skipped"] += 1
                return True
            else:
                self.log(f"HTTP {e.code}: {filename}", "ERROR")
            return False
        except Exception as e:
            self.log(f"下载失败: {filename} — {e}", "ERROR")
            return False

    def download_model(self, model_id: str) -> bool:
        """下载并验证单个模型"""
        model_info = self.registry["models"].get(model_id)
        if not model_info:
            self.log(f"未知模型: {model_id}", "ERROR")
            return False

        print(f"\n{'='*60}")
        print(f"  模型: {model_info['name']}")
        print(f"  类别: {model_info['category']}")
        print(f"  格式: {model_info['format']}")
        if model_info.get("estimated_size_gb"):
            print(f"  预估: {model_info['estimated_size_gb']:.1f} GB")
        elif model_info.get("estimated_size_mb"):
            print(f"  预估: {model_info['estimated_size_mb']:.1f} MB")
        print(f"{'='*60}")

        hf = model_info.get("huggingface", {})
        if not hf:
            self.log("无 HuggingFace 源配置，跳过下载", "WARN")
            self.stats["skipped"] += 1
            self.stats["models"][model_id] = "skipped_no_source"
            return True

        repo = hf.get("repo", "")
        revision = hf.get("revision", "main")
        files = hf.get("files", [])
        local_dir = PROJECT_ROOT / model_info.get("local_path", "").replace("brain_models/", "brain_models/", 1)

        if not local_dir or not files:
            self.log("配置不完整 (缺少 local_path 或 files)", "ERROR")
            self.stats["failed"] += 1
            self.stats["models"][model_id] = "failed_config"
            return False

        ensure_dir(local_dir)
        success = True

        for filename in files:
            dest = local_dir / filename

            # 跳过已有有效文件
            if dest.exists() and not check_lfs_stub(dest) and self.overwrite == "resume":
                file_size = dest.stat().st_size
                if file_size > 1000:  # 超过 1KB 视为有效
                    self.log(f"已存在: {filename} ({human_size(file_size)})", "SKIP")
                    self.stats["skipped"] += 1
                    continue

            if not self.download_file(model_id, repo, filename, dest, revision):
                success = False
                self.stats["failed"] += 1
                self.stats["models"][model_id] = "failed_download"
            else:
                self.stats["downloaded"] += 1

            # 校验 (如果有校验和)
            if self.verify and success and dest.exists():
                checksums = model_info.get("checksums", {})
                expected = checksums.get(filename)
                if expected and expected != "TBD":
                    actual = compute_sha256(dest)
                    if actual == expected:
                        self.log(f"校验通过: {filename}", "OK")
                        self.stats["verified"] += 1
                    else:
                        self.log(f"校验失败! {filename}: got {actual[:12]}..., expected {expected[:12]}...", "ERROR")
                        self.stats["failed"] += 1
                        success = False
                elif expected == "TBD":
                    # 记录实际 checksum 供更新注册表
                    actual = compute_sha256(dest)
                    self.log(f"校验和: {filename} = {actual} (请更新 registry)", "WARN")

        # 处理 SAM2 的两部分
        if "parts" in model_info:
            for part_name, part_info in model_info["parts"].items():
                dest = local_dir / part_info["file"]
                if not dest.exists():
                    continue
                # 如果是 LFS 占位符，尝试恢复
                if check_lfs_stub(dest):
                    self.log(f"LFS 占位符: {part_info['file']} (需先运行 git lfs pull)", "WARN")

        self.stats["models"][model_id] = "ok" if success else "failed"
        return success

    def download_group(self, group_name: str) -> int:
        """下载一组模型"""
        groups = self.registry.get("download_groups", {})
        if group_name not in groups:
            print(f"[ERROR] 未知下载组: {group_name}")
            print(f"  可用: {', '.join(groups.keys())}")
            return 0

        model_ids = groups[group_name]["models"]
        print(f"\n📦 下载组: {group_name} ({groups[group_name]['description']})")
        print(f"   模型: {', '.join(model_ids)}")

        success_count = 0
        for model_id in model_ids:
            if self.download_model(model_id):
                success_count += 1

        return success_count

    def download_category(self, category: str) -> int:
        """下载某个类别的所有模型"""
        model_ids = [
            mid
            for mid, info in self.registry["models"].items()
            if info["category"] == category
        ]
        if not model_ids:
            print(f"[WARN] 无模型匹配类别: {category}")
            return 0

        print(f"\n📦 类别: {category}")
        print(f"   模型: {', '.join(model_ids)}")

        success_count = 0
        for model_id in model_ids:
            if self.download_model(model_id):
                success_count += 1

        return success_count

    def print_summary(self) -> None:
        """打印下载摘要"""
        elapsed = time.time() - self.stats["start_time"]

        print(f"\n{'='*60}")
        print(f"  下载摘要")
        print(f"{'='*60}")
        print(f"  耗时:       {elapsed:.1f}s")
        print(f"  下载:       {self.stats['downloaded']} 文件")
        print(f"  跳过:       {self.stats['skipped']} 文件")
        print(f"  校验:       {self.stats['verified']} 文件")
        print(f"  失败:       {self.stats['failed']} 文件")
        print(f"  总大小:     {human_size(self.stats['total_bytes'])}")
        print(f"{'='*60}")

        # 模型级别统计
        failed_models = [mid for mid, status in self.stats["models"].items() if "failed" in status]
        if failed_models:
            print(f"\n⚠️  失败的模型: {', '.join(failed_models)}")
        elif self.stats["failed"] == 0:
            print(f"\n✅ 全部成功!")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Brain OS 模型下载脚本 — 从 HuggingFace Hub 批量下载模型权重",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --group minimal          # 最小部署
  %(prog)s --llm --cv               # 仅 LLM + CV
  %(prog)s --model yolov11n         # 单个模型
  %(prog)s --all --verify-only      # 仅校验所有权重
  %(prog)s --group standard --mirror # 使用镜像源
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--group", type=str, help="下载组: minimal|standard|full|llm_only|cv_only")
    group.add_argument("--all", action="store_true", help="下载所有模型")
    group.add_argument("--model", type=str, help="下载单个模型 (如 yolov11n)")

    parser.add_argument("--llm", action="store_true", help="下载所有 LLM 模型")
    parser.add_argument("--cv", action="store_true", help="下载所有 CV 模型")
    parser.add_argument("--asr", action="store_true", help="下载所有 ASR 模型")
    parser.add_argument("--slam", action="store_true", help="下载 SLAM 模型")
    parser.add_argument("--vla", action="store_true", help="下载 VLA 模型")
    parser.add_argument("--sim", action="store_true", help="下载仿真模型")

    parser.add_argument("--mirror", action="store_true", help="使用 hf-mirror.com 镜像源")
    parser.add_argument("--no-verify", action="store_true", help="跳过 SHA256 校验")
    parser.add_argument("--overwrite", type=str, default="resume",
                        choices=["resume", "overwrite", "skip"],
                        help="文件覆盖策略 (默认: resume)")
    parser.add_argument("--verify-only", action="store_true", help="仅校验已下载文件，不下载")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    parser.add_argument("--list", action="store_true", help="列出所有可用模型")

    args = parser.parse_args()

    # 列出模型
    if args.list:
        registry = load_registry()
        print("\n可用模型:\n")
        for mid, info in registry["models"].items():
            size_gb = info.get("estimated_size_gb")
            size_mb = info.get("estimated_size_mb", 0)
            if size_gb:
                size_str = f"~{size_gb:.1f}GB"
            elif size_mb:
                size_str = f"~{size_mb:.0f}MB"
            else:
                size_str = "?MB"
            print(f"  {mid:35s}  {info['category']:8s}  {info['format']:15s}  "
                  f"{size_str:>8s}  [{info['priority']}]")
        print(f"\n下载组:")
        for gname, ginfo in registry["download_groups"].items():
            print(f"  {gname:15s}  {ginfo['description']}")
        return

    # 确定下载范围
    registry = load_registry()
    model_ids: List[str] = []

    if args.all:
        model_ids = list(registry["models"].keys())
    elif args.group:
        model_ids = registry["download_groups"].get(args.group, {}).get("models", [])
    elif args.model:
        if args.model in registry["models"]:
            model_ids = [args.model]
        else:
            print(f"[ERROR] 未知模型: {args.model}")
            print(f"  可用: {', '.join(registry['models'].keys())}")
            sys.exit(1)
    else:
        # 按类别
        categories = []
        if args.llm: categories.append("llm")
        if args.cv: categories.append("cv")
        if args.asr: categories.append("asr")
        if args.slam: categories.append("slam")
        if args.vla: categories.append("vla")
        if args.sim: categories.append("simulation")

        if not categories:
            parser.print_help()
            print("\n[ERROR] 请指定下载范围 (--group / --all / --llm / --model / ...)")
            sys.exit(1)

        for mid, info in registry["models"].items():
            if info["category"] in categories:
                model_ids.append(mid)

    if not model_ids:
        print("[ERROR] 无模型需要下载")
        sys.exit(1)

    print(f"\n🚀 Brain OS 模型下载器")
    print(f"   模型数: {len(model_ids)}")
    print(f"   镜像源: {'hf-mirror.com' if args.mirror else 'huggingface.co'}")
    print(f"   覆盖策略: {args.overwrite}")
    print(f"   校验: {'关闭' if args.no_verify else '开启'}")

    downloader = ModelDownloader(
        use_mirror=args.mirror,
        verify=not args.no_verify,
        overwrite=args.overwrite,
        verbose=not args.quiet,
    )

    # 仅校验模式
    if args.verify_only:
        print("\n🔍 仅校验模式 — 检查已下载文件...\n")
        verified = 0
        for model_id in model_ids:
            model_info = registry["models"][model_id]
            local_dir = PROJECT_ROOT / model_info["local_path"].replace("brain_models/", "brain_models/", 1)
            checksums = model_info.get("checksums", {})
            if checksums.get("algorithm") != "sha256":
                continue
            for filename, expected_hash in checksums.items():
                if filename == "algorithm" or expected_hash == "TBD":
                    continue
                filepath = local_dir / filename
                if not filepath.exists():
                    print(f"  [❌] {model_id}/{filename} — 文件不存在")
                    continue
                actual = compute_sha256(filepath)
                if actual == expected_hash:
                    print(f"  [✅] {model_id}/{filename}")
                    verified += 1
                else:
                    print(f"  [❌] {model_id}/{filename} — 校验和不匹配")
        print(f"\n  校验完成: {verified} 文件")
        return

    # 下载
    final_success = 0
    if args.group:
        final_success = downloader.download_group(args.group)
    elif args.model:
        final_success = 1 if downloader.download_model(args.model) else 0
    else:
        # 按类别或全部
        for model_id in model_ids:
            if downloader.download_model(model_id):
                final_success += 1

    downloader.print_summary()

    # 退出码
    if downloader.stats["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
