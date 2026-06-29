add_library(svc_people SHARED
    people_service.cpp
)

target_link_libraries(svc_people PUBLIC
    qoosvc_common
)

target_include_directories(svc_people PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_options(svc_people PRIVATE
    -Wall -Wextra
)
