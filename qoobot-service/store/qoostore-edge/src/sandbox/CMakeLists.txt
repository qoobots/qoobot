# sandbox — 沙箱隔离引擎
# 职责：cgroups v2 资源配额、OverlayFS 文件系统隔离、Network Namespace 网络隔离、进程隔离

set(SANDBOX_SOURCES
    sandbox_engine.cpp
    fs_isolation.cpp
    net_isolation.cpp
    process_isolation.cpp
    resource_quota.cpp
)

add_library(qoostore_sandbox STATIC ${SANDBOX_SOURCES})

target_include_directories(qoostore_sandbox PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoostore_sandbox PUBLIC
    qoostore_edge_common
)

# Linux 特定：需要 cgroups 和 mount 支持
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_libraries(qoostore_sandbox PUBLIC pthread)
    target_compile_definitions(qoostore_sandbox PRIVATE QOOSTORE_PLATFORM_LINUX)
endif()

target_compile_features(qoostore_sandbox PUBLIC cxx_std_17)
