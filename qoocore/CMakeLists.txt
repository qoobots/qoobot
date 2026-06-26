cmake_minimum_required(VERSION 3.25)
project(qoocore VERSION 0.1.0 LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ── 编译选项 ────────────────────────────────────────────────────────────
option(QOOCORE_BUILD_PYTHON    "Build Python bindings (pybind11)"  OFF)
option(QOOCORE_BUILD_CLI       "Build CLI tool"                   ON)
option(QOOCORE_BUILD_TESTS     "Build unit tests (GTest)"         ON)
option(QOOCORE_BUILD_BENCHMARKS "Build benchmarks"               OFF)
option(QOOCORE_BUILD_SAMPLES   "Build sample programs"            OFF)

# 后端开关
option(QOOCORE_ENABLE_NPU_QNN   "Enable Qualcomm QNN HAL"    OFF)
option(QOOCORE_ENABLE_NPU_BPU   "Enable Horizon BPU HAL"     OFF)
option(QOOCORE_ENABLE_NPU_RKNN  "Enable Rockchip RKNN HAL"  OFF)
option(QOOCORE_ENABLE_GPU_CUDA  "Enable NVIDIA CUDA backend" OFF)
option(QOOCORE_ENABLE_GPU_OPENCL "Enable OpenCL backend"     OFF)
option(QOOCORE_ENABLE_DSP        "Enable DSP backend"         OFF)

# 高级选项
option(QOOCORE_ENABLE_PROFILING "Enable built-in profiler"    ON)
option(QOOCORE_ENABLE_ION       "Enable ION/DMA-BUF support" ON)
option(QOOCORE_USE_MLIR        "Use MLIR as IR backend"     OFF)

# ── 依赖管理：FetchContent 自动拉取 ──────────────────────────────────
include(FetchContent)
include(GNUInstallDirs)

# 辅助宏：尝试 find_package，失败则用 FetchContent
macro(qoocore_find_or_fetch dep_name fetch_name)
    find_package(${dep_name} QUIET)
    if(NOT ${dep_name}_FOUND)
        message(STATUS "${dep_name} not found, fetching via FetchContent...")
        FetchContent_Declare(${fetch_name} ${ARGN})
        FetchContent_MakeAvailable(${fetch_name})
    endif()
endmacro()

# FlatBuffers (必需)
# 先设置 FlatBuffers 编译选项（禁用 samples/tests，加速构建）
set(FLATBUFFERS_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(FLATBUFFERS_BUILD_SAMPLES OFF CACHE BOOL "" FORCE)
set(FLATBUFFERS_INSTALL OFF CACHE BOOL "" FORCE)

find_package(FlatBuffers 24.0 QUIET)
if(NOT FlatBuffers_FOUND)
    message(STATUS "FlatBuffers not found, fetching v24.3.25...")
    FetchContent_Declare(
        flatbuffers
        GIT_REPOSITORY https://github.com/google/flatbuffers.git
        GIT_TAG        v24.3.25
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(flatbuffers)
    set(FLATBUFFERS_FLATC_EXECUTABLE ${flatbuffers_BINARY_DIR}/flatc CACHE FILEPATH "")
endif()

# spdlog (必需)
find_package(spdlog 1.14 QUIET)
if(NOT spdlog_FOUND)
    message(STATUS "spdlog not found, fetching v1.14.1...")
    FetchContent_Declare(
        spdlog
        GIT_REPOSITORY https://github.com/gabime/spdlog.git
        GIT_TAG        v1.14.1
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(spdlog)
endif()

# yaml-cpp (必需)
find_package(yaml-cpp 0.8 QUIET)
if(NOT yaml-cpp_FOUND)
    message(STATUS "yaml-cpp not found, fetching latest...")
    FetchContent_Declare(
        yaml-cpp
        GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
        GIT_TAG        master
        GIT_SHALLOW    FALSE
    )
    FetchContent_MakeAvailable(yaml-cpp)
endif()

# nlohmann/json (用于 JSON 处理)
find_package(nlohmann_json 3.11 QUIET)
if(NOT nlohmann_json_FOUND)
    message(STATUS "nlohmann_json not found, fetching v3.11.3...")
    FetchContent_Declare(
        nlohmann_json
        GIT_REPOSITORY https://github.com/nlohmann/json.git
        GIT_TAG        v3.11.3
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(nlohmann_json)
endif()

# Threads
find_package(Threads REQUIRED)

# ONNX Runtime（可选，编译工具链需要）
find_package(ONNXRuntime 1.18 QUIET)
if(ONNXRuntime_FOUND)
    add_compile_definitions(QOOCORE_ENABLE_ONNX=1)
else()
    message(WARNING "ONNX Runtime not found — model import will be disabled")
endif()

# ── 源文件定义 ──────────────────────────────────────────────────────────
# 核心源文件
set(QOOCORE_CORE_SOURCES
    src/core/result.cpp
    src/core/dtype.cpp
    src/core/tensor.cpp
)

# 引擎源文件
set(QOOCORE_ENGINE_SOURCES
    src/engine/engine.cpp
    src/engine/model_manager.cpp
    src/engine/backend_manager.cpp
)

# 编译器源文件
set(QOOCORE_COMPILER_SOURCES
    src/compiler/importer/onnx_importer.cpp
    src/compiler/package/qoomodel_writer.cpp
    src/compiler/package/qoomodel_reader.cpp
)

# 运行时源文件（按后端条件编译）
set(QOOCORE_RUNTIME_SOURCES
    # 基础运行时
    src/runtime/hal/npu_hal_loader.cpp
)
if(QOOCORE_ENABLE_NPU_QNN)
    list(APPEND QOOCORE_RUNTIME_SOURCES src/runtime/hal/qnn_hal.cpp)
endif()

# 内存管理源文件
set(QOOCORE_MEMORY_SOURCES
    src/memory/ion/ion_allocator.cpp
)

# 硬件探测源文件
set(QOOCORE_HARDWARE_SOURCES
    src/hardware/probe/hardware_probe.cpp
)

# # 配置管理（暂时跳过，后续实现）
# set(QOOCORE_CONFIG_SOURCES
#     src/config/config_manager.cpp
# )

# 所有源文件合并
set(QOOCORE_ALL_SOURCES
    ${QOOCORE_CORE_SOURCES}
    ${QOOCORE_ENGINE_SOURCES}
    ${QOOCORE_COMPILER_SOURCES}
    ${QOOCORE_RUNTIME_SOURCES}
    ${QOOCORE_MEMORY_SOURCES}
    ${QOOCORE_HARDWARE_SOURCES}
    ${QOOCORE_CONFIG_SOURCES}
)

# ── 核心库 ────────────────────────────────────────────────────────────
add_library(qoocore SHARED ${QOOCORE_ALL_SOURCES})

target_include_directories(qoocore
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(qoocore
    PRIVATE
        flatbuffers
        spdlog::spdlog
        yaml-cpp
        nlohmann_json::nlohmann_json
        Threads::Threads
)

# 条件编译宏
if(QOOCORE_ENABLE_ION)
    target_compile_definitions(qoocore PRIVATE QOOCORE_ENABLE_ION=1)
endif()
if(QOOCORE_ENABLE_PROFILING)
    target_compile_definitions(qoocore PRIVATE QOOCORE_ENABLE_PROFILING=1)
endif()
if(QOOCORE_USE_MLIR)
    target_compile_definitions(qoocore PRIVATE QOOCORE_USE_MLIR=1)
endif()

# 编译器特定选项
if(MSVC)
    target_compile_options(qoocore PRIVATE /W4 /utf-8)
else()
    target_compile_options(qoocore PRIVATE -Wall -Wextra -Wpedantic)
endif()

# 设置输出名称
set_target_properties(qoocore PROPERTIES
    OUTPUT_NAME "qoocore"
    VERSION ${PROJECT_VERSION}
    SOVERSION 0
    EXPORT_NAME QooCore
)

# ── FlatBuffers 模式编译 ──────────────────────────────────────────────
# 兼容系统安装和 FetchContent 两种场景
# FetchContent 构建时 flatc 目标是 `flatc`（非 imported）
if(TARGET flatbuffers::flatc)
    # 系统安装的场景
    set(FLATC_TARGET flatbuffers::flatc)
elseif(TARGET flatc)
    # FetchContent 构建的场景
    set(FLATC_TARGET flatc)
else()
    message(FATAL_ERROR "FlatBuffers flatc target not found. Please install FlatBuffers or enable FetchContent.")
endif()

add_custom_command(
    OUTPUT
        ${CMAKE_CURRENT_SOURCE_DIR}/schema/qoomodel_generated.h
    COMMAND
        $<TARGET_FILE:${FLATC_TARGET}>
        --cpp
        --gen-object-api
        --gen-compare
        -o ${CMAKE_CURRENT_SOURCE_DIR}/schema
        ${CMAKE_CURRENT_SOURCE_DIR}/schema/qoomodel.fbs
    DEPENDS
        ${CMAKE_CURRENT_SOURCE_DIR}/schema/qoomodel.fbs
    COMMENT "Compiling FlatBuffers schema: qoomodel.fbs"
    VERBATIM
)
add_custom_target(
    qoomodel_schema
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/schema/qoomodel_generated.h
)
add_dependencies(qoocore qoomodel_schema)

# ── CLI 工具 ─────────────────────────────────────────────────────────
if(QOOCORE_BUILD_CLI)
    set(QOOCORE_CLI_SOURCES
        cli/main.cpp
        cli/cli_parser.cpp
        cli/commands/compile_cmd.cpp
        cli/commands/infer_cmd.cpp
        cli/commands/profile_cmd.cpp
        cli/commands/list_cmd.cpp
        cli/commands/info_cmd.cpp
    )
    add_executable(qoocore-cli ${QOOCORE_CLI_SOURCES})
    target_include_directories(qoocore-cli PRIVATE cli)
    target_link_libraries(qoocore-cli PRIVATE qoocore)
    if(MSVC)
        target_compile_options(qoocore-cli PRIVATE /W4 /utf-8)
    else()
        target_compile_options(qoocore-cli PRIVATE -Wall -Wextra)
    endif()
endif()

# ── Python 绑定 ───────────────────────────────────────────────────────
if(QOOCORE_BUILD_PYTHON)
    message(STATUS "Python bindings requested — need pybind11")
    find_package(pybind11 2.13 QUIET)
    if(NOT pybind11_FOUND)
        message(STATUS "pybind11 not found, fetching v2.13.6...")
        FetchContent_Declare(
            pybind11
            GIT_REPOSITORY https://github.com/pybind/pybind11.git
            GIT_TAG        v2.13.6
            GIT_SHALLOW    TRUE
        )
        FetchContent_MakeAvailable(pybind11)
    endif()
    # TODO: Python binding sources
    message(WARNING "Python bindings not yet implemented")
endif()

# ── 测试 ─────────────────────────────────────────────────────────────
if(QOOCORE_BUILD_TESTS)
    find_package(GTest 1.14 QUIET)
    if(NOT GTest_FOUND)
        message(STATUS "GTest not found, fetching v1.14.0...")
        FetchContent_Declare(
            googletest
            GIT_REPOSITORY https://github.com/google/googletest.git
            GIT_TAG        v1.14.0
            GIT_SHALLOW    TRUE
        )
        # For Windows: disable installing
        set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
        FetchContent_MakeAvailable(googletest)
    endif()

    set(QOOCORE_TEST_SOURCES
        tests/unit/test_core.cpp
    )
    add_executable(qoocore-test ${QOOCORE_TEST_SOURCES})
    target_link_libraries(qoocore-test
        PRIVATE
            qoocore
            GTest::gtest
            GTest::gtest_main
    )
    include(CTest)
    enable_testing()
    add_test(NAME qoocore_unit_tests COMMAND qoocore-test)
endif()

# ── 安装规则 ──────────────────────────────────────────────────────────
install(TARGETS qoocore
    EXPORT QooCoreTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

if(QOOCORE_BUILD_CLI)
    install(TARGETS qoocore-cli
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    )
endif()

install(DIRECTORY include/qoocore
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT QooCoreTargets
    FILE QooCoreTargets.cmake
    NAMESPACE QooCore::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/QooCore
)

# 生成 Config 文件
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/QooCoreConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)
configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake/QooCoreConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/QooCoreConfig.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/QooCore
)
install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/QooCoreConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/QooCoreConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/QooCore
)

# ── 汇总信息 ──────────────────────────────────────────────────────────
message(STATUS "")
message(STATUS "=== QooCore ${PROJECT_VERSION} Configuration ===")
message(STATUS "  CXX Standard:        ${CMAKE_CXX_STANDARD}")
message(STATUS "  Build CLI:           ${QOOCORE_BUILD_CLI}")
message(STATUS "  Build Tests:         ${QOOCORE_BUILD_TESTS}")
message(STATUS "  Build Python:        ${QOOCORE_BUILD_PYTHON}")
message(STATUS "  Enable QNN:          ${QOOCORE_ENABLE_NPU_QNN}")
message(STATUS "  Enable BPU:          ${QOOCORE_ENABLE_NPU_BPU}")
message(STATUS "  Enable RKNN:         ${QOOCORE_ENABLE_NPU_RKNN}")
message(STATUS "  Enable CUDA:         ${QOOCORE_ENABLE_GPU_CUDA}")
message(STATUS "  Enable ION:          ${QOOCORE_ENABLE_ION}")
message(STATUS "  Enable Profiling:    ${QOOCORE_ENABLE_PROFILING}")
message(STATUS "  Use MLIR:            ${QOOCORE_USE_MLIR}")
message(STATUS "===============================================")
message(STATUS "")
