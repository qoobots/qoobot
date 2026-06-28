/**
 * @file federated_learning.cpp
 * @brief 联邦学习实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/cloud/federated_learning.h"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <random>

namespace qoocore {
namespace cloud {

FederatedLearning::FederatedLearning(const FederatedConfig& config)
    : config_(config) {}

ErrorCode FederatedLearning::initialize(const std::vector<float>& initial_weights) {
    global_weights_ = initial_weights;
    round_ = 0;
    initialized_ = true;
    return ErrorCode::OK;
}

ErrorCode FederatedLearning::submit_client_update(const ClientUpdate& update) {
    if (!initialized_) return ErrorCode::ENGINE_NOT_INIT;
    pending_updates_.push_back(update);
    return ErrorCode::OK;
}

ErrorCode FederatedLearning::aggregate_round(FederatedRound& round) {
    if (!initialized_) return ErrorCode::ENGINE_NOT_INIT;
    if (pending_updates_.empty()) return ErrorCode::INVALID_ARGUMENT;
    if (global_weights_.empty()) return ErrorCode::MODEL_NOT_LOADED;

    round.round = ++round_;
    round.global_weights = global_weights_;
    round.client_updates = std::move(pending_updates_);
    pending_updates_.clear();

    // FedAvg 聚合
    if (config_.aggregation_method == "fedavg") {
        std::size_t total_samples = 0;
        for (const auto& cu : round.client_updates) {
            total_samples += cu.num_samples;
        }

        if (total_samples == 0) {
            for (const auto& cu : round.client_updates) {
                total_samples++;
            }
        }

        // 加权平均
        for (std::size_t i = 0; i < global_weights_.size(); ++i) {
            float sum = 0.0f;
            for (const auto& cu : round.client_updates) {
                if (i < cu.gradients.size()) {
                    float weight = static_cast<float>(cu.num_samples) /
                                   static_cast<float>(total_samples);
                    sum += weight * cu.gradients[i];
                }
            }
            // 梯度下降更新
            global_weights_[i] -= config_.server_learning_rate * sum;
        }

        // 差分隐私
        float noise_scale = 0.0f;
        add_differential_privacy(global_weights_, noise_scale);
        round.dp_noise_scale = noise_scale;
    }

    round.global_weights = global_weights_;

    // 计算全局损失
    float total_loss = 0.0f;
    for (const auto& cu : round.client_updates) {
        total_loss += cu.local_loss;
    }
    round.global_loss = round.client_updates.empty() ? 0.0f :
        total_loss / static_cast<float>(round.client_updates.size());

    history_.push_back(round);
    return ErrorCode::OK;
}

ErrorCode FederatedLearning::add_differential_privacy(
    std::vector<float>& gradients, float& noise_scale)
{
    if (config_.dp_epsilon <= 0.0f) {
        noise_scale = 0.0f;
        return ErrorCode::OK;
    }

    // 梯度裁剪
    float norm = 0.0f;
    for (float g : gradients) norm += g * g;
    norm = std::sqrt(norm);

    if (norm > config_.clipping_norm && norm > 1e-10f) {
        float scale = config_.clipping_norm / norm;
        for (auto& g : gradients) g *= scale;
    }

    // 添加高斯噪声（满足 (ε, δ)-DP）
    // 噪声标准差 σ = Δf * sqrt(2*log(1.25/δ)) / ε
    float sigma = config_.clipping_norm *
                  std::sqrt(2.0f * std::log(1.25f / config_.dp_delta)) /
                  config_.dp_epsilon;

    noise_scale = sigma;

    static std::mt19937 rng(std::random_device{}());
    std::normal_distribution<float> noise(0.0f, sigma);

    for (auto& g : gradients) {
        g += noise(rng);
    }

    return ErrorCode::OK;
}

std::vector<float> FederatedLearning::global_weights() const {
    return global_weights_;
}

} // namespace cloud
} // namespace qoocore
