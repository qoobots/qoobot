cmake_minimum_required(VERSION 3.22)

# Voice interaction service library
add_library(qoosvc_voice SHARED
    voice_service.cpp
)

target_include_directories(qoosvc_voice PRIVATE
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoosvc_voice PUBLIC
    qoosvc_common
)

set_target_properties(qoosvc_voice PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 0
    CXX_STANDARD 17
)
