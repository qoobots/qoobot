add_library(svc_hmi SHARED
    hmi_service.cpp
    expression/led_controller.cpp
    lighting/light_ring.cpp
    gesture/gesture_recognizer.cpp
)

target_link_libraries(svc_hmi PUBLIC
    qoosvc_common
)

target_include_directories(svc_hmi PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_options(svc_hmi PRIVATE
    -Wall -Wextra
)
