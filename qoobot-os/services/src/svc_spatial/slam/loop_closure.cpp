#include "loop_closure.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace qoosvc::spatial {

LoopClosureDetector::LoopClosureDetector(const Config& config)
    : config_(config) {
}

LoopClosureDetector::~LoopClosureDetector() = default;

bool LoopClosureDetector::detect(const OccupancyGrid& current_submap,
                                  const std::vector<OccupancyGrid>& history_submaps,
                                  const std::vector<Pose3D>& history_poses,
                                  Pose3D& relative_pose, double& score) {
    if (history_submaps.empty() || history_poses.empty()) return false;

    double best_score = config_.min_score;
    int32_t best_idx = -1;
    Pose3D best_relative;

    // Search through history submaps for potential closures
    for (size_t i = 0; i < history_submaps.size(); ++i) {
        // Skip recent submaps (they can't be loop closures)
        if (static_cast<int32_t>(history_submaps.size() - i) < config_.min_scans_between) {
            continue;
        }

        // Coarse distance check
        double dist = std::hypot(
            current_submap.origin.x - history_poses[i].x,
            current_submap.origin.y - history_poses[i].y);

        if (dist > config_.search_radius) continue;

        // Angular check
        double angle_diff = std::abs(current_submap.origin.yaw - history_poses[i].yaw);
        angle_diff = std::fmod(angle_diff, 2.0 * M_PI);
        if (angle_diff > M_PI) angle_diff = 2.0 * M_PI - angle_diff;
        if (angle_diff > config_.search_angle) continue;

        // Multi-resolution matching
        double match_score = match_submaps(current_submap, history_submaps[i],
                                            current_submap.origin, history_poses[i],
                                            config_.resolution_low);

        if (match_score > best_score) {
            // Refine at high resolution
            match_score = match_submaps(current_submap, history_submaps[i],
                                         current_submap.origin, history_poses[i],
                                         config_.resolution_high);

            if (match_score > best_score) {
                best_score = match_score;
                best_idx = static_cast<int32_t>(i);
                best_relative = {
                    current_submap.origin.x - history_poses[i].x,
                    current_submap.origin.y - history_poses[i].y,
                    0,
                    0, 0,
                    current_submap.origin.yaw - history_poses[i].yaw
                };
            }
        }
    }

    if (best_idx >= 0) {
        relative_pose = best_relative;
        score = best_score;

        if (closure_callback_) {
            closure_callback_(static_cast<int32_t>(history_submaps.size()) - 1,
                              best_idx, best_relative);
        }

        return true;
    }

    return false;
}

double LoopClosureDetector::match_submaps(const OccupancyGrid& a,
                                            const OccupancyGrid& b,
                                            const Pose3D& a_pose,
                                            const Pose3D& b_pose,
                                            double resolution) {
    // Simplified correlation-based matching
    // In production, this uses branch-and-bound for efficiency

    int matches = 0;
    int total = 0;

    // Sample points from submap a at the given resolution
    for (double ax = 0; ax < a.width * a.resolution; ax += resolution) {
        for (double ay = 0; ay < a.height * a.resolution; ay += resolution) {
            int sx = static_cast<int>(ax / a.resolution);
            int sy = static_cast<int>(ay / a.resolution);

            if (!a.is_in_bounds(sx, sy)) continue;

            auto cell_a = a.at(sx, sy);
            if (cell_a == static_cast<int8_t>(OccupancyState::UNKNOWN)) continue;

            // Transform point from a's frame to b's frame
            double wx = a_pose.x + ax - a.origin.x;
            double wy = a_pose.y + ay - a.origin.y;

            double bx = wx - b_pose.x + b.origin.x;
            double by = wy - b_pose.y + b.origin.y;

            int bx_grid = static_cast<int>(bx / b.resolution);
            int by_grid = static_cast<int>(by / b.resolution);

            if (!b.is_in_bounds(bx_grid, by_grid)) continue;

            auto cell_b = b.at(bx_grid, by_grid);

            total++;
            if (cell_a == cell_b) {
                matches++;
            }
        }
    }

    return total > 0 ? static_cast<double>(matches) / total : 0.0;
}

void LoopClosureDetector::on_closure_detected(
    std::function<void(int32_t, int32_t, Pose3D)> cb) {
    closure_callback_ = std::move(cb);
}

} // namespace qoosvc::spatial
