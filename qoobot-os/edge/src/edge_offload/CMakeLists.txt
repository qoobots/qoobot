add_library(qooedge_offload STATIC
    edge_offload.cpp
)
target_include_directories(qooedge_offload PUBLIC ${qooedge_INCLUDE_DIR})
target_link_libraries(qooedge_offload PUBLIC qooedge_common)
target_compile_features(qooedge_offload PUBLIC cxx_std_17)
