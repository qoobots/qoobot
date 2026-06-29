/**
 * @file anomaly_diagnosis.h
 * @brief 异常诊断 — 推理超时、OOM、精度异常自动告警与根因分析
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <chrono>

namespace qoocore {
namespace profiler {

enum class AnomalyType : std::uint8_t {
    INFERENCE_TIMEOUT   = 0,
    OUT_OF_MEMORY       = 1,
    ACCURACY_DEGRADATION= 2,
    LATENCY_SPIKE       = 3,
    BACKEND_FAILURE     = 4,
    THERMAL_THROTTLE    = 5,
    DATA_CORRUPTION     = 6,
};

struct AnomalyEvent {
    AnomalyType type;
    std::string description;
    std::string root_cause;
    std::string suggestion;
    double timestamp{0.0};
    float severity{0.0f};           ///< 0.0~1.0
    std::unordered_map<std::string, std::string> metadata;
};

struct DiagnosisConfig {
    float timeout_threshold_ms{100.0f};
    float latency_spike_factor{3.0f};
    float memory_pressure_threshold{0.9f};
    bool auto_recovery{true};
};

class AnomalyDiagnosis {
public:
    explicit AnomalyDiagnosis(const DiagnosisConfig& config);
    ~AnomalyDiagnosis() = default;

    ErrorCode detect_timeout(const std::string& model, float latency_ms,
                             AnomalyEvent& event);
    ErrorCode detect_oom(const std::string& component, std::size_t requested,
                         std::size_t available, AnomalyEvent& event);
    ErrorCode detect_accuracy_degradation(const std::string& model,
                                          float drift_score, AnomalyEvent& event);
    ErrorCode detect_latency_spike(const std::string& model, float current_ms,
                                   float baseline_ms, AnomalyEvent& event);

    std::vector<AnomalyEvent> recent_events() const;
    void clear_events();

    using AlertCallback = std::function<void(const AnomalyEvent&)>;
    void set_alert_callback(AlertCallback cb);

    static std::string suggest_recovery(const AnomalyEvent& event);

private:
    DiagnosisConfig config_;
    std::vector<AnomalyEvent> events_;
    AlertCallback alert_cb_;
};

} // namespace profiler
} // namespace qoocore
