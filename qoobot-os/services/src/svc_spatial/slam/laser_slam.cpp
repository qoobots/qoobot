#include "laser_slam.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <queue>
#include <unordered_set>

namespace qoosvc::spatial {

// ============================================================================
// Constructor / Destructor
// ============================================================================

LaserSLAM::LaserSLAM(const SLAMConfig& config)
    : config_(config) {
}

LaserSLAM::~LaserSLAM() = default;

// ============================================================================
// Initialization
// ============================================================================

bool LaserSLAM::initialize() {
    grid_.resolution = config_.resolution;
    grid_.width = 4096;   // Default: ~200m at 0.05 resolution
    grid_.height = 4096;
    grid_.origin.x = -grid_.width * grid_.resolution / 2.0;
    grid_.origin.y = -grid_.height * grid_.resolution / 2.0;
    grid_.data.resize(grid_.width * grid_.height,
                       static_cast<int8_t>(OccupancyState::UNKNOWN));

    current_pose_ = Pose3D{0, 0, 0, 0, 0, 0, config_.map_frame};
    status_.state = SLAMState::MAPPING;
    status_.current_pose = current_pose_;

    // Initialize first submap
    current_submap_.grid.resolution = config_.resolution;
    current_submap_.grid.width = 512;
    current_submap_.grid.height = 512;
    current_submap_.grid.origin = current_pose_;
    current_submap_.grid.data.resize(512 * 512,
                                      static_cast<int8_t>(OccupancyState::UNKNOWN));
    current_submap_.origin = current_pose_;

    return true;
}

// ============================================================================
// LiDAR Scan Processing
// ============================================================================

Pose3D LaserSLAM::process_scan(const std::vector<double>& ranges,
                                 double angle_min, double angle_max,
                                 double angle_increment) {
    if (ranges.empty()) return current_pose_;

    // Convert ranges to Cartesian points in sensor frame
    auto points = ranges_to_points(ranges, angle_min, angle_max, angle_increment);

    // Filter out invalid points (too close or too far)
    points.erase(std::remove_if(points.begin(), points.end(),
        [this](const Point3D& p) {
            double dist = p.norm();
            return dist < config_.min_range || dist > config_.max_range;
        }), points.end());

    if (points.empty()) return current_pose_;

    // Predict pose from odometry (simple constant velocity model)
    Pose3D predicted_pose = current_pose_;
    if (scan_count_ > 0) {
        // Use last odometry delta as motion prediction
        predicted_pose.x += (current_pose_.x - last_odom_.x);
        predicted_pose.y += (current_pose_.y - last_odom_.y);
        predicted_pose.yaw += (current_pose_.yaw - last_odom_.yaw);
    }

    // Scan-to-submap matching
    Pose3D matched_pose = scan_match(points, current_submap_.grid, predicted_pose);
    current_pose_ = matched_pose;
    status_.current_pose = matched_pose;
    status_.localization_error = matched_pose.distance_to(predicted_pose);

    // Insert scan into submap
    insert_scan(points, matched_pose);

    // Update submap scan count
    current_submap_.scan_poses.push_back(matched_pose);
    scan_count_++;
    scans_since_loop_check_++;

    // Check if we should create a new submap
    if (current_submap_.scan_poses.size() >= static_cast<size_t>(config_.submap_size)) {
        submaps_.push_back(std::move(current_submap_));

        // Add pose graph node
        PoseNode node;
        node.id = node_count_++;
        node.pose = matched_pose;
        node.submap_id = static_cast<int32_t>(submaps_.size() - 1);
        pose_graph_.push_back(node);

        status_.num_submaps = static_cast<int32_t>(submaps_.size());

        // Initialize new submap
        current_submap_ = Submap{};
        current_submap_.grid.resolution = config_.resolution;
        current_submap_.grid.width = 512;
        current_submap_.grid.height = 512;
        current_submap_.grid.origin = matched_pose;
        current_submap_.grid.data.resize(512 * 512,
                                          static_cast<int8_t>(OccupancyState::UNKNOWN));
        current_submap_.origin = matched_pose;

        // Check for loop closures periodically
        if (config_.loop_closure_enabled &&
            scans_since_loop_check_ > config_.submap_size * 2) {
            scans_since_loop_check_ = 0;
            if (detect_loop_closure(matched_pose)) {
                loop_closure_detected_ = true;
                status_.num_loop_closures++;
                status_.state = SLAMState::LOOP_CLOSURE;

                optimize_pose_graph();
                status_.state = SLAMState::MAPPING;
            }
        }

        // Update global grid from submaps
        update_global_grid();
    }

    // Update status
    status_.mapping_area_sqm = grid_.total_area_sqm;
    status_.num_landmarks = static_cast<int32_t>(pose_graph_.size());
    status_.last_update_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    last_odom_ = current_pose_;
    return current_pose_;
}

// ============================================================================
// Odometry / IMU
// ============================================================================

void LaserSLAM::process_odometry(const Pose3D& odom) {
    last_odom_ = odom;
}

void LaserSLAM::process_imu(double accel_x, double accel_y, double accel_z,
                             double gyro_x, double gyro_y, double gyro_z) {
    // In production, IMU data would be fused with LiDAR via EKF/UKF
    // For now, simple integration of gyro for yaw prediction
    if (config_.use_imu) {
        // Store for potential future use in scan matching initialization
        current_pose_.yaw += gyro_z * 0.01;  // Assuming ~100Hz IMU
    }
}

// ============================================================================
// Ranges to Points Conversion
// ============================================================================

std::vector<Point3D> LaserSLAM::ranges_to_points(const std::vector<double>& ranges,
                                                   double angle_min, double angle_max,
                                                   double angle_increment) {
    std::vector<Point3D> points;
    points.reserve(ranges.size());

    for (size_t i = 0; i < ranges.size(); ++i) {
        double angle = angle_min + i * angle_increment;
        if (angle > angle_max) break;

        double r = ranges[i];
        if (r >= config_.min_range && r <= config_.max_range) {
            points.push_back({
                r * std::cos(angle),
                r * std::sin(angle),
                0.0
            });
        }
    }

    return points;
}

// ============================================================================
// Scan Matching (Correlation-based, simplified Ceres-style)
// ============================================================================

Pose3D LaserSLAM::scan_match(const std::vector<Point3D>& scan_points,
                               const OccupancyGrid& submap,
                               const Pose3D& initial_guess) {
    // Simplified correlation scan matcher
    // In production, this would use Ceres Solver for nonlinear optimization

    // Search window in x, y, theta
    const double search_window_x = 1.0;      // meters
    const double search_window_y = 1.0;
    const double search_window_theta = 0.5;  // radians
    const double step_x = config_.resolution;
    const double step_y = config_.resolution;
    const double step_theta = 0.02;

    double best_score = -std::numeric_limits<double>::max();
    Pose3D best_pose = initial_guess;

    for (double dx = -search_window_x; dx <= search_window_x; dx += step_x) {
        for (double dy = -search_window_y; dy <= search_window_y; dy += step_y) {
            for (double dt = -search_window_theta; dt <= search_window_theta; dt += step_theta) {
                Pose3D candidate = initial_guess;
                candidate.x += dx;
                candidate.y += dy;
                candidate.yaw += dt;

                // Score: count how many scan points hit occupied cells
                double score = 0.0;
                int valid_points = 0;

                double cos_yaw = std::cos(candidate.yaw);
                double sin_yaw = std::sin(candidate.yaw);

                for (const auto& pt : scan_points) {
                    // Transform point from sensor frame to map frame
                    double wx = candidate.x + pt.x * cos_yaw - pt.y * sin_yaw;
                    double wy = candidate.y + pt.x * sin_yaw + pt.y * cos_yaw;

                    auto grid_pt = grid_.world_to_grid({wx, wy, 0});
                    if (submap.is_in_bounds(grid_pt.x, grid_pt.y)) {
                        valid_points++;
                        auto cell = submap.at(grid_pt.x, grid_pt.y);
                        if (cell == static_cast<int8_t>(OccupancyState::OCCUPIED)) {
                            score += 1.0;
                        } else if (cell == static_cast<int8_t>(OccupancyState::FREE)) {
                            score -= 0.5;
                        }
                    }
                }

                if (valid_points > 0) {
                    score /= valid_points;
                }

                if (score > best_score) {
                    best_score = score;
                    best_pose = candidate;
                }
            }
        }
    }

    return best_pose;
}

// ============================================================================
// Scan Insertion (Bresenham Ray Casting)
// ============================================================================

void LaserSLAM::insert_scan(const std::vector<Point3D>& scan_points,
                             const Pose3D& pose) {
    // Transform all points to map frame
    double cos_yaw = std::cos(pose.yaw);
    double sin_yaw = std::sin(pose.yaw);

    std::vector<Point3D> world_points;
    world_points.reserve(scan_points.size());

    for (const auto& pt : scan_points) {
        world_points.push_back({
            pose.x + pt.x * cos_yaw - pt.y * sin_yaw,
            pose.y + pt.x * sin_yaw + pt.y * cos_yaw,
            0.0
        });
    }

    auto sensor_grid = grid_.world_to_grid({pose.x, pose.y, 0});

    for (const auto& wp : world_points) {
        auto hit_grid = grid_.world_to_grid(wp);

        // Mark free space along the ray using Bresenham
        int dx = std::abs(hit_grid.x - sensor_grid.x);
        int dy = std::abs(hit_grid.y - sensor_grid.y);
        int sx = sensor_grid.x < hit_grid.x ? 1 : -1;
        int sy = sensor_grid.y < hit_grid.y ? 1 : -1;
        int err = dx - dy;

        int cx = sensor_grid.x;
        int cy = sensor_grid.y;

        while (cx != hit_grid.x || cy != hit_grid.y) {
            // Mark as free in both submap and global grid
            if (current_submap_.grid.is_in_bounds(cx, cy)) {
                update_cell(cx, cy, false);
            }
            if (grid_.is_in_bounds(cx, cy)) {
                update_cell(cx, cy, false);
            }

            int e2 = 2 * err;
            if (e2 > -dy) {
                err -= dy;
                cx += sx;
            }
            if (e2 < dx) {
                err += dx;
                cy += sy;
            }
        }

        // Mark hit point as occupied
        if (current_submap_.grid.is_in_bounds(hit_grid.x, hit_grid.y)) {
            update_cell(hit_grid.x, hit_grid.y, true);
        }
        if (grid_.is_in_bounds(hit_grid.x, hit_grid.y)) {
            update_cell(hit_grid.x, hit_grid.y, true);
        }
    }
}

// ============================================================================
// Cell Update (Log-Odds)
// ============================================================================

void LaserSLAM::update_cell(int32_t x, int32_t y, bool hit) {
    // Update submap
    auto& submap_cell = current_submap_.grid.data[y * current_submap_.grid.width + x];
    double submap_log_odds = occupancy_probability(submap_cell);
    submap_log_odds += hit ? kLogOddsOccupied : kLogOddsFree;
    submap_log_odds = std::clamp(submap_log_odds, kLogOddsClampMin, kLogOddsClampMax);
    submap_cell = static_cast<int8_t>(
        submap_log_odds > 0 ? OccupancyState::OCCUPIED : OccupancyState::FREE);

    // Update global grid
    auto& grid_cell = grid_.data[y * grid_.width + x];
    double grid_log_odds = occupancy_probability(grid_cell);
    grid_log_odds += hit ? kLogOddsOccupied : kLogOddsFree;
    grid_log_odds = std::clamp(grid_log_odds, kLogOddsClampMin, kLogOddsClampMax);
    grid_cell = static_cast<int8_t>(
        grid_log_odds > 0 ? OccupancyState::OCCUPIED : OccupancyState::FREE);
}

double LaserSLAM::occupancy_probability(double log_odds) const {
    return log_odds;  // Already in log-odds form
}

// ============================================================================
// Loop Closure Detection
// ============================================================================

bool LaserSLAM::detect_loop_closure(const Pose3D& current_pose) {
    if (submaps_.size() < 3) return false;

    // Search for nearby submaps that are far in time
    for (size_t i = 0; i < submaps_.size() - 2; ++i) {
        double dist = current_pose.distance_to(submaps_[i].origin);

        if (dist < config_.loop_closure_distance) {
            // Check angular alignment
            double angle_diff = std::abs(current_pose.yaw - submaps_[i].origin.yaw);
            angle_diff = std::fmod(angle_diff, 2.0 * M_PI);
            if (angle_diff > M_PI) angle_diff = 2.0 * M_PI - angle_diff;

            if (angle_diff < config_.loop_closure_angle) {
                // Verify with scan matching against the candidate submap
                // (Simplified: assume valid if distance + angle match)
                loop_closure_detected_ = true;

                LoopConstraint constraint;
                constraint.from_node = node_count_ - 1;
                constraint.to_node = static_cast<int32_t>(i);
                constraint.relative_pose = current_pose;
                constraint.score = 1.0 - dist / config_.loop_closure_distance;
                loop_constraints_.push_back(constraint);

                return true;
            }
        }
    }

    return false;
}

// ============================================================================
// Pose Graph Optimization
// ============================================================================

void LaserSLAM::optimize_pose_graph() {
    // In production, this would use GTSAM or g2o for full nonlinear optimization.
    // Simplified version: apply loop closure constraint to affected nodes.

    if (loop_constraints_.empty()) return;

    for (const auto& constraint : loop_constraints_) {
        if (constraint.from_node < static_cast<int32_t>(pose_graph_.size()) &&
            constraint.to_node < static_cast<int32_t>(pose_graph_.size())) {

            // Compute correction and distribute along the path
            Pose3D from_pose = pose_graph_[constraint.from_node].pose;
            Pose3D to_pose = pose_graph_[constraint.to_node].pose;

            double error_x = from_pose.x - to_pose.x;
            double error_y = from_pose.y - to_pose.y;
            double error_yaw = from_pose.yaw - to_pose.yaw;

            // Simple error distribution (in production: use information matrix)
            int32_t range = constraint.from_node - constraint.to_node;
            if (range <= 0) continue;

            for (int32_t i = constraint.to_node + 1; i <= constraint.from_node; ++i) {
                double alpha = static_cast<double>(i - constraint.to_node) / range;
                pose_graph_[i].pose.x -= error_x * alpha * 0.5;
                pose_graph_[i].pose.y -= error_y * alpha * 0.5;
                pose_graph_[i].pose.yaw -= error_yaw * alpha * 0.5;
            }
        }
    }

    // Update submap origins from optimized poses
    for (const auto& node : pose_graph_) {
        if (node.submap_id >= 0 &&
            static_cast<size_t>(node.submap_id) < submaps_.size()) {
            submaps_[node.submap_id].origin = node.pose;
        }
    }

    update_global_grid();
}

// ============================================================================
// Global Grid Update
// ============================================================================

void LaserSLAM::update_global_grid() {
    // Reset grid
    std::fill(grid_.data.begin(), grid_.data.end(),
              static_cast<int8_t>(OccupancyState::UNKNOWN));

    int occupied_count = 0;

    // Merge all submaps into global grid
    for (const auto& submap : submaps_) {
        for (int32_t sy = 0; sy < submap.grid.height; ++sy) {
            for (int32_t sx = 0; sx < submap.grid.width; ++sx) {
                auto cell = submap.grid.at(sx, sy);
                if (cell == static_cast<int8_t>(OccupancyState::UNKNOWN)) continue;

                // Transform submap cell to global coordinates
                double wx = submap.origin.x + sx * submap.grid.resolution;
                double wy = submap.origin.y + sy * submap.grid.resolution;

                auto gpt = grid_.world_to_grid({wx, wy, 0});
                if (grid_.is_in_bounds(gpt.x, gpt.y)) {
                    grid_.data[gpt.y * grid_.width + gpt.x] = cell;
                    if (cell == static_cast<int8_t>(OccupancyState::OCCUPIED)) {
                        occupied_count++;
                    }
                }
            }
        }
    }

    grid_.total_area_sqm = occupied_count * grid_.resolution * grid_.resolution;
}

// ============================================================================
// Status
// ============================================================================

SLAMStatus LaserSLAM::get_status() const {
    return status_;
}

bool LaserSLAM::has_new_loop_closure() const {
    return loop_closure_detected_;
}

// ============================================================================
// Map Save/Load
// ============================================================================

bool LaserSLAM::save_map(const std::string& filepath) const {
    std::ofstream file(filepath, std::ios::binary);
    if (!file.is_open()) return false;

    // Write header
    QooMapHeader header;
    header.map_type = MapType::OCCUPANCY_GRID;
    header.resolution = grid_.resolution;
    header.width = grid_.width;
    header.height = grid_.height;
    header.origin_x = grid_.origin.x;
    header.origin_y = grid_.origin.y;
    auto now = std::chrono::system_clock::now().time_since_epoch();
    header.created_at_us = std::chrono::duration_cast<std::chrono::microseconds>(now).count();
    header.updated_at_us = header.created_at_us;

    file.write(reinterpret_cast<const char*>(&header), sizeof(QooMapHeader));

    // Write grid data
    file.write(reinterpret_cast<const char*>(grid_.data.data()),
               grid_.data.size() * sizeof(int8_t));

    // Compute and write checksum (simplified CRC32)
    uint32_t crc = 0;
    for (auto cell : grid_.data) {
        crc = crc ^ static_cast<uint32_t>(static_cast<uint8_t>(cell));
        for (int i = 0; i < 8; ++i) {
            crc = (crc >> 1) ^ (0xEDB88320 & -(crc & 1));
        }
    }
    file.write(reinterpret_cast<const char*>(&crc), sizeof(uint32_t));

    return file.good();
}

bool LaserSLAM::load_map(const std::string& filepath) {
    std::ifstream file(filepath, std::ios::binary);
    if (!file.is_open()) return false;

    QooMapHeader header;
    file.read(reinterpret_cast<char*>(&header), sizeof(QooMapHeader));

    // Verify magic
    if (std::memcmp(header.magic, "QOOMAP  ", 8) != 0) return false;

    grid_.resolution = header.resolution;
    grid_.width = header.width;
    grid_.height = header.height;
    grid_.origin.x = header.origin_x;
    grid_.origin.y = header.origin_y;
    grid_.data.resize(header.width * header.height);

    file.read(reinterpret_cast<char*>(grid_.data.data()),
              grid_.data.size() * sizeof(int8_t));

    // Update status for localization mode
    status_.state = SLAMState::LOCALIZING;

    return file.good();
}

} // namespace qoosvc::spatial
