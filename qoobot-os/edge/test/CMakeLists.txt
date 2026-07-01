add_executable(test_qooedge
    test_main.cpp
    test_edge_runtime.cpp
    test_edge_offload.cpp
    test_edge_sync.cpp
    test_edge_mesh.cpp
)

target_include_directories(test_qooedge PRIVATE
    ${qooedge_INCLUDE_DIR}
)

target_link_libraries(test_qooedge PRIVATE
    qooedge_runtime
    qooedge_offload
    qooedge_sync
    qooedge_mesh
    pthread
)

add_test(NAME qooedge_tests COMMAND test_qooedge)
