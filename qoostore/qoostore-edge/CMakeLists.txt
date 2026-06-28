cmake_minimum_required(VERSION 3.22)
project(qoostore-edge VERSION 0.1.0 LANGUAGES CXX)

# ============================================================================
# qoostore-edge — QooBot 机器人端技能运行环境
# 运行位置：机器人计算平台 (非云端)
# 技术栈：C++17 + Python 3.11
# 职责：技能安装管理、沙箱隔离、权限管控、运行时监控、技能间 IPC
# ============================================================================

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_compile_options(-Wall -Wextra -Wpedantic)

# 公共头文件
set(qoostore_EDGE_INCLUDE_DIR ${CMAKE_SOURCE_DIR}/include)

add_library(qoostore_edge_common INTERFACE)
target_include_directories(qoostore_edge_common INTERFACE
    ${qoostore_EDGE_INCLUDE_DIR}
)

# 子模块（按需添加）
# add_subdirectory(src/skill_manager)    # 技能安装/卸载/更新/启用/停用
# add_subdirectory(src/sandbox)          # 技能沙箱隔离
# add_subdirectory(src/permission)       # 权限管控
# add_subdirectory(src/runtime_monitor)  # 运行时监控
# add_subdirectory(src/skill_ipc)        # 技能间通信

enable_testing()
# add_subdirectory(test)

message(STATUS "qoostore-edge v${PROJECT_VERSION} — 机器人端技能运行环境 (C++17)")
message(STATUS "  运行位置: 机器人计算平台")
message(STATUS "  职责: 技能安装 / 沙箱隔离 / 权限管控 / 运行时监控")
