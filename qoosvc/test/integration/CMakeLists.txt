cmake_minimum_required(VERSION 3.22)

# ============================================================================
# 集成测试 — 跨模块端到端测试
# ============================================================================

# --- Voice pipeline integration test ---
add_executable(test_voice_pipeline
    test_voice_pipeline.cpp
)
target_link_libraries(test_voice_pipeline PRIVATE qoosvc_test_common svc_voice)
add_test(NAME qoosvc.integration.voice_pipeline COMMAND test_voice_pipeline)

# --- Navigation pipeline integration test ---
add_executable(test_nav_pipeline
    test_nav_pipeline.cpp
)
target_link_libraries(test_nav_pipeline PRIVATE qoosvc_test_common svc_navigation)
add_test(NAME qoosvc.integration.nav_pipeline COMMAND test_nav_pipeline)

# --- Service Manager integration test ---
add_executable(test_manager_integration
    test_manager_integration.cpp
)
target_link_libraries(test_manager_integration PRIVATE qoosvc_test_common svc_manager svc_voice svc_diagnostics)
add_test(NAME qoosvc.integration.manager COMMAND test_manager_integration)
