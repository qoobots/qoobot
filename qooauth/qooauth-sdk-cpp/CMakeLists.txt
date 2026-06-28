cmake_minimum_required(VERSION 3.16)
project(qooauth-sdk-cpp VERSION 1.0.0 LANGUAGES CXX C)

# ============================================================================
# QooBot Device Authentication SDK
# ============================================================================
# Platform: onboard_core (C++17)
# Purpose: Device-side authentication — TLS 1.3 + mTLS, secure storage,
#          device activation, X.509 certificate management.
# Dependencies: mbedTLS 3.x, libcurl 8.x (optional, for HTTP), json-c
# ============================================================================

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(QOOAUTH_BUILD_EXAMPLES "Build example programs" ON)
option(QOOAUTH_BUILD_TESTS "Build test programs" ON)
option(QOOAUTH_ENABLE_HTTP "Enable HTTP client (requires libcurl)" ON)
option(QOOAUTH_ENABLE_TPM "Enable TPM-backed key storage" OFF)

# --------------------------------------------------------------------------
# Dependencies
# --------------------------------------------------------------------------
find_package(mbedTLS 3.0 REQUIRED)
if(QOOAUTH_ENABLE_HTTP)
    find_package(CURL 8.0 REQUIRED)
endif()
find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(JSONC json-c)
endif()
if(NOT JSONC_FOUND)
    find_path(JSONC_INCLUDE_DIRS json-c/json.h)
    find_library(JSONC_LIBRARIES json-c)
    if(NOT JSONC_INCLUDE_DIRS OR NOT JSONC_LIBRARIES)
        message(FATAL_ERROR "json-c not found. Install libjson-c-dev or equivalent.")
    endif()
endif()

# --------------------------------------------------------------------------
# Library target
# --------------------------------------------------------------------------
set(SOURCES
    src/qooauth_error.c
    src/qooauth_internal_utils.c
    src/qooauth_secure_storage.c
    src/qooauth_tls.c
    src/qooauth_cert_manager.c
    src/qooauth_activation_client.c
    src/qooauth_device_auth.c
)

set(HEADERS
    include/qooauth/qooauth.h
    include/qooauth/qooauth_error.h
    include/qooauth/qooauth_secure_storage.h
    include/qooauth/qooauth_tls.h
    include/qooauth/qooauth_cert_manager.h
    include/qooauth/qooauth_activation_client.h
    include/qooauth/qooauth_device_auth.h
    include/qooauth/qooauth_internal.h
)

add_library(qooauth-sdk STATIC ${SOURCES} ${HEADERS})
add_library(qooauth::sdk ALIAS qooauth-sdk)

target_include_directories(qooauth-sdk
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(qooauth-sdk
    PUBLIC
        mbedTLS::mbedtls mbedTLS::mbedcrypto mbedTLS::mbedx509
        ${JSONC_LIBRARIES}
    PRIVATE
        $<$<BOOL:${QOOAUTH_ENABLE_HTTP}>:CURL::libcurl>
)

target_compile_options(qooauth-sdk PRIVATE
    $<$<COMPILE_LANG_AND_ID:C,GNU,Clang,AppleClang>:-Wall -Wextra -Wpedantic>
    $<$<COMPILE_LANG_AND_ID:C,GNU>:-fvisibility=hidden>
)

target_compile_definitions(qooauth-sdk
    PRIVATE
        $<$<BOOL:${QOOAUTH_ENABLE_HTTP}>:QOOAUTH_HAVE_HTTP=1>
        $<$<BOOL:${QOOAUTH_ENABLE_TPM}>:QOOAUTH_HAVE_TPM=1>
)

# --------------------------------------------------------------------------
# Examples
# --------------------------------------------------------------------------
if(QOOAUTH_BUILD_EXAMPLES)
    add_executable(device_activate examples/device_activate.c)
    target_link_libraries(device_activate PRIVATE qooauth-sdk)

    add_executable(mtls_echo examples/mtls_echo.c)
    target_link_libraries(mtls_echo PRIVATE qooauth-sdk)
endif()

# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------
if(QOOAUTH_BUILD_TESTS)
    enable_testing()
    add_executable(qooauth_test
        tests/test_secure_storage.c
        tests/test_cert_manager.c
        tests/test_tls.c
        tests/test_activation_client.c
    )
    target_link_libraries(qooauth_test PRIVATE qooauth-sdk)
    add_test(NAME qooauth_test COMMAND qooauth_test)
endif()

# --------------------------------------------------------------------------
# Install
# --------------------------------------------------------------------------
include(GNUInstallDirs)
install(TARGETS qooauth-sdk
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(DIRECTORY include/qooauth
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
install(FILES
    cmake/qooauth-sdk-config.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/qooauth-sdk
)
