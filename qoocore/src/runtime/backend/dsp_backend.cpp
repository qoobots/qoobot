/**
 * @file dsp_backend.cpp
 * @brief DSP 推理后端实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/dsp_backend.h"
#include <cstring>

namespace qoocore {

DSPBackend::DSPBackend(const DSPConfig& config) : config_(config) {}
DSPBackend::~DSPBackend() { shutdown(); }

bool DSPBackend::initialize() {
    if (initialized_) return true;

    // 模拟 DSP 库加载
    if (!config_.lib_path.empty()) {
        // 实际环境中通过 FastRPC 或 dlopen 加载 DSP 共享库
    }

    initialized_ = true;
    return true;
}

void DSPBackend::shutdown() { initialized_ = false; }

std::string DSPBackend::name() const {
    switch (config_.vendor) {
        case DSPVendor::QUALCOMM_HEXAGON: return "Qualcomm Hexagon DSP";
        case DSPVendor::CEVA_TELEK_LITE:  return "CEVA TeakLite DSP";
        case DSPVendor::CADENCE_TENSILICA:return "Cadence Tensilica DSP";
        default:                           return "Generic DSP";
    }
}

std::string DSPBackend::version() const { return "0.1.0"; }

BackendCapabilities DSPBackend::capabilities() const {
    BackendCapabilities caps;
    caps.max_model_size_mb = 128;
    caps.max_batch_size = 1;
    caps.supported_dtypes = {DType::FLOAT32, DType::FLOAT16, DType::QINT8};
    caps.supports_async = true;
    caps.supports_batching = false;
    caps.supports_multi_model = true;
    caps.has_unified_memory = true;
    return caps;
}

bool DSPBackend::supports_dtype(DType dtype) const {
    return dtype == DType::FLOAT32 || dtype == DType::FLOAT16 || dtype == DType::QINT8;
}

ErrorCode DSPBackend::load_model(const ModelConfig& config) {
    (void)config;
    return ErrorCode::OK;
}

ErrorCode DSPBackend::unload_model(ModelHandle handle) {
    (void)handle;
    return ErrorCode::OK;
}

Result<Tensor> DSPBackend::infer(ModelHandle handle, const Tensor& input) {
    (void)handle;
    // 模拟推理：返回输入拷贝
    return input;
}

Result<std::vector<Tensor>> DSPBackend::infer_batch(
    ModelHandle handle, const std::vector<Tensor>& inputs)
{
    (void)handle;
    return inputs;
}

ErrorCode DSPBackend::synchronize() { return ErrorCode::OK; }

ErrorCode DSPBackend::get_memory_usage(std::size_t& used, std::size_t& total) const {
    used = 0;
    total = config_.l2_cache_kb * 1024;
    return ErrorCode::OK;
}

} // namespace qoocore
