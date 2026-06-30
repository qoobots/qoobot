add_library(qooedge_mesh STATIC
    edge_mesh.cpp
)
target_include_directories(qooedge_mesh PUBLIC ${qooedge_INCLUDE_DIR})
target_link_libraries(qooedge_mesh PUBLIC qooedge_common)
target_compile_features(qooedge_mesh PUBLIC cxx_std_17)
