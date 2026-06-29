cmake_minimum_required(VERSION 3.22)

# ============================================================================
# C++ 单元测试
# ============================================================================

# --- Common types tests ---
add_executable(test_common
    test_error_codes.cpp
    test_result.cpp
    test_service_base.cpp
)
target_link_libraries(test_common PRIVATE qoosvc_test_common)
add_test(NAME qoosvc.unit.common COMMAND test_common)

# --- Voice service tests ---
add_executable(test_voice
    test_voice_service.cpp
    test_wake_word.cpp
    test_nlu.cpp
    test_tts.cpp
)
target_link_libraries(test_voice PRIVATE qoosvc_test_common svc_voice)
add_test(NAME qoosvc.unit.voice COMMAND test_voice)

# --- Navigation service tests ---
add_executable(test_navigation
    test_astar.cpp
    test_teb.cpp
    test_exploration.cpp
    test_navigation_service.cpp
)
target_link_libraries(test_navigation PRIVATE qoosvc_test_common svc_navigation)
add_test(NAME qoosvc.unit.navigation COMMAND test_navigation)

# --- Diagnostics service tests ---
add_executable(test_diagnostics
    test_post.cpp
    test_diagnostics_service.cpp
)
target_link_libraries(test_diagnostics PRIVATE qoosvc_test_common svc_diagnostics)
add_test(NAME qoosvc.unit.diagnostics COMMAND test_diagnostics)

# --- Spatial service tests ---
add_executable(test_spatial
    test_slam.cpp
    test_spatial_service.cpp
)
target_link_libraries(test_spatial PRIVATE qoosvc_test_common svc_spatial)
add_test(NAME qoosvc.unit.spatial COMMAND test_spatial)

# --- Service Manager tests ---
add_executable(test_manager
    test_service_manager.cpp
)
target_link_libraries(test_manager PRIVATE qoosvc_test_common svc_manager)
add_test(NAME qoosvc.unit.manager COMMAND test_manager)
