cmake_minimum_required(VERSION 3.22)

add_library(qoosvc_diagnostics SHARED
    diagnostics_service.cpp
    log_diagnostics.cpp
)

target_include_directories(qoosvc_diagnostics PRIVATE
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoosvc_diagnostics PUBLIC
    qoosvc_common
)

set_target_properties(qoosvc_diagnostics PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 0
    CXX_STANDARD 17
)
