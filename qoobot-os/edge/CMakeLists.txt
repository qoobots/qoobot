cmake_minimum_required(VERSION 3.22)
project(qooedge VERSION 0.1.0 LANGUAGES CXX)

# ============================================================================
# qooedge — QooBot 边缘计算层
# 运行位置：机器人计算平台 (onboard_core)
# 技术栈：C++17
# 职责：边缘推理运行时、端云任务卸载、数据同步、多机器人Mesh网络
# ============================================================================

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_compile_options(-Wall -Wextra -Wpedantic)

# 公共头文件
set(qooedge_INCLUDE_DIR ${CMAKE_SOURCE_DIR}/include)

add_library(qooedge_common INTERFACE)
target_include_directories(qooedge_common INTERFACE
    ${qooedge_INCLUDE_DIR}
)

# 子模块
add_subdirectory(src/edge_runtime)   # 边缘推理运行时
add_subdirectory(src/edge_offload)   # 端-云任务卸载决策引擎
add_subdirectory(src/edge_sync)      # 端-云数据同步引擎
add_subdirectory(src/edge_mesh)      # 多机器人Mesh网络

# 边缘守护进程主入口
add_executable(qooedge-daemon
    src/main.cpp
)
target_include_directories(qooedge-daemon PRIVATE ${qooedge_INCLUDE_DIR})
target_link_libraries(qooedge-daemon PRIVATE
    qooedge_runtime
    qooedge_offload
    qooedge_sync
    qooedge_mesh
    pthread
)

# 边缘 CLI 工具
add_executable(qooedge-cli
    src/cli/qooedge_cli.cpp
)
target_include_directories(qooedge-cli PRIVATE ${qooedge_INCLUDE_DIR})
target_link_libraries(qooedge-cli PRIVATE
    qooedge_runtime
    qooedge_offload
    pthread
)

enable_testing()
add_subdirectory(test)

message(STATUS "qooedge v${PROJECT_VERSION} — QooBot 边缘计算层 (C++17)")
message(STATUS "  运行位置: 机器人计算平台")
message(STATUS "  职责: 边缘推理 / 任务卸载 / 端云同步 / Mesh网络")
message(STATUS "  入口: qooedge-daemon | qooedge-cli")
