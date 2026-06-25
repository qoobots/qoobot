// brain_core/core_types.h — Common types shared across all modules
#pragma once

#include <string>
#include <chrono>
#include <vector>
#include <optional>
#include <memory>

namespace brain_core {

// ── ROS 2 Handle Types ────────────────────────────────────
using NodeHandle    = void*;   // rclcpp::Node*
using TimerHandle   = void*;   // rclcpp::TimerBase::SharedPtr
using PubHandle     = void*;   // rclcpp::PublisherBase::SharedPtr
using SubHandle     = void*;   // rclcpp::SubscriptionBase::SharedPtr
using ClientHandle  = void*;   // rclcpp::ClientBase::SharedPtr
using ServiceHandle = void*;   // rclcpp::ServiceBase::SharedPtr

// ── Domain Events ─────────────────────────────────────────
enum class EventType {
    NODE_STARTED,
    NODE_STOPPED,
    NODE_ERROR,
    SAFETY_BREACH,
    TASK_RECEIVED,
    TASK_COMPLETED,
    TRAJECTORY_GENERATED,
    PERCEPTION_UPDATE,
    COLLISION_WARNING,
    EMERGENCY_STOP,
};

struct DomainEvent {
    EventType     type;
    std::string   source_node;
    std::string   payload;
    std::chrono::system_clock::time_point timestamp;
};

// ── Safety Enums ──────────────────────────────────────────
enum class SafetyLevel {
    NORMAL     = 0,
    WARNING    = 1,
    CRITICAL   = 2,
    EMERGENCY  = 3,
};

enum class SafetyZone {
    SAFE       = 0,
    CAUTION    = 1,
    DANGER     = 2,
};

// ── Behavior Tree ─────────────────────────────────────────
enum class BTNodeStatus {
    IDLE,
    RUNNING,
    SUCCESS,
    FAILURE,
};

// ── Trajectory ────────────────────────────────────────────
struct TrajectoryWaypoint {
    double x, y, z;               // position
    double qx, qy, qz, qw;        // orientation quaternion
    double time_from_start_sec;
};

struct Trajectory {
    std::string                name;
    std::vector<TrajectoryWaypoint> waypoints;
    double                     score{0.0};  // quality metric
    bool                       collision_free{true};
};

// ── Sensor Frame ──────────────────────────────────────────
struct SensorFrame {
    std::string source_id;
    std::vector<uint8_t> rgb_data;      // compressed or raw RGB
    std::vector<float>    depth_data;   // depth in meters
    int width{0}, height{0};
    std::chrono::system_clock::time_point stamp;
};

// ── Robot State ───────────────────────────────────────────
struct JointState {
    std::vector<std::string> names;
    std::vector<double>      positions;
    std::vector<double>      velocities;
    std::vector<double>      efforts;
};

struct RobotState {
    JointState   joints;
    double       gripper_position{0.0};  // 0.0=closed, 1.0=open
    bool         emergency_stop_active{false};
    SafetyLevel  safety_level{SafetyLevel::NORMAL};
};

} // namespace brain_core
