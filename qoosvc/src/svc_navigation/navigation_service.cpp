#include "qoosvc/navigation/navigation_service.h"
#include <algorithm>
#include <cmath>
#include <mutex>
#include <queue>

namespace qoosvc::navigation {

// ============================================================================
// NavigationService::Impl
// ============================================================================

struct NavigationService::Impl {
    NavigationStatus current_status;
    NavigationGoal current_goal;
    NavigationPath current_path;
    std::vector<Obstacle> obstacles;
    std::vector<Zone> zones;
    std::function<void(const NavigationStatus&)> status_callback;
    bool navigating = false;
    bool exploring = false;

    // Multi-floor
    std::vector<FloorInfo> floors;
    ElevatorState elevator_state = ElevatorState::WAITING_FOR_ELEVATOR;
    int32_t target_floor_id = 0;
    NavigationGoal pending_goal_on_target_floor;

    // Narrow passage
    bool in_narrow_passage = false;
    bool robot_contracted = false;

    mutable std::mutex mutex;
};

// ============================================================================
// Constructor / Destructor
// ============================================================================

NavigationService::NavigationService()
    : ServiceBase("navigation_service")
    , impl_(std::make_unique<Impl>()) {
}

NavigationService::~NavigationService() {
    stop();
}

// ============================================================================
// Configuration
// ============================================================================

Result<void> NavigationService::configure(const NavigationConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    config_ = config;
    return Result<void>::ok();
}

// ============================================================================
// Path Planning
// ============================================================================

Result<NavigationPath> NavigationService::plan_global_path(const NavigationGoal& goal) {
    // In production, this uses A* or Dijkstra on the global costmap
    // The costmap is provided by qoobrain's SLAM module

    NavigationPath path;
    path.planner_name = config_.global_planner;

    // Generate a simple straight-line path as placeholder
    // Real implementation would use occupancy grid + A* search
    Pose3D start = impl_->current_status.current_pose;
    Pose3D end = goal.target_pose;

    int num_waypoints = std::max(2, static_cast<int>(
        std::hypot(end.x - start.x, end.y - start.y) / 0.5));

    for (int i = 0; i <= num_waypoints; ++i) {
        double t = static_cast<double>(i) / num_waypoints;
        Waypoint wp;
        wp.pose.x = start.x + (end.x - start.x) * t;
        wp.pose.y = start.y + (end.y - start.y) * t;
        wp.pose.z = start.z + (end.z - start.z) * t;
        wp.pose.frame_id = "map";
        wp.target_velocity = config_.max_linear_velocity;
        wp.time_from_start = t * std::hypot(end.x - start.x, end.y - start.y)
                             / config_.max_linear_velocity;
        path.waypoints.push_back(wp);
    }

    path.total_length = std::hypot(end.x - start.x, end.y - start.y);
    path.estimated_time = path.total_length / config_.max_linear_velocity;

    return path;
}

Result<NavigationPath> NavigationService::plan_local_path(
    const NavigationPath& global_path,
    const std::vector<Obstacle>& obstacles) {

    if (global_path.waypoints.empty()) {
        return Result<NavigationPath>::err(ErrorCode::NAV_NO_PATH, "Global path is empty");
    }

    // In production, this uses TEB or DWA for local trajectory optimization
    // considering dynamic obstacles and robot kinematics

    NavigationPath local_path = global_path;
    local_path.planner_name = config_.local_planner;

    // Check for obstacles near the path
    for (const auto& obstacle : obstacles) {
        for (auto& wp : local_path.waypoints) {
            double dist = std::hypot(wp.pose.x - obstacle.pose.x,
                                      wp.pose.y - obstacle.pose.y);
            if (dist < config_.min_obstacle_distance + obstacle.radius) {
                // Adjust waypoint to avoid obstacle (simplified)
                double dx = wp.pose.x - obstacle.pose.x;
                double dy = wp.pose.y - obstacle.pose.y;
                double scale = (config_.min_obstacle_distance + obstacle.radius) / dist;
                wp.pose.x = obstacle.pose.x + dx * scale;
                wp.pose.y = obstacle.pose.y + dy * scale;
                wp.target_velocity *= 0.5;  // Slow down near obstacles
            }
        }
    }

    return local_path;
}

// ============================================================================
// Navigation Control
// ============================================================================

Result<void> NavigationService::navigate_to(const NavigationGoal& goal) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    impl_->current_goal = goal;

    // Plan global path
    auto path_result = plan_global_path(goal);
    if (path_result.is_err()) {
        state_ = NavigationState::ERROR;
        return Result<void>::err(path_result.error_code(), path_result.error_message());
    }

    // Plan local path considering current obstacles
    auto local_result = plan_local_path(*path_result, impl_->obstacles);
    if (local_result.is_err()) {
        state_ = NavigationState::ERROR;
        return Result<void>::err(local_result.error_code(), local_result.error_message());
    }

    impl_->current_path = *local_result;
    impl_->navigating = true;
    state_ = NavigationState::FOLLOWING_PATH;

    // Update status
    impl_->current_status.state = NavigationState::FOLLOWING_PATH;
    impl_->current_status.distance_to_goal = impl_->current_path.total_length;
    impl_->current_status.time_to_goal = impl_->current_path.estimated_time;
    impl_->current_status.current_waypoint_index = 0;

    if (impl_->status_callback) {
        impl_->status_callback(impl_->current_status);
    }

    return Result<void>::ok();
}

Result<void> NavigationService::navigate_waypoints(const std::vector<NavigationGoal>& waypoints) {
    if (waypoints.empty()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "Waypoint list is empty");
    }

    // Navigate to first waypoint, subsequent waypoints handled on arrival
    return navigate_to(waypoints.front());
}

Result<void> NavigationService::cancel_navigation() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->navigating = false;
    impl_->exploring = false;
    state_ = NavigationState::IDLE;
    impl_->current_status.state = NavigationState::IDLE;
    return Result<void>::ok();
}

Result<void> NavigationService::pause_navigation() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->navigating) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "Not currently navigating");
    }
    state_ = NavigationState::IDLE;
    impl_->current_status.state = NavigationState::IDLE;
    return Result<void>::ok();
}

Result<void> NavigationService::resume_navigation() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (!impl_->navigating) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "No navigation to resume");
    }
    return navigate_to(impl_->current_goal);
}

// ============================================================================
// Status
// ============================================================================

NavigationStatus NavigationService::get_status() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->current_status;
}

void NavigationService::on_status_update(std::function<void(const NavigationStatus&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->status_callback = std::move(callback);
}

// ============================================================================
// Obstacle Management
// ============================================================================

Result<void> NavigationService::update_obstacles(const std::vector<Obstacle>& obstacles) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->obstacles = obstacles;

    // Re-plan local path if navigating and obstacles changed significantly
    if (impl_->navigating && !obstacles.empty()) {
        auto result = plan_local_path(impl_->current_path, obstacles);
        if (result.is_ok()) {
            impl_->current_path = *result;
        }
    }

    return Result<void>::ok();
}

bool NavigationService::is_pose_safe(const Pose3D& pose) const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    for (const auto& obs : impl_->obstacles) {
        double dist = std::hypot(pose.x - obs.pose.x, pose.y - obs.pose.y);
        if (dist < config_.min_obstacle_distance + obs.radius) {
            return false;
        }
    }

    // Check forbidden zones
    for (const auto& zone : impl_->zones) {
        if (zone.type == Zone::Type::FORBIDDEN && is_point_in_polygon(pose, zone.boundary)) {
            return false;
        }
    }

    return true;
}

// ============================================================================
// Zone Management
// ============================================================================

Result<void> NavigationService::add_zone(const Zone& zone) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // Check for duplicate names
    auto it = std::find_if(impl_->zones.begin(), impl_->zones.end(),
        [&](const Zone& z) { return z.name == zone.name; });
    if (it != impl_->zones.end()) {
        *it = zone;  // Update existing zone
    } else {
        impl_->zones.push_back(zone);
    }

    return Result<void>::ok();
}

Result<void> NavigationService::remove_zone(const std::string& zone_name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->zones.begin(), impl_->zones.end(),
        [&](const Zone& z) { return z.name == zone_name; });
    if (it == impl_->zones.end()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "Zone not found: " + zone_name);
    }

    impl_->zones.erase(it);
    return Result<void>::ok();
}

std::vector<Zone> NavigationService::get_zones() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->zones;
}

bool NavigationService::is_in_forbidden_zone(const Pose3D& pose) const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    for (const auto& zone : impl_->zones) {
        if (zone.type == Zone::Type::FORBIDDEN && is_point_in_polygon(pose, zone.boundary)) {
            return true;
        }
    }
    return false;
}

// ============================================================================
// Exploration
// ============================================================================

Result<void> NavigationService::start_exploration() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->exploring = true;
    // In production, this would start frontier-based exploration
    return Result<void>::ok();
}

Result<void> NavigationService::stop_exploration() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->exploring = false;
    return Result<void>::ok();
}

// ============================================================================
// Recovery
// ============================================================================

Result<void> NavigationService::recover() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    state_ = NavigationState::RECOVERING;

    // Recovery strategies (in order):
    // 1. Rotate in place to clear costmap
    // 2. Back up slightly
    // 3. Re-plan from current position

    // Simplified: just mark as recovered and re-plan
    state_ = NavigationState::IDLE;
    impl_->current_status.state = NavigationState::IDLE;

    return Result<void>::ok();
}

// ============================================================================
// Service Lifecycle
// ============================================================================

Result<void> NavigationService::on_initialize() {
    state_ = NavigationState::IDLE;
    impl_->current_status.state = NavigationState::IDLE;
    return Result<void>::ok();
}

Result<void> NavigationService::on_stop() {
    cancel_navigation();
    return Result<void>::ok();
}

// ============================================================================
// Helper: Point-in-polygon test (ray casting algorithm)
// ============================================================================

bool NavigationService::is_point_in_polygon(const Pose3D& point,
                                              const std::vector<Pose3D>& polygon) const {
    if (polygon.size() < 3) return false;

    bool inside = false;
    size_t n = polygon.size();
    for (size_t i = 0, j = n - 1; i < n; j = i++) {
        double xi = polygon[i].x, yi = polygon[i].y;
        double xj = polygon[j].x, yj = polygon[j].y;

        if (((yi > point.y) != (yj > point.y)) &&
            (point.x < (xj - xi) * (point.y - yi) / (yj - yi) + xi)) {
            inside = !inside;
        }
    }
    return inside;
}

} // namespace qoosvc::navigation
