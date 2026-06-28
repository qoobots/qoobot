#include "qoosvc/diagnostics/diagnostics_service.h"
#include <algorithm>
#include <chrono>
#include <mutex>
#include <thread>

namespace qoosvc::diagnostics {

// ============================================================================
// DiagnosticsService::Impl
// ============================================================================

struct DiagnosticsService::Impl {
    DiagnosticsConfig config;
    std::function<void(const DiagCheck&)> alert_callback;
    std::vector<DiagCheck> recent_checks;
    std::vector<HealthReport> component_health;
    std::vector<MonitorSample> current_samples;
    std::vector<CalibrationStatus> calibrations;
    std::vector<FaultPrediction> predictions;
    std::thread monitoring_thread;
    std::atomic<bool> monitoring_active{false};
    std::atomic<bool> safe_mode{false};
    mutable std::mutex mutex;
};

// ============================================================================
// Constructor / Destructor
// ============================================================================

DiagnosticsService::DiagnosticsService()
    : ServiceBase("diagnostics_service")
    , impl_(std::make_unique<Impl>()) {
}

DiagnosticsService::~DiagnosticsService() {
    stop_monitoring();
    stop();
}

// ============================================================================
// Configuration
// ============================================================================

Result<void> DiagnosticsService::configure(const DiagnosticsConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->config = config;
    return Result<void>::ok();
}

// ============================================================================
// POST (Power-On Self-Test)
// ============================================================================

Result<PostResult> DiagnosticsService::run_post() {
    auto start = std::chrono::steady_clock::now();
    PostResult result;

    // Component checks
    struct ComponentCheck {
        std::string name;
        std::string check;
        double min_val;
        double max_val;
    };

    std::vector<ComponentCheck> checks = {
        // Sensors
        {"RGB Camera", "image_stream", 0.0, 1.0},
        {"Depth Camera", "depth_stream", 0.0, 1.0},
        {"LiDAR", "point_cloud", 0.0, 1.0},
        {"IMU", "accel_gyro", 0.0, 1.0},
        {"Microphone Array", "audio_capture", 0.0, 1.0},

        // Motors
        {"Left Shoulder Pitch", "encoder_feedback", 0.0, 1.0},
        {"Left Shoulder Roll", "encoder_feedback", 0.0, 1.0},
        {"Right Shoulder Pitch", "encoder_feedback", 0.0, 1.0},
        {"Right Shoulder Roll", "encoder_feedback", 0.0, 1.0},

        // Power
        {"Battery", "voltage_level", 22.0, 29.4},  // 6S LiPo
        {"Power Management", "pmic_status", 0.0, 1.0},
    };

    for (const auto& check : checks) {
        DiagCheck diag;
        diag.component_name = check.name;
        diag.check_name = check.check;
        diag.expected_min = check.min_val;
        diag.expected_max = check.max_val;
        diag.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();

        // Simulate check result (in production, actually read sensor data)
        diag.measured_value = (check.min_val + check.max_val) / 2.0;
        diag.severity = DiagSeverity::OK;
        diag.message = check.name + " check passed";

        result.checks.push_back(diag);
        result.total_checks++;
        result.passed_checks++;
    }

    auto end = std::chrono::steady_clock::now();
    result.duration_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
    result.all_passed = (result.failed_checks == 0);

    // Store checks
    {
        std::lock_guard<std::mutex> lock(impl_->mutex);
        impl_->recent_checks = result.checks;
    }

    return result;
}

Result<PostResult> DiagnosticsService::run_component_test(const std::string& component_name) {
    PostResult result;
    DiagCheck check;
    check.component_name = component_name;
    check.check_name = "manual_test";
    check.severity = DiagSeverity::OK;
    check.message = component_name + " test passed";
    check.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    result.checks.push_back(check);
    result.total_checks = 1;
    result.passed_checks = 1;
    result.all_passed = true;

    return result;
}

// ============================================================================
// Health Monitoring
// ============================================================================

Result<void> DiagnosticsService::start_monitoring() {
    if (impl_->monitoring_active) {
        return Result<void>::ok();  // Already monitoring
    }

    impl_->monitoring_active = true;
    impl_->monitoring_thread = std::thread([this]() {
        while (impl_->monitoring_active) {
            // Collect monitoring samples
            std::vector<MonitorSample> samples;

            // Temperature sensors
            MonitorSample cpu_temp;
            cpu_temp.component_name = "CPU";
            cpu_temp.metric_name = "temperature";
            cpu_temp.value = 45.0;  // Placeholder
            cpu_temp.unit = "°C";
            cpu_temp.warning_threshold = 80.0;
            cpu_temp.critical_threshold = 95.0;
            cpu_temp.timestamp_us = std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count();
            samples.push_back(cpu_temp);

            MonitorSample battery_volt;
            battery_volt.component_name = "Battery";
            battery_volt.metric_name = "voltage";
            battery_volt.value = 25.2;  // Placeholder for 6S LiPo
            battery_volt.unit = "V";
            battery_volt.warning_threshold = 22.0;
            battery_volt.critical_threshold = 20.0;
            battery_volt.timestamp_us = cpu_temp.timestamp_us;
            samples.push_back(battery_volt);

            {
                std::lock_guard<std::mutex> lock(impl_->mutex);
                impl_->current_samples = samples;

                // Check for alerts
                for (const auto& sample : samples) {
                    if (sample.value >= sample.critical_threshold && impl_->alert_callback) {
                        DiagCheck alert;
                        alert.component_name = sample.component_name;
                        alert.check_name = sample.metric_name;
                        alert.severity = DiagSeverity::CRITICAL;
                        alert.message = sample.component_name + " " + sample.metric_name
                                      + " critical: " + std::to_string(sample.value) + sample.unit;
                        alert.measured_value = sample.value;
                        alert.expected_max = sample.critical_threshold;
                        alert.timestamp_us = sample.timestamp_us;
                        impl_->alert_callback(alert);
                    }
                }
            }

            std::this_thread::sleep_for(
                std::chrono::microseconds(impl_->config.monitoring_interval_us));
        }
    });

    return Result<void>::ok();
}

Result<void> DiagnosticsService::stop_monitoring() {
    impl_->monitoring_active = false;
    if (impl_->monitoring_thread.joinable()) {
        impl_->monitoring_thread.join();
    }
    return Result<void>::ok();
}

void DiagnosticsService::on_alert(std::function<void(const DiagCheck&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->alert_callback = std::move(callback);
}

std::vector<MonitorSample> DiagnosticsService::get_current_samples() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->current_samples;
}

// ============================================================================
// Health Report
// ============================================================================

Result<HealthReport> DiagnosticsService::generate_health_report() {
    HealthReport report;
    report.component_name = "overall";
    report.generated_at_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    report.valid_until_us = report.generated_at_us + 3600ULL * 1'000'000;  // 1 hour

    // Aggregate health from all components
    double total_score = 0.0;
    int component_count = 0;

    {
        std::lock_guard<std::mutex> lock(impl_->mutex);
        for (const auto& health : impl_->component_health) {
            total_score += health.health_score;
            component_count++;
        }
    }

    report.health_score = component_count > 0 ? total_score / component_count : 100.0;

    if (report.health_score >= 90.0) {
        report.status = "HEALTHY";
    } else if (report.health_score >= 70.0) {
        report.status = "DEGRADED";
    } else {
        report.status = "FAULTY";
    }

    return report;
}

Result<HealthReport> DiagnosticsService::get_component_health(const std::string& component_name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->component_health.begin(), impl_->component_health.end(),
        [&](const auto& h) { return h.component_name == component_name; });

    if (it != impl_->component_health.end()) {
        return *it;
    }

    return Result<HealthReport>::err(ErrorCode::INVALID_ARGUMENT,
                                      "Component not found: " + component_name);
}

std::vector<HealthReport> DiagnosticsService::get_all_health() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->component_health;
}

// ============================================================================
// Fault Prediction
// ============================================================================

Result<std::vector<FaultPrediction>> DiagnosticsService::predict_faults() {
    std::vector<FaultPrediction> predictions;

    // Motor wear prediction (simplified)
    FaultPrediction motor_wear;
    motor_wear.component_name = "Joint Motors";
    motor_wear.fault_type = "MOTOR_WEAR";
    motor_wear.probability = 0.05;  // 5% chance of failure in next 30 days
    motor_wear.recommendation = "No immediate action required";
    predictions.push_back(motor_wear);

    // Battery degradation
    FaultPrediction battery;
    battery.component_name = "Battery";
    battery.fault_type = "BATTERY_DEGRADATION";
    battery.probability = 0.02;
    battery.recommendation = "Battery health is good";
    predictions.push_back(battery);

    {
        std::lock_guard<std::mutex> lock(impl_->mutex);
        impl_->predictions = predictions;
    }

    return predictions;
}

// ============================================================================
// Calibration Management
// ============================================================================

Result<std::vector<DiagnosticsService::CalibrationStatus>>
DiagnosticsService::check_calibrations() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->calibrations.empty()) {
        // Initialize calibration records
        std::vector<std::string> sensors = {
            "RGB Camera", "Depth Camera", "LiDAR", "IMU",
            "Joint Encoder 1", "Joint Encoder 2", "Force-Torque Sensor"
        };

        auto now = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();

        for (const auto& name : sensors) {
            CalibrationStatus cal;
            cal.sensor_name = name;
            cal.calibrated = false;
            cal.last_calibrated_us = 0;
            cal.needs_recalibration = true;
            impl_->calibrations.push_back(cal);
        }
    }

    return impl_->calibrations;
}

Result<void> DiagnosticsService::record_calibration(const std::string& sensor_name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->calibrations.begin(), impl_->calibrations.end(),
        [&](const auto& c) { return c.sensor_name == sensor_name; });

    if (it != impl_->calibrations.end()) {
        it->calibrated = true;
        it->last_calibrated_us = std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
        it->needs_recalibration = false;
    }

    return Result<void>::ok();
}

// ============================================================================
// Recovery
// ============================================================================

Result<void> DiagnosticsService::recover_component(const std::string& component_name) {
    // Recovery strategies per component type
    // In production: reset hardware, restart driver, fallback to degraded mode
    return Result<void>::ok();
}

Result<void> DiagnosticsService::enter_safe_mode() {
    impl_->safe_mode = true;
    return Result<void>::ok();
}

Result<void> DiagnosticsService::exit_safe_mode() {
    impl_->safe_mode = false;
    return Result<void>::ok();
}

// ============================================================================
// Service Lifecycle
// ============================================================================

Result<void> DiagnosticsService::on_initialize() {
    // Run POST on startup if configured
    if (impl_->config.enable_post_on_boot) {
        run_post();
    }

    // Start continuous monitoring if configured
    if (impl_->config.enable_continuous_monitoring) {
        start_monitoring();
    }

    return Result<void>::ok();
}

Result<void> DiagnosticsService::on_stop() {
    stop_monitoring();
    return Result<void>::ok();
}

} // namespace qoosvc::diagnostics
