// ============================================================================
// navigation_multifloor_narrow.cpp — Multi-floor & narrow passage navigation
// Part of qoosvc::navigation::NavigationService (PIMPL extension)
// ============================================================================

#include "qoosvc/navigation/navigation_service.h"
#include <algorithm>
#include <cmath>
#include <queue>
#include <set>
#include <unordered_map>

namespace qoosvc::navigation {

// ============================================================================
// Multi-Floor Navigation
// ============================================================================

Result<void> NavigationService::register_floor(const FloorInfo& floor) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // Check for duplicate floor ID
    auto it = std::find_if(impl_->floors.begin(), impl_->floors.end(),
        [&](const auto& f) { return f.floor_id == floor.floor_id; });

    if (it != impl_->floors.end()) {
        *it = floor;  // Update existing
    } else {
        impl_->floors.push_back(floor);
    }

    return Result<void>::ok();
}

Result<void> NavigationService::remove_floor(int32_t floor_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->floors.begin(), impl_->floors.end(),
        [floor_id](const auto& f) { return f.floor_id == floor_id; });

    if (it == impl_->floors.end()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
            "Floor not found: " + std::to_string(floor_id));
    }

    impl_->floors.erase(it);
    return Result<void>::ok();
}

std::vector<FloorInfo> NavigationService::get_floors() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->floors;
}

Result<void> NavigationService::navigate_to_floor(const NavigationGoal& goal,
                                                    int32_t target_floor_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->floors.empty()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
            "No floors registered. Use register_floor() first.");
    }

    int32_t current_floor = get_current_floor();

    // Find target floor info
    auto target_it = std::find_if(impl_->floors.begin(), impl_->floors.end(),
        [target_floor_id](const auto& f) { return f.floor_id == target_floor_id; });
    if (target_it == impl_->floors.end()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
            "Target floor not registered: " + std::to_string(target_floor_id));
    }

    auto current_it = std::find_if(impl_->floors.begin(), impl_->floors.end(),
        [current_floor](const auto& f) { return f.floor_id == current_floor; });
    if (current_it == impl_->floors.end()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
            "Current floor not registered: " + std::to_string(current_floor));
    }

    if (current_floor == target_floor_id) {
        // Same floor — use standard navigation
        return navigate_to(goal);
    }

    // Multi-floor path planning:
    // Phase 1: Navigate to elevator/stair on current floor
    // Phase 2: Use elevator or stair to reach target floor
    // Phase 3: Navigate from elevator/stair to goal on target floor

    bool going_up = (target_floor_id > current_floor);

    // Select elevator entrance as transfer point (preferred over stairs)
    Pose3D transfer_point;
    bool found_transfer = false;

    if (!target_it->elevator_entrances.empty()) {
        // Find nearest elevator entrance on current floor
        double min_dist = std::numeric_limits<double>::max();
        for (const auto& entrance : current_it->elevator_entrances) {
            double dist = std::hypot(
                entrance.x - impl_->current_status.current_pose.x,
                entrance.y - impl_->current_status.current_pose.y);
            if (dist < min_dist) {
                min_dist = dist;
                transfer_point = entrance;
                found_transfer = true;
            }
        }
    }

    if (!found_transfer && !current_it->stair_entrances.empty()) {
        // Fall back to stairs
        double min_dist = std::numeric_limits<double>::max();
        for (const auto& entrance : current_it->stair_entrances) {
            double dist = std::hypot(
                entrance.x - impl_->current_status.current_pose.x,
                entrance.y - impl_->current_status.current_pose.y);
            if (dist < min_dist) {
                min_dist = dist;
                transfer_point = entrance;
                found_transfer = true;
            }
        }
    }

    if (!found_transfer) {
        return Result<void>::err(ErrorCode::NAV_NO_PATH,
            "No elevator or stair entrance found on current floor");
    }

    // Phase 1: Navigate to transfer point
    NavigationGoal transfer_goal;
    transfer_goal.target_pose = transfer_point;
    transfer_goal.goal_name = "Floor transfer point (Floor " +
                              std::to_string(current_floor) + " → " +
                              std::to_string(target_floor_id) + ")";

    auto phase1_result = navigate_to(transfer_goal);
    if (phase1_result.is_err()) {
        return phase1_result;
    }

    // In production: Phase 2 would involve elevator interaction
    // (wait for elevator, enter, select floor, exit) or stair traversal
    // For framework: mark elevator state
    impl_->elevator_state = ElevatorState::WAITING_FOR_ELEVATOR;

    // Phase 3: Navigate to final goal on target floor (after floor transition)
    // In production, this triggers after floor arrival detection
    impl_->target_floor_id = target_floor_id;
    impl_->pending_goal_on_target_floor = goal;

    return Result<void>::ok();
}

int32_t NavigationService::get_current_floor() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    double current_z = impl_->current_status.current_pose.z;

    // Find which floor the robot is on based on Z position
    int32_t best_floor = 0;
    double best_diff = std::numeric_limits<double>::max();

    for (const auto& floor : impl_->floors) {
        double diff = std::abs(current_z - floor.floor_height);
        if (diff < best_diff && diff < 3.0) {  // Within 3m of floor height
            best_diff = diff;
            best_floor = floor.floor_id;
        }
    }

    return best_floor;
}

ElevatorState NavigationService::get_elevator_state() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->elevator_state;
}

// ============================================================================
// Narrow Passage Navigation
// ============================================================================

Result<void> NavigationService::configure_narrow_passage(const NarrowPassageConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    config_.narrow_passage = config;
    return Result<void>::ok();
}

bool NavigationService::is_narrow_passage_ahead(const NavigationPath& path) const {
    if (path.waypoints.empty()) return false;

    std::lock_guard<std::mutex> lock(impl_->mutex);
    const auto& cfg = config_.narrow_passage;

    // Check clearance along the path
    // For each waypoint, estimate corridor width from obstacles on both sides
    double min_clearance = std::numeric_limits<double>::max();

    for (const auto& wp : path.waypoints) {
        // Calculate lateral clearance: check obstacles to left and right of path direction
        double clearance_left = cfg.robot_normal_width * 2.0;
        double clearance_right = cfg.robot_normal_width * 2.0;

        for (const auto& obs : impl_->obstacles) {
            // Project obstacle onto perpendicular to path direction
            double dx = obs.pose.x - wp.pose.x;
            double dy = obs.pose.y - wp.pose.y;
            double dist = std::hypot(dx, dy);

            // Lateral component (rough estimate)
            double lateral = std::abs(dx);  // Simplified
            if (lateral < clearance_left && dx < 0) {
                clearance_left = lateral;
            }
            if (lateral < clearance_right && dx > 0) {
                clearance_right = lateral;
            }
        }

        double total_clearance = clearance_left + clearance_right;
        if (total_clearance < min_clearance) {
            min_clearance = total_clearance;
        }
    }

    return min_clearance < cfg.narrow_width_threshold;
}

Result<NavigationPath> NavigationService::plan_narrow_passage_path(const NavigationGoal& goal) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    const auto& cfg = config_.narrow_passage;

    // First, plan a standard global path
    auto global_path_result = plan_global_path(goal);
    if (global_path_result.is_err()) {
        return global_path_result;
    }

    NavigationPath path = *global_path_result;
    path.planner_name = "narrow_passage";

    // Check if path goes through narrow passages
    if (!is_narrow_passage_ahead(path)) {
        // No narrow passage — return standard path with slight adjustments
        for (auto& wp : path.waypoints) {
            wp.target_velocity = config_.max_linear_velocity;
        }
        return path;
    }

    // Path goes through narrow areas — optimize for narrow passage traversal
    // Strategy:
    // 1. Reduce speed in narrow segments
    // 2. Add side-slip / contraction waypoints
    // 3. Ensure minimum lateral clearance

    double robot_half_width = cfg.robot_narrow_width / 2.0;

    for (auto& wp : path.waypoints) {
        wp.target_velocity = config_.max_linear_velocity * cfg.narrow_speed_factor;

        // Adjust waypoint positions to center in narrow corridors
        // (shift away from nearby obstacles to maximize clearance)
        double best_lateral_shift = 0.0;
        double best_min_clearance = 0.0;

        for (double shift = -robot_half_width; shift <= robot_half_width; shift += 0.05) {
            double test_x = wp.pose.x + shift;
            double min_dist = std::numeric_limits<double>::max();

            for (const auto& obs : impl_->obstacles) {
                double dist = std::hypot(test_x - obs.pose.x, wp.pose.y - obs.pose.y)
                              - obs.radius;
                if (dist < min_dist) min_dist = dist;
            }

            if (min_dist > best_min_clearance) {
                best_min_clearance = min_dist;
                best_lateral_shift = shift;
            }
        }

        // Apply lateral shift if it improves clearance
        if (best_lateral_shift != 0.0 && best_min_clearance > cfg.side_slip_tolerance) {
            wp.pose.x += best_lateral_shift;
        }
    }

    // Mark path as narrow passage traversal
    impl_->in_narrow_passage = true;

    return path;
}

Result<void> NavigationService::execute_narrow_passage(const NavigationPath& path) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    const auto& cfg = config_.narrow_passage;

    // Set robot to narrow/contracted pose
    if (cfg.enable_contraction) {
        // In production: send joint contraction command to qoobody
        // For framework: mark contraction state
        impl_->robot_contracted = true;

        // Log joint angles for contraction
        if (!cfg.contraction_joint_angles.empty()) {
            // Apply contraction joint configuration
            // e.g., fold arms, lower head, tuck sensors
        }
    }

    // Store path for execution
    impl_->current_path = path;
    impl_->navigating = true;
    impl_->in_narrow_passage = true;
    state_ = NavigationState::FOLLOWING_PATH;

    // Reduce speed during narrow passage traversal
    impl_->current_status.current_velocity = config_.max_linear_velocity * cfg.narrow_speed_factor;

    return Result<void>::ok();
}

} // namespace qoosvc::navigation
