cmake_minimum_required(VERSION 3.10)
project(qoobot-dyn-control)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Add local cmake modules (Findmujoco, FindEigen3, Findglfw3)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

# On Windows, copy DLLs to output directory
set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)

# MSVC needs _USE_MATH_DEFINES for M_PI, suppress deprecation warnings
if(MSVC)
    add_definitions(-D_USE_MATH_DEFINES -D_CRT_SECURE_NO_WARNINGS)
    # Suppress Eigen warnings in MSVC
    add_definitions(-D_SILENCE_CXX17_RESULT_OF_DEPRECATION_WARNING)
endif()

# Pinocchio and Quill are not available on Windows — disable them
add_definitions(-DQUILL_DISABLED)
# pino_kin_dyn.cpp requires Pinocchio; stub it out
add_definitions(-DPINOCHIO_DISABLED)

# ============================================================================
# Dependencies
# ============================================================================

# MuJoCo (required for simulation)
find_package(mujoco REQUIRED)

# Eigen3 (required for linear algebra)
find_package(Eigen3 REQUIRED)

# GLFW3 (required for rendering)
find_package(glfw3 REQUIRED)

# qpOASES — use local source build
set(QPOASES_DIR "${CMAKE_CURRENT_SOURCE_DIR}/qpOASES-releases-3.2.1")
set(QPOASES_INCLUDE_DIR "${QPOASES_DIR}/include")
set(QPOASES_SRC_DIR "${QPOASES_DIR}/src")

# Collect qpOASES source files (all .cpp in src/)
file(GLOB QPOASES_SOURCES "${QPOASES_SRC_DIR}/*.cpp")

# QooBot local copy of OpenLoong algorithm library
set(OPENLOONG_LIBS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/libs")

# ============================================================================
# Include directories
# ============================================================================
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${EIGEN3_INCLUDE_DIRS}
    ${MUJOCO_INCLUDE_DIRS}
    ${QPOASES_INCLUDE_DIR}
    ${OPENLOONG_LIBS_DIR}/openloong_algorithm
    ${OPENLOONG_LIBS_DIR}/openloong_common
    ${OPENLOONG_LIBS_DIR}/openloong_math
    ${OPENLOONG_LIBS_DIR}/openloong_sim
)

# ============================================================================
# qpOASES Library
# ============================================================================
add_library(qpoases STATIC ${QPOASES_SOURCES})
target_include_directories(qpoases PUBLIC ${QPOASES_INCLUDE_DIR})
target_compile_definitions(qpoases PRIVATE __NO_COPYRIGHT__)

# ============================================================================
# QooBot Core Library
# ============================================================================

set(CORE_SOURCES
    MJ_interface.cpp
    PVT_ctrl.cpp
    qoobot_controller.cpp
    qoobot_mpc.cpp
    qoobot_wbc.cpp
)

# OpenLoong Algorithm Library sources
set(OPENLOONG_ALGORITHM_SOURCES
    libs/openloong_algorithm/Eul_W_filter.cpp
    libs/openloong_algorithm/foot_placement.cpp
    libs/openloong_algorithm/gait_scheduler.cpp
    libs/openloong_algorithm/joystick_interpreter.cpp
    libs/openloong_algorithm/mpc.cpp
    libs/openloong_algorithm/priority_tasks.cpp
    libs/openloong_algorithm/StateEst.cpp
    libs/openloong_algorithm/wbc_priority.cpp
)

# pino_kin_dyn.cpp requires Pinocchio → stub it
if(NOT PINOCHIO_DISABLED)
    list(APPEND OPENLOONG_ALGORITHM_SOURCES libs/openloong_algorithm/pino_kin_dyn.cpp)
endif()

# OpenLoong Common sources
set(OPENLOONG_COMMON_SOURCES
    libs/openloong_common/PVT_ctrl.cpp
)
# data_logger.cpp requires Quill → skip
if(NOT QUILL_DISABLED)
    list(APPEND OPENLOONG_COMMON_SOURCES libs/openloong_common/data_logger.cpp)
endif()

# OpenLoong Math sources
set(OPENLOONG_MATH_SOURCES
    libs/openloong_math/bezier_1D.cpp
    libs/openloong_math/LPF_fst.cpp
    libs/openloong_math/ramp_trajectory.cpp
    libs/openloong_math/useful_math.cpp
)

# OpenLoong Sim Interface sources
set(OPENLOONG_SIM_SOURCES
    libs/openloong_sim/GLFW_callbacks.cpp
    libs/openloong_sim/MJ_interface.cpp
)

set(ALL_SOURCES
    ${CORE_SOURCES}
    ${OPENLOONG_ALGORITHM_SOURCES}
    ${OPENLOONG_COMMON_SOURCES}
    ${OPENLOONG_MATH_SOURCES}
    ${OPENLOONG_SIM_SOURCES}
)

add_library(qoobot_core STATIC ${ALL_SOURCES})
target_link_libraries(qoobot_core
    PUBLIC Mujoco::mujoco
    PUBLIC glfw
    PUBLIC Eigen3::Eigen
    PUBLIC qpoases
)

# ============================================================================
# Demos
# ============================================================================

# Walk Demo (MPC + WBC)
add_executable(walk_mpc_wbc walk_mpc_wbc.cpp)
target_link_libraries(walk_mpc_wbc
    qoobot_core
    Mujoco::mujoco
    glfw
)

# ============================================================================
# Install
# ============================================================================

install(TARGETS qoobot_core walk_mpc_wbc
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

message(STATUS "QooBot Dynamics Control configured:")
message(STATUS "  - C++ Standard: C++17")
message(STATUS "  - Build Type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  - MuJoCo: ${MUJOCO_INCLUDE_DIRS}")
message(STATUS "  - Eigen3: ${EIGEN3_INCLUDE_DIRS}")
message(STATUS "  - GLFW3: found")
message(STATUS "  - qpOASES: local build (${QPOASES_DIR})")
message(STATUS "  - Pinocchio: disabled (stub)")
message(STATUS "  - Quill: disabled")
