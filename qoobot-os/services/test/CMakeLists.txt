cmake_minimum_required(VERSION 3.22)

# ============================================================================
# qoosvc 测试框架
# ============================================================================

enable_testing()

# 查找 Google Test
find_package(GTest QUIET)
if(NOT GTest_FOUND)
    message(STATUS "GTest not found — downloading via FetchContent")
    include(FetchContent)
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.14.0
    )
    FetchContent_MakeAvailable(googletest)
endif()

# ============================================================================
# 公共测试工具库
# ============================================================================
add_library(qoosvc_test_common INTERFACE)
target_include_directories(qoosvc_test_common INTERFACE
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}
)
target_link_libraries(qoosvc_test_common INTERFACE
    GTest::gtest
    GTest::gtest_main
    qoosvc_common
)

# ============================================================================
# 单元测试子目录
# ============================================================================
add_subdirectory(unit)
add_subdirectory(integration)
