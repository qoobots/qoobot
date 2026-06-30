cmake_minimum_required(VERSION 3.20)
project(qoobot-sdk-cpp VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Library target (header-only + compiled core)
add_library(qoobot_sdk INTERFACE)

target_include_directories(qoobot_sdk INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(qoobot_sdk INTERFACE cxx_std_17)

# Dependencies
find_package(Threads REQUIRED)
target_link_libraries(qoobot_sdk INTERFACE Threads::Threads)

# Install
include(GNUInstallDirs)
install(TARGETS qoobot_sdk EXPORT qoobot_sdk-targets)
install(DIRECTORY qoobot_sdk/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/qoobot/sdk
        FILES_MATCHING PATTERN "*.h")

# Export
install(EXPORT qoobot_sdk-targets
        FILE qoobot_sdk-targets.cmake
        DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/qoobot_sdk)
