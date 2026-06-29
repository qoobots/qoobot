# permission — 权限管控
# 职责：声明式权限模型 (NORMAL/DANGEROUS/SIGNATURE)、权限授予/撤销、权限持久化

set(PERMISSION_SOURCES
    permission_manager.cpp
    permission_store.cpp
)

add_library(qoostore_permission STATIC ${PERMISSION_SOURCES})

target_include_directories(qoostore_permission PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoostore_permission PUBLIC
    qoostore_edge_common
)

# 链接 nlohmann/json（用于权限持久化）
find_package(nlohmann_json QUIET)
if(nlohmann_json_FOUND)
    target_link_libraries(qoostore_permission PUBLIC nlohmann_json::nlohmann_json)
endif()

target_compile_features(qoostore_permission PUBLIC cxx_std_17)
