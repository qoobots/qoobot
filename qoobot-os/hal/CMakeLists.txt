# =============================================================================
# QooBody — QooBot Hardware Reference Design
# Root CMakeLists.txt — Multi-module C/Embedded Build System
#
# Usage:
#   cmake -B build -DPLATFORM=jetson_orin -DCMAKE_BUILD_TYPE=Release
#   cmake --build build --parallel $(nproc)
# =============================================================================

cmake_minimum_required(VERSION 3.21)
project(qoobody
    VERSION     0.6.0
    DESCRIPTION "QooBot Hardware Reference Design — HAL, Drivers, Firmware & Tests"
    LANGUAGES   C CXX
)

# ---- Platform Detection & Cross-Compilation ---------------------------------
include(cmake/qoobody_platform.cmake)

# ---- Build Options ----------------------------------------------------------
option(QOOBODY_BUILD_HAL        "Build Hardware Abstraction Layer library"     ON)
option(QOOBODY_BUILD_DRIVERS    "Build reference driver implementations"       ON)
option(QOOBODY_BUILD_FIRMWARE   "Build safety & motor control firmware"        ON)
option(QOOBODY_BUILD_COMPUTE    "Build compute platform modules"               ON)
option(QOOBODY_BUILD_POWER      "Build power system modules"                   ON)
option(QOOBODY_BUILD_TESTS      "Build test suites (HIL / benchmark / interop)" ON)
option(QOOBODY_BUILD_EXAMPLES   "Build example applications"                   OFF)
option(QOOBODY_ENABLE_SANITIZERS "Enable Address / Undefined Behaviour sanitizers" OFF)

# ---- C/C++ Standards --------------------------------------------------------
set(CMAKE_C_STANDARD          11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD        17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# ---- Compiler Warnings ------------------------------------------------------
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(
        -Wall -Wextra -Wpedantic
        -Wshadow -Wformat=2 -Wconversion -Wsign-conversion
        -Wstrict-prototypes -Wmissing-prototypes -Wmissing-declarations
    )
    # C-specific
    add_compile_options($<$<COMPILE_LANGUAGE:C>:-Wdeclaration-after-statement>)
endif()

# Release optimisations (embedded-friendly)
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_options(-O3 -DNDEBUG)
    if(CMAKE_C_COMPILER_ID MATCHES "GNU")
        add_compile_options(-flto -ffunction-sections -fdata-sections)
        add_link_options(-flto -Wl,--gc-sections)
    endif()
endif()

# Debug builds
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_options(-g3 -O0)
    if(QOOBODY_ENABLE_SANITIZERS)
        add_compile_options(-fsanitize=address,undefined)
        add_link_options(-fsanitize=address,undefined)
    endif()
endif()

# ---- Library Targets --------------------------------------------------------

# --- HAL (Header-only + thin C binding) ---
if(QOOBODY_BUILD_HAL)
    add_library(qoobody_hal INTERFACE)
    target_include_directories(qoobody_hal INTERFACE
        ${CMAKE_CURRENT_SOURCE_DIR}/hal
    )
    target_compile_features(qoobody_hal INTERFACE c_std_11)
    add_library(QooBody::HAL ALIAS qoobody_hal)
endif()

# --- Drivers (reference implementation library) ---
if(QOOBODY_BUILD_DRIVERS)
    file(GLOB_RECURSE DRIVER_SOURCES drivers/*.c)
    add_library(qoobody_drivers STATIC ${DRIVER_SOURCES})
    target_include_directories(qoobody_drivers PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/hal
        ${CMAKE_CURRENT_SOURCE_DIR}/drivers
    )
    target_link_libraries(qoobody_drivers PUBLIC QooBody::HAL)
    target_compile_definitions(qoobody_drivers PRIVATE
        QOO_DRIVER_PLATFORM_${QOOBODY_PLATFORM_UPPER}
    )
    add_library(QooBody::Drivers ALIAS qoobody_drivers)
endif()

# --- Compute Modules ---
if(QOOBODY_BUILD_COMPUTE)
    file(GLOB COMPUTE_SOURCES compute/*.c)
    if(COMPUTE_SOURCES)
        add_library(qoobody_compute STATIC ${COMPUTE_SOURCES})
        target_include_directories(qoobody_compute PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/hal
            ${CMAKE_CURRENT_SOURCE_DIR}/compute
        )
        target_link_libraries(qoobody_compute PUBLIC QooBody::HAL)
        add_library(QooBody::Compute ALIAS qoobody_compute)
    endif()
endif()

# --- Power Modules ---
if(QOOBODY_BUILD_POWER)
    file(GLOB POWER_SOURCES power/*.c)
    if(POWER_SOURCES)
        add_library(qoobody_power STATIC ${POWER_SOURCES})
        target_include_directories(qoobody_power PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/hal
            ${CMAKE_CURRENT_SOURCE_DIR}/power
        )
        target_link_libraries(qoobody_power PUBLIC QooBody::HAL)
        add_library(QooBody::Power ALIAS qoobody_power)
    endif()
endif()

# --- Firmware (cross-compiled for target MCU) ---
if(QOOBODY_BUILD_FIRMWARE AND QOOBODY_CROSS_COMPILING)
    # Safety MCU firmware
    add_executable(qoo_safety_fw
        firmware/safety_mcu/qoo_safety_fw.c
    )
    target_include_directories(qoo_safety_fw PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/hal
    )
    target_link_options(qoo_safety_fw PRIVATE
        -T ${QOOBODY_LINKER_SCRIPT_SAFETY}
        -nostartfiles -nostdlib
    )

    # Motor control firmware
    add_executable(qoo_motor_ctrl
        firmware/motor_ctrl/qoo_motor_ctrl.c
    )
    target_include_directories(qoo_motor_ctrl PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/hal
    )
    target_link_options(qoo_motor_ctrl PRIVATE
        -T ${QOOBODY_LINKER_SCRIPT_MOTOR}
        -nostartfiles -nostdlib
    )
endif()

# ---- Tests ------------------------------------------------------------------
if(QOOBODY_BUILD_TESTS)
    enable_testing()

    # Helper: declare a test target
    function(qoobody_add_test TEST_NAME TEST_SOURCE)
        add_executable(${TEST_NAME} ${TEST_SOURCE} ${ARGN})
        target_include_directories(${TEST_NAME} PRIVATE
            ${CMAKE_CURRENT_SOURCE_DIR}/hal
            ${CMAKE_CURRENT_SOURCE_DIR}/test
        )
        target_link_libraries(${TEST_NAME} PRIVATE
            QooBody::HAL
            $<$<BOOL:${QOOBODY_BUILD_DRIVERS}>:QooBody::Drivers>
            $<$<BOOL:${QOOBODY_BUILD_POWER}>:QooBody::Power>
            $<$<BOOL:${QOOBODY_BUILD_COMPUTE}>:QooBody::Compute>
        )
        add_test(NAME ${TEST_NAME} COMMAND ${TEST_NAME})
    endfunction()

    if(QOOBODY_BUILD_DRIVERS)
        qoobody_add_test(qoo_perf_benchmark    test/qoo_perf_benchmark.c)
        qoobody_add_test(qoo_interop_test      test/qoo_interop_test.c)
    endif()

    qoobody_add_test(qoo_reliability_test   test/qoo_reliability_test.c)
    qoobody_add_test(qoo_hil_platform       test/qoo_hil_platform.c)
    qoobody_add_test(qoo_hil_test           test/qoo_hil_test.c)
endif()

# ---- Installation -----------------------------------------------------------
include(GNUInstallDirs)
install(TARGETS qoobody_hal EXPORT qoobody-targets)
install(DIRECTORY hal/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/qoobody
    FILES_MATCHING PATTERN "*.h"
)
install(DIRECTORY docs/ DESTINATION ${CMAKE_INSTALL_DATADIR}/qoobody/docs)

# ---- Export -----------------------------------------------------------------
install(EXPORT qoobody-targets
    NAMESPACE QooBody::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/qoobody
)

# ---- Summary ----------------------------------------------------------------
message(STATUS "=============================================")
message(STATUS "QooBody ${PROJECT_VERSION} — Build Configuration")
message(STATUS "  Platform:    ${QOOBODY_PLATFORM}")
message(STATUS "  Build Type:  ${CMAKE_BUILD_TYPE}")
message(STATUS "  HAL:         ${QOOBODY_BUILD_HAL}")
message(STATUS "  Drivers:     ${QOOBODY_BUILD_DRIVERS}")
message(STATUS "  Firmware:    ${QOOBODY_BUILD_FIRMWARE}")
message(STATUS "  Compute:     ${QOOBODY_BUILD_COMPUTE}")
message(STATUS "  Power:       ${QOOBODY_BUILD_POWER}")
message(STATUS "  Tests:       ${QOOBODY_BUILD_TESTS}")
message(STATUS "=============================================")
