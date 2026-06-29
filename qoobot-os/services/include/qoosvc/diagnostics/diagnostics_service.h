#pragma once

#include "diag_types.h"
#include "../common/result.h"
#include "../common/service_base.h"
#include <functional>
#include <memory>
#include <vector>

namespace qoosvc::diagnostics {

/**
 * DiagnosticsService — Robot self-diagnosis and health monitoring.
 *
 * Provides POST (Power-On Self-Test), continuous health monitoring,
 * fault prediction, calibration management, and health reporting.
 */
class DiagnosticsService : public ServiceBase {
public:
    DiagnosticsService();
    ~DiagnosticsService() override;

    // --- Configuration ---

    Result<void> configure(const DiagnosticsConfig& config);

    // --- Power-On Self-Test (POST) ---

    /**
     * Run full POST: check all sensors, motors, battery, and subsystems.
     * Should be called on robot boot.
     */
    Result<PostResult> run_post();

    /**
     * Run POST for a specific component.
     */
    Result<PostResult> run_component_test(const std::string& component_name);

    // --- Health Monitoring ---

    /**
     * Start continuous health monitoring.
     * Monitors temperature, current, voltage, vibration in real-time.
     */
    Result<void> start_monitoring();

    /**
     * Stop continuous monitoring.
     */
    Result<void> stop_monitoring();

    /**
     * Register callback for real-time monitoring alerts.
     */
    void on_alert(std::function<void(const DiagCheck&)> callback);

    /**
     * Get current monitoring samples.
     */
    std::vector<MonitorSample> get_current_samples() const;

    // --- Health Report ---

    /**
     * Generate a comprehensive health report.
     */
    Result<HealthReport> generate_health_report();

    /**
     * Get health report for a specific component.
     */
    Result<HealthReport> get_component_health(const std::string& component_name);

    /**
     * Get all component health scores.
     */
    std::vector<HealthReport> get_all_health() const;

    // --- Fault Prediction ---

    /**
     * Run fault prediction analysis.
     * Uses historical data to predict motor wear, battery degradation, sensor drift.
     */
    Result<std::vector<FaultPrediction>> predict_faults();

    // --- Calibration Management ---

    /**
     * Check calibration status of all sensors.
     */
    struct CalibrationStatus {
        std::string sensor_name;
        bool calibrated = false;
        uint64_t last_calibrated_us = 0;
        uint64_t calibration_interval_us = 30ULL * 24 * 3600 * 1'000'000;  // 30 days
        bool needs_recalibration = false;
    };

    Result<std::vector<CalibrationStatus>> check_calibrations();

    /**
     * Register a sensor calibration.
     */
    Result<void> record_calibration(const std::string& sensor_name);

    // --- Log Diagnostics ---

    /**
     * Collect logs from all configured sources (kernel, systemd, app, ROS2, crash).
     */
    Result<std::vector<LogEntry>> collect_logs(uint64_t start_time_us,
                                                 uint64_t end_time_us);

    /**
     * Analyze collected logs for anomalies, patterns, and root causes.
     */
    Result<LogAnalysisResult> analyze_logs(const std::vector<LogEntry>& logs);

    /**
     * Run full log diagnostics: collect + analyze + correlate.
     * Searches for crash reports, kernel panics, and system event correlations.
     */
    Result<LogAnalysisResult> run_log_diagnostics(uint64_t start_time_us,
                                                    uint64_t end_time_us);

    /**
     * Collect crash reports (core dumps) and extract stack traces.
     */
    Result<std::vector<LogEntry>> collect_crash_reports();

    /**
     * Correlate a crash with preceding system events for root cause analysis.
     */
    Result<CorrelatedEvent> analyze_crash(const LogEntry& crash_log);

    // --- Recovery ---

    /**
     * Attempt fault recovery for a component.
     * Strategies: reset, restart, degrade, safe mode.
     */
    Result<void> recover_component(const std::string& component_name);

    /**
     * Enter safe mode — minimal functionality, maximum safety.
     */
    Result<void> enter_safe_mode();

    /**
     * Exit safe mode and restore normal operation.
     */
    Result<void> exit_safe_mode();

protected:
    Result<void> on_initialize() override;
    Result<void> on_stop() override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoosvc::diagnostics
