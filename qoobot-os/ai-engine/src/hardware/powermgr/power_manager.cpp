/**
 * @file power_manager.cpp
 * @brief 电源管理实现 — DVFS 调频、功耗模式切换、热降频感知
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/hardware/power_manager.h"
#include <algorithm>
#include <cmath>
#include <thread>
#include <chrono>

namespace qoocore {
namespace hardware {

namespace {
float simulate_temp(float base, float power) {
    return base + power * 0.5f + std::sin(
        static_cast<float>(std::chrono::steady_clock::now().time_since_epoch().count()) * 1e-9f) * 2.0f;
}
} // anonymous

PowerManager::PowerManager(const PowerConfig& config) : config_(config) {}
PowerManager::~PowerManager() { shutdown(); }

bool PowerManager::initialize() {
    if (initialized_) return true;
    stats_.current_mode = config_.default_mode;
    initialized_ = true;
    return true;
}

void PowerManager::shutdown() { initialized_ = false; }

ErrorCode PowerManager::set_mode(PowerMode mode) {
    if (!initialized_) return ErrorCode::ENGINE_NOT_INIT;
    stats_.current_mode = mode;

    switch (mode) {
        case PowerMode::MAX_PERFORMANCE:
            stats_.cpu_freq_mhz = 2400; stats_.npu_freq_mhz = 1000; stats_.gpu_freq_mhz = 900;
            break;
        case PowerMode::BALANCED:
            stats_.cpu_freq_mhz = 1800; stats_.npu_freq_mhz = 700; stats_.gpu_freq_mhz = 600;
            break;
        case PowerMode::POWER_SAVING:
            stats_.cpu_freq_mhz = 1000; stats_.npu_freq_mhz = 400; stats_.gpu_freq_mhz = 300;
            break;
        case PowerMode::THERMAL_THROTTLE:
            stats_.cpu_freq_mhz = 800; stats_.npu_freq_mhz = 300; stats_.gpu_freq_mhz = 200;
            break;
        case PowerMode::STANDBY:
            stats_.cpu_freq_mhz = 400; stats_.npu_freq_mhz = 0; stats_.gpu_freq_mhz = 0;
            break;
    }
    return ErrorCode::OK;
}

PowerMode PowerManager::get_mode() const { return stats_.current_mode; }

PowerStats PowerManager::get_stats() const { return stats_; }

void PowerManager::poll() {
    if (!initialized_) return;

    // 估算功耗
    float cpu_util = stats_.cpu_freq_mhz / 2400.0f;
    float npu_util = stats_.npu_freq_mhz / 1000.0f;
    float gpu_util = stats_.gpu_freq_mhz / 900.0f;

    stats_.cpu_power_w = 2.0f + cpu_util * 8.0f;
    stats_.npu_power_w = npu_util * 5.0f;
    stats_.gpu_power_w = gpu_util * 3.0f;
    stats_.total_power_w = stats_.cpu_power_w + stats_.npu_power_w + stats_.gpu_power_w;

    // 温度模拟
    stats_.cpu_temp_c = simulate_temp(45.0f, stats_.cpu_power_w);
    stats_.npu_temp_c = simulate_temp(50.0f, stats_.npu_power_w);
    stats_.gpu_temp_c = simulate_temp(48.0f, stats_.gpu_power_w);

    // 热降频检查
    float max_temp = std::max({stats_.cpu_temp_c, stats_.npu_temp_c, stats_.gpu_temp_c});

    if (max_temp >= config_.critical_temp_c) {
        set_mode(PowerMode::STANDBY);
        if (thermal_cb_) thermal_cb_(max_temp);
    } else if (max_temp >= config_.thermal_throttle_temp_c &&
               stats_.current_mode != PowerMode::THERMAL_THROTTLE &&
               stats_.current_mode != PowerMode::STANDBY) {
        set_mode(PowerMode::THERMAL_THROTTLE);
        if (thermal_cb_) thermal_cb_(max_temp);
    } else if (max_temp < config_.thermal_throttle_temp_c - 10.0f &&
               stats_.current_mode == PowerMode::THERMAL_THROTTLE) {
        set_mode(config_.default_mode);
    }
}

void PowerManager::set_thermal_callback(ThermalCallback cb) { thermal_cb_ = std::move(cb); }

} // namespace hardware
} // namespace qoocore
