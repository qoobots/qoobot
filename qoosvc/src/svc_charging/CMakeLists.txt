add_library(svc_charging SHARED
    charging_service.cpp
)

target_link_libraries(svc_charging PUBLIC
    qoosvc_common
)

target_include_directories(svc_charging PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_options(svc_charging PRIVATE
    -Wall -Wextra
)
