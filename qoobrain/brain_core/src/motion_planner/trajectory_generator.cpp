// motion_planner/trajectory_generator.cpp — Multi-strategy trajectory generation
#include "brain_core/motion_planner/trajectory_generator.h"
#include "brain_core/motion_planner/ik_solver.h"
#include <iostream>
#include <cmath>
#include <algorithm>

namespace brain_core {

TrajectoryGenerator::TrajectoryGenerator()
{
    // Initialize default strategy configs
    _configs = {
        {TrajectoryStrategy::OPTIMAL,      0.30, 0.20, 0.25, 0.10, 0.10, 0.05, 1.0, 1.0},
        {TrajectoryStrategy::CONSERVATIVE, 0.15, 0.05, 0.45, 0.15, 0.10, 0.10, 0.5, 0.5},
        {TrajectoryStrategy::AGGRESSIVE,   0.10, 0.35, 0.20, 0.10, 0.15, 0.10, 1.5, 1.5},
        {TrajectoryStrategy::EXPLORATORY,  0.20, 0.10, 0.20, 0.25, 0.10, 0.15, 0.8, 0.8},
        {TrajectoryStrategy::ADVERSARIAL,  0.15, 0.15, 0.30, 0.15, 0.15, 0.10, 1.2, 1.0},
    };

    std::cout << "[TrajectoryGenerator] Initialized (" << _configs.size()
              << " strategies)." << std::endl;
}

Trajectory TrajectoryGenerator::generate(
    const std::vector<double>& start_joints,
    const std::vector<double>& goal_joints,
    TrajectoryStrategy strategy,
    double duration_sec)
{
    const StrategyConfig& config = getStrategyConfig(strategy);

    // Choose interpolation based on strategy
    Trajectory traj;
    if (strategy == TrajectoryStrategy::CONSERVATIVE) {
        traj = _interpolateTrapezoidal(start_joints, goal_joints,
                                        duration_sec, _waypoint_count, 0.5, 0.3);
    } else if (strategy == TrajectoryStrategy::AGGRESSIVE) {
        traj = _interpolateTrapezoidal(start_joints, goal_joints,
                                        duration_sec, _waypoint_count, 2.0, 2.0);
    } else {
        traj = _interpolateLinear(start_joints, goal_joints,
                                   duration_sec, _waypoint_count);
    }

    // Name the trajectory
    switch (strategy) {
        case TrajectoryStrategy::OPTIMAL:      traj.name = "optimal"; break;
        case TrajectoryStrategy::CONSERVATIVE:  traj.name = "conservative"; break;
        case TrajectoryStrategy::AGGRESSIVE:    traj.name = "aggressive"; break;
        case TrajectoryStrategy::EXPLORATORY:   traj.name = "exploratory"; break;
        case TrajectoryStrategy::ADVERSARIAL:   traj.name = "adversarial"; break;
    }

    traj.score = _computeScore(traj, config);
    traj.collision_free = (traj.score < 0.8);

    std::cout << "[TrajectoryGenerator] Generated " << traj.name
              << " trajectory (score=" << traj.score
              << ", wps=" << traj.waypoints.size() << ")" << std::endl;

    return traj;
}

std::vector<Trajectory> TrajectoryGenerator::generateAll(
    const std::vector<double>& start_joints,
    const std::vector<double>& goal_joints,
    double duration_sec)
{
    std::vector<Trajectory> results;
    std::vector<TrajectoryStrategy> strategies = {
        TrajectoryStrategy::OPTIMAL,
        TrajectoryStrategy::CONSERVATIVE,
        TrajectoryStrategy::AGGRESSIVE,
        TrajectoryStrategy::EXPLORATORY,
        TrajectoryStrategy::ADVERSARIAL,
    };

    for (auto s : strategies) {
        results.push_back(generate(start_joints, goal_joints, s, duration_sec));
    }

    // Sort by score descending
    std::sort(results.begin(), results.end(),
              [](const Trajectory& a, const Trajectory& b) {
                  return a.score > b.score;
              });

    return results;
}

Trajectory TrajectoryGenerator::generateToPose(
    double x, double y, double z,
    double qx, double qy, double qz, double qw,
    const std::vector<double>& start_joints,
    TrajectoryStrategy strategy)
{
    // Solve IK to get goal joints
    IKSolver ik;
    auto sol_opt = ik.solve(x, y, z, qx, qy, qz, qw);
    std::vector<double> goal = sol_opt ? sol_opt->joint_positions
                                       : std::vector<double>(6, 0.0);

    return generate(start_joints, goal, strategy);
}

void TrajectoryGenerator::setStrategyConfig(TrajectoryStrategy type,
                                             const StrategyConfig& config)
{
    for (auto& c : _configs) {
        if (c.type == type) {
            c = config;
            return;
        }
    }
    _configs.push_back(config);
}

const StrategyConfig& TrajectoryGenerator::getStrategyConfig(
    TrajectoryStrategy type) const
{
    for (const auto& c : _configs) {
        if (c.type == type) return c;
    }
    return _configs[0];  // fallback to optimal
}

void TrajectoryGenerator::setWaypointCount(int count)
{
    _waypoint_count = std::max(10, count);
}

// ── Private Interpolation Methods ──

Trajectory TrajectoryGenerator::_interpolateLinear(
    const std::vector<double>& start,
    const std::vector<double>& goal,
    double duration_sec, int waypoint_count)
{
    Trajectory traj;
    int n = std::max(static_cast<int>(start.size()),
                     static_cast<int>(goal.size()));

    for (int i = 0; i <= waypoint_count; ++i) {
        double t = static_cast<double>(i) / waypoint_count;
        TrajectoryWaypoint wp;
        wp.time_from_start_sec = t * duration_sec;

        // Linear interpolation of each joint dimension → Cartesian approximate
        wp.x = start[0] + (goal[0] - start[0]) * t;
        wp.y = start[1] + (goal[1] - start[1]) * t;
        wp.z = start[2] + (goal[2] - start[2]) * t;
        wp.qx = 0.0; wp.qy = 0.0; wp.qz = 0.0; wp.qw = 1.0;

        traj.waypoints.push_back(wp);
    }

    return traj;
}

Trajectory TrajectoryGenerator::_interpolateTrapezoidal(
    const std::vector<double>& start,
    const std::vector<double>& goal,
    double duration_sec, int waypoint_count,
    double vmax_scale, double amax_scale)
{
    Trajectory traj;
    int n = std::max(static_cast<int>(start.size()),
                     static_cast<int>(goal.size()));

    // Trapezoidal velocity profile: accel → cruise → decel
    double accel_frac = 0.15 / amax_scale;
    double decel_frac = 0.15 / amax_scale;

    for (int i = 0; i <= waypoint_count; ++i) {
        double raw_t = static_cast<double>(i) / waypoint_count;
        double s;

        if (raw_t < accel_frac) {
            // Acceleration phase: s = 0.5 * a * t^2
            s = 0.5 * (raw_t * raw_t) / accel_frac;
        } else if (raw_t > 1.0 - decel_frac) {
            // Deceleration phase
            double t_rev = (1.0 - raw_t) / decel_frac;
            s = 1.0 - 0.5 * t_rev * t_rev;
        } else {
            // Cruise phase: linear
            s = (raw_t - 0.5 * accel_frac) / (1.0 - 0.5 * accel_frac - 0.5 * decel_frac);
        }

        TrajectoryWaypoint wp;
        wp.time_from_start_sec = s * duration_sec * vmax_scale;
        wp.x = start[0] + (goal[0] - start[0]) * s;
        wp.y = start[1] + (goal[1] - start[1]) * s;
        wp.z = start[2] + (goal[2] - start[2]) * s;
        wp.qx = 0.0; wp.qy = 0.0; wp.qz = 0.0; wp.qw = 1.0;

        traj.waypoints.push_back(wp);
    }

    return traj;
}

double TrajectoryGenerator::_computeScore(const Trajectory& traj,
                                           const StrategyConfig& config)
{
    // Simplified scoring based on config weights
    double path_length = 0.0;
    for (size_t i = 1; i < traj.waypoints.size(); ++i) {
        double dx = traj.waypoints[i].x - traj.waypoints[i-1].x;
        double dy = traj.waypoints[i].y - traj.waypoints[i-1].y;
        double dz = traj.waypoints[i].z - traj.waypoints[i-1].z;
        path_length += std::sqrt(dx*dx + dy*dy + dz*dz);
    }

    double duration = traj.waypoints.empty() ? 0.0
        : traj.waypoints.back().time_from_start_sec;

    // Higher score = better
    double pos_penalty  = std::min(1.0, path_length / 2.0);
    double time_penalty = std::min(1.0, duration / 5.0);
    double coll_penalty = traj.collision_free ? 0.0 : 1.0;
    double man_penalty  = 0.2;  // stub
    double torque_pen   = 0.1;  // stub
    double smooth_pen   = 0.1;  // stub

    double score = 1.0
        - config.position_weight      * pos_penalty
        - config.time_weight           * time_penalty
        - config.collision_weight      * coll_penalty
        - config.manipulability_weight * man_penalty
        - config.torque_weight         * torque_pen
        - config.smoothness_weight     * smooth_pen;

    return std::max(0.0, std::min(1.0, score));
}

} // namespace brain_core
