#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::multi_robot {

struct Pose3D {
    double x = 0, y = 0, z = 0;
    double roll = 0, pitch = 0, yaw = 0;
    std::string frame_id = "map";
};

struct RobotCapability {
    bool has_manipulator = false;
    bool has_lifting = false;
    double max_payload_kg = 0.0;
    double max_speed_ms = 1.0;
    double battery_remaining = 0.0;
    std::vector<std::string> skills;
};

struct RobotInfo {
    std::string robot_id;
    std::string name;
    std::string model;
    Pose3D pose;
    RobotCapability capability;
    std::string status;  // "idle", "busy", "charging", "error"
    int64_t last_heartbeat_us = 0;
    std::string ip_address;
    int32_t port = 0;
};

struct DiscoveryResult {
    std::vector<RobotInfo> robots;
    int64_t timestamp_us = 0;
};

// ========================================================================
// Task Types
// ========================================================================

enum class TaskType : uint8_t {
    TRANSPORT,       // Move object from A to B
    PATROL,          // Security patrol route
    CLEAN,           // Cleaning area
    INSPECT,         // Visual inspection
    DELIVERY,        // Deliver item to person
    CO_CARRY,        // Multi-robot cooperative carrying
    SURVEILLANCE,    // Area monitoring
    CUSTOM           // User-defined task
};

enum class TaskPriority : uint8_t {
    LOW = 0,
    NORMAL = 50,
    HIGH = 100,
    CRITICAL = 200
};

struct TaskRequirement {
    bool needs_manipulator = false;
    double min_payload_kg = 0.0;
    double min_battery = 0.2;
    std::vector<std::string> required_skills;
};

struct CooperativeTask {
    std::string task_id;
    TaskType type = TaskType::TRANSPORT;
    TaskPriority priority = TaskPriority::NORMAL;
    std::string description;
    Pose3D start_pose;
    Pose3D goal_pose;
    TaskRequirement requirements;
    int32_t required_robots = 1;
    int32_t assigned_robots = 0;
    std::vector<std::string> assigned_robot_ids;
    double estimated_duration_s = 0.0;
    int64_t created_at_us = 0;
    int64_t deadline_us = 0;
};

struct TaskAllocationResult {
    std::string task_id;
    bool success = false;
    std::vector<std::string> assigned_robot_ids;
    std::string reason;
};

// ========================================================================
// Cooperative Carrying Types
// ========================================================================

struct CoCarryConfig {
    std::string object_id;
    double object_mass_kg = 0.0;
    double object_length_m = 0.0;
    double object_width_m = 0.0;
    int32_t num_robots = 2;
    std::string leader_robot_id;
    std::vector<std::string> follower_robot_ids;
    double formation_distance_m = 1.0;
    double max_velocity_ms = 0.5;
};

struct CoCarryStatus {
    bool active = false;
    Pose3D object_pose;
    Pose3D target_pose;
    double progress = 0.0;
    std::string leader_id;
    std::vector<std::string> active_followers;
    bool all_synced = false;
};

// ========================================================================
// Information Sharing Types
// ========================================================================

enum class SharedDataType : uint8_t {
    MAP_UPDATE,        // Partial map update
    OBSTACLE,          // Dynamic obstacle location
    OBJECT_DETECTION,  // Detected object info
    SEMANTIC_LABEL,    // Room/object label
    BATTERY_STATUS,    // Battery level sharing
    TASK_STATUS        // Task progress update
};

struct SharedData {
    SharedDataType type;
    std::string source_robot_id;
    std::string data;            // Serialized data (JSON/protobuf)
    int64_t timestamp_us = 0;
    double confidence = 1.0;
    int32_t ttl_ms = 5000;       // Time-to-live for transient data
};

struct LoadBalanceInfo {
    std::string robot_id;
    double cpu_usage = 0.0;
    double memory_usage = 0.0;
    double battery_level = 0.0;
    int32_t active_tasks = 0;
    int32_t queued_tasks = 0;
    double load_score = 0.0;     // Computed load metric
};

} // namespace qoosvc::multi_robot
