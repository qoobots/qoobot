// ============================================================================
// log_diagnostics.cpp — Log collection, analysis & crash correlation
// Part of qoosvc::diagnostics::DiagnosticsService (PIMPL extension)
// ============================================================================

#include "qoosvc/diagnostics/diagnostics_service.h"
#include <algorithm>
#include <chrono>
#include <fstream>
#include <map>
#include <regex>
#include <set>
#include <sstream>

namespace qoosvc::diagnostics {

// ============================================================================
// Log Collection
// ============================================================================

Result<std::vector<LogEntry>> DiagnosticsService::collect_logs(
    uint64_t start_time_us, uint64_t end_time_us) {

    std::vector<LogEntry> logs;

    // In production: read from actual log sources
    // - /var/log/syslog → kernel & system logs
    // - journald → systemd service logs
    // - ROS 2 log directory → node logs
    // - Application log files → QooBot app logs

    // Framework skeleton: generate representative log entries for analysis
    auto now_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    // Simulate kernel logs
    {
        LogEntry entry;
        entry.source = LogEntry::Source::KERNEL;
        entry.severity = DiagSeverity::INFO;
        entry.component = "kernel";
        entry.message = "USB device connected: QooBot Sensor Hub (vid:pid=2e8a:000a)";
        entry.timestamp_us = now_us - 3600'000'000;
        entry.pid = 0;
        entry.thread_name = "kworker";
        logs.push_back(entry);
    }
    {
        LogEntry entry;
        entry.source = LogEntry::Source::KERNEL;
        entry.severity = DiagSeverity::WARNING;
        entry.component = "kernel";
        entry.message = "thermal: CPU temperature 82°C approaching throttle threshold";
        entry.timestamp_us = now_us - 1800'000'000;
        entry.pid = 0;
        entry.thread_name = "thermal-monitor";
        logs.push_back(entry);
    }

    // Simulate application logs
    {
        LogEntry entry;
        entry.source = LogEntry::Source::APPLICATION;
        entry.severity = DiagSeverity::ERROR;
        entry.component = "qoosvc.navigation";
        entry.message = "Navigation recovery failed: localization lost near (x=3.2, y=1.8)";
        entry.file = "navigation_service.cpp";
        entry.line = 326;
        entry.timestamp_us = now_us - 900'000'000;
        entry.pid = 1234;
        entry.thread_name = "nav_planner";
        logs.push_back(entry);
    }
    {
        LogEntry entry;
        entry.source = LogEntry::Source::APPLICATION;
        entry.severity = DiagSeverity::WARNING;
        entry.component = "qoosvc.voice";
        entry.message = "ASR confidence below threshold (0.42), retrying with noise reduction";
        entry.file = "voice_service.cpp";
        entry.line = 108;
        entry.timestamp_us = now_us - 600'000'000;
        entry.pid = 1234;
        entry.thread_name = "voice_asr";
        logs.push_back(entry);
    }
    {
        LogEntry entry;
        entry.source = LogEntry::Source::APPLICATION;
        entry.severity = DiagSeverity::INFO;
        entry.component = "qoosvc.charging";
        entry.message = "Auto-docking successful: dock_id=main_dock, alignment_error=0.02m";
        entry.file = "charging_service.cpp";
        entry.line = 167;
        entry.timestamp_us = now_us - 300'000'000;
        entry.pid = 1234;
        entry.thread_name = "charge_ctrl";
        logs.push_back(entry);
    }

    // Simulate ROS2 logs
    {
        LogEntry entry;
        entry.source = LogEntry::Source::ROS2;
        entry.severity = DiagSeverity::WARNING;
        entry.component = "qoobody.lidar_driver";
        entry.message = "LiDAR scan rate dropped to 8Hz (expected 10Hz), possible USB bandwidth issue";
        entry.timestamp_us = now_us - 1200'000'000;
        entry.pid = 5678;
        entry.thread_name = "lidar_poll";
        logs.push_back(entry);
    }
    {
        LogEntry entry;
        entry.source = LogEntry::Source::ROS2;
        entry.severity = DiagSeverity::ERROR;
        entry.component = "qoobody.motor_controller";
        entry.message = "Joint 'left_shoulder_pitch' overcurrent: 12.5A > 10A limit, emergency stop";
        entry.timestamp_us = now_us - 100'000'000;
        entry.pid = 5678;
        entry.thread_name = "motor_ctrl";
        logs.push_back(entry);
    }

    // Simulate systemd logs
    {
        LogEntry entry;
        entry.source = LogEntry::Source::SYSTEMD;
        entry.severity = DiagSeverity::INFO;
        entry.component = "qoosvc.service";
        entry.message = "Service qoosvc started successfully (PID=1234)";
        entry.timestamp_us = now_us - 7200'000'000;
        entry.pid = 1;
        entry.thread_name = "systemd";
        logs.push_back(entry);
    }
    {
        LogEntry entry;
        entry.source = LogEntry::Source::SYSTEMD;
        entry.severity = DiagSeverity::WARNING;
        entry.component = "qoosvc.service";
        entry.message = "Memory usage high: 1.8GB / 2GB (90%), consider increasing swap";
        entry.timestamp_us = now_us - 2400'000'000;
        entry.pid = 1;
        entry.thread_name = "systemd";
        logs.push_back(entry);
    }

    // Filter by time range if specified
    if (start_time_us > 0 || end_time_us > 0) {
        std::vector<LogEntry> filtered;
        for (const auto& log : logs) {
            if (log.timestamp_us >= start_time_us &&
                (end_time_us == 0 || log.timestamp_us <= end_time_us)) {
                filtered.push_back(log);
            }
        }
        return filtered;
    }

    return logs;
}

// ============================================================================
// Log Analysis
// ============================================================================

Result<LogAnalysisResult> DiagnosticsService::analyze_logs(const std::vector<LogEntry>& logs) {
    LogAnalysisResult result;
    result.analysis_time_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    result.total_logs_analyzed = static_cast<int>(logs.size());

    if (logs.empty()) {
        result.system_stability_score = 100.0;
        return result;
    }

    // Set time range
    if (!logs.empty()) {
        result.log_range_start_us = logs.front().timestamp_us;
        result.log_range_end_us = logs.back().timestamp_us;
    }

    // Count severity distribution
    std::map<DiagSeverity, int> severity_counts;
    for (const auto& log : logs) {
        severity_counts[log.severity]++;
    }

    // Calculate system stability score
    // Weight: CRITICAL=-30, ERROR=-15, WARNING=-5, INFO=+1, OK=+2
    double score = 100.0;
    score -= severity_counts[DiagSeverity::CRITICAL] * 30.0;
    score -= severity_counts[DiagSeverity::ERROR] * 15.0;
    score -= severity_counts[DiagSeverity::WARNING] * 5.0;
    score += severity_counts[DiagSeverity::INFO] * 1.0;
    score += severity_counts[DiagSeverity::OK] * 2.0;
    result.system_stability_score = std::max(0.0, std::min(100.0, score));

    // Detect anomalies and correlate events
    std::map<std::string, std::vector<LogEntry>> component_logs;
    for (const auto& log : logs) {
        component_logs[log.component].push_back(log);
    }

    // Find components with multiple ERROR/CRITICAL logs
    for (const auto& [component, comp_logs] : component_logs) {
        int error_count = 0;
        int critical_count = 0;

        for (const auto& log : comp_logs) {
            if (log.severity == DiagSeverity::ERROR) error_count++;
            if (log.severity == DiagSeverity::CRITICAL) critical_count++;
        }

        if (error_count >= 2 || critical_count >= 1) {
            // This component has anomalies — create a correlated event
            CorrelatedEvent event;
            event.event_id = "evt_" + component + "_" +
                             std::to_string(comp_logs.front().timestamp_us);
            event.root_cause = "Component '" + component + "' has " +
                               std::to_string(error_count) + " errors and " +
                               std::to_string(critical_count) + " critical events";
            event.related_logs = comp_logs;
            event.severity = critical_count > 0 ? DiagSeverity::CRITICAL : DiagSeverity::ERROR;
            event.correlation_score = std::min(1.0,
                0.5 + 0.1 * (error_count + critical_count * 3));
            event.first_seen_us = comp_logs.front().timestamp_us;
            event.last_seen_us = comp_logs.back().timestamp_us;

            // Generate recommendation
            if (component.find("navigation") != std::string::npos) {
                event.recommendation = "Check SLAM localization quality and sensor calibration";
            } else if (component.find("motor") != std::string::npos) {
                event.recommendation = "Inspect motor driver and check for mechanical binding";
            } else if (component.find("voice") != std::string::npos) {
                event.recommendation = "Check microphone array and reduce ambient noise";
            } else if (component.find("lidar") != std::string::npos) {
                event.recommendation = "Check USB bandwidth allocation and LiDAR cable connection";
            } else {
                event.recommendation = "Review component logs and run hardware diagnostics";
            }

            result.correlated_events.push_back(event);

            // Create diagnostic check for each anomaly
            DiagCheck diag;
            diag.component_name = component;
            diag.check_name = "log_anomaly_detected";
            diag.severity = event.severity;
            diag.message = event.root_cause;
            diag.recommendation = event.recommendation;
            diag.timestamp_us = event.last_seen_us;
            result.issues.push_back(diag);
            result.anomalies_found++;
        }
    }

    // Detect temporal correlations: events that happened close together
    for (size_t i = 0; i < result.correlated_events.size(); ++i) {
        for (size_t j = i + 1; j < result.correlated_events.size(); ++j) {
            auto& evt_a = result.correlated_events[i];
            auto& evt_b = result.correlated_events[j];

            int64_t time_diff = static_cast<int64_t>(evt_a.first_seen_us) -
                                static_cast<int64_t>(evt_b.first_seen_us);
            if (std::abs(time_diff) < 5'000'000) {  // Within 5 seconds
                // Events are temporally correlated — merge or link
                evt_a.correlation_score = std::max(evt_a.correlation_score, 0.8);
                evt_b.correlation_score = std::max(evt_b.correlation_score, 0.8);

                // Cross-reference
                evt_a.root_cause += " | Temporally correlated with: " + evt_b.event_id;
                evt_b.root_cause += " | Temporally correlated with: " + evt_a.event_id;
            }
        }
    }

    // Sort issues by severity (most severe first)
    std::sort(result.issues.begin(), result.issues.end(),
        [](const auto& a, const auto& b) {
            return static_cast<int>(a.severity) > static_cast<int>(b.severity);
        });

    return result;
}

// ============================================================================
// Full Log Diagnostics Pipeline
// ============================================================================

Result<LogAnalysisResult> DiagnosticsService::run_log_diagnostics(
    uint64_t start_time_us, uint64_t end_time_us) {

    // Step 1: Collect logs
    auto logs_result = collect_logs(start_time_us, end_time_us);
    if (logs_result.is_err()) {
        return Result<LogAnalysisResult>::err(logs_result.error_code(),
            "Log collection failed: " + logs_result.error_message());
    }

    // Step 2: Collect crash reports
    auto crash_result = collect_crash_reports();
    std::vector<LogEntry> all_logs = *logs_result;
    if (crash_result.is_ok()) {
        auto& crashes = *crash_result;
        all_logs.insert(all_logs.end(), crashes.begin(), crashes.end());
    }

    // Step 3: Analyze
    return analyze_logs(all_logs);
}

// ============================================================================
// Crash Report Collection & Analysis
// ============================================================================

Result<std::vector<LogEntry>> DiagnosticsService::collect_crash_reports() {
    std::vector<LogEntry> crash_logs;

    // In production: scan crash dump directory for core dumps
    // Parse core dump metadata: signal, PID, timestamp, stack trace
    // For framework: generate representative crash entries

    auto now_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    // Simulate a crash report
    LogEntry crash;
    crash.source = LogEntry::Source::CRASH;
    crash.severity = DiagSeverity::CRITICAL;
    crash.component = "qoosvc.navigation";
    crash.message = "SIGSEGV (Segmentation fault) in NavigationService::plan_global_path() "
                    "at navigation_service.cpp:78 — null pointer dereference in costmap access";
    crash.file = "navigation_service.cpp";
    crash.line = 78;
    crash.timestamp_us = now_us - 1500'000'000;
    crash.pid = 1234;
    crash.thread_name = "nav_planner";
    crash_logs.push_back(crash);

    // Simulate an OOM kill
    LogEntry oom;
    oom.source = LogEntry::Source::CRASH;
    oom.severity = DiagSeverity::CRITICAL;
    oom.component = "qoosvc.spatial";
    oom.message = "OOM Killer: qoosvc (PID=1234) killed due to memory exhaustion "
                  "(RSS=1.92GB, limit=2.0GB) during 3D reconstruction";
    oom.timestamp_us = now_us - 3600'000'000;
    oom.pid = 1234;
    oom.thread_name = "oom-killer";
    crash_logs.push_back(oom);

    return crash_logs;
}

Result<CorrelatedEvent> DiagnosticsService::analyze_crash(const LogEntry& crash_log) {
    if (crash_log.source != LogEntry::Source::CRASH) {
        return Result<CorrelatedEvent>::err(ErrorCode::INVALID_ARGUMENT,
            "Not a crash log entry");
    }

    CorrelatedEvent event;
    event.event_id = "crash_" + crash_log.component + "_" +
                     std::to_string(crash_log.timestamp_us);
    event.root_cause = "Crash detected in " + crash_log.component + ": " + crash_log.message;
    event.related_logs.push_back(crash_log);
    event.severity = DiagSeverity::CRITICAL;
    event.correlation_score = 1.0;  // Direct crash event
    event.first_seen_us = crash_log.timestamp_us;
    event.last_seen_us = crash_log.timestamp_us;

    // Root cause analysis based on crash type
    if (crash_log.message.find("SIGSEGV") != std::string::npos) {
        event.recommendation = "Segmentation fault detected. Check null pointer dereference. "
                               "Review code at " + crash_log.file + ":" +
                               std::to_string(crash_log.line) +
                               ". Run with AddressSanitizer for detailed report.";
    } else if (crash_log.message.find("OOM") != std::string::npos ||
               crash_log.message.find("memory") != std::string::npos) {
        event.recommendation = "Out of memory. Consider: (1) reducing map resolution, "
                               "(2) limiting point cloud density, (3) increasing swap space, "
                               "(4) adding memory monitoring with early warning thresholds.";
    } else if (crash_log.message.find("SIGABRT") != std::string::npos) {
        event.recommendation = "Assertion failure. Check invariant conditions. "
                               "Review recent code changes for violated assumptions.";
    } else {
        event.recommendation = "Unexpected crash. Collect core dump for offline analysis. "
                               "Enable crash reporting to qoocloud for centralized triage.";
    }

    return event;
}

} // namespace qoosvc::diagnostics
