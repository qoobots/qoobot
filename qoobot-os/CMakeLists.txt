# ============================================================
# QooBot-OS — 顶层 CMake Superbuild
# 统一管理 qoobot-os 下各 C++ 子项目的构建
# ============================================================
cmake_minimum_required(VERSION 3.25)
project(qoobot-os
    VERSION 0.1.0
    DESCRIPTION "QooBot Humanoid Robot Operating System"
    LANGUAGES CXX C
)

# ── 全局编译设置 ──────────────────────────────────────────
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(WIN32)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# ── 子项目开关 ────────────────────────────────────────────
option(QOOBOT_BUILD_ALL     "Build all available subprojects"           OFF)
option(QOOBOT_BUILD_CORE    "Build QooCore AI inference engine"         OFF)
option(QOOBOT_BUILD_HAL     "Build QooBody HAL (mechanical/sensor/...)" OFF)
option(QOOBOT_BUILD_SERVICES "Build QooSvc system services"             OFF)
option(QOOBOT_BUILD_STORE   "Build QooStore edge runtime"               OFF)
option(QOOBOT_BUILD_TESTS   "Enable CTest for subprojects"              ON)

# QOOBOT_BUILD_ALL 快捷开关
if(QOOBOT_BUILD_ALL)
    set(QOOBOT_BUILD_CORE    ON)
    set(QOOBOT_BUILD_HAL     ON)
    set(QOOBOT_BUILD_SERVICES ON)
    set(QOOBOT_BUILD_STORE   ON)
endif()

# ── 输出目录统一 ──────────────────────────────────────────
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

message(STATUS "QooBot-OS ${PROJECT_VERSION} — CMake Superbuild")
message(STATUS "  Build type:  ${CMAKE_BUILD_TYPE}")
message(STATUS "  C++ standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Install prefix: ${CMAKE_INSTALL_PREFIX}")

# ── 子项目：QooCore (ai-engine) ──────────────────────────
if(QOOBOT_BUILD_CORE)
    message(STATUS "[QooCore]   Enabling ai-engine build")
    add_subdirectory(ai-engine)
endif()

# ── 子项目：QooBody HAL ──────────────────────────────────
if(QOOBOT_BUILD_HAL)
    message(STATUS "[QooBody]   Enabling HAL build")
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/hal/mechanical/CMakeLists.txt")
        # HAL 各子模块由 hal/ 自身 CMakeLists 管理
        add_subdirectory(hal)
    else()
        message(WARNING "[QooBody] No top-level HAL CMakeLists.txt found, "
                        "build individual modules directly.")
    endif()
endif()

# ── 子项目：QooSvc (services) ────────────────────────────
if(QOOBOT_BUILD_SERVICES)
    message(STATUS "[QooSvc]    Enabling services build")
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/services/CMakeLists.txt")
        add_subdirectory(services)
    else()
        message(STATUS "[QooSvc]    No CMakeLists.txt, skipping (Python-only or not yet ready)")
    endif()
endif()

# ── 子项目：QooStore ─────────────────────────────────────
if(QOOBOT_BUILD_STORE)
    message(STATUS "[QooStore]  Enabling store build")
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/store/CMakeLists.txt")
        add_subdirectory(store)
    else()
        message(STATUS "[QooStore]  No CMakeLists.txt, skipping")
    endif()
endif()

# ── 构建摘要 ─────────────────────────────────────────────
message(STATUS "")
message(STATUS "========================================")
message(STATUS "  QooBot-OS Build Configuration Summary")
message(STATUS "  QooCore  (ai-engine): ${QOOBOT_BUILD_CORE}")
message(STATUS "  QooBody  (hal):       ${QOOBOT_BUILD_HAL}")
message(STATUS "  QooSvc   (services):  ${QOOBOT_BUILD_SERVICES}")
message(STATUS "  QooStore (store):     ${QOOBOT_BUILD_STORE}")
message(STATUS "  QooBrain (brain):     使用 colcon build 或 pip install (非 CMake)")
message(STATUS "========================================")
