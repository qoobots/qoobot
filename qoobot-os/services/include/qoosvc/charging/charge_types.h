#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::charging {

// ============================================================================
// Charging Dock Types
// ============================================================================

struct ChargingDock {
    std::string dock_id;
    std::string name;              // e.g., "Living Room Dock"
    Pose3D pose;                    // Dock pose in map frame
    std::string detection_method;  // "visual", "infrared", "magnetic", "contact"
    double approach_distance = 0.5; // Distance to start docking procedure
    double alignment_tolerance = 0.05; // meters
    double angle_tolerance = 5.0;  // degrees
    bool is_available = true;
    int64_t last_docked_us = 0;
};

struct Pose3D {
    double x = 0, y = 0, z = 0;
    double roll = 0, pitch = 0, yaw = 0;
    std::string frame_id = "map";
    double distance_to(const Pose3D& other) const {
        return std::sqrt((x-other.x)*(x-other.x) + (y-other.y)*(y-other.y));
    }
};

// ============================================================================
// Charging Strategy Types
// ============================================================================

enum class ChargingMode : uint8_t {
    OPPORTUNISTIC,     // Charge whenever at dock
    SCHEDULED,         // Charge at specific times (off-peak)
    THRESHOLD,         // Charge when battery drops below threshold
    PRE_TASK,          // Charge before scheduled tasks
    MANUAL             // User-initiated charging
};

struct ChargingSchedule {
    std::string start_time;        // "HH:MM" format
    std::string end_time;
    std::vector<int> days_of_week; // 0=Sun, 6=Sat
    bool enabled = true;
};

struct ChargingStrategy {
    ChargingMode mode = ChargingMode::THRESHOLD;
    double low_battery_threshold = 0.20;   // Start charging below 20%
    double full_battery_threshold = 0.95;  // Stop charging at 95%
    double task_min_battery = 0.40;        // Minimum battery before task
    std::vector<ChargingSchedule> schedules;
    bool prefer_off_peak = true;           // Prefer charging during low-cost hours
    bool interruptible = true;             // Can interrupt charging for urgent tasks
};

// ============================================================================
// Charging Status Types
// ============================================================================

enum class ChargingState : uint8_t {
    IDLE,
    SEARCHING_DOCK,     // Looking for charging dock
    APPROACHING,        // Moving toward dock
    ALIGNING,           // Fine alignment with dock contacts
    DOCKED,             // Physically connected
    CHARGING,           // Power flowing
    CHARGED,            // Battery full, still connected
    UNDOCKING,          // Disconnecting from dock
    ERROR               // Charging fault
};

struct ChargingStatus {
    ChargingState state = ChargingState::IDLE;
    std::string dock_id;
    double battery_level = 0.0;    // [0, 1]
    double charging_power_w = 0.0; // Current charging power
    double voltage_v = 0.0;
    double current_a = 0.0;
    double temperature_c = 25.0;
    double estimated_time_to_full_s = 0.0;
    int32_t charge_cycles = 0;
    bool dock_connected = false;
    std::string error_message;
};

// ============================================================================
// Dock Detection Types
// ============================================================================

enum class DockDetectionMethod : uint8_t {
    VISUAL_MARKER,     // QR/ArUco marker on dock
    INFRARED_BEACON,   // IR beacon on dock
    MAGNETIC_FIELD,    // Magnetic alignment
    LIDAR_FEATURE,     // LiDAR-based dock recognition
    CONTACT_SENSOR     // Physical contact detection
};

struct DockDetectionResult {
    bool detected = false;
    Pose3D dock_pose;
    double confidence = 0.0;
    double distance_m = 0.0;
    double angle_offset_deg = 0.0;
    DockDetectionMethod method = DockDetectionMethod::VISUAL_MARKER;
    int64_t timestamp_us = 0;
};

// ============================================================================
// Wireless Charging Types
// ============================================================================

struct WirelessChargingConfig {
    bool enabled = false;
    double efficiency = 0.85;      // Typical Qi efficiency
    double max_power_w = 15.0;     // Maximum wireless power
    double alignment_tolerance_m = 0.02;
    double max_distance_m = 0.01;  // Maximum gap for wireless
};

} // namespace qoosvc::charging
