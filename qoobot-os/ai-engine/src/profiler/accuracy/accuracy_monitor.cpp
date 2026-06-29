/**
 * @file accuracy_monitor.cpp
 * @brief 精度监控实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/profiler/accuracy_monitor.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>

namespace qoocore {
namespace profiler {

AccuracyMonitor::AccuracyMonitor(const AccuracyMonitorConfig& config)
    : config_(config) {}

ErrorCode AccuracyMonitor::compare(
    const Tensor& reference, const Tensor& quantized, AccuracySnapshot& snapshot)
{
    if (reference.shape() != quantized.shape()) {
        return ErrorCode::INVALID_ARGUMENT;
    }

    std::size_t n = 1;
    for (auto d : reference.shape()) n *= d;

    const float* ref = static_cast<const float*>(reference.data());
    const float* qnt = static_cast<const float*>(quantized.data());

    // 基础指标
    double mse = 0.0, mae = 0.0, max_err = 0.0;
    double dot = 0.0, norm_ref = 0.0, norm_qnt = 0.0;

    for (std::size_t i = 0; i < n; ++i) {
        double diff = static_cast<double>(ref[i]) - static_cast<double>(qnt[i]);
        mse += diff * diff;
        mae += std::abs(diff);
        max_err = std::max(max_err, std::abs(diff));
        dot += static_cast<double>(ref[i]) * static_cast<double>(qnt[i]);
        norm_ref += static_cast<double>(ref[i]) * static_cast<double>(ref[i]);
        norm_qnt += static_cast<double>(qnt[i]) * static_cast<double>(qnt[i]);
    }

    snapshot.timestamp = std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    snapshot.mse = static_cast<float>(mse / n);
    snapshot.mae = static_cast<float>(mae / n);
    snapshot.max_error = static_cast<float>(max_err);

    // 余弦相似度
    double denom = std::sqrt(norm_ref) * std::sqrt(norm_qnt);
    snapshot.cosine_similarity = (denom > 1e-10)
        ? static_cast<float>(dot / denom) : 1.0f;

    // 简化 KL 散度（直方图近似）
    const int num_bins = 64;
    std::vector<int> hist_ref(num_bins, 0), hist_qnt(num_bins, 0);
    float min_val = std::numeric_limits<float>::max();
    float max_val = std::numeric_limits<float>::lowest();

    for (std::size_t i = 0; i < n; ++i) {
        min_val = std::min(min_val, std::min(ref[i], qnt[i]));
        max_val = std::max(max_val, std::max(ref[i], qnt[i]));
    }

    float range = max_val - min_val;
    if (range < 1e-10f) range = 1.0f;

    for (std::size_t i = 0; i < n; ++i) {
        int b_ref = std::min(num_bins - 1,
            static_cast<int>((ref[i] - min_val) / range * num_bins));
        int b_qnt = std::min(num_bins - 1,
            static_cast<int>((qnt[i] - min_val) / range * num_bins));
        hist_ref[b_ref]++; hist_qnt[b_qnt]++;
    }

    double kl = 0.0;
    for (int i = 0; i < num_bins; ++i) {
        double p = static_cast<double>(hist_ref[i]) / n + 1e-10;
        double q = static_cast<double>(hist_qnt[i]) / n + 1e-10;
        kl += p * std::log(p / q);
    }
    snapshot.kl_divergence = static_cast<float>(kl);

    // Wasserstein 距离（1D 简化）
    double wass = 0.0;
    double cum_diff = 0.0;
    for (int i = 0; i < num_bins; ++i) {
        cum_diff += (static_cast<double>(hist_ref[i]) - static_cast<double>(hist_qnt[i])) / n;
        wass += std::abs(cum_diff);
    }
    snapshot.wasserstein_distance = static_cast<float>(wass * range / num_bins);

    // 漂移检测
    snapshot.drift_detected = (snapshot.kl_divergence > config_.drift_threshold) ||
                              (snapshot.wasserstein_distance > config_.drift_threshold * 10.0f);

    // 更新历史
    history_.push_back(snapshot);
    while (history_.size() > config_.window_size) history_.pop_front();
    latest_ = snapshot;

    return ErrorCode::OK;
}

bool AccuracyMonitor::is_drift_detected() const { return latest_.drift_detected; }

std::vector<AccuracySnapshot> AccuracyMonitor::history() const {
    return std::vector<AccuracySnapshot>(history_.begin(), history_.end());
}

void AccuracyMonitor::reset() { history_.clear(); }

} // namespace profiler
} // namespace qoocore
