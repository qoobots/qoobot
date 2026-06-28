cmake_minimum_required(VERSION 3.22)

add_library(qoosvc_navigation SHARED
    navigation_service.cpp
    navigation_multifloor_narrow.cpp
)

target_include_directories(qoosvc_navigation PRIVATE
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoosvc_navigation PUBLIC
    qoosvc_common
)

set_target_properties(qoosvc_navigation PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 0
    CXX_STANDARD 17
)
