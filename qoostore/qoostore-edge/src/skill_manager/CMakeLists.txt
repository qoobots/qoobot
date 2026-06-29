# skill_manager — 技能安装管理
# 职责：安装/卸载/更新/启用/停用、.qooskills 包解析、签名验证、本地仓库管理

set(SKILL_MANAGER_SOURCES
    skill_manager.cpp
    package_parser.cpp
    signature_verifier.cpp
    skill_repo.cpp
)

add_library(qoostore_skill_manager STATIC ${SKILL_MANAGER_SOURCES})

target_include_directories(qoostore_skill_manager PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoostore_skill_manager PUBLIC
    qoostore_edge_common
)

# 链接 nlohmann/json（通过 FetchContent 或系统包）
find_package(nlohmann_json QUIET)
if(nlohmann_json_FOUND)
    target_link_libraries(qoostore_skill_manager PUBLIC nlohmann_json::nlohmann_json)
else()
    message(STATUS "nlohmann_json not found, using embedded single-header")
    # 生产环境通过 FetchContent 或系统包管理安装
endif()

target_compile_features(qoostore_skill_manager PUBLIC cxx_std_17)
