cmake_minimum_required(VERSION 3.22)
project(brain_core VERSION 0.1.0 LANGUAGES CXX)

# ── C++17 Standard ──────────────────────────────────────────
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Compiler Settings ───────────────────────────────────────
include(cmake/CompilerSettings.cmake)

# ── Dependencies ────────────────────────────────────────────
find_package(ament_cmake REQUIRED)
# ── CI flag: skip ROS 2 deps for quick lint-syntax checks ──
option(BRAIN_CORE_SKIP_ROS2 "Skip ROS 2 dependencies (CI syntax check only)" OFF)

if(NOT BRAIN_CORE_SKIP_ROS2)
  find_package(rclcpp REQUIRED)
  find_package(rclcpp_lifecycle REQUIRED)
  find_package(rclcpp_action REQUIRED)
  find_package(std_msgs REQUIRED)
  find_package(geometry_msgs REQUIRED)
  find_package(sensor_msgs REQUIRED)
  find_package(nav_msgs REQUIRED)
  find_package(trajectory_msgs REQUIRED)
  find_package(tf2 REQUIRED)
  find_package(tf2_geometry_msgs REQUIRED)
  find_package(visualization_msgs REQUIRED)
  find_package(builtin_interfaces REQUIRED)
endif()

# ── Optional: FCL / MoveIt2 / TRAC-IK ──────────────────────
find_package(fcl QUIET)
find_package(moveit_core QUIET)
find_package(moveit_ros_planning_interface QUIET)

# ── Protobuf + gRPC ────────────────────────────────────────
find_package(Protobuf REQUIRED)
find_package(gRPC CONFIG REQUIRED)

# ── Generated proto files ──────────────────────────────────
set(PROTO_GEN_DIR "${CMAKE_SOURCE_DIR}/../brain_proto/gen/cpp")
if(EXISTS "${PROTO_GEN_DIR}")
  include_directories("${PROTO_GEN_DIR}")
endif()

# ── Include paths ──────────────────────────────────────────
set(BRAIN_CORE_INCLUDE_DIRS
  ${CMAKE_CURRENT_SOURCE_DIR}/include
  ${Protobuf_INCLUDE_DIRS}
)
if(NOT BRAIN_CORE_SKIP_ROS2)
  list(APPEND BRAIN_CORE_INCLUDE_DIRS
    ${rclcpp_INCLUDE_DIRS}
    ${geometry_msgs_INCLUDE_DIRS}
    ${sensor_msgs_INCLUDE_DIRS}
    ${tf2_INCLUDE_DIRS}
    ${visualization_msgs_INCLUDE_DIRS}
    ${builtin_interfaces_INCLUDE_DIRS}
    ${nav_msgs_INCLUDE_DIRS}
    ${trajectory_msgs_INCLUDE_DIRS}
  )
endif()
include_directories(${BRAIN_CORE_INCLUDE_DIRS})

# ── Source files ───────────────────────────────────────────
# Explicit list below in add_library — see Check 1 in verify_brain_core_build.py
# (GLOB_RECURSE removed: unused and discouraged by CMake best practices)

# ── Core Library ───────────────────────────────────────────
add_library(brain_core_lib STATIC
  src/ros2_bridge/node_manager.cpp
  src/ros2_bridge/topic_adapter.cpp
  src/ros2_bridge/service_adapter.cpp
  src/ros2_bridge/action_adapter.cpp
  src/ros2_bridge/lifecycle_manager.cpp
  src/event_bus/event_publisher.cpp
  src/event_bus/event_subscriber.cpp
  src/event_bus/domain_event.cpp
  src/hal_interface/config_loader.cpp
  src/hal_interface/sensor_reader.cpp
  src/hal_interface/actuator_writer.cpp
  src/hal_interface/robot_model.cpp
  src/hal_interface/urdf_parser.cpp
  src/safety_monitor/collision_checker.cpp
  src/safety_monitor/emergency_stop.cpp
  src/safety_monitor/joint_limiter.cpp
  src/safety_monitor/force_monitor.cpp
  src/safety_monitor/watchdog.cpp
  src/safety_monitor/workspace_validator.cpp
  src/motion_planner/ik_solver.cpp
  src/motion_planner/trajectory_generator.cpp
  src/motion_planner/trajectory_optimizer.cpp
  src/motion_planner/trajectory_follower.cpp
  src/motion_planner/collision_checker_fcl.cpp
  src/motion_planner/moveit2_client.cpp
  src/behavior_engine/tree_executor.cpp
  src/behavior_engine/node_factory.cpp
  src/behavior_engine/bt_loader.cpp
  src/behavior_engine/tick_scheduler.cpp
  src/behavior_engine/action_nodes/navigate_to_node.cpp
  src/behavior_engine/action_nodes/detect_object_node.cpp
  src/behavior_engine/action_nodes/pick_object_node.cpp
  src/behavior_engine/action_nodes/place_object_node.cpp
  src/behavior_engine/action_nodes/avoid_obstacle_node.cpp
  src/behavior_engine/action_nodes/wait_node.cpp
  src/behavior_engine/action_nodes/speak_node.cpp
  src/behavior_engine/action_nodes/observe_node.cpp
  src/behavior_engine/action_nodes/hitl_confirm_node.cpp
  src/grpc_server/server.cpp
  src/grpc_server/control_service_impl.cpp
  src/grpc_server/perception_service_impl.cpp
  src/grpc_server/safety_service_impl.cpp
  src/utils/pose_utils.cpp
  src/utils/coordinate_transform.cpp
  src/utils/time_utils.cpp
  src/utils/logger.cpp
  src/utils/thread_pool.cpp
  src/grpc_client/brain_ai_client.cpp
)

set(BRAIN_CORE_LINK_LIBS
  ${Protobuf_LIBRARIES}
  gRPC::grpc++
)
if(NOT BRAIN_CORE_SKIP_ROS2)
  list(APPEND BRAIN_CORE_LINK_LIBS
    ${rclcpp_LIBRARIES}
    ${geometry_msgs_LIBRARIES}
    ${sensor_msgs_LIBRARIES}
    ${tf2_LIBRARIES}
    ${tf2_geometry_msgs_LIBRARIES}
    ${visualization_msgs_LIBRARIES}
    ${builtin_interfaces_LIBRARIES}
    ${nav_msgs_LIBRARIES}
    ${trajectory_msgs_LIBRARIES}
  )
endif()
target_link_libraries(brain_core_lib ${BRAIN_CORE_LINK_LIBS})

# ── Main executable ────────────────────────────────────────
add_executable(brain_core_node src/main.cpp)
target_link_libraries(brain_core_node brain_core_lib)

# ── Install ────────────────────────────────────────────────
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY config/ DESTINATION share/${PROJECT_NAME}/config)
install(DIRECTORY launch/ DESTINATION share/${PROJECT_NAME}/launch)
install(TARGETS brain_core_node brain_core_lib
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

# ── Tests (optional) ───────────────────────────────────────
if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  enable_testing()
  add_subdirectory(test)
endif()

ament_package()
