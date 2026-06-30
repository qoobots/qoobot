add_library(qoostore_edge_resolver STATIC
    skill_resolver.cpp
)

target_include_directories(qoostore_edge_resolver PRIVATE
    ${qoostore_EDGE_INCLUDE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../common
)

target_link_libraries(qoostore_edge_resolver PUBLIC
    qoostore_edge_common
)
