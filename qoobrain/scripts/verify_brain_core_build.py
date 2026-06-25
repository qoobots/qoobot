#!/usr/bin/env python3
"""
brain_core C++ 编译验证脚本
=============================
验证 brain_core 模块的构建完整性和潜在问题，无需实际编译器。

检查项目：
  1. CMakeLists.txt 中引用的源文件是否全部存在于磁盘
  2. 头文件与实现文件的配对一致性
  3. package.xml 与 CMakeLists.txt 的 find_package 依赖声明一致性
  4. CMakeLists.txt 语法特征（未使用变量、缺失标志检查等）
  5. gRPC/proto 生成代码目录状态
  6. 测试文件与 CMakeLists.txt test/CMakeLists.txt 一致性
  7. 配置文件引用完整性

用法：
  python scripts/verify_brain_core_build.py [--ci] [--verbose]
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# ── Constants ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BRAIN_CORE_DIR = PROJECT_ROOT / "brain_core"
CMAKE_FILE = BRAIN_CORE_DIR / "CMakeLists.txt"
PACKAGE_XML = BRAIN_CORE_DIR / "package.xml"
TEST_CMAKE = BRAIN_CORE_DIR / "test" / "CMakeLists.txt"
PROTO_GEN_DIR = PROJECT_ROOT / "brain_proto" / "gen" / "cpp"
LAUNCH_FILE = BRAIN_CORE_DIR / "launch" / "brain_core.launch.py"


class Colors:
    """ANSI terminal colors."""
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def icon(ok: bool) -> str:
    return f"{Colors.GREEN}✓{Colors.RESET}" if ok else f"{Colors.RED}✗{Colors.RESET}"


def warn_icon() -> str:
    return f"{Colors.YELLOW}⚠{Colors.RESET}"


# ── Check 1: Source file existence ─────────────────────────
def parse_cmake_source_list(cmake_path: Path) -> List[str]:
    """Extract the list of .cpp files from add_library(brain_core_lib ...)."""
    content = cmake_path.read_text(encoding="utf-8")
    # Find the add_library block for brain_core_lib
    match = re.search(
        r'add_library\(brain_core_lib\s+STATIC\s*(.*?)\)',
        content, re.DOTALL
    )
    if not match:
        print(f"{Colors.RED}ERROR: Could not find add_library(brain_core_lib ...) block{Colors.RESET}")
        return []

    block = match.group(1)
    sources = re.findall(r'src/[\w/]+\.cpp', block)
    return sorted(set(sources))


def check_source_files_exist(cmake_sources: List[str]) -> Tuple[int, int]:
    """Verify every .cpp referenced in CMakeLists.txt exists on disk."""
    missing = 0
    found = 0
    for src in cmake_sources:
        full = BRAIN_CORE_DIR / src
        if full.is_file():
            found += 1
        else:
            print(f"  {icon(False)} Missing: {src}")
            missing += 1
    return found, missing


# ── Check 2: Header / implementation pairing ───────────────
def scan_module(module_dir: Path, module_name: str) -> Dict[str, Set[str]]:
    """Scan a module directory for .h and .cpp files."""
    result: Dict[str, Set[str]] = {"headers": set(), "impls": set()}
    include_root = BRAIN_CORE_DIR / "include" / "brain_core" / module_dir
    src_root = BRAIN_CORE_DIR / "src" / module_dir

    if include_root.is_dir():
        for h in include_root.rglob("*.h"):
            result["headers"].add(h.stem)
    if src_root.is_dir():
        for cpp in src_root.rglob("*.cpp"):
            result["impls"].add(cpp.stem)

    return result


def check_header_impl_pairing() -> List[str]:
    """Check that public headers generally have corresponding implementations."""
    warnings: List[str] = []

    modules = [
        "ros2_bridge", "event_bus", "hal_interface",
        "safety_monitor", "motion_planner", "behavior_engine",
        "grpc_server", "utils"
    ]

    for mod in modules:
        scan = scan_module(mod, mod)
        headers = scan["headers"]
        impls = scan["impls"]

        # Headers without a matching .cpp (might be valid: template-only, inline-only)
        orphan_headers = headers - impls - {"core_types"}
        for oh in sorted(orphan_headers):
            warnings.append(
                f"  {warn_icon()} Header without matching .cpp: include/brain_core/{mod}/{oh}.h"
            )

    return warnings


# ── Check 3: package.xml ↔ CMakeLists.txt dependency consistency ──
def parse_package_deps(pkg_path: Path) -> Set[str]:
    """Extract <depend> entries from package.xml."""
    content = pkg_path.read_text(encoding="utf-8")
    deps = set()
    for tag in ["depend", "buildtool_depend"]:
        for m in re.finditer(rf'<{tag}[^>]*>([^<]+)</{tag}>', content):
            deps.add(m.group(1))
    # Filter out build tool deps that don't map to find_package
    deps.discard("ament_cmake")
    return deps


def parse_cmake_find_packages(cmake_path: Path) -> Set[str]:
    """Extract find_package entries from CMakeLists.txt."""
    content = cmake_path.read_text(encoding="utf-8")
    pkgs = set()
    for m in re.finditer(r'find_package\((\S+)', content):
        name = m.group(1)
        # Normalize: drop version requirements
        pkgs.add(name.split()[0] if " " in name else name)
    return pkgs


def check_dependency_consistency() -> List[str]:
    """Compare package.xml deps with CMakeLists.txt find_package calls."""
    issues: List[str] = []

    pkg_deps = parse_package_deps(PACKAGE_XML)
    cmake_deps = parse_cmake_find_packages(CMAKE_FILE)

    # Remove non-Rosdep for normalization
    # package.xml uses rosdep keys (underscores), cmake uses CMake names
    # Common mappings:
    rosdep_to_cmake = {
        "rclcpp": "rclcpp",
        "rclcpp_lifecycle": "rclcpp_lifecycle",
        "rclcpp_action": "rclcpp_action",
        "std_msgs": "std_msgs",
        "geometry_msgs": "geometry_msgs",
        "sensor_msgs": "sensor_msgs",
        "visualization_msgs": "visualization_msgs",
        "nav_msgs": "nav_msgs",
        "trajectory_msgs": "trajectory_msgs",
        "tf2": "tf2",
        "tf2_geometry_msgs": "tf2_geometry_msgs",
        "builtin_interfaces": "builtin_interfaces",
        "moveit_core": "moveit_core",
        "moveit_ros_planning_interface": "moveit_ros_planning_interface",
        "fcl": "fcl",
        "protobuf": "Protobuf",
        "ament_cmake_gtest": "ament_cmake_gtest",
    }

    # For gRPC, it's not a rosdep key but required in CMake
    special_cmake = {"gRPC", "Protobuf", "ament_cmake_gtest"}

    for rosdep in sorted(pkg_deps):
        cmake_name = rosdep_to_cmake.get(rosdep, rosdep)
        if cmake_name not in cmake_deps and cmake_name not in special_cmake:
            issues.append(
                f"  {icon(False)} package.xml has <depend>{rosdep}</depend> but CMakeLists.txt lacks find_package({cmake_name})"
            )

    return issues


# ── Check 4: CMakeLists.txt code quality ───────────────────
def check_cmake_quality() -> List[str]:
    """Check for common CMake issues."""
    issues: List[str] = []
    content = CMAKE_FILE.read_text(encoding="utf-8")

    # GLOB_RECURSE without usage
    if "GLOB_RECURSE" in content and "BRAIN_CORE_SOURCES" in content:
        if "BRAIN_CORE_SOURCES" not in re.sub(
            r'file\(GLOB_RECURSE BRAIN_CORE_SOURCES.*?\)',
            '', content, flags=re.DOTALL
        ):
            # After removing the GLOB_RECURSE, still has BRAIN_CORE_SOURCES?
            # No — the GLOB_RECURSE defines it, but it's not used elsewhere
            issues.append(
                f"  {warn_icon()} GLOB_RECURSE creates BRAIN_CORE_SOURCES but variable is never used in target_sources() or add_library()"
            )

    # SKIP_ROS2 flag check
    if "BRAIN_CORE_SKIP_ROS2" not in content:
        issues.append(
            f"  {warn_icon()} CI uses -DBRAIN_CORE_SKIP_ROS2=ON but CMakeLists.txt never checks this variable — ROS 2 deps always required"
        )

    # Missing include/library hookup
    extra_finds = ["visualization_msgs", "builtin_interfaces"]
    for pkg in extra_finds:
        if f"find_package({pkg}" in content:
            has_include = f"${{{pkg}_INCLUDE_DIRS}}" in content or \
                          f"${{{pkg}_INCLUDE_DIR}}" in content
            has_lib = f"${{{pkg}_LIBRARIES}}" in content or \
                      f"${{{pkg}_LIBRARY}}" in content
            if not has_include and not has_lib:
                issues.append(
                    f"  {warn_icon()} find_package({pkg}) found but {pkg}_INCLUDE_DIRS / {pkg}_LIBRARIES not used in include_directories or target_link_libraries"
                )

    # gRPC client: check if listed in add_library block
    if "src/grpc_client/brain_ai_client.cpp" in content:
        # Check if it's INSIDE the add_library(brain_core_lib ...) block
        lib_match = re.search(
            r'add_library\(brain_core_lib\s+STATIC\s*(.*?)\)',
            content, re.DOTALL
        )
        if lib_match and "src/grpc_client/brain_ai_client.cpp" not in lib_match.group(1):
            issues.append(
                f"  {icon(False)} src/grpc_client/brain_ai_client.cpp exists but is not listed in add_library(brain_core_lib ...)"
            )

    return issues


# ── Check 5: Proto generation status ───────────────────────
def check_proto_gen() -> List[str]:
    """Check if proto-generated C++ files exist."""
    info: List[str] = []
    if PROTO_GEN_DIR.is_dir():
        pb_h_files = list(PROTO_GEN_DIR.rglob("*.pb.h"))
        pb_cc_files = list(PROTO_GEN_DIR.rglob("*.pb.cc"))
        grpc_h_files = list(PROTO_GEN_DIR.rglob("*.grpc.pb.h"))
        grpc_cc_files = list(PROTO_GEN_DIR.rglob("*.grpc.pb.cc"))
        total = len(pb_h_files) + len(pb_cc_files) + len(grpc_h_files) + len(grpc_cc_files)
        if total > 0:
            info.append(f"  {icon(True)} Proto gen dir: {PROTO_GEN_DIR}")
            info.append(f"     .pb.h:  {len(pb_h_files)}  | .pb.cc:  {len(pb_cc_files)}")
            info.append(f"     .grpc.pb.h: {len(grpc_h_files)}  | .grpc.pb.cc: {len(grpc_cc_files)}")
        else:
            info.append(f"  {warn_icon()} Proto gen dir exists but is empty: {PROTO_GEN_DIR}")
            info.append(f"     Run: bash brain_proto/scripts/buf_generate.sh  (or python brain_proto/scripts/generate_proto.py)")
    else:
        info.append(f"  {icon(False)} Proto gen dir missing: {PROTO_GEN_DIR}")
        info.append(f"     Run: python brain_proto/scripts/generate_proto.py")
    return info


# ── Check 6: Launch file config references ─────────────────
def check_launch_config_refs() -> List[str]:
    """Verify YAML configs referenced in launch file exist."""
    info: List[str] = []
    if not LAUNCH_FILE.is_file():
        info.append(f"  {icon(False)} Launch file missing: {LAUNCH_FILE}")
        return info

    content = LAUNCH_FILE.read_text(encoding="utf-8")
    # Find all os.path.join(config_dir, ...) patterns to extract relative YAML paths
    yaml_refs_raw = re.findall(
        r"os\.path\.join\(config_dir,\s*['\"]([^'\"]+\.yaml)['\"]\)",
        content
    )
    # Also catch config_dir + subdir patterns: ...join(config_dir, 'safety', 'xxx.yaml')
    nested_refs = re.findall(
        r"os\.path\.join\(config_dir,\s*['\"]([^'\"]+)['\"],\s*['\"]([^'\"]+\.yaml)['\"]\)",
        content
    )

    seen = set()
    for ref in yaml_refs_raw:
        if ref in seen:
            continue
        seen.add(ref)
        full = BRAIN_CORE_DIR / "config" / ref
        if full.is_file():
            info.append(f"  {icon(True)} Launch YAML ref: config/{ref}")
        else:
            info.append(f"  {icon(False)} Launch YAML ref missing: config/{ref}")

    for subdir, yaml_file in nested_refs:
        full_path = f"{subdir}/{yaml_file}"
        if full_path in seen:
            continue
        seen.add(full_path)
        full = BRAIN_CORE_DIR / "config" / subdir / yaml_file
        if full.is_file():
            info.append(f"  {icon(True)} Launch YAML ref: config/{subdir}/{yaml_file}")
        else:
            info.append(f"  {icon(False)} Launch YAML ref missing: config/{subdir}/{yaml_file}")

    return info


# ── Check 7: Test CMakeLists.txt consistency ───────────────
def check_test_cmake() -> List[str]:
    """Verify test/CMakeLists.txt consistency with test files on disk."""
    info: List[str] = []
    if not TEST_CMAKE.is_file():
        main_cmake = CMAKE_FILE.read_text(encoding="utf-8")
        if "add_subdirectory(test)" in main_cmake:
            info.append(
                f"  {icon(False)} test/CMakeLists.txt missing — build will fail with BUILD_TESTING=ON"
            )
        else:
            info.append(f"  {warn_icon()} test/CMakeLists.txt not found (BUILD_TESTING not configured)")
        return info

    content = TEST_CMAKE.read_text(encoding="utf-8")
    # Match ament_add_gtest(test_name ...) — ROS 2 gtest registration
    test_targets = re.findall(r'ament_add_gtest\((\S+)', content)
    if not test_targets:
        # Fallback: plain add_executable
        test_targets = re.findall(r'add_executable\((\S+)', content)
    actual_tests = [
        f.stem for f in BRAIN_CORE_DIR.rglob("test/**/*.cpp")
    ]

    for tgt in test_targets:
        if tgt in actual_tests:
            info.append(f"  {icon(True)} Test target: {tgt}")
        else:
            info.append(f"  {icon(False)} Test target has no .cpp: {tgt}")

    # Check for test files not in CMake
    cmake_test_files = set()
    for m in re.finditer(r'([\w/]+\.cpp)', content):
        cmake_test_files.add(m.group(1).split("/")[-1])  # just the filename
    disk_test_files = {f.name for f in BRAIN_CORE_DIR.rglob("test/**/*.cpp")}
    unused = disk_test_files - cmake_test_files
    if unused:
        for u in sorted(unused):
            info.append(f"  {warn_icon()} Test file not in CMakeLists.txt: {u}")

    return info


# ── Check 8: Header dependency scan ────────────────────────
def check_header_includes() -> List[str]:
    """Scan .cpp files for #include references to self-headers."""
    warnings: List[str] = []
    for cpp_file in BRAIN_CORE_DIR.rglob("src/**/*.cpp"):
        content = cpp_file.read_text(encoding="utf-8")
        # Find the expected self-header based on the file path
        rel = cpp_file.relative_to(BRAIN_CORE_DIR / "src")
        module = rel.parts[0]
        expected_header = f"brain_core/{module}/{cpp_file.stem}.h"

        if f'#include "{expected_header}"' not in content and \
           f"#include <{expected_header}>" not in content:
            # This is a soft warning — some impl files might not need a matching header
            # (e.g. main.cpp, or internal helpers)
            if cpp_file.name not in ("main.cpp",):
                warnings.append(
                    f"  {warn_icon()} {cpp_file.relative_to(BRAIN_CORE_DIR)} does not include its own header: {expected_header}"
                )
    return warnings


# ── Main ───────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="brain_core C++ 编译验证脚本"
    )
    parser.add_argument(
        "--ci", action="store_true",
        help="CI 模式：非交互输出，有错误则返回非零退出码"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="显示详细通过项"
    )
    args = parser.parse_args()

    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  brain_core C++ 编译验证{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print()

    total_errors = 0
    total_warnings = 0

    # ── Check 1: Source files ───────────────────────────────
    print(f"{Colors.BOLD}[1/8] 源文件存在性检查{Colors.RESET}")
    cmake_sources = parse_cmake_source_list(CMAKE_FILE)
    found, missing = check_source_files_exist(cmake_sources)
    print(f"  CMakeLists.txt 引用: {len(cmake_sources)} 个 .cpp 文件")
    if args.verbose:
        for s in cmake_sources:
            print(f"    {icon(True)} {s}")
    else:
        print(f"  {icon(True)} 全部 {found} 个源文件存在" if missing == 0 else "")
    total_errors += missing
    print()

    # ── Check 2: Header/impl pairing ───────────────────────
    print(f"{Colors.BOLD}[2/8] 头文件 / 实现文件配对检查{Colors.RESET}")
    hdr_warnings = check_header_impl_pairing()
    if hdr_warnings:
        for w in hdr_warnings:
            print(w)
        total_warnings += len(hdr_warnings)
    else:
        print(f"  {icon(True)} 所有头文件均有对应实现")
    print()

    # ── Check 3: Dependency consistency ─────────────────────
    print(f"{Colors.BOLD}[3/8] package.xml ↔ CMakeLists.txt 依赖一致性{Colors.RESET}")
    dep_issues = check_dependency_consistency()
    if dep_issues:
        for issue in dep_issues:
            print(issue)
        total_warnings += len(dep_issues)
    else:
        print(f"  {icon(True)} 依赖声明一致")
    print()

    # ── Check 4: CMake quality ──────────────────────────────
    print(f"{Colors.BOLD}[4/8] CMakeLists.txt 代码质量检查{Colors.RESET}")
    cmake_issues = check_cmake_quality()
    if cmake_issues:
        for issue in cmake_issues:
            print(issue)
        total_warnings += len(cmake_issues)
    else:
        print(f"  {icon(True)} CMakeLists.txt 无质量问题")
    print()

    # ── Check 5: Proto generation ───────────────────────────
    print(f"{Colors.BOLD}[5/8] Proto 生成代码状态{Colors.RESET}")
    proto_info = check_proto_gen()
    for line in proto_info:
        print(line)
    if any("false" in line or "missing" in line.lower() for line in proto_info):
        total_warnings += 1
    print()

    # ── Check 6: Launch config refs ─────────────────────────
    print(f"{Colors.BOLD}[6/8] Launch 文件配置引用{Colors.RESET}")
    launch_info = check_launch_config_refs()
    if launch_info:
        for line in launch_info:
            print(line)
    else:
        print(f"  {warn_icon()} Launch 文件不存在或无 YAML 引用")
    print()

    # ── Check 7: Test CMakeLists ────────────────────────────
    print(f"{Colors.BOLD}[7/8] 测试 CMakeLists.txt 一致性{Colors.RESET}")
    test_info = check_test_cmake()
    for line in test_info:
        print(line)
    print()

    # ── Check 8: Self-header includes ───────────────────────
    print(f"{Colors.BOLD}[8/8] 自引用头文件检查{Colors.RESET}")
    include_warnings = check_header_includes()
    if include_warnings:
        for w in include_warnings[:5]:  # Show first 5
            print(w)
        if len(include_warnings) > 5:
            print(f"  ... 及另外 {len(include_warnings) - 5} 个")
        total_warnings += len(include_warnings)
    else:
        print(f"  {icon(True)} 所有 .cpp 均包含对应的自引用头文件")
    print()

    # ── Summary ─────────────────────────────────────────────
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  验证结果汇总{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"  错误: {Colors.RED}{total_errors}{Colors.RESET}")
    print(f"  警告: {Colors.YELLOW}{total_warnings}{Colors.RESET}")

    if total_errors == 0 and total_warnings == 0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}✓ 全部通过 — brain_core 构建配置健康{Colors.RESET}")
    elif total_errors == 0:
        print(f"\n  {Colors.YELLOW}{Colors.BOLD}⚠ 有 {total_warnings} 个警告，不影响编译{Colors.RESET}")
    else:
        print(f"\n  {Colors.RED}{Colors.BOLD}✗ 发现 {total_errors} 个错误，需修复后方可编译{Colors.RESET}")

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
