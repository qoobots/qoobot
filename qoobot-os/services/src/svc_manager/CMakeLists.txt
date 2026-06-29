cmake_minimum_required(VERSION 3.22)

add_library(svc_manager SHARED
    service_manager.cpp
    lifecycle.cpp
    config_loader.cpp
    health_checker.cpp
    resource_monitor.cpp
    dds_bridge.cpp
)

target_link_libraries(svc_manager PUBLIC
    qoosvc_common
    pthread
)

target_include_directories(svc_manager PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

set_target_properties(svc_manager PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION 1
)

install(TARGETS svc_manager LIBRARY DESTINATION lib)
