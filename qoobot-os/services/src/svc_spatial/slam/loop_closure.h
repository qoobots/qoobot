#pragma once

#include "qoosvc/spatial/map_types.h"
#include <functional>
#include <vector>

namespace qoosvc::spatial {

/**
 * LoopClosureDetector — Detects when the robot revisits a previously mapped area.
 *
 * Uses a multi-resolution branch-and-bound scan matching approach
 * (inspired by Google Cartographer's loop closure).
 */
class LoopClosureDetector {
public:
    struct Config {
        double min_score = 0.55;          // Minimum match score
        double search_radius = 15.0;      // Search radius (meters)
        double search_angle = 0.5;        // Search angle (radians)
        int32_t min_scans_between = 100;  // Minimum scans between closure checks
        double resolution_low = 0.1;      // Low-res branch-and-bound
        double resolution_high = 0.05;    // High-res branch-and-bound
    };

    explicit LoopClosureDetector(const Config& config);
    ~LoopClosureDetector();

    /**
     * Try to detect a loop closure between the current scan and historical submaps.
     * Returns true if a closure was found, and populates the relative_pose.
     */
    bool detect(const OccupancyGrid& current_submap,
                const std::vector<OccupancyGrid>& history_submaps,
                const std::vector<Pose3D>& history_poses,
                Pose3D& relative_pose, double& score);

    /**
     * Register a callback for loop closure events.
     */
    void on_closure_detected(std::function<void(int32_t from, int32_t to, Pose3D)> cb);

private:
    // Branch-and-bound scan matching at multiple resolutions
    double match_submaps(const OccupancyGrid& a, const OccupancyGrid& b,
                         const Pose3D& a_pose, const Pose3D& b_pose,
                         double resolution);

    Config config_;
    std::function<void(int32_t, int32_t, Pose3D)> closure_callback_;
};

} // namespace qoosvc::spatial
