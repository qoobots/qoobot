# skill_downloader — 技能下载器
# 职责：断点续传、增量更新、包校验 (SHA-256)、签名验证

set(SKILL_DOWNLOADER_SOURCES
    skill_downloader.cpp
    package_validator.cpp
)

add_library(qoostore_skill_downloader STATIC ${SKILL_DOWNLOADER_SOURCES})

target_include_directories(qoostore_skill_downloader PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(qoostore_skill_downloader PUBLIC
    qoostore_edge_common
)

# libcurl 用于 HTTP 下载
find_package(CURL QUIET)
if(CURL_FOUND)
    target_link_libraries(qoostore_skill_downloader PUBLIC CURL::libcurl)
    target_compile_definitions(qoostore_skill_downloader PRIVATE QOOSTORE_HAS_CURL)
else()
    message(STATUS "libcurl not found — downloader will use stub implementation")
endif()

# OpenSSL 用于 SHA-256 和 Ed25519 签名验证
find_package(OpenSSL QUIET)
if(OpenSSL_FOUND)
    target_link_libraries(qoostore_skill_downloader PUBLIC OpenSSL::SSL OpenSSL::Crypto)
    target_compile_definitions(qoostore_skill_downloader PRIVATE QOOSTORE_HAS_OPENSSL)
else()
    message(STATUS "OpenSSL not found — hash/verify will use stub implementation")
endif()

target_compile_features(qoostore_skill_downloader PUBLIC cxx_std_17)
