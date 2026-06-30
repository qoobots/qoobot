/**
 * @file gpu_backend.cpp
 * @brief GPU 推理后端 — CUDA/OpenCL/Vulkan 统一抽象
 *
 * 为 InferenceEngine 提供 GPU 加速推理能力。
 * 支持三种 GPU API 后端：
 *   - CUDA (NVIDIA Jetson/GPU)
 *   - OpenCL (跨平台：ARM Mali/Adreno/Intel/AMD)
 *   - Vulkan Compute (跨平台：Android/Windows/Linux)
 *
 * 设计要点：
 *   - 运行时自动探测并选择最佳 GPU API
 *   - 实现 Backend 抽象接口，与引擎无缝集成
 *   - 支持 FP32/FP16/INT8 混合精度
 *   - 支持多 CUDA Stream/OpenCL CommandQueue 并发
 *   - 零拷贝：支持导入 ION/DMA-BUF (Linux) 和 CUDA IPC
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/backend.h"
#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <algorithm>
#include <atomic>
#include <cstring>
#include <fstream>
#include <map>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <spdlog/spdlog.h>

// ─────────────────────────────────────────────────────────────
//  编译时特性开关
// ─────────────────────────────────────────────────────────────
#ifndef QOOCORE_ENABLE_CUDA
#  define QOOCORE_ENABLE_CUDA 0
#endif
#ifndef QOOCORE_ENABLE_OPENCL
#  define QOOCORE_ENABLE_OPENCL 0
#endif
#ifndef QOOCORE_ENABLE_VULKAN
#  define QOOCORE_ENABLE_VULKAN 0
#endif

namespace qoocore {

// ═══════════════════════════════════════════════════════════════════════════════
//  GPU API 枚举与选择
// ═══════════════════════════════════════════════════════════════════════════════

/// GPU API 后端类型
enum class GpuApiType : uint8_t {
    NONE,
    CUDA,
    OPENCL,
    VULKAN,
};

/// 将 GpuApiType 转为字符串
[[nodiscard]] const char* gpu_api_to_string(GpuApiType t) {
    switch (t) {
        case GpuApiType::CUDA:   return "cuda";
        case GpuApiType::OPENCL: return "opencl";
        case GpuApiType::VULKAN: return "vulkan";
        default:                 return "none";
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//  GPU 设备探测
// ═══════════════════════════════════════════════════════════════════════════════

/// GPU 设备信息
struct GpuDeviceInfo {
    std::string name;
    std::string vendor;
    GpuApiType preferred_api{GpuApiType::NONE};
    std::size_t global_memory_bytes{0};
    std::size_t shared_memory_per_block{0};
    int max_compute_units{0};
    int max_work_group_size{256};
    int warp_size{32};
    float peak_tflops_fp32{0.0f};
    float peak_tflops_fp16{0.0f};
    bool supports_fp16{false};
    bool supports_int8{false};
    bool supports_unified_memory{false};  // 统一内存（如 Jetson）
    bool is_integrated{false};            // 集成显卡
};

/// 探测系统上的 GPU 设备
[[nodiscard]] std::vector<GpuDeviceInfo> probe_gpu_devices() {
    std::vector<GpuDeviceInfo> devices;

    // 优先探测 CUDA
#if QOOCORE_ENABLE_CUDA
    {
        // CUDA 运行时探测
        // int count = 0;
        // cudaGetDeviceCount(&count);
        // for (int i = 0; i < count; ++i) { ... }
        spdlog::info("[gpu] CUDA probing: runtime linked, would enumerate devices");
    }
#endif

    // OpenCL 探测
#if QOOCORE_ENABLE_OPENCL
    {
        // clGetPlatformIDs / clGetDeviceIDs
        spdlog::info("[gpu] OpenCL probing: runtime linked, would enumerate devices");
    }
#endif

    // Vulkan 探测
#if QOOCORE_ENABLE_VULKAN
    {
        // vkEnumeratePhysicalDevices
        spdlog::info("[gpu] Vulkan probing: runtime linked, would enumerate devices");
    }
#endif

    // 为常见平台提供默认设备信息（桩实现）
    // NVIDIA Jetson Orin
    {
        GpuDeviceInfo dev;
        dev.name = "NVIDIA Orin GPU (Ampere)";
        dev.vendor = "NVIDIA";
        dev.preferred_api = GpuApiType::CUDA;
        dev.global_memory_bytes = 32ULL * 1024 * 1024 * 1024;  // 32GB unified
        dev.shared_memory_per_block = 48 * 1024;
        dev.max_compute_units = 16;   // 2048 CUDA cores / 128 = 16 SM
        dev.warp_size = 32;
        dev.peak_tflops_fp32 = 5.3f;
        dev.peak_tflops_fp16 = 10.6f;
        dev.supports_fp16 = true;
        dev.supports_int8 = true;
        dev.supports_unified_memory = true;
        dev.is_integrated = true;
        devices.push_back(dev);
    }

    // Qualcomm Adreno (Snapdragon)
    {
        GpuDeviceInfo dev;
        dev.name = "Qualcomm Adreno 750";
        dev.vendor = "Qualcomm";
        dev.preferred_api = GpuApiType::OPENCL;
        dev.global_memory_bytes = 12ULL * 1024 * 1024 * 1024;
        dev.shared_memory_per_block = 32 * 1024;
        dev.max_compute_units = 6;
        dev.max_work_group_size = 1024;
        dev.warp_size = 64;
        dev.peak_tflops_fp32 = 3.4f;
        dev.peak_tflops_fp16 = 6.8f;
        dev.supports_fp16 = true;
        dev.supports_int8 = false;
        dev.supports_unified_memory = true;
        dev.is_integrated = true;
        devices.push_back(dev);
    }

    // ARM Mali (MediaTek Dimensity)
    {
        GpuDeviceInfo dev;
        dev.name = "ARM Mali-G720 Immortalis";
        dev.vendor = "ARM";
        dev.preferred_api = GpuApiType::VULKAN;
        dev.global_memory_bytes = 8ULL * 1024 * 1024 * 1024;
        dev.shared_memory_per_block = 32 * 1024;
        dev.max_compute_units = 12;
        dev.max_work_group_size = 256;
        dev.warp_size = 16;
        dev.peak_tflops_fp32 = 1.8f;
        dev.peak_tflops_fp16 = 3.6f;
        dev.supports_fp16 = true;
        dev.supports_int8 = false;
        dev.supports_unified_memory = true;
        dev.is_integrated = true;
        devices.push_back(dev);
    }

    spdlog::info("[gpu] Probed {} GPU device(s) (simulated)", devices.size());
    return devices;
}

/// 根据偏好和可用 API 选择最佳 GPU API
[[nodiscard]] GpuApiType select_gpu_api(const std::vector<GpuDeviceInfo>& devices) {
    if (devices.empty()) return GpuApiType::NONE;

    // 优先级：CUDA > Vulkan > OpenCL
    for (const auto& dev : devices) {
        if (dev.preferred_api == GpuApiType::CUDA
#if QOOCORE_ENABLE_CUDA
            && true
#endif
        ) {
            return GpuApiType::CUDA;
        }
    }

    for (const auto& dev : devices) {
        if (dev.preferred_api == GpuApiType::VULKAN
#if QOOCORE_ENABLE_VULKAN
            && true
#endif
        ) {
            return GpuApiType::VULKAN;
        }
    }

    for (const auto& dev : devices) {
        if (dev.preferred_api == GpuApiType::OPENCL
#if QOOCORE_ENABLE_OPENCL
            && true
#endif
        ) {
            return GpuApiType::OPENCL;
        }
    }

    // Fallback：返回第一个设备的偏好
    return devices[0].preferred_api;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  GPU 内核缓存
// ═══════════════════════════════════════════════════════════════════════════════

/// 编译后的 GPU 内核
struct GpuKernel {
    std::string name;
    std::string source;           // 源码（GLSL/OpenCL C/CUDA）
    std::vector<uint8_t> binary;  // 编译后的二进制
    std::size_t local_mem_bytes{0};
    int optimal_workgroup_size{256};
};

/// 内核缓存（按操作类型索引）
class GpuKernelCache {
public:
    /// 获取或编译内核
    [[nodiscard]] const GpuKernel* get_or_compile(
        const std::string& op_type,
        GpuApiType api,
        DType input_dtype,
        DType output_dtype) {

        std::string key = op_type + "_" +
            std::to_string(static_cast<int>(api)) + "_" +
            std::to_string(static_cast<int>(input_dtype)) + "_" +
            std::to_string(static_cast<int>(output_dtype));

        std::lock_guard<std::mutex> lock(mutex_);
        auto it = cache_.find(key);
        if (it != cache_.end()) {
            return &it->second;
        }

        // 编译内核（桩：生成空的内核描述）
        GpuKernel kernel;
        kernel.name = key;

        if (api == GpuApiType::CUDA) {
            kernel.source = generate_cuda_kernel(op_type, input_dtype, output_dtype);
            kernel.optimal_workgroup_size = 256;
        } else if (api == GpuApiType::OPENCL) {
            kernel.source = generate_opencl_kernel(op_type, input_dtype, output_dtype);
            kernel.optimal_workgroup_size = 256;
        } else if (api == GpuApiType::VULKAN) {
            kernel.source = generate_vulkan_kernel(op_type, input_dtype, output_dtype);
            kernel.optimal_workgroup_size = 256;
        }

        cache_[key] = std::move(kernel);
        return &cache_[key];
    }

    /// 清除缓存
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_.clear();
    }

private:
    [[nodiscard]] static std::string generate_cuda_kernel(
        const std::string& op_type, DType in_dt, DType out_dt) {
        // CUDA PTX 源码桩
        (void)in_dt; (void)out_dt;
        return "// CUDA kernel for " + op_type + "\n"
               "__global__ void kernel_" + op_type +
               "(const float* __restrict__ in, float* __restrict__ out, int n) {\n"
               "  int idx = blockIdx.x * blockDim.x + threadIdx.x;\n"
               "  if (idx < n) out[idx] = in[idx];\n"
               "}\n";
    }

    [[nodiscard]] static std::string generate_opencl_kernel(
        const std::string& op_type, DType in_dt, DType out_dt) {
        (void)in_dt; (void)out_dt;
        return "// OpenCL kernel for " + op_type + "\n"
               "__kernel void kernel_" + op_type +
               "(__global const float* in, __global float* out, int n) {\n"
               "  int idx = get_global_id(0);\n"
               "  if (idx < n) out[idx] = in[idx];\n"
               "}\n";
    }

    [[nodiscard]] static std::string generate_vulkan_kernel(
        const std::string& op_type, DType in_dt, DType out_dt) {
        (void)in_dt; (void)out_dt;
        return "// Vulkan GLSL compute shader for " + op_type + "\n"
               "#version 450\n"
               "layout(local_size_x = 256) in;\n"
               "layout(std430, binding = 0) readonly buffer InBuf { float data[]; } in_buf;\n"
               "layout(std430, binding = 1) writeonly buffer OutBuf { float data[]; } out_buf;\n"
               "void main() {\n"
               "  uint idx = gl_GlobalInvocationID.x;\n"
               "  out_buf.data[idx] = in_buf.data[idx];\n"
               "}\n";
    }

    std::unordered_map<std::string, GpuKernel> cache_;
    std::mutex mutex_;
};

// ═══════════════════════════════════════════════════════════════════════════════
//  GpuBackend — GPU 推理后端实现
// ═══════════════════════════════════════════════════════════════════════════════

class GpuBackend final : public Backend {
public:
    explicit GpuBackend(GpuApiType api = GpuApiType::NONE)
        : selected_api_(api) {}

    ~GpuBackend() override {
        if (initialized_) deinit();
    }

    // ── 后端元信息 ──────────────────────────────────────────────────────────
    BackendType type() const noexcept override { return BackendType::GPU; }
    std::string name() const noexcept override {
        return gpu_api_to_string(selected_api_);
    }

    BackendCapabilities capabilities() const override {
        BackendCapabilities caps;
        caps.type = BackendType::GPU;

        if (!device_info_.name.empty()) {
            caps.peak_tops = device_info_.peak_tflops_fp32;
            caps.max_memory_bytes = device_info_.global_memory_bytes;
            caps.supports_fp32 = true;
            caps.supports_fp16 = device_info_.supports_fp16;
            caps.supports_int8 = device_info_.supports_int8;
            caps.supports_zero_copy = device_info_.supports_unified_memory;
            caps.supports_async = true;
            caps.supports_dynamic_batch = true;
            caps.max_concurrent_models = 8;
            caps.typical_latency_ms = 2.0;  // GPU 典型推理延迟
            caps.typical_power_w = device_info_.is_integrated ? 5.0 : 150.0;
        }

        return caps;
    }

    // ── 生命周期 ────────────────────────────────────────────────────────────
    Result<void> init(const BackendConfig& config = {}) override {
        if (initialized_) {
            spdlog::warn("[gpu] Backend already initialized");
            return Ok();
        }

        config_ = config;

        // 探测 GPU 设备
        auto devices = probe_gpu_devices();
        if (devices.empty()) {
            return Error<void>(ErrorCode::BACKEND_UNAVAILABLE,
                "No GPU devices found");
        }

        // 选择 API
        if (selected_api_ == GpuApiType::NONE) {
            selected_api_ = select_gpu_api(devices);
            if (selected_api_ == GpuApiType::NONE) {
                return Error<void>(ErrorCode::BACKEND_UNAVAILABLE,
                    "No suitable GPU API available");
            }
        }

        // 选择设备
        device_info_ = devices[0];  // 默认使用第一个设备

        spdlog::info("[gpu] Initializing {} backend on '{}'",
                      gpu_api_to_string(selected_api_), device_info_.name);
        spdlog::info("[gpu]   Memory: {} MB, FP32: {:.1f} TFLOPS, FP16: {:.1f} TFLOPS",
                      device_info_.global_memory_bytes / (1024 * 1024),
                      device_info_.peak_tflops_fp32,
                      device_info_.peak_tflops_fp16);

        // 初始化 GPU 运行时
        Result<void> init_result = init_gpu_runtime();
        if (!init_result.ok()) {
            return init_result;
        }

        // 预热内核缓存
        kernel_cache_ = std::make_unique<GpuKernelCache>();

        initialized_ = true;
        spdlog::info("[gpu] Backend initialized successfully ({} streams)",
                      config_.gpu.cuda_streams);
        return Ok();
    }

    void deinit() override {
        if (!initialized_) return;

        spdlog::info("[gpu] Deinitializing {} backend", gpu_api_to_string(selected_api_));

        // 卸载所有模型
        for (const auto& [handle, model] : loaded_models_) {
            unload_model_gpu(model);
        }
        loaded_models_.clear();

        // 释放内核缓存
        kernel_cache_.reset();

        // 释放 GPU 资源
        deinit_gpu_runtime();

        initialized_ = false;
        spdlog::info("[gpu] Backend deinitialized");
    }

    bool is_initialized() const noexcept override { return initialized_; }

    // ── 模型管理 ────────────────────────────────────────────────────────────
    Result<std::uint64_t> load_model(
        const std::vector<std::uint8_t>& model_data,
        const std::optional<ModelInfo>& info = std::nullopt) override {

        if (!initialized_) {
            return Error<std::uint64_t>(ErrorCode::BACKEND_UNAVAILABLE,
                "GPU backend not initialized");
        }

        auto model_name = info.has_value() ? info->name : "unknown";
        spdlog::info("[gpu] Loading model '{}' ({} bytes)", model_name, model_data.size());

        // 解析编译后的模型数据
        GpuModelData gpu_model;
        gpu_model.name = model_name;
        gpu_model.data = model_data;

        // 分配 GPU 内存（桩：模拟）
        gpu_model.gpu_memory_bytes = estimate_gpu_memory(model_data);

        // 注册模型
        std::lock_guard<std::mutex> lock(models_mutex_);
        std::uint64_t handle = next_model_handle_++;
        loaded_models_[handle] = std::move(gpu_model);

        spdlog::info("[gpu] Model loaded: handle={}, gpu_mem={} MB",
                      handle, loaded_models_[handle].gpu_memory_bytes / (1024 * 1024));
        return handle;
    }

    Result<void> unload_model(std::uint64_t model_handle) override {
        std::lock_guard<std::mutex> lock(models_mutex_);
        auto it = loaded_models_.find(model_handle);
        if (it == loaded_models_.end()) {
            return Error<void>(ErrorCode::MODEL_NOT_LOADED,
                "GPU model handle " + std::to_string(model_handle) + " not found");
        }

        unload_model_gpu(it->second);
        loaded_models_.erase(it);

        spdlog::info("[gpu] Model unloaded: handle={}", model_handle);
        return Ok();
    }

    std::size_t loaded_model_count() const override {
        std::lock_guard<std::mutex> lock(models_mutex_);
        return loaded_models_.size();
    }

    // ── 推理 ────────────────────────────────────────────────────────────────
    Result<std::vector<Tensor>> infer(
        std::uint64_t model_handle,
        const std::vector<Tensor>& inputs) override {

        if (!initialized_) {
            return Error<std::vector<Tensor>>(ErrorCode::BACKEND_UNAVAILABLE,
                "GPU backend not initialized");
        }

        GpuModelData* model = nullptr;
        {
            std::lock_guard<std::mutex> lock(models_mutex_);
            auto it = loaded_models_.find(model_handle);
            if (it == loaded_models_.end()) {
                return Error<std::vector<Tensor>>(ErrorCode::MODEL_NOT_LOADED,
                    "GPU model not loaded");
            }
            model = &it->second;
        }

        return execute_gpu_inference(*model, inputs);
    }

    std::future<Result<std::vector<Tensor>>> infer_async(
        std::uint64_t model_handle,
        const std::vector<Tensor>& inputs) override {
        // Clone inputs for async execution (Tensor is move-only)
        auto cloned_inputs = std::make_shared<std::vector<Tensor>>();
        cloned_inputs->reserve(inputs.size());
        for (const auto& t : inputs) {
            auto c = t.clone();
            if (c.ok()) cloned_inputs->push_back(std::move(c).value());
        }
        return std::async(std::launch::async,
            [this, model_handle, cloned_inputs]() {
                return infer(model_handle, *cloned_inputs);
            });
    }

    Result<std::vector<std::vector<Tensor>>> infer_batch(
        std::uint64_t model_handle,
        const std::vector<std::vector<Tensor>>& batch_inputs) override {

        if (!initialized_) {
            return Error<std::vector<std::vector<Tensor>>>(ErrorCode::BACKEND_UNAVAILABLE,
                "GPU backend not initialized");
        }

        std::vector<std::vector<Tensor>> batch_outputs;
        batch_outputs.reserve(batch_inputs.size());

        for (const auto& inputs : batch_inputs) {
            auto result = infer(model_handle, inputs);
            if (!result.ok()) {
                return Error<std::vector<std::vector<Tensor>>>(ErrorCode::INFER_FAILED,
                    "GPU batch inference failed: " + result.error().message);
            }
            batch_outputs.push_back(std::move(result).value());
        }

        return batch_outputs;
    }

    // ── 诊断 ────────────────────────────────────────────────────────────────
    std::string diagnostic_info() const override {
        std::stringstream ss;
        ss << "{"
           << "\"api\": \"" << gpu_api_to_string(selected_api_) << "\","
           << "\"device\": \"" << device_info_.name << "\","
           << "\"vendor\": \"" << device_info_.vendor << "\","
           << "\"memory_mb\": " << (device_info_.global_memory_bytes / (1024 * 1024)) << ","
           << "\"compute_units\": " << device_info_.max_compute_units << ","
           << "\"fp32_tflops\": " << device_info_.peak_tflops_fp32 << ","
           << "\"fp16_tflops\": " << device_info_.peak_tflops_fp16 << ","
           << "\"unified_memory\": " << (device_info_.supports_unified_memory ? "true" : "false") << ","
           << "\"loaded_models\": " << loaded_model_count()
           << "}";
        return ss.str();
    }

private:
    /// GPU 模型数据
    struct GpuModelData {
        std::string name;
        std::vector<std::uint8_t> data;   // 编译后的模型数据
        std::size_t gpu_memory_bytes{0};  // GPU 内存占用
        // 实际 GPU 资源句柄（桩实现中为模拟）
        uint64_t gpu_weights_buffer{0};   // 权重缓冲区
        uint64_t gpu_workspace_buffer{0}; // 工作空间
    };

    // ── GPU 运行时初始化（桩）──────────────────────────────────────────
    Result<void> init_gpu_runtime() {
        switch (selected_api_) {
            case GpuApiType::CUDA:
                spdlog::info("[gpu/cuda] Initializing CUDA runtime...");
                // 实际实现：
                //   cudaSetDevice(0);
                //   cudaStreamCreate(&stream_);
                break;
            case GpuApiType::OPENCL:
                spdlog::info("[gpu/opencl] Initializing OpenCL runtime...");
                // 实际实现：
                //   clGetPlatformIDs(1, &platform_, &num_platforms);
                //   clGetDeviceIDs(platform_, CL_DEVICE_TYPE_GPU, ...);
                //   context_ = clCreateContext(...);
                //   queue_ = clCreateCommandQueue(...);
                break;
            case GpuApiType::VULKAN:
                spdlog::info("[gpu/vulkan] Initializing Vulkan runtime...");
                // 实际实现：
                //   vkCreateInstance(...);
                //   vkEnumeratePhysicalDevices(...);
                //   vkCreateDevice(...);
                //   vkCreateCommandPool(...);
                break;
            default:
                return Error<void>(ErrorCode::BACKEND_UNAVAILABLE,
                    "No GPU API selected");
        }
        return Ok();
    }

    void deinit_gpu_runtime() {
        switch (selected_api_) {
            case GpuApiType::CUDA:
                // cudaStreamDestroy(stream_);
                break;
            case GpuApiType::OPENCL:
                // clReleaseCommandQueue(queue_);
                // clReleaseContext(context_);
                break;
            case GpuApiType::VULKAN:
                // vkDestroyCommandPool(...);
                // vkDestroyDevice(...);
                // vkDestroyInstance(...);
                break;
            default:
                break;
        }
    }

    void unload_model_gpu(const GpuModelData& model) {
        (void)model;
        // 实际实现：释放 GPU 缓冲区
        // cudaFree(gpu_weights_buffer);
        // cudaFree(gpu_workspace_buffer);
    }

    [[nodiscard]] static std::size_t estimate_gpu_memory(
        const std::vector<std::uint8_t>& model_data) {
        // 简化估算：模型数据大小的 2.5 倍（权重 + 工作空间 + 元数据）
        return model_data.size() * 5 / 2;
    }

    // ── GPU 推理执行（桩）──────────────────────────────────────────────
    [[nodiscard]] Result<std::vector<Tensor>> execute_gpu_inference(
        const GpuModelData& model,
        const std::vector<Tensor>& inputs) {

        (void)model;

        spdlog::debug("[gpu/{}] Executing inference on model '{}' with {} inputs",
                       gpu_api_to_string(selected_api_), model.name, inputs.size());

        // 实际 GPU 推理流程：
        // 1. 将输入张量拷贝到 GPU 内存 (cudaMemcpy / clEnqueueWriteBuffer / vkCmdCopyBuffer)
        // 2. 启动 GPU kernel 网格 (cudaLaunchKernel / clEnqueueNDRangeKernel / vkCmdDispatch)
        // 3. 等待完成 (cudaStreamSynchronize / clFinish / vkQueueWaitIdle)
        // 4. 将输出张量拷贝回 CPU 内存

        // 桩：模拟 GPU 推理延迟 (1-5ms)
        auto start = std::chrono::high_resolution_clock::now();

        // 为每个输入生成输出张量
        std::vector<Tensor> outputs;
        outputs.reserve(inputs.size());

        for (const auto& input : inputs) {
            // 保持相同形状，输出类型默认 FP32
            auto output = Tensor::create(input.shape(), DType::FLOAT32);
            if (!output.ok()) {
                return Error<std::vector<Tensor>>(ErrorCode::OUT_OF_MEMORY,
                    "Failed to create GPU output tensor");
            }
            outputs.push_back(std::move(output).value());
        }

        // 模拟 GPU 计算时间
        std::this_thread::sleep_for(std::chrono::microseconds(1500));

        auto end = std::chrono::high_resolution_clock::now();
        double elapsed_us = std::chrono::duration<double, std::micro>(end - start).count();

        // 更新性能统计
        {
            std::lock_guard<std::mutex> lock(perf_mutex_);
            perf_.total_inferences++;
            perf_.total_time_us += elapsed_us;
            perf_.min_time_us = std::min(perf_.min_time_us, elapsed_us);
            perf_.max_time_us = std::max(perf_.max_time_us, elapsed_us);
        }

        spdlog::debug("[gpu/{}] Inference complete: {:.1f} us, {} inputs → {} outputs",
                       gpu_api_to_string(selected_api_), elapsed_us,
                       inputs.size(), outputs.size());

        return outputs;
    }

    // ── 成员变量 ───────────────────────────────────────────────────────
    GpuApiType selected_api_{GpuApiType::NONE};
    GpuDeviceInfo device_info_;
    BackendConfig config_;
    bool initialized_{false};

    std::unique_ptr<GpuKernelCache> kernel_cache_;

    std::unordered_map<std::uint64_t, GpuModelData> loaded_models_;
    mutable std::mutex models_mutex_;
    std::uint64_t next_model_handle_{1};

    // 性能统计
    struct GpuPerfStats {
        std::size_t total_inferences{0};
        double total_time_us{0.0};
        double min_time_us{std::numeric_limits<double>::max()};
        double max_time_us{0.0};
    };
    GpuPerfStats perf_;
    mutable std::mutex perf_mutex_;
};

// ═══════════════════════════════════════════════════════════════════════════════
//  工厂函数
// ═══════════════════════════════════════════════════════════════════════════════

/// 创建 GPU 后端（自动选择 API）
BackendPtr create_gpu_backend(const BackendConfig& config = {}) {
    (void)config;
    auto backend = std::make_shared<GpuBackend>(GpuApiType::NONE);
    spdlog::info("[gpu] Created GPU backend (auto API selection)");
    return backend;
}

/// 创建 CUDA 后端
BackendPtr create_cuda_backend(const BackendConfig& config = {}) {
    (void)config;
    auto backend = std::make_shared<GpuBackend>(GpuApiType::CUDA);
    spdlog::info("[gpu] Created CUDA backend");
    return backend;
}

/// 创建 OpenCL 后端
BackendPtr create_opencl_backend(const BackendConfig& config = {}) {
    (void)config;
    auto backend = std::make_shared<GpuBackend>(GpuApiType::OPENCL);
    spdlog::info("[gpu] Created OpenCL backend");
    return backend;
}

/// 创建 Vulkan 后端
BackendPtr create_vulkan_backend(const BackendConfig& config = {}) {
    (void)config;
    auto backend = std::make_shared<GpuBackend>(GpuApiType::VULKAN);
    spdlog::info("[gpu] Created Vulkan backend");
    return backend;
}

}  // namespace qoocore
