/**
 * @file anomaly_diagnosis.cpp
 * @brief 异常诊断实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/profiler/anomaly_diagnosis.h"
#include <algorithm>
#include <chrono>
#include <sstream>

namespace qoocore {
namespace profiler {

namespace {
double now_sec() {
    return std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

AnomalyEvent make_event(AnomalyType type, const std::string& desc,
                        const std::string& cause, const std::string& suggestion,
                        float severity = 0.5f)
{
    AnomalyEvent e;
    e.type = type;
    e.description = desc;
    e.root_cause = cause;
    e.suggestion = suggestion;
    e.timestamp = now_sec();
    e.severity = severity;
    return e;
}
} // anonymous

AnomalyDiagnosis::AnomalyDiagnosis(const DiagnosisConfig& config)
    : config_(config) {}

ErrorCode AnomalyDiagnosis::detect_timeout(
    const std::string& model, float latency_ms, AnomalyEvent& event)
{
    if (latency_ms > config_.timeout_threshold_ms) {
        std::ostringstream desc, cause, sugg;
        desc << "Inference timeout: " << model << " took " << latency_ms << "ms";
        cause << "Model complexity or backend overload";
        sugg << "Consider model pruning, quantization, or switching backend";
        event = make_event(AnomalyType::INFERENCE_TIMEOUT,
            desc.str(), cause.str(), sugg.str(), 0.7f);
        events_.push_back(event);
        if (alert_cb_) alert_cb_(event);
    }
    return ErrorCode::OK;
}

ErrorCode AnomalyDiagnosis::detect_oom(
    const std::string& component, std::size_t requested,
    std::size_t available, AnomalyEvent& event)
{
    if (requested > available) {
        std::ostringstream desc, cause, sugg;
        desc << "OOM: " << component << " requested " << (requested/1024/1024)
             << "MB but only " << (available/1024/1024) << "MB available";
        cause << "Memory fragmentation or model too large";
        sugg << "Enable memory swapping, reduce model size, or use weight sharing";
        event = make_event(AnomalyType::OUT_OF_MEMORY,
            desc.str(), cause.str(), sugg.str(), 0.9f);
        events_.push_back(event);
        if (alert_cb_) alert_cb_(event);
    }
    return ErrorCode::OK;
}

ErrorCode AnomalyDiagnosis::detect_accuracy_degradation(
    const std::string& model, float drift_score, AnomalyEvent& event)
{
    if (drift_score > 0.1f) {
        std::ostringstream desc, cause, sugg;
        desc << "Accuracy degradation: " << model << " drift=" << drift_score;
        cause << "Quantization error, data distribution shift, or model staleness";
        sugg << "Recalibrate quantization, update model, or check input distribution";
        event = make_event(AnomalyType::ACCURACY_DEGRADATION,
            desc.str(), cause.str(), sugg.str(),
            std::min(1.0f, drift_score * 5.0f));
        events_.push_back(event);
        if (alert_cb_) alert_cb_(event);
    }
    return ErrorCode::OK;
}

ErrorCode AnomalyDiagnosis::detect_latency_spike(
    const std::string& model, float current_ms, float baseline_ms,
    AnomalyEvent& event)
{
    if (current_ms > baseline_ms * config_.latency_spike_factor) {
        std::ostringstream desc, cause, sugg;
        desc << "Latency spike: " << model << " " << current_ms
             << "ms vs baseline " << baseline_ms << "ms";
        cause << "Thermal throttling, resource contention, or backend overload";
        sugg << "Check thermal status, reduce concurrent load, or enable batching";
        event = make_event(AnomalyType::LATENCY_SPIKE,
            desc.str(), cause.str(), sugg.str(), 0.6f);
        events_.push_back(event);
        if (alert_cb_) alert_cb_(event);
    }
    return ErrorCode::OK;
}

std::vector<AnomalyEvent> AnomalyDiagnosis::recent_events() const {
    return events_;
}

void AnomalyDiagnosis::clear_events() { events_.clear(); }

void AnomalyDiagnosis::set_alert_callback(AlertCallback cb) {
    alert_cb_ = std::move(cb);
}

std::string AnomalyDiagnosis::suggest_recovery(const AnomalyEvent& event) {
    switch (event.type) {
        case AnomalyType::INFERENCE_TIMEOUT:
            return "Reduce input resolution or switch to smaller model variant";
        case AnomalyType::OUT_OF_MEMORY:
            return "Unload unused models, enable memory swapping, or reduce batch size";
        case AnomalyType::ACCURACY_DEGRADATION:
            return "Recalibrate quantization parameters or rollback to FP32 model";
        case AnomalyType::LATENCY_SPIKE:
            return "Enable dynamic batching or reduce concurrent inference requests";
        case AnomalyType::BACKEND_FAILURE:
            return "Fallback to CPU backend and restart the failed backend";
        case AnomalyType::THERMAL_THROTTLE:
            return "Reduce inference frequency and enable power saving mode";
        case AnomalyType::DATA_CORRUPTION:
            return "Reload model from verified source and check storage integrity";
        default:
            return "Restart inference engine and reload models";
    }
}

} // namespace profiler
} // namespace qoocore
