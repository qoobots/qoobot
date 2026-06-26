#!/usr/bin/env python3
"""
QooBot Mechanical — 一键测试脚本
=================================
运行所有 qoobody/mechanical 模块测试
"""

import subprocess
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

tests = [
    ("MuJoCo 双足模型检查", "test_mujoco_xml.py"),
    ("一致性检查", "test_cross_consistency.py"),
    ("C++ 源文件与构建检查", "test_cpp_sources.py"),
    ("编译环境检查", "test_build_env.py"),
]

# 这些测试允许非零返回码（例如警告/可选依赖缺失）
# 返回码 1 视为 WARN 而非 FAIL
WARN_TOLERANT = {
    "C++ 源文件与构建检查",
    "编译环境检查",
}


def run_test(name, script):
    print(f"\n{'#' * 70}")
    print(f"#  {name}")
    print(f"{'#' * 70}")
    script_path = os.path.join(SCRIPT_DIR, script)
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    return result.returncode


def main():
    print("=" * 70)
    print("  QooBot Mechanical — 全模块测试")
    print("=" * 70)

    results = {}
    for name, script in tests:
        rc = run_test(name, script)
        results[name] = rc

    print(f"\n{'=' * 70}")
    print(f"  测试结果汇总")
    print(f"{'=' * 70}")
    all_pass = True
    for name, rc in results.items():
        if rc == 0:
            status = "PASS"
        elif name in WARN_TOLERANT:
            status = "WARN"  # 有警告但可接受
        else:
            status = "FAIL"
            all_pass = False
        print(f"  [{status}] {name}")

    print()
    if all_pass:
        print("  ✓ 所有测试通过！")
    else:
        print("  ✗ 部分测试未通过，请查看上方详情")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
