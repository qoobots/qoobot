cmake_minimum_required(VERSION 3.22)
project(qoostore-edge VERSION 0.2.0 LANGUAGES CXX)

# ============================================================================
# qoostore-edge — QooBot 机器人端技能运行环境
# 运行位置：机器人计算平台 (非云端)
# 技术栈：C++17 + Python 3.11
# 职责：技能安装管理、沙箱隔离、权限管控、运行时监控、技能间 IPC、依赖解析
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
    ${CMAKE_SOURCE_DIR}/src/common
)

# 子模块
add_subdirectory(src/skill_manager)    # 技能安装/卸载/更新/启用/停用
add_subdirectory(src/sandbox)          # 技能沙箱隔离
add_subdirectory(src/permission)       # 权限管控
add_subdirectory(src/runtime_monitor)  # 运行时监控
add_subdirectory(src/skill_ipc)        # 技能间通信
add_subdirectory(src/skill_downloader) # 技能下载器
add_subdirectory(src/skill_resolver)   # 技能依赖解析

# 主入口
add_executable(qoostore-daemon
    src/main.cpp
)
target_include_directories(qoostore-daemon PRIVATE
    ${qoostore_EDGE_INCLUDE_DIR}
    ${CMAKE_SOURCE_DIR}/src/common
)
target_link_libraries(qoostore-daemon PRIVATE
    qoostore_skill_manager
    qoostore_sandbox
    qoostore_permission
    qoostore_runtime_monitor
    qoostore_skill_ipc
    qoostore_skill_downloader
    qoostore_edge_resolver
    pthread
)

# CLI 工具
add_executable(qoostore-cli
    src/cli/qoostore_cli.cpp
)
target_include_directories(qoostore-cli PRIVATE
    ${qoostore_EDGE_INCLUDE_DIR}
    ${CMAKE_SOURCE_DIR}/src/common
)
target_link_libraries(qoostore-cli PRIVATE
    qoostore_skill_manager
    qoostore_permission
    qoostore_edge_resolver
    pthread
)

enable_testing()
add_subdirectory(test)

message(STATUS "qoostore-edge v${PROJECT_VERSION} — 机器人端技能运行环境 (C++17)")
message(STATUS "  运行位置: 机器人计算平台")
message(STATUS "  职责: 技能安装 / 沙箱隔离 / 权限管控 / 运行时监控 / 依赖解析")
message(STATUS "  入口: qoostore-daemon | qoostore-cli")
