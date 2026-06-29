#pragma once

#include "qoosvc/spatial/map_types.h"
#include <vector>

namespace qoosvc::spatial {

/**
 * GlobalOptimizer — Sparse pose graph optimization.
 *
 * Integration point for GTSAM/g2o. Performs nonlinear least-squares
 * optimization over the pose graph with loop closure constraints.
 */
class GlobalOptimizer {
public:
    struct Config {
        int32_t max_iterations = 50;
        double convergence_threshold = 1e-5;
        bool use_robust_kernel = true;
        double huber_delta = 1.0;
    };

    struct PoseNode {
        int32_t id;
        Pose3D pose;
        bool fixed = false;  // Fixed nodes are not optimized
    };

    struct Constraint {
        int32_t from_id;
        int32_t to_id;
        Pose3D relative_pose;  // T_from_to
        double information_weight = 1.0;
    };

    explicit GlobalOptimizer(const Config& config);
    ~GlobalOptimizer();

    /**
     * Add a pose node to the graph.
     */
    void add_node(const PoseNode& node);

    /**
     * Add an odometry constraint (sequential).
     */
    void add_odometry_constraint(int32_t from_id, int32_t to_id,
                                  const Pose3D& relative, double weight = 1.0);

    /**
     * Add a loop closure constraint.
     */
    void add_loop_closure_constraint(int32_t from_id, int32_t to_id,
                                      const Pose3D& relative, double weight = 1.0);

    /**
     * Run the optimization.
     * Returns the optimized poses in the same order as nodes were added.
     */
    bool optimize(std::vector<Pose3D>& optimized_poses);

    /**
     * Get the current residual error.
     */
    double total_error() const;

    /**
     * Clear the graph.
     */
    void clear();

private:
    // Compute SE(2) error between two poses given a relative constraint
    void compute_error(const Pose3D& from, const Pose3D& to,
                       const Pose3D& constraint, double& ex, double& ey, double& eth) const;

    // Gauss-Newton step for SE(2) pose graph optimization
    bool gauss_newton_step();

    Config config_;
    std::vector<PoseNode> nodes_;
    std::vector<Constraint> odometry_constraints_;
    std::vector<Constraint> loop_constraints_;
    double current_error_ = 0.0;
};

} // namespace qoosvc::spatial
