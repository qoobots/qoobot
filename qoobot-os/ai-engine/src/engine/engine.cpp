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
#include <algorithm>
#include <chrono>
#include <cstring>
#include <fstream>
#include <memory>
#include <mutex>
#include <sstream>
#include <unordered_map>
#include <vector>

namespace qoocore {

// ────────────────────────────────────────────────────────────────────────────
//  InferenceEngine::Impl — Pimpl 实现
// ────────────────────────────────────────────────────────────────────────────
struct InferenceEngine::Impl {
    EngineConfig  config;
    bool          initialized{false};

    // 已加载模型表：ModelHandle → {backend_model_handle, backend_ptr, info, model_data}
    struct LoadedModel {
        std::uint64_t  backend_model_handle{0};  // 后端内部句柄
        BackendPtr     backend;                   // 后端指针
        BackendType    backend_type;
        ModelInfo      info;
        std::vector<std::uint8_t> compiled_data;  // 编译后的模型数据
        ModelConfig    model_config;
    };
    std::unordered_map<ModelHandle, LoadedModel> models;
    std::mutex models_mutex;

    // 后端表
    std::unordered_map<BackendType, BackendPtr> backends;
    std::mutex backends_mutex;

    // 下一个模型句柄
    std::uint64_t next_handle{1};

    // 性能统计
    struct PerfStats {
        std::size_t total_inferences{0};
        double total_infer_time_ms{0.0};
        double min_infer_time_ms{std::numeric_limits<double>::max()};
        double max_infer_time_ms{0.0};
    };
    PerfStats perf;
    mutable std::mutex perf_mutex;
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
    auto probe_result = hardware::HardwareProber::probe();
    if (probe_result.ok()) {
        const auto& hw_profile = probe_result.value();
        spdlog::info("Probed {} NPU(s), {} GPU(s), {} bytes memory",
                      hw_profile.npu_candidates.size(),
                      hw_profile.gpu_candidates.size(),
                      hw_profile.total_memory_bytes);
    } else {
        spdlog::warn("Hardware probe failed: {}", probe_result.error().message);
    }

    // 根据硬件能力自动注册后端
    if (probe_result.ok()) {
        const auto& hw_profile = probe_result.value();

        // 若探测到 NPU，尝试加载 NPU HAL
        if (!hw_profile.npu_candidates.empty()) {
            for (const auto& npu : hw_profile.npu_candidates) {
                if (npu.available) {
                    spdlog::info("NPU detected: {} {} ({}), will use NPU backend",
                                  npu.vendor, npu.chip_model, npu.device_path);
                }
            }
            // TODO: 根据 NPU 厂商加载对应的 HAL 后端
            // 当前默认：使用 CPU 回退
            spdlog::info("NPU backend registration deferred (HAL loading TODO)");
        }

        // CPU 后端始终可用（作为兜底）
        spdlog::info("CPU backend available as fallback");
    }

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

    spdlog::info("Loading model: {}", qoomodel_path);

    // 读取 .qoomodel 文件
    std::ifstream ifs(qoomodel_path, std::ios::binary | std::ios::ate);
    if (!ifs) {
        return Error<ModelHandle>(ErrorCode::FILE_NOT_FOUND,
                                   "Model file not found: " + qoomodel_path);
    }

    std::size_t file_size = static_cast<std::size_t>(ifs.tellg());
    ifs.seekg(0, std::ios::beg);

    // 读取文件头（128 字节）
    if (file_size < 128 + 32) {  // Header + Checksum 最小大小
        return Error<ModelHandle>(ErrorCode::FILE_CORRUPTED,
                                   "File too small: " + qoomodel_path);
    }

    std::vector<std::uint8_t> header(128);
    ifs.read(reinterpret_cast<char*>(header.data()), 128);

    // 验证 Magic Number
    static constexpr std::uint8_t MAGIC[4] = {'Q', 'O', 'O', 0x01};
    if (std::memcmp(header.data(), MAGIC, 4) != 0) {
        return Error<ModelHandle>(ErrorCode::FILE_CORRUPTED,
                                   "Invalid .qoomodel magic number");
    }

    // 解析 Header
    std::uint32_t version = *reinterpret_cast<std::uint32_t*>(&header[4]);
    std::uint32_t flags = *reinterpret_cast<std::uint32_t*>(&header[8]);
    char model_name_cstr[65] = {0};
    std::memcpy(model_name_cstr, &header[12], 64);
    std::string model_name(model_name_cstr);
    std::uint32_t target_backend_raw = *reinterpret_cast<std::uint32_t*>(&header[76]);
    std::uint64_t compiled_size = *reinterpret_cast<std::uint64_t*>(&header[80]);
    std::uint64_t weight_size = *reinterpret_cast<std::uint64_t*>(&header[88]);

    spdlog::info("  version:       {}", version);
    spdlog::info("  model_name:    {}", model_name);
    spdlog::info("  target_backend: {}", target_backend_raw);
    spdlog::info("  compiled_size: {} bytes", compiled_size);
    spdlog::info("  weight_size:   {} bytes", weight_size);

    // 读取编译后的模型数据
    std::vector<std::uint8_t> compiled_data(compiled_size);
    if (compiled_size > 0) {
        ifs.read(reinterpret_cast<char*>(compiled_data.data()), compiled_size);
    }

    // 选择后端
    BackendType target = static_cast<BackendType>(target_backend_raw);
    BackendPtr selected_backend;

    if (model_config.preferred_backend.has_value()) {
        // 用户指定了后端
        target = model_config.preferred_backend.value();
    }

    // 查找后端
    {
        std::lock_guard<std::mutex> bk_lock(impl_->backends_mutex);
        auto bk_it = impl_->backends.find(target);
        if (bk_it != impl_->backends.end()) {
            selected_backend = bk_it->second;
        } else if (impl_->config.enable_cpu_fallback) {
            // 回退到 CPU
            auto cpu_it = impl_->backends.find(BackendType::CPU);
            if (cpu_it != impl_->backends.end()) {
                selected_backend = cpu_it->second;
                spdlog::warn("Target backend not available, falling back to CPU");
            }
        }
    }

    // 注册到模型表
    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    ModelHandle handle = impl_->next_handle++;

    Impl::LoadedModel model;
    model.backend = selected_backend;
    model.backend_type = target;
    model.compiled_data = std::move(compiled_data);
    model.model_config = model_config;
    model.info.name = model_name;
    model.info.version = "v" + std::to_string(version);
    model.info.compiled_for = target;

    // 如果有后端，在后端中加载模型
    if (selected_backend) {
        auto load_result = selected_backend->load_model(
            model.compiled_data, model.info);
        if (!load_result.ok()) {
            return Error<ModelHandle>(ErrorCode::COMPILE_FAILED,
                                       "Backend failed to load model: " +
                                       load_result.error().message);
        }
        model.backend_model_handle = load_result.value();
    }

    impl_->models[handle] = std::move(model);

    spdlog::info("Model loaded: handle={}, name='{}', backend={}",
                  handle, model_name,
                  selected_backend ? selected_backend->name() : "none");
    return handle;
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

    // 从后端卸载模型
    if (it->second.backend) {
        auto unload_result = it->second.backend->unload_model(
            it->second.backend_model_handle);
        if (!unload_result.ok()) {
            spdlog::warn("Backend failed to unload model handle={}: {}",
                          handle, unload_result.error().message);
        }
    }

    impl_->models.erase(it);
    spdlog::info("Model unloaded, handle={}", handle);
    return Ok();
}

void InferenceEngine::unload_all_models() {
    if (!impl_) return;
    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    for (auto& [handle, model] : impl_->models) {
        if (model.backend) {
            model.backend->unload_model(model.backend_model_handle);
        }
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
    return it->second.info;  // 隐式构造 Result<ModelInfo>
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

    // 获取模型信息
    Impl::LoadedModel* model = nullptr;
    {
        std::lock_guard<std::mutex> lock(impl_->models_mutex);
        auto it = impl_->models.find(handle);
        if (it == impl_->models.end()) {
            return Error<Tensor>(ErrorCode::MODEL_NOT_LOADED, "Model not loaded");
        }
        model = &it->second;
    }

    auto start = std::chrono::high_resolution_clock::now();

    // 通过后端执行推理
    std::vector<Tensor> outputs;
    if (model->backend) {
        // Clone input for backend (Tensor is move-only)
        auto input_clone = input.clone();
        if (!input_clone.ok()) {
            return Error<Tensor>(ErrorCode::OUT_OF_MEMORY, "Failed to clone input tensor");
        }
        std::vector<Tensor> inputs_vec;
        inputs_vec.push_back(std::move(input_clone).value());
        auto result = model->backend->infer(model->backend_model_handle, inputs_vec);
        if (!result.ok()) {
            return Error<Tensor>(ErrorCode::INFER_FAILED,
                                 "Backend inference failed: " + result.error().message);
        }
        outputs = std::move(result).value();
    } else {
        // 无后端：返回 dummy 输出（用于测试/开发）
        spdlog::warn("No backend available for model handle={}, returning dummy output",
                      handle);
        auto output = Tensor::create({1, 1000}, DType::FLOAT32);
        if (!output.ok()) {
            return Error<Tensor>(ErrorCode::OUT_OF_MEMORY,
                                 "Failed to create output tensor");
        }
        outputs.push_back(std::move(output).value());
    }

    auto end = std::chrono::high_resolution_clock::now();
    double elapsed_ms = std::chrono::duration<double, std::milli>(end - start).count();

    // 更新性能统计
    {
        std::lock_guard<std::mutex> lock(impl_->perf_mutex);
        auto& p = impl_->perf;
        p.total_inferences++;
        p.total_infer_time_ms += elapsed_ms;
        p.min_infer_time_ms = std::min(p.min_infer_time_ms, elapsed_ms);
        p.max_infer_time_ms = std::max(p.max_infer_time_ms, elapsed_ms);
    }

    spdlog::debug("Infer: handle={}, time={:.3f}ms, input_shape=[{}]",
                   handle, elapsed_ms,
                   [&]() {
                       std::string s;
                       for (auto d : input.shape()) {
                           if (!s.empty()) s += ",";
                           s += std::to_string(d);
                       }
                       return s;
                   }());

    if (outputs.empty()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED, "Backend returned no outputs");
    }

    return std::move(outputs[0]);
}

Result<std::vector<Tensor>> InferenceEngine::infer_multi_input(
    ModelHandle handle,
    const std::vector<Tensor>& inputs) {
    if (!impl_ || !impl_->initialized) {
        return Error<std::vector<Tensor>>(ErrorCode::ENGINE_NOT_INIT,
                                            "Engine not initialized");
    }

    Impl::LoadedModel* model = nullptr;
    {
        std::lock_guard<std::mutex> lock(impl_->models_mutex);
        auto it = impl_->models.find(handle);
        if (it == impl_->models.end()) {
            return Error<std::vector<Tensor>>(ErrorCode::MODEL_NOT_LOADED,
                                                "Model not loaded");
        }
        model = &it->second;
    }

    auto start = std::chrono::high_resolution_clock::now();

    std::vector<Tensor> outputs;
    if (model->backend) {
        auto result = model->backend->infer(model->backend_model_handle, inputs);
        if (!result.ok()) {
            return Error<std::vector<Tensor>>(ErrorCode::INFER_FAILED,
                                                "Backend inference failed: " +
                                                result.error().message);
        }
        outputs = std::move(result).value();
    } else {
        // 无后端：为每个输入返回一个 dummy 输出
        for (const auto& input : inputs) {
            auto output = Tensor::create(input.shape(), input.dtype());
            if (output.ok()) {
                outputs.push_back(std::move(output).value());
            }
        }
    }

    auto end = std::chrono::high_resolution_clock::now();
    double elapsed_ms = std::chrono::duration<double, std::milli>(end - start).count();

    {
        std::lock_guard<std::mutex> lock(impl_->perf_mutex);
        auto& p = impl_->perf;
        p.total_inferences++;
        p.total_infer_time_ms += elapsed_ms;
        p.min_infer_time_ms = std::min(p.min_infer_time_ms, elapsed_ms);
        p.max_infer_time_ms = std::max(p.max_infer_time_ms, elapsed_ms);
    }

    spdlog::debug("Infer multi-input: handle={}, {} inputs, time={:.3f}ms",
                   handle, inputs.size(), elapsed_ms);

    return outputs;
}

std::future<Result<Tensor>> InferenceEngine::infer_async(
    ModelHandle handle,
    Tensor input) {
    // 移动捕获 input 避免异步执行时引用失效
    return std::async(std::launch::async,
                      [this, handle, input = std::move(input)]() { return infer(handle, input); });
}

std::future<Result<std::vector<Tensor>>> InferenceEngine::infer_async_multi_input(
    ModelHandle handle,
    std::vector<Tensor> inputs) {
    return std::async(std::launch::async,
                      [this, handle, inputs = std::move(inputs)]() {
                          return infer_multi_input(handle, inputs);
                      });
}

Result<std::vector<std::vector<Tensor>>> InferenceEngine::infer_batch(
    ModelHandle handle,
    const std::vector<std::vector<Tensor>>& batch_inputs) {
    if (!impl_ || !impl_->initialized) {
        return Error<std::vector<std::vector<Tensor>>>(ErrorCode::ENGINE_NOT_INIT,
                                                         "Engine not initialized");
    }

    Impl::LoadedModel* model = nullptr;
    {
        std::lock_guard<std::mutex> lock(impl_->models_mutex);
        auto it = impl_->models.find(handle);
        if (it == impl_->models.end()) {
            return Error<std::vector<std::vector<Tensor>>>(ErrorCode::MODEL_NOT_LOADED,
                                                              "Model not loaded");
        }
        model = &it->second;
    }

    std::vector<std::vector<Tensor>> batch_outputs;

    if (model->backend) {
        // 后端支持批量推理
        auto result = model->backend->infer_batch(
            model->backend_model_handle, batch_inputs);
        if (result.ok()) {
            batch_outputs = std::move(result).value();
        } else {
            // Fallback：逐个推理
            spdlog::warn("Backend batch inference failed, falling back to sequential: {}",
                          result.error().message);
            for (const auto& inputs : batch_inputs) {
                auto infer_result = model->backend->infer(
                    model->backend_model_handle, inputs);
                if (infer_result.ok()) {
                    batch_outputs.push_back(std::move(infer_result).value());
                } else {
                    return Error<std::vector<std::vector<Tensor>>>(
                        ErrorCode::INFER_FAILED,
                        "Sequential fallback failed: " + infer_result.error().message);
                }
            }
        }
    } else {
        return Error<std::vector<std::vector<Tensor>>>(ErrorCode::BACKEND_UNAVAILABLE,
                                                         "No backend available for batch inference");
    }

    return batch_outputs;
}

Result<std::vector<std::vector<Tensor>>> InferenceEngine::infer_multi_model(
    const std::vector<std::pair<ModelHandle, std::vector<Tensor>>>& requests) {
    if (!impl_ || !impl_->initialized) {
        return Error<std::vector<std::vector<Tensor>>>(ErrorCode::ENGINE_NOT_INIT,
                                                         "Engine not initialized");
    }

    std::vector<std::vector<Tensor>> results;
    results.reserve(requests.size());

    // 串行执行多模型推理（TODO：真正的并行调度）
    for (const auto& [handle, inputs] : requests) {
        auto result = infer_multi_input(handle, inputs);
        if (!result.ok()) {
            return Error<std::vector<std::vector<Tensor>>>(
                ErrorCode::INFER_FAILED,
                "Multi-model inference failed at model handle=" +
                std::to_string(handle) + ": " + result.error().message);
        }
        results.push_back(std::move(result).value());
    }

    spdlog::debug("Multi-model inference: {} models, {} total outputs",
                   requests.size(), results.size());
    return results;
}

Result<ModelHandle> InferenceEngine::load_model_from_buffer(
    const std::vector<std::uint8_t>& buffer,
    const ModelConfig& model_config) {
    if (!impl_ || !impl_->initialized) {
        return Error<ModelHandle>(ErrorCode::ENGINE_NOT_INIT,
                                   "Engine not initialized");
    }

    if (buffer.size() < 128) {
        return Error<ModelHandle>(ErrorCode::INVALID_MODEL,
                                   "Buffer too small for .qoomodel");
    }

    // 验证 Magic Number
    static constexpr std::uint8_t MAGIC[4] = {'Q', 'O', 'O', 0x01};
    if (std::memcmp(buffer.data(), MAGIC, 4) != 0) {
        return Error<ModelHandle>(ErrorCode::INVALID_MODEL,
                                   "Invalid .qoomodel magic number in buffer");
    }

    // 解析 Header（从 buffer 中）
    std::uint32_t version = *reinterpret_cast<const std::uint32_t*>(&buffer[4]);
    char model_name_cstr[65] = {0};
    std::memcpy(model_name_cstr, &buffer[12], 64);
    std::string model_name(model_name_cstr);
    std::uint64_t compiled_size = *reinterpret_cast<const std::uint64_t*>(&buffer[80]);
    std::uint32_t target_backend_raw = *reinterpret_cast<const std::uint32_t*>(&buffer[76]);

    // 提取编译后的模型数据
    std::vector<std::uint8_t> compiled_data(
        buffer.begin() + 128,
        buffer.begin() + 128 + std::min(compiled_size,
                                         static_cast<std::uint64_t>(buffer.size() - 128)));

    BackendType target = static_cast<BackendType>(target_backend_raw);
    if (model_config.preferred_backend.has_value()) {
        target = model_config.preferred_backend.value();
    }

    BackendPtr selected_backend;
    {
        std::lock_guard<std::mutex> bk_lock(impl_->backends_mutex);
        auto bk_it = impl_->backends.find(target);
        if (bk_it != impl_->backends.end()) {
            selected_backend = bk_it->second;
        }
    }

    std::lock_guard<std::mutex> lock(impl_->models_mutex);
    ModelHandle handle = impl_->next_handle++;

    Impl::LoadedModel model;
    model.backend = selected_backend;
    model.backend_type = target;
    model.compiled_data = std::move(compiled_data);
    model.model_config = model_config;
    model.info.name = model_name;
    model.info.version = "v" + std::to_string(version);

    if (selected_backend) {
        auto load_result = selected_backend->load_model(
            model.compiled_data, model.info);
        if (load_result.ok()) {
            model.backend_model_handle = load_result.value();
        }
    }

    impl_->models[handle] = std::move(model);
    spdlog::info("Model loaded from buffer: handle={}, name='{}'", handle, model_name);
    return handle;
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
    return it->second;  // 隐式构造 Result<BackendPtr>
}

// ────────────────────────────────────────────────────────────────────────────
//  编译器 / 剖析器接口
// ────────────────────────────────────────────────────────────────────────────
ModelCompiler* InferenceEngine::compiler() {
    // 运行时编译器：返回全局编译器实例
    // 完整实现应在引擎 init() 时创建编译器实例
    static auto compiler_instance = create_compiler(/*use_mlir=*/true);
    return compiler_instance.get();
}

std::string InferenceEngine::profiling_summary() const {
    std::lock_guard<std::mutex> lock(impl_->perf_mutex);
    const auto& p = impl_->perf;

    std::stringstream ss;
    ss << "{"
       << "\"total_inferences\": " << p.total_inferences << ","
       << "\"total_time_ms\": " << p.total_infer_time_ms << ","
       << "\"avg_time_ms\": "
       << (p.total_inferences > 0 ? p.total_infer_time_ms / p.total_inferences : 0.0) << ","
       << "\"min_time_ms\": "
       << (p.total_inferences > 0 ? p.min_infer_time_ms : 0.0) << ","
       << "\"max_time_ms\": " << p.max_infer_time_ms << ","
       << "\"loaded_models\": " << impl_->models.size() << ","
       << "\"backends\": " << impl_->backends.size()
       << "}";
    return ss.str();
}

Result<std::string> InferenceEngine::export_profiling_report() const {
    std::stringstream ss;
    ss << "{\n";

    // 引擎级统计
    {
        std::lock_guard<std::mutex> lock(impl_->perf_mutex);
        const auto& p = impl_->perf;
        ss << "  \"engine\": {\n";
        ss << "    \"total_inferences\": " << p.total_inferences << ",\n";
        ss << "    \"total_time_ms\": " << p.total_infer_time_ms << ",\n";
        ss << "    \"avg_time_ms\": "
           << (p.total_inferences > 0 ? p.total_infer_time_ms / p.total_inferences : 0.0) << ",\n";
        ss << "    \"min_time_ms\": "
           << (p.total_inferences > 0 ? p.min_infer_time_ms : 0.0) << ",\n";
        ss << "    \"max_time_ms\": " << p.max_infer_time_ms << "\n";
        ss << "  },\n";
    }

    // 模型级统计
    ss << "  \"models\": [\n";
    {
        std::lock_guard<std::mutex> lock(impl_->models_mutex);
        std::size_t idx = 0;
        for (const auto& [handle, model] : impl_->models) {
            if (idx > 0) ss << ",\n";
            ss << "    {"
               << "\"handle\": " << handle << ","
               << "\"name\": \"" << model.info.name << "\","
               << "\"backend\": \""
               << (model.backend ? model.backend->name() : "none") << "\","
               << "\"compiled_size\": " << model.compiled_data.size()
               << "}";
            idx++;
        }
    }
    ss << "\n  ],\n";

    // 后端级统计
    ss << "  \"backends\": [\n";
    {
        std::lock_guard<std::mutex> lock(impl_->backends_mutex);
        std::size_t idx = 0;
        for (const auto& [type, backend] : impl_->backends) {
            if (idx > 0) ss << ",\n";
            auto caps = backend->capabilities();
            ss << "    {"
               << "\"type\": \"" << backend_to_string(type) << "\","
               << "\"name\": \"" << backend->name() << "\","
               << "\"peak_tops\": " << caps.peak_tops << ","
               << "\"max_memory_mb\": " << (caps.max_memory_bytes / (1024 * 1024)) << ","
               << "\"loaded_models\": " << backend->loaded_model_count()
               << "}";
            idx++;
        }
    }
    ss << "\n  ]\n";
    ss << "}\n";

    return ss.str();
}

// ────────────────────────────────────────────────────────────────────────────
//  诊断
// ────────────────────────────────────────────────────────────────────────────
std::string InferenceEngine::status_json() const {
    if (!impl_) {
        return R"({"status": "not_initialized"})";
    }

    std::stringstream ss;
    ss << "{"
       << "\"status\": \"ok\","
       << "\"version\": \"" << QOOCORE_VERSION_STRING << "\","
       << "\"loaded_models\": " << impl_->models.size() << ","
       << "\"registered_backends\": " << impl_->backends.size() << ","
       << "\"total_inferences\": " << impl_->perf.total_inferences
       << "}";
    return ss.str();
}

}  // namespace qoocore
