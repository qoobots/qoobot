cmake_minimum_required(VERSION 3.20)
project(qoogear_sdk VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 库
add_library(qoogear_sdk STATIC
    src/peripheral_base.cpp
    src/comm/can_interface.cpp
    src/security/chip_auth.cpp
)

target_include_directories(qoogear_sdk PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# 安装
install(TARGETS qoogear_sdk
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)

install(DIRECTORY include/
    DESTINATION include
)
