/**
 * @file power_measurement.h
 * @brief 功耗测量 — 单模型/单算子功耗归因、能效比 (TOPS/W)
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include <cstdint>
#include <string>
#include <vector>
#include <unordered_map>

namespace qoocore {
namespace profiler {

struct PowerSample {
    double timestamp{0.0};
    float total_power_w{0.0f};
    float cpu_power_w{0.0f};
    float npu_power_w{0.0f};
    float gpu_power_w{0.0f};
    float memory_power_w{0.0f};
};

struct OperatorPowerProfile {
    std::string op_name;
    float avg_power_mw{0.0f};
    float peak_power_mw{0.0f};
    float energy_mj{0.0f};             ///< 总能耗（毫焦）
    float tops{0.0f};                  ///< 吞吐量（TOPS）
    float efficiency_tops_per_w{0.0f}; ///< 能效比
};

struct ModelPowerProfile {
    std::string model_name;
    float avg_power_w{0.0f};
    float peak_power_w{0.0f};
    float total_energy_j{0.0f};
    float avg_efficiency_tops_per_w{0.0f};
    std::vector<OperatorPowerProfile> operator_profiles;
};

class PowerMeasurement {
public:
    PowerMeasurement() = default;
    ~PowerMeasurement() = default;

    ErrorCode start_session(const std::string& model_name);
    ErrorCode end_session(ModelPowerProfile& profile);

    ErrorCode sample(PowerSample& sample);
    std::vector<PowerSample> history() const;

    static float calculate_efficiency(float tops, float power_w);

private:
    bool active_{false};
    std::string current_model_;
    std::vector<PowerSample> samples_;
};

} // namespace profiler
} // namespace qoocore
