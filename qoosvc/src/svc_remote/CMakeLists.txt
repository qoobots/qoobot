cmake_minimum_required(VERSION 3.22)

add_library(svc_remote SHARED
    remote_service.cpp
)

target_link_libraries(svc_remote PUBLIC
    qoosvc_common
)

target_include_directories(svc_remote PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

set_target_properties(svc_remote PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

install(TARGETS svc_remote LIBRARY DESTINATION lib)
