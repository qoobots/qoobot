#pragma once

#include "qoosvc/spatial/map_types.h"
#include <vector>

namespace qoosvc::spatial {

/**
 * LaserSLAM — 2D LiDAR-based SLAM using scan matching and pose graph optimization.
 *
 * Implements a simplified Cartographer-style SLAM pipeline:
 *   1. Scan-to-submap matching (Ceres-based)
 *   2. Submap construction
 *   3. Loop closure detection (branch-and-bound scan matching)
 *   4. Global pose graph optimization (GTSAM/g2o integration point)
 */
class LaserSLAM {
public:
    explicit LaserSLAM(const SLAMConfig& config);
    ~LaserSLAM();

    // Initialize the SLAM system
    bool initialize();

    // Process a new LiDAR scan (range data as polar coordinates)
    // Returns updated robot pose
    Pose3D process_scan(const std::vector<double>& ranges, double angle_min,
                        double angle_max, double angle_increment);

    // Process odometry data
    void process_odometry(const Pose3D& odom);

    // Process IMU data
    void process_imu(double accel_x, double accel_y, double accel_z,
                     double gyro_x, double gyro_y, double gyro_z);

    // Get current occupancy grid
    const OccupancyGrid& get_grid() const { return grid_; }

    // Get current robot pose
    Pose3D get_pose() const { return current_pose_; }

    // Get SLAM status
    SLAMStatus get_status() const;

    // Save map to file
    bool save_map(const std::string& filepath) const;

    // Load map from file
    bool load_map(const std::string& filepath);

    // Check if a loop closure was detected recently
    bool has_new_loop_closure() const;

private:
    // Convert LiDAR ranges to Cartesian points
    std::vector<Point3D> ranges_to_points(const std::vector<double>& ranges,
                                           double angle_min, double angle_max,
                                           double angle_increment);

    // Perform scan-to-submap matching using Ceres solver
    Pose3D scan_match(const std::vector<Point3D>& scan_points,
                      const OccupancyGrid& submap, const Pose3D& initial_guess);

    // Insert scan data into occupancy grid (Bresenham ray casting)
    void insert_scan(const std::vector<Point3D>& scan_points, const Pose3D& pose);

    // Detect loop closures using branch-and-bound scan matching
    bool detect_loop_closure(const Pose3D& current_pose);

    // Optimize the global pose graph
    void optimize_pose_graph();

    // Update occupancy grid from all submaps
    void update_global_grid();

    // Compute the probability a cell is occupied given a hit/miss
    double occupancy_probability(double log_odds) const;

    // Update a single cell with a hit or miss observation
    void update_cell(int32_t x, int32_t y, bool hit);

    SLAMConfig config_;
    OccupancyGrid grid_;
    Pose3D current_pose_;
    Pose3D last_odom_;
    SLAMStatus status_;

    // Submaps for local optimization
    struct Submap {
        OccupancyGrid grid;
        Pose3D origin;
        std::vector<Pose3D> scan_poses;
    };
    std::vector<Submap> submaps_;
    Submap current_submap_;

    // Pose graph nodes
    struct PoseNode {
        int32_t id;
        Pose3D pose;
        int32_t submap_id;
    };
    std::vector<PoseNode> pose_graph_;

    // Loop closure constraints
    struct LoopConstraint {
        int32_t from_node;
        int32_t to_node;
        Pose3D relative_pose;
        double score;
    };
    std::vector<LoopConstraint> loop_constraints_;

    // Internal state
    int32_t scan_count_ = 0;
    int32_t node_count_ = 0;
    bool loop_closure_detected_ = false;
    int32_t scans_since_loop_check_ = 0;

    // Log-odds representation: log(p/(1-p))
    // Free: -0.4 (~40% prob), Occupied: 0.85 (~70% prob)
    static constexpr double kLogOddsFree = -0.4;
    static constexpr double kLogOddsOccupied = 0.85;
    static constexpr double kLogOddsClampMin = -4.0;
    static constexpr double kLogOddsClampMax = 4.0;
};

} // namespace qoosvc::spatial
