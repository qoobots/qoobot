#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace qoosvc::diagnostics {

/**
 * Sensor type enumeration.
 */
enum class SensorType : uint8_t {
    CAMERA_RGB,
    CAMERA_DEPTH,
    LIDAR,
    IMU,
    MICROPHONE_ARRAY,
    JOINT_ENCODER,
    MOTOR_CURRENT,
    TEMPERATURE,
    BATTERY_VOLTAGE,
    FORCE_TORQUE,
    TOUCH
};

/**
 * Diagnostic severity.
 */
enum class DiagSeverity : uint8_t {
    OK,
    INFO,
    WARNING,
    ERROR,
    CRITICAL
};

/**
 * Individual diagnostic check result.
 */
struct DiagCheck {
    std::string component_name;
    std::string check_name;
    DiagSeverity severity = DiagSeverity::OK;
    std::string message;
    double measured_value = 0.0;
    double expected_min = 0.0;
    double expected_max = 0.0;
    std::string recommendation;
    uint64_t timestamp_us = 0;
};

/**
 * POST (Power-On Self-Test) result.
 */
struct PostResult {
    bool all_passed = false;
    int total_checks = 0;
    int passed_checks = 0;
    int warning_checks = 0;
    int failed_checks = 0;
    std::vector<DiagCheck> checks;
    uint64_t duration_us = 0;
};

/**
 * Health report for a component.
 */
struct HealthReport {
    std::string component_name;
    double health_score = 100.0;        // 0-100, 100 = perfect health
    std::string status;                 // "HEALTHY", "DEGRADED", "FAULTY"
    std::vector<DiagCheck> recent_issues;
    uint64_t generated_at_us = 0;
    uint64_t valid_until_us = 0;
};

/**
 * Fault prediction.
 */
struct FaultPrediction {
    std::string component_name;
    std::string fault_type;             // "MOTOR_WEAR", "BATTERY_DEGRADATION", "SENSOR_DRIFT"
    double probability = 0.0;           // 0.0 - 1.0
    uint64_t estimated_time_to_failure_us = 0;  // 0 = unknown
    std::string recommendation;
};

/**
 * Real-time monitoring sample.
 */
struct MonitorSample {
    std::string component_name;
    std::string metric_name;            // "temperature", "current", "voltage", "vibration"
    double value = 0.0;
    std::string unit;                   // "°C", "A", "V", "mm/s"
    double warning_threshold = 0.0;
    double critical_threshold = 0.0;
    uint64_t timestamp_us = 0;
};

/**
 * Diagnostics configuration.
 */
struct DiagnosticsConfig {
    bool enable_post_on_boot = true;
    bool enable_continuous_monitoring = true;
    uint64_t monitoring_interval_us = 1'000'000;  // 1 second
    bool enable_fault_prediction = true;
    std::string health_report_path = "/var/lib/qoosvc/diagnostics/";
};

} // namespace qoosvc::diagnostics
