#include "global_optimizer.h"
#include <algorithm>
#include <cmath>
#include <numeric>

namespace qoosvc::spatial {

GlobalOptimizer::GlobalOptimizer(const Config& config)
    : config_(config) {
}

GlobalOptimizer::~GlobalOptimizer() = default;

void GlobalOptimizer::add_node(const PoseNode& node) {
    nodes_.push_back(node);
}

void GlobalOptimizer::add_odometry_constraint(int32_t from_id, int32_t to_id,
                                                const Pose3D& relative, double weight) {
    odometry_constraints_.push_back({from_id, to_id, relative, weight});
}

void GlobalOptimizer::add_loop_closure_constraint(int32_t from_id, int32_t to_id,
                                                    const Pose3D& relative, double weight) {
    loop_constraints_.push_back({from_id, to_id, relative, weight});
}

bool GlobalOptimizer::optimize(std::vector<Pose3D>& optimized_poses) {
    if (nodes_.empty()) return false;

    // Initialize from current poses
    optimized_poses.clear();
    for (const auto& node : nodes_) {
        optimized_poses.push_back(node.pose);
    }

    // Gauss-Newton optimization loop
    double prev_error = std::numeric_limits<double>::max();

    for (int32_t iter = 0; iter < config_.max_iterations; ++iter) {
        // Build linear system A*x = b
        // State: [dx1, dy1, dth1, dx2, dy2, dth2, ..., dxN, dyN, dthN]
        size_t n = nodes_.size();
        size_t dim = n * 3;

        std::vector<double> H(dim * dim, 0.0);  // Hessian approximation
        std::vector<double> b(dim, 0.0);         // Gradient

        double total_error = 0.0;

        // Process odometry constraints
        for (const auto& c : odometry_constraints_) {
            if (c.from_id < 0 || c.from_id >= static_cast<int32_t>(n) ||
                c.to_id < 0 || c.to_id >= static_cast<int32_t>(n))
                continue;

            double ex, ey, eth;
            compute_error(optimized_poses[c.from_id], optimized_poses[c.to_id],
                          c.relative_pose, ex, ey, eth);

            double robust_weight = c.information_weight;
            if (config_.use_robust_kernel) {
                double r = std::sqrt(ex * ex + ey * ey + eth * eth);
                robust_weight *= std::min(1.0, config_.huber_delta / (r + 1e-10));
            }

            total_error += robust_weight * (ex * ex + ey * ey + eth * eth);

            // Jacobian for from node
            double cos_from = std::cos(optimized_poses[c.from_id].yaw);
            double sin_from = std::sin(optimized_poses[c.from_id].yaw);

            // ∂e/∂(from.x, from.y, from.theta)
            // e = T_from⁻¹ * T_to ⊖ T_constraint
            // Simplified SE(2) Jacobian
            double J_from[3][3] = {
                {-cos_from, -sin_from,  sin_from * c.relative_pose.x - cos_from * c.relative_pose.y},
                { sin_from, -cos_from, -cos_from * c.relative_pose.x - sin_from * c.relative_pose.y},
                {0, 0, -1}
            };

            double J_to[3][3] = {
                {cos_from, sin_from, 0},
                {-sin_from, cos_from, 0},
                {0, 0, 1}
            };

            double e[3] = {ex, ey, eth};

            // Update H and b for from node
            for (int i = 0; i < 3; ++i) {
                size_t fi = c.from_id * 3 + i;
                for (int j = 0; j < 3; ++j) {
                    size_t fj = c.from_id * 3 + j;
                    H[fi * dim + fj] += robust_weight * J_from[i][0] * J_from[j][0]
                                      + robust_weight * J_from[i][1] * J_from[j][1]
                                      + robust_weight * J_from[i][2] * J_from[j][2];
                }
                b[fi] -= robust_weight * (J_from[i][0] * e[0] +
                                          J_from[i][1] * e[1] +
                                          J_from[i][2] * e[2]);
            }

            // Update H and b for to node
            for (int i = 0; i < 3; ++i) {
                size_t ti = c.to_id * 3 + i;
                for (int j = 0; j < 3; ++j) {
                    size_t tj = c.to_id * 3 + j;
                    H[ti * dim + tj] += robust_weight * J_to[i][0] * J_to[j][0]
                                      + robust_weight * J_to[i][1] * J_to[j][1]
                                      + robust_weight * J_to[i][2] * J_to[j][2];
                }
                b[ti] -= robust_weight * (J_to[i][0] * e[0] +
                                          J_to[i][1] * e[1] +
                                          J_to[i][2] * e[2]);
            }

            // Cross terms (from × to)
            for (int i = 0; i < 3; ++i) {
                size_t fi = c.from_id * 3 + i;
                for (int j = 0; j < 3; ++j) {
                    size_t tj = c.to_id * 3 + j;
                    H[fi * dim + tj] += robust_weight * J_from[i][0] * J_to[j][0]
                                      + robust_weight * J_from[i][1] * J_to[j][1]
                                      + robust_weight * J_from[i][2] * J_to[j][2];
                }
            }
        }

        // Process loop closure constraints
        for (const auto& c : loop_constraints_) {
            if (c.from_id < 0 || c.from_id >= static_cast<int32_t>(n) ||
                c.to_id < 0 || c.to_id >= static_cast<int32_t>(n))
                continue;

            double ex, ey, eth;
            compute_error(optimized_poses[c.from_id], optimized_poses[c.to_id],
                          c.relative_pose, ex, ey, eth);

            double w = c.information_weight * 10.0;  // Loop closures are more certain
            total_error += w * (ex * ex + ey * ey + eth * eth);

            double cos_f = std::cos(optimized_poses[c.from_id].yaw);
            double sin_f = std::sin(optimized_poses[c.from_id].yaw);

            double e[3] = {ex, ey, eth};

            // Simplified Jacobian for loop closure
            for (int i = 0; i < 3; ++i) {
                size_t fi = c.from_id * 3 + i;
                size_t ti = c.to_id * 3 + i;
                b[fi] -= w * e[i];
                b[ti] += w * e[i];
                H[fi * dim + fi] += w;
                H[ti * dim + ti] += w;
            }
        }

        // Fix first node (anchor)
        for (int i = 0; i < 3; ++i) {
            H[i * dim + i] += 1e10;
        }

        // Solve linear system (simple conjugate gradient for SPD)
        std::vector<double> dx(dim, 0.0);
        {
            std::vector<double> r = b;  // r = b - H*x (x=0 initially)
            std::vector<double> p = r;
            double rsold = 0.0;
            for (size_t i = 0; i < dim; ++i) rsold += r[i] * r[i];

            for (int cg_iter = 0; cg_iter < std::min(100, static_cast<int>(dim)); ++cg_iter) {
                std::vector<double> Ap(dim, 0.0);
                for (size_t i = 0; i < dim; ++i) {
                    for (size_t j = 0; j < dim; ++j) {
                        Ap[i] += H[i * dim + j] * p[j];
                    }
                }

                double pAp = 0.0;
                for (size_t i = 0; i < dim; ++i) pAp += p[i] * Ap[i];
                if (pAp < 1e-20) break;

                double alpha = rsold / pAp;
                for (size_t i = 0; i < dim; ++i) dx[i] += alpha * p[i];
                for (size_t i = 0; i < dim; ++i) r[i] -= alpha * Ap[i];

                double rsnew = 0.0;
                for (size_t i = 0; i < dim; ++i) rsnew += r[i] * r[i];
                if (std::sqrt(rsnew) < 1e-10) break;

                double beta = rsnew / rsold;
                for (size_t i = 0; i < dim; ++i) p[i] = r[i] + beta * p[i];
                rsold = rsnew;
            }
        }

        // Apply update
        for (size_t i = 0; i < n; ++i) {
            if (nodes_[i].fixed) continue;
            optimized_poses[i].x += dx[i * 3 + 0];
            optimized_poses[i].y += dx[i * 3 + 1];
            optimized_poses[i].yaw += dx[i * 3 + 2];
        }

        // Check convergence
        if (std::abs(total_error - prev_error) < config_.convergence_threshold) {
            break;
        }
        prev_error = total_error;
    }

    current_error_ = prev_error;
    return true;
}

double GlobalOptimizer::total_error() const {
    return current_error_;
}

void GlobalOptimizer::clear() {
    nodes_.clear();
    odometry_constraints_.clear();
    loop_constraints_.clear();
    current_error_ = 0.0;
}

void GlobalOptimizer::compute_error(const Pose3D& from, const Pose3D& to,
                                      const Pose3D& constraint,
                                      double& ex, double& ey, double& eth) const {
    // Compute SE(2) error: e = ⊖(⊖T_from ⊕ T_to) ⊖ T_constraint
    double cos_f = std::cos(from.yaw);
    double sin_f = std::sin(from.yaw);

    double dx = to.x - from.x;
    double dy = to.y - from.y;

    // Transform relative position to from's frame
    double rx = cos_f * dx + sin_f * dy;
    double ry = -sin_f * dx + cos_f * dy;

    double rth = to.yaw - from.yaw;
    // Normalize angle
    rth = std::fmod(rth, 2.0 * M_PI);
    if (rth > M_PI) rth -= 2.0 * M_PI;
    if (rth < -M_PI) rth += 2.0 * M_PI;

    ex = rx - constraint.x;
    ey = ry - constraint.y;
    eth = rth - constraint.yaw;
    eth = std::fmod(eth, 2.0 * M_PI);
    if (eth > M_PI) eth -= 2.0 * M_PI;
    if (eth < -M_PI) eth += 2.0 * M_PI;
}

} // namespace qoosvc::spatial
