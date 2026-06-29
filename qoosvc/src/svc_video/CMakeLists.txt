cmake_minimum_required(VERSION 3.22)

add_library(svc_video SHARED
    video_service.cpp
)

target_link_libraries(svc_video PUBLIC
    qoosvc_common
)

target_include_directories(svc_video PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

set_target_properties(svc_video PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

install(TARGETS svc_video LIBRARY DESTINATION lib)
