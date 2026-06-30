# qoostore-edge 测试套件
# 使用内部轻量级测试框架（无外部依赖）

set(TEST_INCLUDE_DIRS
    ${qoostore_EDGE_INCLUDE_DIR}
    ${CMAKE_SOURCE_DIR}/src/common
    ${CMAKE_SOURCE_DIR}/src/skill_manager
    ${CMAKE_SOURCE_DIR}/src/skill_resolver
)

# 测试可执行文件
add_executable(test_qoostore
    test_main.cpp
    test_json_utils.cpp
    test_sha256.cpp
    test_skill_manager.cpp
    test_dependency_resolver.cpp
)

target_include_directories(test_qoostore PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_qoostore PRIVATE
    qoostore_skill_manager
    qoostore_edge_resolver
    pthread
)

add_test(NAME qoostore_tests COMMAND test_qoostore)
