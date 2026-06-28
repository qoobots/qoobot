/**
 * @file dynamic_batcher.cpp
 * @brief 动态批处理实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/dynamic_batcher.h"
#include <algorithm>
#include <cstring>

namespace qoocore {

DynamicBatcher::DynamicBatcher(const BatcherConfig& config)
    : config_(config)
    , queues_(config.num_queues) {}

DynamicBatcher::~DynamicBatcher() { clear(); }

ErrorCode DynamicBatcher::submit(const BatchRequest& request) {
    int q = std::min(std::max(request.priority, 0),
                     static_cast<int>(config_.num_queues) - 1);
    queues_[q].push_back(request);
    return ErrorCode::OK;
}

std::vector<BatchResult> DynamicBatcher::flush(InferFn infer_fn) {
    std::vector<BatchResult> results;

    if (!infer_fn) return results;

    auto now = std::chrono::steady_clock::now();

    for (int q = 0; q < static_cast<int>(queues_.size()); ++q) {
        auto& queue = queues_[q];

        while (!queue.empty()) {
            // 收集一批请求
            std::vector<BatchRequest> batch;
            std::uint32_t count = 0;

            while (!queue.empty() && count < config_.max_batch_size) {
                auto& req = queue.front();
                auto wait_us = std::chrono::duration_cast<std::chrono::microseconds>(
                    now - req.arrival).count();

                if (wait_us >= config_.max_wait_us || count == 0) {
                    batch.push_back(std::move(req));
                    queue.erase(queue.begin());
                    count++;
                } else {
                    break;  // 等待更多请求
                }
            }

            if (batch.empty()) break;

            // 构建批处理输入（沿 batch 维度拼接）
            const auto& f0_shape = batch[0].data.shape();
            std::vector<std::size_t> batched_shape = {batch.size()};
            batched_shape.insert(batched_shape.end(), f0_shape.begin(), f0_shape.end());

            auto batched = Tensor::create(batched_shape, batch[0].data.dtype());
            if (!batched.ok()) continue;

            auto& batched_tensor = batched.value();
            float* dst = static_cast<float*>(batched_tensor.data());
            std::size_t per_item = 1;
            for (auto d : f0_shape) per_item *= d;

            for (std::size_t i = 0; i < batch.size(); ++i) {
                const float* src = static_cast<const float*>(batch[i].data.data());
                std::memcpy(dst + i * per_item, src, per_item * sizeof(float));
            }

            // 执行推理
            auto infer_start = std::chrono::steady_clock::now();
            auto infer_result = infer_fn(batched_tensor);
            auto infer_end = std::chrono::steady_clock::now();
            double batch_latency = std::chrono::duration<double, std::micro>(
                infer_end - infer_start).count();

            // 拆分结果
            if (infer_result.ok()) {
                const auto& out_shape = infer_result.value().shape();
                std::size_t out_per_item = 1;
                for (std::size_t i = 1; i < out_shape.size(); ++i) out_per_item *= out_shape[i];

                const float* out_data = static_cast<const float*>(infer_result.value().data());

                for (std::size_t i = 0; i < batch.size(); ++i) {
                    std::vector<std::size_t> item_shape(out_shape.begin() + 1, out_shape.end());
                    auto item_tensor = Tensor::create(item_shape, infer_result.value().dtype());
                    if (item_tensor.ok()) {
                        float* item_data = static_cast<float*>(item_tensor.value().data());
                        std::memcpy(item_data, out_data + i * out_per_item,
                                    out_per_item * sizeof(float));

                        BatchResult result;
                        result.request_id = batch[i].id;
                        result.output = std::move(item_tensor.value());
                        result.latency_us = batch_latency / static_cast<double>(batch.size());
                        results.push_back(std::move(result));
                    }
                }
            }
        }
    }

    return results;
}

std::size_t DynamicBatcher::pending_count() const {
    std::size_t count = 0;
    for (const auto& q : queues_) count += q.size();
    return count;
}

void DynamicBatcher::clear() {
    for (auto& q : queues_) q.clear();
}

} // namespace qoocore
