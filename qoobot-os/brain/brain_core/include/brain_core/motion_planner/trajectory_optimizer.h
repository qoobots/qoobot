// motion_planner/trajectory_optimizer.h — STOMP-based trajectory optimization
#pragma once

#include "brain_core/core_types.h"
#include <vector>
#include <string>

namespace brain_core {

/// Optimization parameters.
struct OptimizerParams {
    int    max_iterations{200};
    int    num_rollouts{30};
    double noise_stddev{0.05};        // exploration noise
    double cost_threshold{0.01};      // convergence threshold
    bool   optimize_collision{true};
    bool   optimize_smoothness{true};
    bool   optimize_manipulability{true};
};

/// Optimization result.
struct OptimizationResult {
    bool    converged{false};
    int     iterations_used{0};
    double  initial_cost{0.0};
    double  final_cost{0.0};
    double  improvement_pct{0.0};
    Trajectory optimized;
};

class TrajectoryOptimizer {
public:
    TrajectoryOptimizer();

    /// Optimize a trajectory using STOMP (Stochastic Trajectory Optimization).
    OptimizationResult optimize(const Trajectory& initial);

    /// Set optimization parameters.
    void setParams(const OptimizerParams& params);

    /// Get current parameters.
    const OptimizerParams& params() const { return _params; }

    /// Set the method: "stomp" (default), "chomp", "gradient".
    void setMethod(const std::string& method);

    /// Compute the cost of a trajectory (lower = better).
    double computeCost(const Trajectory& traj) const;

private:
    double _collisionCost(const Trajectory& traj) const;
    double _smoothnessCost(const Trajectory& traj) const;
    double _manipulabilityCost(const Trajectory& traj) const;

    Trajectory _addNoise(const Trajectory& base, double stddev) const;
    double _averageCost(const std::vector<Trajectory>& rollouts) const;

    OptimizerParams _params;
    std::string _method{"stomp"};
};

} // namespace brain_core
