/**
 * @file dynamic_batcher.h
 * @brief 动态批处理 — 多传感器源/多 ROI 动态组 batch 推理
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
#include <chrono>

namespace qoocore {

struct BatcherConfig {
    std::uint32_t max_batch_size{8};
    std::uint32_t max_wait_us{5000};        ///< 最大等待时间（微秒）
    bool enable_padding{true};              ///< 是否填充到 max_batch_size
    bool enable_priority{true};             ///< 是否支持优先级
    std::uint32_t num_queues{3};            ///< 优先级队列数
};

struct BatchRequest {
    std::string id;
    Tensor data;
    int priority{0};                        ///< 0=最高优先级
    std::chrono::steady_clock::time_point arrival;
};

struct BatchResult {
    std::string request_id;
    Tensor output;
    double latency_us{0.0};
};

class DynamicBatcher {
public:
    explicit DynamicBatcher(const BatcherConfig& config);
    ~DynamicBatcher();

    using InferFn = std::function<Result<Tensor>(const Tensor& batched_input)>;

    ErrorCode submit(const BatchRequest& request);
    std::vector<BatchResult> flush(InferFn infer_fn);
    std::size_t pending_count() const;
    void clear();

private:
    BatcherConfig config_;
    std::vector<std::vector<BatchRequest>> queues_;
};

} // namespace qoocore
