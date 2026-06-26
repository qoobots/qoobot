/**
 * @file engine.cpp
 * @brief InferenceEngine 统一推理引擎实现
 *
 * 本文件实现 InferenceEngine 的核心逻辑。
 * 使用 Pimpl 模式隔离实现，减少头文件依赖。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/engine.h"
#include "qoocore/backend.h"
#include "qoocore/hardware/hardware_probe.h"
#include <spdlog/spdlog.h>
#include <mutex>
#include <unordered_map>
#include <memory>
#include <fstream>

namespace qoocore {

// ────────────────────────────────────────────────────────────────────────────
//  InferenceEngine::Impl — Pimpl 实现
// ────────────────────────────────────────────────────────────────────────────
struct InferenceEngine::Impl {
    EngineConfig  config;
    bool          initialized{false};

    // 已加载模型表：ModelHandle → {npu_handle, backend_type, info}
    struct LoadedModel {
        std::uint64_t  npu_handle{0};
        BackendType   backend;
        ModelInfo     info;
    };
    std::unordered_map<ModelHandle, LoadedModel> models;
    std::mutex models_mutex;

    // 后端表
    std::unordered_map<BackendType, BackendPtr> backends;
    std::mutex backends_mutex;

    // 下一个模型句柄
    std::uint64_t next_handle{1};
};

// ────────────────────────────────────────────────────────────────────────────
//  单例
// ────────────────────────────────────────────────────────────────────────────
InferenceEngine& InferenceEngine::instance() {
    static InferenceEngine inst;
    return inst;
}

InferenceEngine::~InferenceEngine() {
    if (impl_ && impl_->initialized) {
        shutdown();
    }
}

// ────────────────────────────────────────────────────────────────────────────
//  引擎初始化
// ────────────────────────────────────────────────────────────────────────────
Result<void> InferenceEngine::init(const EngineConfig& config) {
    if (impl_ && impl_->initialized) {
        spdlog::warn("InferenceEngine already initialized");
        return Ok();
    }

    impl_ = std::make_unique<Impl>();
    impl_->config = config;

    spdlog::info("QooCore InferenceEngine v{} initializing...",
                  QOOCORE_VERSION_STRING);

    // 探测硬件能力
    hardware::HardwareProfile hw_profile;
    hardware::HardwareProber::probe(hw_profile);
    spdlog::info("Probed {} NPU(s), {} GPU(s), {} MB memory",
                  hw_profile.npu_candidates.size(),
                  hw_profile.gpu_candidates.size(),
                  hw_profile.total_memory_mb);

    // TODO: 根据硬件能力自动注册后端
    // 示例：若探测到 Qualcomm NPU，注册 QNN 后端
    // if (!hw_profile.npu_candidates.empty()) {
    //     auto hal = NpuHalLoader::load_best_hal(hw_profile);
    //     if (hal) register_backend(...);
    // }

    impl_->initialized = true;
    spdlog::info("InferenceEngine initialized successfully");
    return Ok();
}

void InferenceEngine::shutdown() {
    if (!impl_) return;

    spdlog::info("Shutting down InferenceEngine...");
    unload_all_models();

    // 释放后端
    std::lock_guard<std::mutex> lock(impl_->backends_mutex);
    for (auto& [type, backend] : impl_->backends) {
        backend->deinit();
    }
    impl_->backends.clear();

    impl_->initialized = false;
    spdlog::info("InferenceEngine shutdown complete");
}

bool InferenceEngine::is_initialized() const noexcept {
    return impl_ && impl_->initialized;
}

const EngineConfig& InferenceEngine::config() const noexcept {
    static EngineConfig default_config;
    return impl_ ? impl_->config : default_config;
}

// ────────────────────────────────────────────────────────────────────────────
//  模型管理
// ────────────────────────────────────────────────────────────────────────────
Result<ModelHandle> InferenceEngine::load_model(
    const std::string& qoomodel_path,
    const ModelConfig& model_config) {
    if (!impl_ || !impl_->initialized) {
        return Error<ModelHandle>(ErrorCode::ENGINE_NOT_INIT,
                                   "Engine not initialized");
    }

    // 读取 .qoomodel 文件头
    std::ifstream ifs(qoomodel_path, std::ios::binary);
    if (!ifs) {
        return Error<ModelHandle>(ErrorCode::FILE_NOT_FOUND,
                                   "Model file not found: " + qoomodel_path);
    }

    // TODO: 解析 .qoomodel header，选择合适的后端
    spdlog::info("Loading model: {}", qoomodel_path);

    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    ModelHandle handle = impl_->next_handle++;

    Impl::LoadedModel model;
    model.backend = BackendType::AUTO;  // TODO: 根据模型元数据选择
    model.info.name = qoomodel_path;  // TODO: 从文件读取
    model.info.version = "0.1.0";
    impl_->models[handle] = std::move(model);

    spdlog::info("Model loaded, handle={}", handle);
    return Ok(handle);
}

Result<void> InferenceEngine::unload_model(ModelHandle handle) {
    if (!impl_) {
        return Error<void>(ErrorCode::ENGINE_NOT_INIT, "Engine not initialized");
    }

    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    auto it = impl_->models.find(handle);
    if (it == impl_->models.end()) {
        return Error<void>(ErrorCode::MODEL_NOT_LOADED,
                             "Model handle " + std::to_string(handle) + " not found");
    }

    // TODO: 从后端卸载模型
    impl_->models.erase(it);
    spdlog::info("Model unloaded, handle={}", handle);
    return Ok();
}

void InferenceEngine::unload_all_models() {
    if (!impl_) return;
    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    for (auto& [handle, model] : impl_->models) {
        (void)handle; (void)model;
        // TODO: backend->unload_model(model.npu_handle);
    }
    impl_->models.clear();
    spdlog::info("All models unloaded");
}

Result<ModelInfo> InferenceEngine::get_model_info(ModelHandle handle) const {
    if (!impl_) {
        return Error<ModelInfo>(ErrorCode::ENGINE_NOT_INIT, "Engine not initialized");
    }

    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    auto it = impl_->models.find(handle);
    if (it == impl_->models.end()) {
        return Error<ModelInfo>(ErrorCode::MODEL_NOT_LOADED,
                                   "Model handle not found");
    }
    return Ok(it->second.info);
}

std::vector<ModelHandle> InferenceEngine::list_loaded_models() const {
    if (!impl_) return {};
    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    std::vector<ModelHandle> result;
    for (const auto& [handle, _] : impl_->models) {
        result.push_back(handle);
    }
    return result;
}

// ────────────────────────────────────────────────────────────────────────────
//  推理
// ────────────────────────────────────────────────────────────────────────────
Result<Tensor> InferenceEngine::infer(ModelHandle handle,
                                        const Tensor& input) {
    if (!impl_ || !impl_->initialized) {
        return Error<Tensor>(ErrorCode::ENGINE_NOT_INIT, "Engine not initialized");
    }

    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    auto it = impl_->models.find(handle);
    if (it == impl_->models.end()) {
        return Error<Tensor>(ErrorCode::MODEL_NOT_LOADED, "Model not loaded");
    }

    // TODO: 选择后端，执行推理
    spdlog::info("Infer: handle={}, input={}x{}",
                  handle, input.shape()[0], input.shape()[1]);

    // 当前返回 dummy 输出
    auto output = Tensor::create({1, 1000}, DType::FLOAT32);
    if (!output.ok()) {
        return Error<Tensor>(ErrorCode::MEMORY_ERROR, "Failed to create output tensor");
    }
    return Ok(std::move(*output));
}

Result<std::vector<Tensor>> InferenceEngine::infer_multi_input(
    ModelHandle handle,
    const std::vector<Tensor>& inputs) {
    (void)handle; (void)inputs;
    return Error<std::vector<Tensor>>(ErrorCode::NOT_IMPLEMENTED,
                                        "infer_multi_input() not yet implemented");
}

std::future<Result<Tensor>> InferenceEngine::infer_async(
    ModelHandle handle,
    const Tensor& input) {
    // 按值捕获 input，避免异步执行时引用失效
    return std::async(std::launch::async,
                      [this, handle, input]() { return infer(handle, input); });
}

// ────────────────────────────────────────────────────────────────────────────
//  后端管理
// ────────────────────────────────────────────────────────────────────────────
Result<void> InferenceEngine::register_backend(BackendPtr backend) {
    if (!backend) {
        return Error<void>(ErrorCode::INVALID_ARGUMENT, "Null backend");
    }
    if (!impl_) {
        return Error<void>(ErrorCode::ENGINE_NOT_INIT, "Engine not initialized");
    }

    std::lock_guard<std::mutex> lock(impl_->backends_mutex);
    impl_->backends[backend->type()] = backend;

    auto cfg = backend->capabilities();
    spdlog::info("Registered backend: {} ({})",
                  backend->name(), backend_to_string(cfg.type));
    return Ok();
}

std::vector<BackendType> InferenceEngine::list_available_backends() const {
    if (!impl_) return {};
    std::lock_guard<std::mutex> lock(impl_->backends_mutex);
    std::vector<BackendType> result;
    for (const auto& [type, _] : impl_->backends) {
        result.push_back(type);
    }
    return result;
}

Result<BackendPtr> InferenceEngine::get_backend(BackendType type) const {
    if (!impl_) {
        return Error<BackendPtr>(ErrorCode::ENGINE_NOT_INIT, "Engine not initialized");
    }
    std::lock_guard<std::mutex> lock(impl_->backends_mutex);
    auto it = impl_->backends.find(type);
    if (it == impl_->backends.end()) {
        return Error<BackendPtr>(ErrorCode::BACKEND_UNAVAILABLE,
                                    std::string("Backend ") +
                                    backend_to_string(type) + " not available");
    }
    return Ok(it->second);
}

// ────────────────────────────────────────────────────────────────────────────
//  诊断
// ────────────────────────────────────────────────────────────────────────────
std::string InferenceEngine::status_json() const {
    if (!impl_) {
        return R"({"status": "not_initialized"})";
    }
    return R"({"status": "ok", "version": ")" + std::string(QOOCORE_VERSION_STRING) + R"(", "loaded_models": )" +
           std::to_string(impl_->models.size()) + R"(})";
}

}  // namespace qoocore
