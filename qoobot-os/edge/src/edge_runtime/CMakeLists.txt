add_library(qooedge_runtime STATIC
    edge_runtime.cpp
)
target_include_directories(qooedge_runtime PUBLIC ${qooedge_INCLUDE_DIR})
target_link_libraries(qooedge_runtime PUBLIC qooedge_common)
target_compile_features(qooedge_runtime PUBLIC cxx_std_17)
