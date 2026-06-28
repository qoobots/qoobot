/**
 * @file power_manager.h
 * @brief 电源管理 — DVFS 调频、功耗模式切换、热降频感知
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include <cstdint>
#include <string>
#include <vector>
#include <functional>

namespace qoocore {
namespace hardware {

enum class PowerMode : std::uint8_t {
    MAX_PERFORMANCE = 0,
    BALANCED        = 1,
    POWER_SAVING    = 2,
    THERMAL_THROTTLE= 3,
    STANDBY         = 4,
};

struct PowerConfig {
    PowerMode default_mode{PowerMode::BALANCED};
    float thermal_throttle_temp_c{85.0f};
    float critical_temp_c{100.0f};
    std::uint32_t poll_interval_ms{1000};
};

struct PowerStats {
    PowerMode current_mode{PowerMode::BALANCED};
    float cpu_temp_c{0.0f};
    float npu_temp_c{0.0f};
    float gpu_temp_c{0.0f};
    float total_power_w{0.0f};
    float cpu_power_w{0.0f};
    float npu_power_w{0.0f};
    float gpu_power_w{0.0f};
    std::uint32_t cpu_freq_mhz{0};
    std::uint32_t npu_freq_mhz{0};
    std::uint32_t gpu_freq_mhz{0};
};

class PowerManager {
public:
    explicit PowerManager(const PowerConfig& config);
    ~PowerManager();

    bool initialize();
    void shutdown();

    ErrorCode set_mode(PowerMode mode);
    PowerMode get_mode() const;
    PowerStats get_stats() const;
    void poll();

    using ThermalCallback = std::function<void(float temp_c)>;
    void set_thermal_callback(ThermalCallback cb);

private:
    PowerConfig config_;
    PowerStats stats_;
    ThermalCallback thermal_cb_;
    bool initialized_{false};
};

} // namespace hardware
} // namespace qoocore
