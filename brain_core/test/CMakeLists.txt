# brain_core test/CMakeLists.txt
# GTest-based unit tests for brain_core modules.
# Activated only when BUILD_TESTING=ON in parent CMakeLists.txt.

find_package(ament_cmake_gtest REQUIRED)

# ── Common test include path ────────────────────────────────
set(TEST_INCLUDE_DIRS
  ${CMAKE_CURRENT_SOURCE_DIR}/../include
  ${Protobuf_INCLUDE_DIRS}
)
if(NOT BRAIN_CORE_SKIP_ROS2)
  list(APPEND TEST_INCLUDE_DIRS
    ${rclcpp_INCLUDE_DIRS}
    ${geometry_msgs_INCLUDE_DIRS}
    ${sensor_msgs_INCLUDE_DIRS}
    ${tf2_INCLUDE_DIRS}
    ${visualization_msgs_INCLUDE_DIRS}
    ${builtin_interfaces_INCLUDE_DIRS}
  )
endif()

# ── Common test link libraries ──────────────────────────────
set(TEST_LINK_LIBS brain_core_lib ${Protobuf_LIBRARIES} gRPC::grpc++)
if(NOT BRAIN_CORE_SKIP_ROS2)
  list(APPEND TEST_LINK_LIBS
    ${rclcpp_LIBRARIES}
    ${geometry_msgs_LIBRARIES}
    ${sensor_msgs_LIBRARIES}
    ${tf2_LIBRARIES}
    ${tf2_geometry_msgs_LIBRARIES}
  )
endif()

# ── ros2_bridge tests ───────────────────────────────────────
ament_add_gtest(test_node_manager
  ros2_bridge/test_node_manager.cpp
)
target_include_directories(test_node_manager PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_node_manager ${TEST_LINK_LIBS})

ament_add_gtest(test_topic_adapter
  ros2_bridge/test_topic_adapter.cpp
)
target_include_directories(test_topic_adapter PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_topic_adapter ${TEST_LINK_LIBS})

# ── behavior_engine tests ───────────────────────────────────
ament_add_gtest(test_bt_loader
  behavior_engine/test_bt_loader.cpp
)
target_include_directories(test_bt_loader PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_bt_loader ${TEST_LINK_LIBS})

ament_add_gtest(test_tree_executor
  behavior_engine/test_tree_executor.cpp
)
target_include_directories(test_tree_executor PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_tree_executor ${TEST_LINK_LIBS})

# ── safety_monitor tests ────────────────────────────────────
ament_add_gtest(test_collision_checker
  safety_monitor/test_collision_checker.cpp
)
target_include_directories(test_collision_checker PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_collision_checker ${TEST_LINK_LIBS})

ament_add_gtest(test_emergency_stop
  safety_monitor/test_emergency_stop.cpp
)
target_include_directories(test_emergency_stop PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_emergency_stop ${TEST_LINK_LIBS})

# ── motion_planner tests ────────────────────────────────────
ament_add_gtest(test_ik_solver
  motion_planner/test_ik_solver.cpp
)
target_include_directories(test_ik_solver PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_ik_solver ${TEST_LINK_LIBS})

ament_add_gtest(test_trajectory_generator
  motion_planner/test_trajectory_generator.cpp
)
target_include_directories(test_trajectory_generator PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(test_trajectory_generator ${TEST_LINK_LIBS})
