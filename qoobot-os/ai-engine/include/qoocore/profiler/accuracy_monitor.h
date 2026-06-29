/**
 * @file accuracy_monitor.h
 * @brief 精度监控 — 量化前后精度对比、输出分布漂移检测
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include "qoocore/tensor.h"
#include <cstdint>
#include <string>
#include <vector>
#include <deque>

namespace qoocore {
namespace profiler {

struct AccuracyMonitorConfig {
    float drift_threshold{0.05f};       ///< 分布漂移告警阈值
    std::uint32_t window_size{100};     ///< 滑动窗口大小
    bool track_quantization_error{true};
    bool track_distribution_shift{true};
    bool track_output_anomaly{true};
};

struct AccuracySnapshot {
    double timestamp{0.0};
    float mse{0.0f};                    ///< 均方误差
    float mae{0.0f};                    ///< 平均绝对误差
    float max_error{0.0f};              ///< 最大误差
    float cosine_similarity{1.0f};      ///< 余弦相似度
    float kl_divergence{0.0f};          ///< KL 散度
    float wasserstein_distance{0.0f};   ///< Wasserstein 距离
    bool drift_detected{false};
};

class AccuracyMonitor {
public:
    explicit AccuracyMonitor(const AccuracyMonitorConfig& config);
    ~AccuracyMonitor() = default;

    ErrorCode compare(const Tensor& reference, const Tensor& quantized,
                      AccuracySnapshot& snapshot);

    bool is_drift_detected() const;
    std::vector<AccuracySnapshot> history() const;
    void reset();

private:
    AccuracyMonitorConfig config_;
    std::deque<AccuracySnapshot> history_;
    AccuracySnapshot latest_;
};

} // namespace profiler
} // namespace qoocore
