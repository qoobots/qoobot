# tests/CMakeLists.txt
# QooCore — 测试构建配置

# ── 依赖 ───────────────────────────────────────────────────────────────────
find_package(GTest 1.14 REQUIRED)
find_package(Threads REQUIRED)

# ── 单元测试 ───────────────────────────────────────────────────────────────
set(QOOCORE_TEST_SOURCES
    unit/test_core.cpp
    # 后续添加：
    # unit/test_tensor.cpp
    # unit/test_engine.cpp
    # unit/test_compiler.cpp
    # unit/test_npu_hal.cpp
)

add_executable(qoocore_test ${QOOCORE_TEST_SOURCES})
target_link_libraries(qoocore_test
    PRIVATE
        qoocore
        GTest::gtest
        GTest::gtest_main
        Threads::Threads
)
target_include_directories(qoocore_test
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../include
        ${CMAKE_CURRENT_SOURCE_DIR}/../src
)

# ── 注册测试 ───────────────────────────────────────────────────────────────
add_test(NAME qoocore_unit_tests COMMAND qoocore_test)

# ── 自定义目标：运行测试 ───────────────────────────────────────────────────
add_custom_target(test_qoocore
    COMMAND ${CMAKE_CURRENT_BINARY_DIR}/qoocore_test
    DEPENDS qoocore_test
    COMMENT "运行 QooCore 单元测试"
    VERBATIM
)
