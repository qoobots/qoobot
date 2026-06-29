add_library(svc_multi_robot SHARED
    multi_robot_service.cpp
)

target_link_libraries(svc_multi_robot PUBLIC
    qoosvc_common
)

target_include_directories(svc_multi_robot PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_options(svc_multi_robot PRIVATE
    -Wall -Wextra
)
