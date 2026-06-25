#!/usr/bin/env python3
"""Brain OS 发布打包脚本

功能：
  - 版本号管理
  - 生成 CHANGELOG
  - 打包 Python SDK (.whl)
  - 创建 Git tag
  - 生成发布清单

用法：
  python scripts/release.py --version 1.0.0                 # 完整发布
  python scripts/release.py --version 1.0.0 --dry-run       # 预览（不实际执行）
  python scripts/release.py --version 1.0.0 --skip-tag      # 跳过 Git tag
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# 版本管理
# ============================================================

VERSION_FILE = ROOT / "VERSION"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
RELEASE_MANIFEST_FILE = ROOT / "RELEASE_MANIFEST.json"

MODULES = [
    ("brain_proto", "gRPC Protobuf 服务定义"),
    ("brain_core", "C++17 实时控制引擎"),
    ("brain_ai", "Python AI 认知引擎"),
    ("brain_viz", "Next.js 可视化 Dashboard"),
    ("brain_sdk", "Python SDK (pip install)"),
    ("brain_sim", "Gazebo + Isaac Sim 仿真环境"),
    ("brain_models", "模型注册表 + 下载工具"),
    ("brain_deploy", "Docker/K8s/DEB 部署配置"),
    ("brain_docs", "MkDocs Material 文档站点"),
]


def read_current_version() -> str:
    """读取当前版本号"""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    # 从 git tag 推断
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, cwd=ROOT
        )
        if result.returncode == 0:
            return result.stdout.strip().lstrip("v")
    except Exception:
        pass
    return "0.1.0"


def write_version(version: str):
    """写入版本号"""
    VERSION_FILE.write_text(version + "\n")
    print(f"  [OK] VERSION = {version}")


def bump_version(current: str, bump_type: str) -> str:
    """版本号增量"""
    parts = current.split(".")
    if bump_type == "major":
        parts = [str(int(parts[0]) + 1), "0", "0"]
    elif bump_type == "minor":
        parts = [parts[0], str(int(parts[1]) + 1), "0"]
    elif bump_type == "patch":
        parts = [parts[0], parts[1], str(int(parts[2]) + 1)]
    return ".".join(parts)


# ============================================================
# CHANGELOG
# ============================================================

def generate_changelog(version: str) -> str:
    """生成 CHANGELOG 条目（从 git log）"""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--no-decorate", "-30"],
            capture_output=True, text=True, cwd=ROOT
        )
        commits = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception:
        commits = ["(git 不可用)"]
    
    date_str = datetime.date.today().isoformat()
    
    entry = f"\n## [{version}] — {date_str}\n\n"
    for c in commits:
        entry += f"- {c}\n"
    entry += "\n"
    
    return entry


# ============================================================
# 打包
# ============================================================

def build_python_sdk(version: str, dry_run: bool) -> bool:
    """构建 Python SDK .whl 包"""
    sdk_dir = ROOT / "brain_sdk"
    dist_dir = sdk_dir / "dist"
    
    print(f"\n>>> 构建 Python SDK (brain_sdk) v{version}")
    
    if dry_run:
        print("  [DRY-RUN] pip wheel brain_sdk/")
        return True
    
    # 更新 pyproject.toml 版本号
    pyproject = sdk_dir / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        # 替换 version 行
        import re
        content = re.sub(r'version\s*=\s*"[^"]*"', f'version = "{version}"', content)
        pyproject.write_text(content)
    
    # 构建
    result = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", str(sdk_dir), "-w", str(dist_dir)],
        capture_output=True, text=True, cwd=ROOT
    )
    
    if result.returncode == 0:
        wheels = list(dist_dir.glob("*.whl"))
        for w in wheels:
            print(f"  [OK] {w.name} ({w.stat().st_size / 1024:.1f} KB)")
        return True
    else:
        print(f"  [FAIL] {result.stderr}")
        return False


# ============================================================
# Git Tag
# ============================================================

def create_git_tag(version: str, dry_run: bool):
    """创建 Git 标签"""
    tag = f"v{version}"
    message = f"Release {tag}"
    
    print(f"\n>>> 创建 Git Tag: {tag}")
    
    if dry_run:
        print(f"  [DRY-RUN] git tag -a {tag} -m '{message}'")
        return
    
    try:
        subprocess.run(["git", "tag", "-a", tag, "-m", message], check=True, cwd=ROOT)
        print(f"  [OK] Tag {tag} 已创建")
        print(f"  推送: git push origin {tag}")
    except subprocess.CalledProcessError as e:
        print(f"  [SKIP] Tag 创建失败: {e}")


# ============================================================
# 发布清单
# ============================================================

def generate_manifest(version: str) -> dict:
    """生成发布清单 JSON"""
    manifest = {
        "version": version,
        "release_date": datetime.date.today().isoformat(),
        "project": "Brain OS — 具身智能机器人操作系统",
        "modules": {}
    }
    
    for name, desc in MODULES:
        module_dir = ROOT / name
        file_count = 0
        total_size = 0
        
        if module_dir.exists():
            for f in module_dir.rglob("*"):
                if f.is_file() and f.stat().st_size > 0:
                    file_count += 1
                    total_size += f.stat().st_size
        
        manifest["modules"][name] = {
            "description": desc,
            "files": file_count,
            "size_kb": round(total_size / 1024, 1),
        }
    
    return manifest


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Brain OS 发布打包工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --version 1.0.0                    完整发布
  %(prog)s --version 1.0.0 --dry-run           预览
  %(prog)s --version 1.0.0 --bump minor        自动版本递增
  %(prog)s --version 1.0.0 --skip-tag --skip-sdk 最小发布
        """
    )
    parser.add_argument("--version", type=str, required=True, help="发布版本号")
    parser.add_argument("--bump", type=str, choices=["major", "minor", "patch"],
                       help="自动版本递增（基于当前版本）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际执行")
    parser.add_argument("--skip-tag", action="store_true", help="跳过 Git tag 创建")
    parser.add_argument("--skip-sdk", action="store_true", help="跳过 SDK 打包")
    
    args = parser.parse_args()
    
    # 版本号处理
    version = args.version
    if args.bump:
        current = read_current_version()
        version = bump_version(current, args.bump)
        print(f"版本递增: {current} → {version}")
    
    print("=" * 60)
    print(f"Brain OS 发布打包 v{version}")
    print(f"时间: {datetime.datetime.now().isoformat()}")
    if args.dry_run:
        print(f"模式: 🔍 DRY RUN（预览，不实际执行）")
    print("=" * 60)
    
    # Step 1: 写入版本号
    write_version(version)
    
    # Step 2: 更新 CHANGELOG
    print(f"\n>>> 更新 CHANGELOG.md")
    changelog_entry = generate_changelog(version)
    if not args.dry_run:
        if CHANGELOG_FILE.exists():
            existing = CHANGELOG_FILE.read_text()
            # 在第一个 ## 前插入
            if "## [" in existing:
                idx = existing.index("## [")
                existing = existing[:idx] + changelog_entry + existing[idx:]
            else:
                existing = "# Changelog\n\n" + changelog_entry + existing
            CHANGELOG_FILE.write_text(existing)
        else:
            CHANGELOG_FILE.write_text("# Changelog\n\n" + changelog_entry)
        print(f"  [OK] CHANGELOG 已更新")
    else:
        print(f"  [DRY-RUN] 将添加 entry: {changelog_entry[:80]}...")
    
    # Step 3: 构建 SDK
    sdk_ok = True
    if not args.skip_sdk:
        sdk_ok = build_python_sdk(version, args.dry_run)
    
    # Step 4: 生成发布清单
    print(f"\n>>> 生成发布清单")
    manifest = generate_manifest(version)
    if not args.dry_run:
        RELEASE_MANIFEST_FILE.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
        print(f"  [OK] RELEASE_MANIFEST.json 已生成")
    
    print(f"\n{'=' * 60}")
    print("模块统计:")
    for name, info in manifest["modules"].items():
        print(f"  {name:<16} {info['files']:>4} 文件, {info['size_kb']:>8.1f} KB — {info['description']}")
    
    # Step 5: Git Tag
    if not args.skip_tag:
        create_git_tag(version, args.dry_run)
    
    # 最终结果
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print("🔍 DRY RUN 完成 — 以上操作均为预览")
    else:
        status = "✅" if sdk_ok else "⚠️"
        print(f"{status} 发布 v{version} 完成")
        
        print(f"\n发布检查清单:")
        print(f"  [ ] 运行测试: make test")
        print(f"  [ ] 运行冒烟: tests/simulation_demo.py")
        print(f"  [ ] 运行基准: tests/benchmark.py --quick")
        print(f"  [ ] 推送标签: git push origin v{version}")
        print(f"  [ ] 上传 SDK: twine upload brain_sdk/dist/*.whl")
    
    return 0 if sdk_ok else 1


if __name__ == "__main__":
    sys.exit(main())
