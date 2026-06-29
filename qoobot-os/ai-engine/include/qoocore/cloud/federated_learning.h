/**
 * @file federated_learning.h
 * @brief 联邦学习 — 端侧梯度上传、差分隐私、安全聚合
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include "qoocore/tensor.h"
#include <cstdint>
#include <string>
#include <vector>
#include <functional>

namespace qoocore {
namespace cloud {

struct FederatedConfig {
    std::uint32_t num_rounds{100};
    std::uint32_t clients_per_round{10};
    float dp_epsilon{8.0f};            ///< 差分隐私 ε
    float dp_delta{1e-5f};             ///< 差分隐私 δ
    float clipping_norm{1.0f};         ///< 梯度裁剪范数
    std::string aggregation_method{"fedavg"}; ///< FedAvg / FedProx / SCAFFOLD
    float server_learning_rate{1.0f};
    bool secure_aggregation{true};
};

struct ClientUpdate {
    std::string client_id;
    std::vector<float> gradients;
    std::size_t num_samples{0};
    float local_loss{0.0f};
};

struct FederatedRound {
    std::uint32_t round{0};
    std::vector<float> global_weights;
    float global_loss{0.0f};
    float dp_noise_scale{0.0f};
    std::vector<ClientUpdate> client_updates;
};

class FederatedLearning {
public:
    explicit FederatedLearning(const FederatedConfig& config);
    ~FederatedLearning() = default;

    ErrorCode initialize(const std::vector<float>& initial_weights);
    ErrorCode submit_client_update(const ClientUpdate& update);
    ErrorCode aggregate_round(FederatedRound& round);

    ErrorCode add_differential_privacy(std::vector<float>& gradients,
                                       float& noise_scale);

    std::vector<float> global_weights() const;
    std::uint32_t current_round() const { return round_; }
    std::vector<FederatedRound> history() const { return history_; }

private:
    FederatedConfig config_;
    std::vector<float> global_weights_;
    std::uint32_t round_{0};
    std::vector<ClientUpdate> pending_updates_;
    std::vector<FederatedRound> history_;
    bool initialized_{false};
};

} // namespace cloud
} // namespace qoocore
