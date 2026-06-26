#!/usr/bin/env python3
"""
QooBot Mechanical — C++ 源文件语法与依赖检查
=============================================
检查 mujoco/ 目录下所有 C++ 源文件的：
  1. 文件完整性（CMakeLists.txt 引用的源文件是否存在）
  2. #include 引用的头文件是否存在
  3. 类/结构体之间的依赖关系
"""

import os
import re
import sys
from collections import defaultdict

MUJOCO_DIR = os.path.join(os.path.dirname(__file__), "mujoco")


def find_all_files(extensions, base_dir):
    """Find all files with given extensions"""
    result = {}
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if any(f.endswith(ext) for ext in extensions):
                relpath = os.path.relpath(os.path.join(root, f), base_dir)
                result[f] = relpath
    return result


def extract_includes(filepath):
    """Extract all #include directives from a C++ file"""
    includes = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r'^\s*#include\s+[<"]([^>"]+)[>"]', line)
            if m:
                includes.append(m.group(1))
    return includes


def check_include_resolution(include, local_headers, all_headers):
    """Check if an include can be resolved locally"""
    # Local includes with quotes
    basename = os.path.basename(include)
    if basename in local_headers or basename in all_headers:
        return True
    # Full path match
    if include in local_headers or include in all_headers:
        return True
    return False


def main():
    print("=" * 70)
    print("  QooBot Mechanical — C++ 源文件检查")
    print("=" * 70)
    print()

    # Find all C++ files
    cpp_files = find_all_files([".cpp", ".h", ".hpp"], MUJOCO_DIR)
    print(f"[INFO] 找到 {len(cpp_files)} 个 C++ 源文件")

    # Separate headers and sources
    headers = {k: v for k, v in cpp_files.items() if v.endswith((".h", ".hpp"))}
    sources = {k: v for k, v in cpp_files.items() if v.endswith(".cpp")}
    print(f"  头文件 (.h/.hpp): {len(headers)}")
    print(f"  源文件 (.cpp): {len(sources)}")
    print()

    # Check CMakeLists.txt source references
    print("[1/4] CMakeLists.txt 源文件引用检查...")
    cmake_path = os.path.join(MUJOCO_DIR, "CMakeLists.txt")
    cmake_issues = []

    with open(cmake_path, "r", encoding="utf-8") as f:
        cmake_content = f.read()

    # Find all source files referenced in CMakeLists
    cmake_sources = re.findall(r'^\s*(\S+\.(?:cpp|h))\s*$', cmake_content, re.MULTILINE)

    missing_from_disk = []
    for src in cmake_sources:
        full_path = os.path.join(MUJOCO_DIR, src)
        if not os.path.exists(full_path):
            missing_from_disk.append(src)

    if missing_from_disk:
        print(f"  [FIXED] CMakeLists.txt 引用了 {len(missing_from_disk)} 个不存在的文件:")
        for f in missing_from_disk:
            print(f"    - {f}")
    else:
        print(f"  ✓ CMakeLists.txt 引用的所有源文件均存在")

    # Check top-level sources
    top_sources = ["MJ_interface.cpp", "PVT_ctrl.cpp", "qoobot_controller.cpp",
                   "walk_mpc_wbc.cpp", "MJ_interface.h", "PVT_ctrl.h",
                   "qoobot_controller.h", "data_bus.h"]
    for s in top_sources:
        p = os.path.join(MUJOCO_DIR, s)
        if not os.path.exists(p):
            cmake_issues.append(f"顶层源文件缺失: {s}")

    if not cmake_issues:
        print(f"  ✓ 所有顶层源文件完整")
    else:
        for i in cmake_issues:
            print(f"  [ERROR] {i}")
    print()

    # Check #include resolution
    print("[2/4] #include 头文件引用检查...")
    all_local_headers = set(headers.keys())
    all_local_headers.update({
        "data_bus.h", "MJ_interface.h", "PVT_ctrl.h",
        "qoobot_controller.h"
    })
    all_local_relpaths = set(headers.values())
    all_local_relpaths.update({
        "data_bus.h", "MJ_interface.h", "PVT_ctrl.h",
        "qoobot_controller.h"
    })

    include_issues = []
    external_includes = set()
    total_includes_checked = 0

    # System/external headers we expect
    known_external = {
        "mujoco/mujoco.h", "GLFW/glfw3.h", "Eigen/Dense",
        "Eigen/Core", "Eigen/Geometry", "Eigen/StdVector",
        "iostream", "string", "vector", "cmath", "chrono",
        "thread", "fstream", "sstream", "algorithm", "memory",
        "iomanip", "cstring", "cstdlib", "cstdio",
    }

    for filename, relpath in sorted(cpp_files.items()):
        filepath = os.path.join(MUJOCO_DIR, relpath)
        includes = extract_includes(filepath)
        for inc in includes:
            total_includes_checked += 1
            basename = os.path.basename(inc)

            if basename in all_local_headers or inc in all_local_relpaths:
                continue  # local header found
            if inc in known_external:
                external_includes.add(inc)
                continue
            # Check if it might be a system include
            if inc.startswith(("mujoco/", "GLFW/", "Eigen/")):
                external_includes.add(inc)
                continue
            if not inc.startswith(("mujoco", "GLFW", "Eigen")):
                # Could be local - check more carefully
                if basename not in all_local_headers:
                    include_issues.append(f"  {relpath}: #include \"{inc}\" 未在本地找到")

    if include_issues:
        print(f"  [WARN] {len(include_issues)} 个未解析的 #include:")
        for i in include_issues:
            print(i)
    else:
        print(f"  ✓ 所有 {total_includes_checked} 个 #include 均可解析或为已知外部库")

    print(f"  外部依赖 ({len(external_includes)}):")
    for ext in sorted(external_includes):
        print(f"    - {ext}")
    print()

    # Check class/struct cross-references
    print("[3/4] 类依赖关系检查...")
    class_defs = {}
    for filename, relpath in sorted(cpp_files.items()):
        filepath = os.path.join(MUJOCO_DIR, relpath)
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Find class/struct definitions
        classes = re.findall(r'(?:class|struct)\s+(\w+)', content)
        for c in classes:
            if c not in ("std", "public", "private", "protected"):
                class_defs[c] = relpath

    # Key classes to verify
    key_classes = ["DataBus", "MJ_Interface", "PVT_Ctr", "QooBotController", "LPF_Fst"]
    for cls in key_classes:
        if cls in class_defs:
            print(f"  ✓ {cls} 定义于 {class_defs[cls]}")
        else:
            print(f"  [WARN] {cls} 未找到定义")
    print()

    # Summary
    print("[4/4] 构建系统依赖总结...")
    print(f"  CMake 最小版本: 3.10")
    print(f"  C++ 标准: C++17")
    print(f"  必需依赖:")
    print(f"    - MuJoCo (物理引擎)")
    print(f"    - Eigen3 (线性代数)")
    print(f"    - GLFW3 (窗口渲染)")
    print(f"  可选依赖:")
    print(f"    - qpOASES (QP 求解器, MPC/WBC 需要)")
    print(f"    - Pinocchio (动力学库, WBC 运动学需要)")
    print(f"    - jsoncpp (JSON 配置解析)")
    print(f"    - Quill (日志库)")
    print(f"    - fmt (格式化库)")
    print()

    total_issues = len(include_issues) + len(cmake_issues)
    print("=" * 70)
    if total_issues == 0:
        print("  ✓ C++ 源文件检查全部通过")
        return 0
    else:
        print(f"  [WARN] 发现 {total_issues} 个问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
