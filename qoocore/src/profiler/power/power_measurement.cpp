/**
 * @file power_measurement.cpp
 * @brief 功耗测量实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/profiler/power_measurement.h"
#include <algorithm>
#include <chrono>
#include <cmath>

namespace qoocore {
namespace profiler {

namespace {
double now_sec() {
    return std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
} // anonymous

ErrorCode PowerMeasurement::start_session(const std::string& model_name) {
    if (active_) return ErrorCode::DEVICE_BUSY;
    active_ = true;
    current_model_ = model_name;
    samples_.clear();

    // 初始采样
    PowerSample init;
    init.timestamp = now_sec();
    init.total_power_w = 5.0f;
    init.cpu_power_w = 2.0f;
    init.npu_power_w = 1.5f;
    init.gpu_power_w = 1.0f;
    init.memory_power_w = 0.5f;
    samples_.push_back(init);

    return ErrorCode::OK;
}

ErrorCode PowerMeasurement::end_session(ModelPowerProfile& profile) {
    if (!active_) return ErrorCode::ENGINE_NOT_INIT;
    active_ = false;

    profile.model_name = current_model_;

    if (samples_.empty()) {
        profile.avg_power_w = 0.0f;
        profile.peak_power_w = 0.0f;
        profile.total_energy_j = 0.0f;
        return ErrorCode::OK;
    }

    // 计算统计数据
    float sum_power = 0.0f, max_power = 0.0f, total_energy = 0.0f;

    for (std::size_t i = 0; i < samples_.size(); ++i) {
        sum_power += samples_[i].total_power_w;
        max_power = std::max(max_power, samples_[i].total_power_w);

        if (i > 0) {
            double dt = samples_[i].timestamp - samples_[i-1].timestamp;
            float avg_p = (samples_[i].total_power_w + samples_[i-1].total_power_w) * 0.5f;
            total_energy += avg_p * static_cast<float>(dt);
        }
    }

    profile.avg_power_w = sum_power / static_cast<float>(samples_.size());
    profile.peak_power_w = max_power;
    profile.total_energy_j = total_energy;
    profile.avg_efficiency_tops_per_w = calculate_efficiency(1.0f, profile.avg_power_w);

    return ErrorCode::OK;
}

ErrorCode PowerMeasurement::sample(PowerSample& sample) {
    sample.timestamp = now_sec();

    // 模拟功耗数据
    float base = 5.0f;
    sample.total_power_w = base + std::sin(sample.timestamp * 0.5f) * 1.0f;
    sample.cpu_power_w = sample.total_power_w * 0.4f;
    sample.npu_power_w = sample.total_power_w * 0.3f;
    sample.gpu_power_w = sample.total_power_w * 0.2f;
    sample.memory_power_w = sample.total_power_w * 0.1f;

    if (active_) samples_.push_back(sample);

    return ErrorCode::OK;
}

std::vector<PowerSample> PowerMeasurement::history() const { return samples_; }

float PowerMeasurement::calculate_efficiency(float tops, float power_w) {
    return (power_w > 0.0f) ? tops / power_w : 0.0f;
}

} // namespace profiler
} // namespace qoocore
