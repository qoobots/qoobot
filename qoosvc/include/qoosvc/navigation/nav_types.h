#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::navigation {

/**
 * 3D pose with orientation quaternion.
 */
struct Pose3D {
    double x = 0.0, y = 0.0, z = 0.0;
    double qx = 0.0, qy = 0.0, qz = 0.0, qw = 1.0;
    std::string frame_id = "map";
};

/**
 * Navigation goal.
 */
struct NavigationGoal {
    Pose3D target_pose;
    double goal_tolerance_xy = 0.1;     // meters
    double goal_tolerance_yaw = 0.1;    // radians
    std::string goal_name;              // Human-readable name
};

/**
 * Waypoint along a path.
 */
struct Waypoint {
    Pose3D pose;
    double target_velocity = 0.5;       // m/s
    double time_from_start = 0.0;       // seconds
};

/**
 * Navigation path — sequence of waypoints.
 */
struct NavigationPath {
    std::vector<Waypoint> waypoints;
    double total_length = 0.0;          // meters
    double estimated_time = 0.0;        // seconds
    std::string planner_name;           // "global_a_star", "local_teb", etc.
};

/**
 * Navigation state enumeration.
 */
enum class NavigationState : uint8_t {
    IDLE,
    PLANNING,
    FOLLOWING_PATH,
    GOAL_REACHED,
    ABORTED,
    RECOVERING,
    ERROR
};

/**
 * Navigation status update.
 */
struct NavigationStatus {
    NavigationState state = NavigationState::IDLE;
    Pose3D current_pose;
    double distance_to_goal = 0.0;      // meters
    double time_to_goal = 0.0;          // seconds (estimated)
    int32_t current_waypoint_index = -1;
    double current_velocity = 0.0;      // m/s
    std::string message;
};

/**
 * Obstacle information.
 */
struct Obstacle {
    Pose3D pose;
    double radius = 0.3;                // meters (bounding cylinder radius)
    double height = 1.0;                // meters
    double velocity_x = 0.0;            // m/s (for dynamic obstacles)
    double velocity_y = 0.0;
    std::string type;                   // "static", "dynamic", "human", "pet"
    float confidence = 1.0f;
};

/**
 * Zone definition for restricted areas.
 */
struct Zone {
    enum class Type : uint8_t {
        FORBIDDEN,      // Cannot enter
        SPEED_LIMIT,    // Reduced speed
        PREFERRED,      // Preferred navigation area
        CHARGING        // Charging dock area
    };

    std::string name;
    Type type = Type::FORBIDDEN;
    std::vector<Pose3D> boundary;       // Polygon boundary vertices
    double speed_limit = 0.5;           // m/s (for SPEED_LIMIT zones)
};

/**
 * Floor level information for multi-floor navigation.
 */
struct FloorInfo {
    int32_t floor_id = 0;               // Floor index (0 = ground)
    std::string floor_name;             // Human-readable name (e.g., "1F", "B1")
    double floor_height = 0.0;          // Height relative to ground (meters)
    std::string map_file_path;          // Floor-specific map file
    std::vector<Pose3D> elevator_entrances;  // Elevator entry positions
    std::vector<Pose3D> stair_entrances;     // Stair entry positions
};

/**
 * Elevator interaction state.
 */
enum class ElevatorState : uint8_t {
    WAITING_FOR_ELEVATOR,
    ENTERING_ELEVATOR,
    INSIDE_ELEVATOR,
    EXITING_ELEVATOR,
    ELEVATOR_ERROR
};

/**
 * Narrow passage navigation config.
 */
struct NarrowPassageConfig {
    double narrow_width_threshold = 0.8;    // meters, below this is "narrow"
    double robot_normal_width = 0.65;       // meters, robot width in normal pose
    double robot_narrow_width = 0.45;       // meters, robot width in slim/sideways pose
    double narrow_speed_factor = 0.3;       // Speed reduction in narrow passages
    double side_slip_tolerance = 0.05;      // meters, lateral clearance tolerance
    bool enable_contraction = true;         // Whether robot can contract joints
    std::vector<double> contraction_joint_angles;  // Target joint angles for slim pose
};

/**
 * Navigation configuration.
 */
struct NavigationConfig {
    double max_linear_velocity = 1.0;   // m/s
    double max_angular_velocity = 1.0;  // rad/s
    double min_obstacle_distance = 0.3; // meters
    double inflation_radius = 0.5;      // meters (costmap inflation)
    double goal_tolerance_xy = 0.1;     // meters
    double goal_tolerance_yaw = 0.1;    // radians
    std::string global_planner = "a_star";
    std::string local_planner = "teb";
    bool use_dynamic_obstacle_avoidance = true;
    // Multi-floor
    bool enable_multi_floor = false;
    std::vector<FloorInfo> floors;
    NarrowPassageConfig narrow_passage;
};

} // namespace qoosvc::navigation
