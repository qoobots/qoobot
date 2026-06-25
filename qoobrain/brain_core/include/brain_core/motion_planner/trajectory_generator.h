// motion_planner/trajectory_generator.h — Multi-strategy trajectory generation
#pragma once

#include "brain_core/core_types.h"
#include <vector>
#include <string>
#include <functional>

namespace brain_core {

/// Trajectory generation strategy types.
enum class TrajectoryStrategy {
    OPTIMAL,        // shortest path, best score
    CONSERVATIVE,   // wider margins, slower
    AGGRESSIVE,     // speed-optimized
    EXPLORATORY,    // varied paths for HITL comparison
    ADVERSARIAL,    // intentionally different for contrast
};

/// Strategy configuration parameters.
struct StrategyConfig {
    TrajectoryStrategy type{TrajectoryStrategy::OPTIMAL};
    double position_weight{0.3};
    double time_weight{0.2};
    double collision_weight{0.25};
    double manipulability_weight{0.1};
    double torque_weight{0.1};
    double smoothness_weight{0.05};
    double max_velocity_scale{1.0};
    double max_accel_scale{1.0};
};

class TrajectoryGenerator {
public:
    TrajectoryGenerator();

    /// Generate a single trajectory with the given strategy.
    Trajectory generate(const std::vector<double>& start_joints,
                         const std::vector<double>& goal_joints,
                         TrajectoryStrategy strategy = TrajectoryStrategy::OPTIMAL,
                         double duration_sec = 2.0);

    /// Generate multiple trajectories using all strategies.
    std::vector<Trajectory> generateAll(const std::vector<double>& start_joints,
                                         const std::vector<double>& goal_joints,
                                         double duration_sec = 2.0);

    /// Generate to Cartesian pose (via IK then trajectory).
    Trajectory generateToPose(double x, double y, double z,
                               double qx, double qy, double qz, double qw,
                               const std::vector<double>& start_joints,
                               TrajectoryStrategy strategy = TrajectoryStrategy::OPTIMAL);

    /// Set the strategy configuration.
    void setStrategyConfig(TrajectoryStrategy type, const StrategyConfig& config);

    /// Get strategy configuration.
    const StrategyConfig& getStrategyConfig(TrajectoryStrategy type) const;

    /// Set the number of waypoints for trajectory interpolation.
    void setWaypointCount(int count);

private:
    Trajectory _interpolateLinear(const std::vector<double>& start,
                                   const std::vector<double>& goal,
                                   double duration_sec, int waypoint_count);

    Trajectory _interpolateTrapezoidal(const std::vector<double>& start,
                                        const std::vector<double>& goal,
                                        double duration_sec, int waypoint_count,
                                        double vmax_scale, double amax_scale);

    double _computeScore(const Trajectory& traj, const StrategyConfig& config);

    // Default strategy configs
    std::vector<StrategyConfig> _configs;
    int _waypoint_count{50};
};

} // namespace brain_core
