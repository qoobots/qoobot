/**
 * @file hybrid_inference.h
 * @brief 混合推理 — 端侧轻量模型 + 云端大模型协同，自动切流
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include "qoocore/tensor.h"
#include <cstdint>
#include <string>
#include <functional>

namespace qoocore {
namespace cloud {

enum class InferenceTarget : std::uint8_t {
    LOCAL_ONLY    = 0,
    CLOUD_ONLY    = 1,
    HYBRID_AUTO   = 2,  ///< 自动选择
};

struct HybridConfig {
    InferenceTarget default_target{InferenceTarget::HYBRID_AUTO};
    float cloud_latency_threshold_ms{50.0f};  ///< 超过此延迟切云端
    float confidence_threshold{0.7f};          ///< 低于此置信度切云端
    bool fallback_to_local{true};              ///< 云端不可用时回退本地
    std::string cloud_endpoint;
    std::string api_key;
    std::uint32_t timeout_ms{5000};
};

struct HybridResult {
    Tensor output;
    InferenceTarget used_target{InferenceTarget::LOCAL_ONLY};
    float confidence{0.0f};
    float latency_ms{0.0f};
    bool fallback_occurred{false};
};

class HybridInference {
public:
    explicit HybridInference(const HybridConfig& config);
    ~HybridInference() = default;

    using LocalInferFn = std::function<Result<Tensor>(const Tensor&)>;
    using CloudInferFn = std::function<Result<Tensor>(const Tensor&)>;

    ErrorCode infer(const Tensor& input,
                    LocalInferFn local_fn,
                    CloudInferFn cloud_fn,
                    HybridResult& result);

    ErrorCode infer_with_fallback(const Tensor& input,
                                  LocalInferFn local_fn,
                                  CloudInferFn cloud_fn,
                                  HybridResult& result);

    void set_config(const HybridConfig& config);
    const HybridConfig& config() const { return config_; }

private:
    HybridConfig config_;
};

} // namespace cloud
} // namespace qoocore
