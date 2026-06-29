/**
 * @file hybrid_inference.cpp
 * @brief 混合推理实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/cloud/hybrid_inference.h"
#include <chrono>

namespace qoocore {
namespace cloud {

HybridInference::HybridInference(const HybridConfig& config)
    : config_(config) {}

ErrorCode HybridInference::infer(
    const Tensor& input,
    LocalInferFn local_fn,
    CloudInferFn cloud_fn,
    HybridResult& result)
{
    if (!local_fn) return ErrorCode::INVALID_ARGUMENT;

    auto start = std::chrono::steady_clock::now();

    switch (config_.default_target) {
        case InferenceTarget::LOCAL_ONLY: {
            auto local_result = local_fn(input);
            auto end = std::chrono::steady_clock::now();

            if (!local_result.ok()) return ErrorCode::INFER_FAILED;

            result.output = std::move(local_result.value());
            result.used_target = InferenceTarget::LOCAL_ONLY;
            result.latency_ms = std::chrono::duration<float, std::milli>(end - start).count();
            result.confidence = 1.0f;
            return ErrorCode::OK;
        }

        case InferenceTarget::CLOUD_ONLY: {
            if (!cloud_fn) return ErrorCode::BACKEND_UNAVAILABLE;

            auto cloud_result = cloud_fn(input);
            auto end = std::chrono::steady_clock::now();

            if (cloud_result.ok()) {
                result.output = std::move(cloud_result.value());
                result.used_target = InferenceTarget::CLOUD_ONLY;
                result.latency_ms = std::chrono::duration<float, std::milli>(end - start).count();
                result.confidence = 1.0f;
                return ErrorCode::OK;
            }

            // 回退到本地
            if (config_.fallback_to_local) {
                auto local_result = local_fn(input);
                if (!local_result.ok()) return ErrorCode::INFER_FAILED;
                result.output = std::move(local_result.value());
                result.used_target = InferenceTarget::LOCAL_ONLY;
                result.fallback_occurred = true;
                result.latency_ms = std::chrono::duration<float, std::milli>(
                    std::chrono::steady_clock::now() - start).count();
                return ErrorCode::OK;
            }
            return ErrorCode::BACKEND_UNAVAILABLE;
        }

        case InferenceTarget::HYBRID_AUTO: {
            // 策略：先本地推理，评估置信度，必要时切云端
            auto local_result = local_fn(input);
            auto local_end = std::chrono::steady_clock::now();
            float local_latency = std::chrono::duration<float, std::milli>(
                local_end - start).count();

            if (!local_result.ok()) {
                // 本地失败，尝试云端
                if (cloud_fn) {
                    auto cloud_result = cloud_fn(input);
                    if (cloud_result.ok()) {
                        result.output = std::move(cloud_result.value());
                        result.used_target = InferenceTarget::CLOUD_ONLY;
                        result.latency_ms = std::chrono::duration<float, std::milli>(
                            std::chrono::steady_clock::now() - start).count();
                        result.confidence = 1.0f;
                        return ErrorCode::OK;
                    }
                }
                return ErrorCode::INFER_FAILED;
            }

            // 评估是否需要切云端
            bool needs_cloud = (local_latency > config_.cloud_latency_threshold_ms);

            if (needs_cloud && cloud_fn) {
                auto cloud_result = cloud_fn(input);
                if (cloud_result.ok()) {
                    result.output = std::move(cloud_result.value());
                    result.used_target = InferenceTarget::CLOUD_ONLY;
                    result.confidence = 1.0f;
                } else {
                    result.output = std::move(local_result.value());
                    result.used_target = InferenceTarget::LOCAL_ONLY;
                    result.confidence = 0.8f;
                    result.fallback_occurred = true;
                }
            } else {
                result.output = std::move(local_result.value());
                result.used_target = InferenceTarget::LOCAL_ONLY;
                result.confidence = 0.9f;
            }

            result.latency_ms = std::chrono::duration<float, std::milli>(
                std::chrono::steady_clock::now() - start).count();
            return ErrorCode::OK;
        }

        default:
            return ErrorCode::INVALID_ARGUMENT;
    }
}

ErrorCode HybridInference::infer_with_fallback(
    const Tensor& input,
    LocalInferFn local_fn,
    CloudInferFn cloud_fn,
    HybridResult& result)
{
    // 确保无论如何都有结果
    auto saved_target = config_.default_target;
    config_.default_target = InferenceTarget::HYBRID_AUTO;
    config_.fallback_to_local = true;

    auto ec = infer(input, local_fn, cloud_fn, result);

    config_.default_target = saved_target;
    return ec;
}

void HybridInference::set_config(const HybridConfig& config) {
    config_ = config;
}

} // namespace cloud
} // namespace qoocore
