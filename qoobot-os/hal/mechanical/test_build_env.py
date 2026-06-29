#!/usr/bin/env python3
"""
QooBot Mechanical — C++ 编译环境检查
========================================
检测 MuJoCo 仿真工程的编译依赖是否已安装

检查项：
  1. C++ 编译器 (g++ / clang++ / MSVC)
  2. CMake
  3. MuJoCo
  4. Eigen3
  5. GLFW3
  6. qpOASES (可选)
  7. Pinocchio (可选)
  8. jsoncpp (可选)
  9. Quill (可选)
  10. fmt (可选)
"""

import subprocess
import sys
import os
import platform

RESULTS = {}


def run_cmd(cmd, desc):
    """运行命令并返回成功与否"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout.strip()[:200]
    except Exception as e:
        return False, str(e)


def check(name, cmd, required=True, version_flag=None):
    """统一检查项"""
    print(f"\n  [{name}]")
    ok, output = run_cmd(cmd, name)
    if version_flag and ok:
        ok_v, vout = run_cmd(version_flag, name + "-version")
        if ok_v:
            output = vout

    RESULTS[name] = {"ok": ok, "required": required, "output": output}

    if ok:
        first_line = output.split("\n")[0] if output else ""
        print(f"    ✓ 已安装  {first_line}")
    else:
        tag = "必需" if required else "可选"
        print(f"    ✗ 未安装 ({tag})")
    return ok


def check_headers():
    """检查 C++ 头文件"""
    print("\n--- C++ 头文件可用性 ---")

    includes = {
        "Eigen3": ("#include <Eigen/Core>", "Eigen/Core"),
        "GLFW3": ("#include <GLFW/glfw3.h>", "GLFW/glfw3.h"),
    }

    for name, (include_stmt, path) in includes.items():
        test_code = f'{include_stmt}\nint main() {{ return 0; }}'
        # 尝试用 g++ 编译一个最小文件
        cmd = f'echo {test_code} | g++ -x c++ - -o /dev/null -fsyntax-only 2>&1'
        ok, output = run_cmd(cmd, name)
        RESULTS[f"{name}-header"] = {"ok": ok, "required": False, "output": output}
        if ok:
            print(f"    ✓ {name} 头文件可用")
        else:
            print(f"    ✗ {name} 头文件不可用")


def main():
    print("=" * 60)
    print("  QooBot MuJoCo 仿真 — 编译环境检查")
    print("=" * 60)

    system = platform.system()
    print(f"\n  操作系统: {system} ({platform.release()})")
    print(f"  Python: {sys.version.split()[0]}")

    print("\n--- 编译器与构建工具 ---")
    if system == "Windows":
        check("MSVC (cl)", "where cl 2>&1", required=True)
        check("CMake", "cmake --version 2>&1", required=True)
    else:
        check("g++", "g++ --version 2>&1", required=True)
        check("CMake", "cmake --version 2>&1", required=True)

    print("\n--- 核心依赖 (必需) ---")
    check("MuJoCo", "pkg-config --modversion mujoco 2>&1", required=True)
    check("Eigen3", "pkg-config --modversion eigen3 2>&1", required=True)
    check("GLFW3", "pkg-config --modversion glfw3 2>&1", required=True)

    print("\n--- 可选依赖 ---")
    check("qpOASES", "pkg-config --modversion qpOASES 2>&1", required=False)
    check("Pinocchio", "pkg-config --modversion pinocchio 2>&1", required=False)
    check("jsoncpp", "pkg-config --modversion jsoncpp 2>&1", required=False)
    check("fmt", "pkg-config --modversion fmt 2>&1", required=False)
    check("Quill", "pkg-config --modversion quill 2>&1", required=False)

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"  编译环境检查结果")
    print(f"{'=' * 60}")

    required_ok = all(v["ok"] for k, v in RESULTS.items() if v["required"])
    optional_ok = [k for k, v in RESULTS.items() if not v["required"] and v["ok"]]
    optional_missing = [k for k, v in RESULTS.items() if not v["required"] and not v["ok"]]

    print(f"\n  必需依赖: {'✓ 全部就绪' if required_ok else '✗ 有缺失'}")
    if optional_ok:
        print(f"  已安装可选依赖: {', '.join(optional_ok)}")
    if optional_missing:
        print(f"  缺失可选依赖: {', '.join(optional_missing)}")

    if not required_ok:
        print(f"\n  缺失的必需依赖安装方法 (Ubuntu):")
        missing_req = [k for k, v in RESULTS.items() if v["required"] and not v["ok"]]
        for dep in missing_req:
            if dep == "MuJoCo":
                print(f"    MuJoCo: 从 https://mujoco.org/ 下载")
            elif dep == "Eigen3":
                print(f"    Eigen3: sudo apt install libeigen3-dev")
            elif dep == "GLFW3":
                print(f"    GLFW3: sudo apt install libglfw3-dev")
            elif dep == "g++":
                print(f"    g++: sudo apt install build-essential")
            elif dep == "CMake":
                print(f"    CMake: sudo apt install cmake")
            elif dep == "MSVC (cl)":
                print(f"    MSVC: 安装 Visual Studio Build Tools")

    return 0 if required_ok else 1


if __name__ == "__main__":
    sys.exit(main())
