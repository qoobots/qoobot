add_library(qooedge_sync STATIC
    edge_sync.cpp
)
target_include_directories(qooedge_sync PUBLIC ${qooedge_INCLUDE_DIR})
target_link_libraries(qooedge_sync PUBLIC qooedge_common)
target_compile_features(qooedge_sync PUBLIC cxx_std_17)
