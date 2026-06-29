#pragma once

#include "nav_types.h"
#include "../common/result.h"
#include "../common/service_base.h"
#include <functional>
#include <memory>
#include <vector>

namespace qoosvc::navigation {

/**
 * NavigationService — Robot autonomous navigation engine.
 *
 * Provides global path planning, local trajectory optimization,
 * dynamic obstacle avoidance, zone management, and navigation recovery.
 */
class NavigationService : public ServiceBase {
public:
    NavigationService();
    ~NavigationService() override;

    // --- Configuration ---

    Result<void> configure(const NavigationConfig& config);
    const NavigationConfig& config() const { return config_; }

    // --- Path Planning ---

    /**
     * Plan a global path from current position to goal.
     * Uses A* or Dijkstra on the global costmap.
     */
    Result<NavigationPath> plan_global_path(const NavigationGoal& goal);

    /**
     * Plan a local trajectory considering dynamic obstacles.
     * Uses TEB (Timed Elastic Band) or DWA (Dynamic Window Approach).
     */
    Result<NavigationPath> plan_local_path(const NavigationPath& global_path,
                                            const std::vector<Obstacle>& obstacles);

    // --- Navigation Control ---

    /**
     * Start navigating to a goal. Combines global + local planning.
     */
    Result<void> navigate_to(const NavigationGoal& goal);

    /**
     * Navigate through a sequence of waypoints.
     */
    Result<void> navigate_waypoints(const std::vector<NavigationGoal>& waypoints);

    /**
     * Cancel current navigation.
     */
    Result<void> cancel_navigation();

    /**
     * Pause navigation (hold position).
     */
    Result<void> pause_navigation();

    /**
     * Resume paused navigation.
     */
    Result<void> resume_navigation();

    // --- Status ---

    NavigationStatus get_status() const;
    NavigationState get_state() const { return state_; }

    /**
     * Register a callback for navigation status updates.
     */
    void on_status_update(std::function<void(const NavigationStatus&)> callback);

    // --- Obstacle Management ---

    /**
     * Update the obstacle list for dynamic obstacle avoidance.
     */
    Result<void> update_obstacles(const std::vector<Obstacle>& obstacles);

    /**
     * Check if a pose is safe (no collision with known obstacles).
     */
    bool is_pose_safe(const Pose3D& pose) const;

    // --- Zone Management ---

    /**
     * Define a navigation zone (forbidden, speed limit, preferred, charging).
     */
    Result<void> add_zone(const Zone& zone);

    /**
     * Remove a zone by name.
     */
    Result<void> remove_zone(const std::string& zone_name);

    /**
     * Get all defined zones.
     */
    std::vector<Zone> get_zones() const;

    /**
     * Check if a pose is inside a forbidden zone.
     */
    bool is_in_forbidden_zone(const Pose3D& pose) const;

    // --- Exploration ---

    /**
     * Start autonomous exploration of unknown environment.
     * Uses frontier-based exploration with information gain.
     */
    Result<void> start_exploration();

    /**
     * Stop exploration.
     */
    Result<void> stop_exploration();

    // --- Multi-Floor Navigation ---

    /**
     * Register a floor with its map and access points (elevator/stair).
     */
    Result<void> register_floor(const FloorInfo& floor);

    /**
     * Remove a registered floor.
     */
    Result<void> remove_floor(int32_t floor_id);

    /**
     * Get all registered floors.
     */
    std::vector<FloorInfo> get_floors() const;

    /**
     * Navigate to a goal on a different floor.
     * Plans cross-floor path: floor traversal → elevator/stair → target floor.
     */
    Result<void> navigate_to_floor(const NavigationGoal& goal, int32_t target_floor_id);

    /**
     * Get current floor ID based on robot position.
     */
    int32_t get_current_floor() const;

    /**
     * Get current elevator interaction state.
     */
    ElevatorState get_elevator_state() const;

    // --- Narrow Passage ---

    /**
     * Configure narrow passage behavior.
     */
    Result<void> configure_narrow_passage(const NarrowPassageConfig& config);

    /**
     * Check if the path ahead is a narrow passage (below threshold width).
     */
    bool is_narrow_passage_ahead(const NavigationPath& path) const;

    /**
     * Plan a path optimized for narrow passage traversal.
     * Uses side-slip / contraction strategies when needed.
     */
    Result<NavigationPath> plan_narrow_passage_path(const NavigationGoal& goal);

    /**
     * Execute narrow passage traversal with contraction.
     * Robot adjusts joint positions for minimum width.
     */
    Result<void> execute_narrow_passage(const NavigationPath& path);

    // --- Recovery ---

    /**
     * Attempt to recover from navigation failure.
     * Strategies: rotate in place, back up, re-localize.
     */
    Result<void> recover();

protected:
    Result<void> on_initialize() override;
    Result<void> on_stop() override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;

    NavigationConfig config_;
    NavigationState state_ = NavigationState::IDLE;
};

} // namespace qoosvc::navigation
