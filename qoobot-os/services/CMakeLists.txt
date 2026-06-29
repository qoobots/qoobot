cmake_minimum_required(VERSION 3.22)
project(qoosvc VERSION 0.3.0 LANGUAGES CXX)

# ============================================================================
# qoosvc — QooBot 机器人端系统服务
# 运行位置：机器人计算平台 (非云端)
# 技术栈：C++17 + Python 3.11
# 通信：通过 DDS / iceoryx2 与 qoobrain 交互
# ============================================================================

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# CMake 模块路径
list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)

# 查找可选依赖
find_package(DDS QUIET)
find_package(Iceoryx QUIET)

# 编译选项
include(cmake/CompilerWarnings.cmake)

# 公共头文件目录
set(QOOSVC_INCLUDE_DIR ${CMAKE_SOURCE_DIR}/include)

# 公共库（header-only 接口）
add_library(qoosvc_common INTERFACE)
target_include_directories(qoosvc_common INTERFACE
    ${QOOSVC_INCLUDE_DIR}
)

# 子服务模块（各模块独立编译为共享库）
# P0 核心服务
add_subdirectory(src/svc_manager)
add_subdirectory(src/svc_voice)
add_subdirectory(src/svc_navigation)
add_subdirectory(src/svc_diagnostics)

# P1 服务
add_subdirectory(src/svc_spatial)
add_subdirectory(src/svc_hmi)
add_subdirectory(src/svc_charging)
add_subdirectory(src/svc_people)
add_subdirectory(src/svc_multi_robot)
add_subdirectory(src/svc_remote)
add_subdirectory(src/svc_video)

# 测试
enable_testing()
add_subdirectory(test)

# 安装配置
install(DIRECTORY config/ DESTINATION etc/qoosvc
    FILES_MATCHING PATTERN "*.yaml"
)

message(STATUS "====================================================")
message(STATUS "qoosvc v${PROJECT_VERSION} — 机器人端系统服务 (C++17)")
message(STATUS "  运行位置: 机器人计算平台")
message(STATUS "  通信方式: DDS / iceoryx2 → qoobrain")
message(STATUS "  构建系统: CMake ${CMAKE_VERSION}")
if(DDS_FOUND)
    message(STATUS "  DDS 支持: 已启用 (${DDS_INCLUDE_DIR})")
else()
    message(STATUS "  DDS 支持: 未找到 — 使用 stub IPC")
endif()
message(STATUS "====================================================")
