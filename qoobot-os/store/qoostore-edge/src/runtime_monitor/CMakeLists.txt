# runtime_monitor — 运行时监控
# 职责：CPU/内存/网络统计、异常行为检测、崩溃收集、定期上报 (5s)

set(RUNTIME_MONITOR_SOURCES
    runtime_monitor.cpp
    crash_collector.cpp
    stats_reporter.cpp
)

add_library(qoostore_runtime_monitor STATIC ${RUNTIME_MONITOR_SOURCES})

target_include_directories(qoostore_runtime_monitor PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoostore_runtime_monitor PUBLIC
    qoostore_edge_common
)

# libcurl 用于 HTTP 上报统计
find_package(CURL QUIET)
if(CURL_FOUND)
    target_link_libraries(qoostore_runtime_monitor PUBLIC CURL::libcurl)
    target_compile_definitions(qoostore_runtime_monitor PRIVATE QOOSTORE_HAS_CURL)
else()
    message(STATUS "libcurl not found — stats reporter will use stub implementation")
endif()

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_libraries(qoostore_runtime_monitor PUBLIC pthread)
endif()

target_compile_features(qoostore_runtime_monitor PUBLIC cxx_std_17)
