// motion_planner/trajectory_optimizer.cpp — STOMP trajectory optimization
#include "brain_core/motion_planner/trajectory_optimizer.h"
#include <iostream>
#include <cmath>
#include <random>
#include <algorithm>

namespace brain_core {

TrajectoryOptimizer::TrajectoryOptimizer()
{
    std::cout << "[TrajectoryOptimizer] Initialized (method=" << _method << ")." << std::endl;
}

OptimizationResult TrajectoryOptimizer::optimize(const Trajectory& initial)
{
    OptimizationResult result;
    result.initial_cost = computeCost(initial);
    result.optimized = initial;

    if (result.initial_cost < _params.cost_threshold) {
        result.converged = true;
        result.final_cost = result.initial_cost;
        result.iterations_used = 0;
        std::cout << "[TrajectoryOptimizer] Already at threshold (cost="
                  << result.initial_cost << ")." << std::endl;
        return result;
    }

    // STOMP: sample rollouts, compute costs, weighted update
    std::mt19937 rng(42);  // fixed seed for reproducibility
    std::normal_distribution<double> noise(0.0, _params.noise_stddev);

    Trajectory best = initial;
    double best_cost = result.initial_cost;

    for (int iter = 0; iter < _params.max_iterations; ++iter) {
        // Generate rollouts with noise
        std::vector<Trajectory> rollouts;
        std::vector<double> costs;
        rollouts.reserve(_params.num_rollouts);
        costs.reserve(_params.num_rollouts);

        for (int r = 0; r < _params.num_rollouts; ++r) {
            auto noisy = _addNoise(best, _params.noise_stddev * rng());
            double c = computeCost(noisy);
            rollouts.push_back(noisy);
            costs.push_back(c);
        }

        // Find best rollout
        double min_cost = *std::min_element(costs.begin(), costs.end());
        if (min_cost < best_cost) {
            size_t idx = std::distance(costs.begin(),
                          std::min_element(costs.begin(), costs.end()));
            best = rollouts[idx];
            best_cost = min_cost;

            std::cout << "[TrajectoryOptimizer] Iter " << (iter+1)
                      << ": cost " << result.initial_cost << " → "
                      << best_cost << std::endl;
        }

        if (best_cost < _params.cost_threshold) {
            result.converged = true;
            result.iterations_used = iter + 1;
            break;
        }

        result.iterations_used = iter + 1;
    }

    result.optimized = best;
    result.final_cost = best_cost;
    result.improvement_pct = (result.initial_cost > 0.0)
        ? 100.0 * (result.initial_cost - result.final_cost) / result.initial_cost
        : 0.0;

    if (!result.converged && result.iterations_used >= _params.max_iterations) {
        result.converged = false;
        std::cout << "[TrajectoryOptimizer] Max iterations reached ("
                  << _params.max_iterations << ")." << std::endl;
    }

    result.optimized.score = 1.0 - result.final_cost;
    result.optimized.name = "optimized";

    std::cout << "[TrajectoryOptimizer] Optimization complete: "
              << result.improvement_pct << "% improvement ("
              << result.iterations_used << " iters)." << std::endl;

    return result;
}

void TrajectoryOptimizer::setParams(const OptimizerParams& params)
{
    _params = params;
}

void TrajectoryOptimizer::setMethod(const std::string& method)
{
    _method = method;
    std::cout << "[TrajectoryOptimizer] Method: " << method << std::endl;
}

double TrajectoryOptimizer::computeCost(const Trajectory& traj) const
{
    double cost = 0.0;
    if (_params.optimize_collision) cost += _collisionCost(traj);
    if (_params.optimize_smoothness) cost += _smoothnessCost(traj);
    if (_params.optimize_manipulability) cost += _manipulabilityCost(traj);
    return cost;
}

double TrajectoryOptimizer::_collisionCost(const Trajectory& traj) const
{
    if (!traj.collision_free) return 10.0;
    return 0.0;  // stub
}

double TrajectoryOptimizer::_smoothnessCost(const Trajectory& traj) const
{
    if (traj.waypoints.size() < 3) return 0.0;

    double jerk_sum = 0.0;
    for (size_t i = 2; i < traj.waypoints.size(); ++i) {
        // Approximate jerk as third finite difference of position
        auto& w0 = traj.waypoints[i-2];
        auto& w1 = traj.waypoints[i-1];
        auto& w2 = traj.waypoints[i];

        double dt1 = w1.time_from_start_sec - w0.time_from_start_sec;
        double dt2 = w2.time_from_start_sec - w1.time_from_start_sec;
        if (dt1 <= 0.0 || dt2 <= 0.0) continue;

        double ax = (w2.x - 2.0*w1.x + w0.x) / (dt1 * dt2);
        double ay = (w2.y - 2.0*w1.y + w0.y) / (dt1 * dt2);
        double az = (w2.z - 2.0*w1.z + w0.z) / (dt1 * dt2);
        jerk_sum += std::sqrt(ax*ax + ay*ay + az*az);
    }

    return 0.1 * jerk_sum / traj.waypoints.size();
}

double TrajectoryOptimizer::_manipulabilityCost(const Trajectory&) const
{
    return 0.05;  // stub
}

Trajectory TrajectoryOptimizer::_addNoise(const Trajectory& base,
                                           double stddev) const
{
    Trajectory noisy = base;
    std::mt19937 rng(std::random_device{}());
    std::normal_distribution<double> dist(0.0, stddev);

    for (auto& wp : noisy.waypoints) {
        wp.x += dist(rng) * 0.01;
        wp.y += dist(rng) * 0.01;
        wp.z += dist(rng) * 0.005;
    }

    return noisy;
}

double TrajectoryOptimizer::_averageCost(
    const std::vector<Trajectory>& rollouts) const
{
    if (rollouts.empty()) return 0.0;
    double sum = 0.0;
    for (const auto& t : rollouts) {
        sum += computeCost(t);
    }
    return sum / rollouts.size();
}

} // namespace brain_core
