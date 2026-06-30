/**
 * @file mock_npu_hal.cpp
 * @brief Mock NPU HAL 实现 — 用于单元测试和 CI 环境（无真实 NPU 硬件）
 *
 * 提供完整的 NpuHal 接口实现，但推理使用 CPU 模拟。
 * 功能：
 *   - 完整的 init/deinit 生命周期
 *   - 模拟硬件能力探测
 *   - 模拟模型加载（存储编译后的模型数据）
 *   - 模拟推理（返回零填充输出或简单矩阵运算）
 *   - 性能剖析（CPU 计时）
 *   - 温度/功耗模拟
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/hal/npu_hal.h"

#include <spdlog/spdlog.h>
#include <algorithm>
#include <chrono>
#include <cstring>
#include <mutex>
#include <random>
#include <unordered_map>
#include <vector>

namespace qoocore {

// ── MockNpuHal 实现 ──────────────────────────────────────────────────
class MockNpuHal : public NpuHal {
public:
    MockNpuHal() = default;
    ~MockNpuHal() override { if (initialized_) deinit(); }

    // ── 生命周期 ─────────────────────────────────────────────────────
    Result<void> init(const NpuConfig& config) override {
        if (initialized_) {
            return Error(ErrorCode::INVALID_ARGUMENT,
                         "MockNpuHal already initialized");
        }

        config_ = config;
        initialized_ = true;
        npu_util_ = 0.0f;
        temperature_ = 45;  // 初始温度 45°C
        power_ = 0.5f;      // 空闲功耗 0.5W

        spdlog::info("MockNpuHal initialized (device={}, max_memory={} MB, power_mode={})",
                      config_.device_name,
                      config_.max_memory_bytes / (1024 * 1024),
                      config_.power_mode);
        return Ok();
    }

    void deinit() override {
        std::lock_guard<std::mutex> lock(mutex_);

        // 卸载所有模型
        for (auto& [handle, model] : loaded_models_) {
            (void)handle;
            model.data.clear();
        }
        loaded_models_.clear();

        initialized_ = false;
        spdlog::info("MockNpuHal deinitialized");
    }

    bool is_initialized() const noexcept override {
        return initialized_;
    }

    // ── 硬件能力查询 ─────────────────────────────────────────────────
    NpuCapabilities get_capabilities() const override {
        NpuCapabilities caps;
        caps.vendor = "Mock";
        caps.chip_model = "Mock-NPU-v1.0";
        caps.sdk_version = "mock-1.0.0";
        caps.driver_version = "mock-drv-1.0.0";

        caps.peak_tops_fp16 = 8.0f;
        caps.peak_tops_int8 = 16.0f;
        caps.peak_tops_int4 = 32.0f;

        caps.total_memory_bytes = config_.max_memory_bytes;
        caps.max_model_size_bytes = config_.max_memory_bytes / 2;

        caps.supports_fp32 = true;
        caps.supports_fp16 = true;
        caps.supports_int8 = true;
        caps.supports_int4 = true;

        caps.supports_zero_copy = true;
        caps.supports_perf_hint = true;
        caps.supports_batch = true;
        caps.max_concurrent_models = 4;

        caps.max_power_w = 5.0f;
        caps.typical_power_w = 2.0f;
        caps.max_temperature_c = 85;

        return caps;
    }

    std::unordered_map<std::string, double> get_dynamic_status() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        return {
            {"temperature_c", static_cast<double>(temperature_)},
            {"utilization", static_cast<double>(npu_util_)},
            {"power_w", static_cast<double>(power_)},
            {"loaded_models", static_cast<double>(loaded_models_.size())},
        };
    }

    // ── 模型管理 ─────────────────────────────────────────────────────
    Result<NpuModelHandle> load_model(
        const std::vector<std::uint8_t>& compiled_model,
        const std::string& model_name) override {

        std::lock_guard<std::mutex> lock(mutex_);

        if (!initialized_) {
            return Error<NpuModelHandle>(ErrorCode::ENGINE_NOT_INIT,
                                          "MockNpuHal not initialized");
        }

        // 检查内存限制
        std::size_t total_used = 0;
        for (const auto& [h, m] : loaded_models_) {
            total_used += m.data.size();
        }
        if (total_used + compiled_model.size() > config_.max_memory_bytes) {
            return Error<NpuModelHandle>(ErrorCode::OUT_OF_MEMORY,
                                          "Mock NPU out of memory (used=" +
                                          std::to_string(total_used) +
                                          ", needed=" +
                                          std::to_string(compiled_model.size()) +
                                          ", max=" +
                                          std::to_string(config_.max_memory_bytes) +
                                          ")");
        }

        // 分配句柄
        NpuModelHandle handle = reinterpret_cast<NpuModelHandle>(
            static_cast<std::intptr_t>(next_handle_++));

        LoadedModel model;
        model.name = model_name.empty() ? "model_" + std::to_string(next_handle_ - 1)
                                        : model_name;
        model.data = compiled_model;
        model.data_size = compiled_model.size();

        loaded_models_[handle] = std::move(model);

        spdlog::info("MockNpuHal loaded model '{}' ({} bytes), handle={}",
                      model_name, compiled_model.size(),
                      reinterpret_cast<std::intptr_t>(handle));
        return handle;
    }

    Result<void> unload_model(NpuModelHandle handle) override {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = loaded_models_.find(handle);
        if (it == loaded_models_.end()) {
            return Error(ErrorCode::MODEL_NOT_LOADED,
                         "Model handle not found in MockNpuHal");
        }

        spdlog::info("MockNpuHal unloaded model '{}'", it->second.name);
        loaded_models_.erase(it);
        return Ok();
    }

    std::size_t loaded_model_count() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        return loaded_models_.size();
    }

    // ── 推理 ─────────────────────────────────────────────────────────
    Result<std::vector<Tensor>> infer(
        NpuModelHandle handle,
        const std::vector<Tensor>& inputs) override {

        std::lock_guard<std::mutex> lock(mutex_);

        if (!initialized_) {
            return Error<std::vector<Tensor>>(ErrorCode::ENGINE_NOT_INIT,
                                               "MockNpuHal not initialized");
        }

        auto it = loaded_models_.find(handle);
        if (it == loaded_models_.end()) {
            return Error<std::vector<Tensor>>(ErrorCode::MODEL_NOT_LOADED,
                                               "Model not loaded");
        }

        // 模拟 NPU 推理延迟
        simulate_compute_load(inputs);

        // 生成模拟输出
        // 策略：为每个输入生成一个合理大小的输出张量
        // 对于分类模型：输出 (1, 1000) FP32
        // 对于检测模型：输出 (1, 84, 8400) FP32
        // 这里使用简单的启发式
        std::vector<Tensor> outputs;

        if (inputs.empty()) {
            // 无输入 → 返回 dummy 输出
            auto t = Tensor::create({1, 1000}, DType::FLOAT32);
            if (t.ok()) outputs.push_back(std::move(t).value());
        } else {
            // 根据输入形状生成模拟输出
            for (const auto& input : inputs) {
                auto shape = input.shape();
                if (shape.size() >= 2) {
                    // 检测模型风格输出
                    std::vector<std::int64_t> out_shape = {
                        shape[0],
                        static_cast<std::int64_t>(84),
                        static_cast<std::int64_t>(8400)
                    };
                    auto t = Tensor::create(out_shape, DType::FLOAT32);
                    if (t.ok()) outputs.push_back(std::move(t).value());
                } else {
                    // 简单输出
                    auto t = Tensor::create({1, 1000}, DType::FLOAT32);
                    if (t.ok()) outputs.push_back(std::move(t).value());
                }
            }
        }

        // 更新模拟状态
        npu_util_ = std::min(1.0f, npu_util_ + 0.1f);
        temperature_ = std::min(85, temperature_ + 1);
        power_ = 1.5f + npu_util_ * 2.0f;

        // 记录性能数据
        last_profiling_.infer_ms = last_infer_time_ms_;
        last_profiling_.input_bytes = 0;
        last_profiling_.output_bytes = 0;
        for (const auto& t : inputs) {
            last_profiling_.input_bytes += t.meta().num_elements() * dtype_bytes(t.dtype());
        }
        for (const auto& t : outputs) {
            last_profiling_.output_bytes += t.meta().num_elements() * dtype_bytes(t.dtype());
        }
        last_profiling_.npu_utilization = npu_util_;
        last_profiling_.power_w = power_;
        last_profiling_.temperature_c = temperature_;

        return outputs;
    }

    std::future<Result<std::vector<Tensor>>> infer_async(
        NpuModelHandle handle,
        const std::vector<Tensor>& inputs) override {
        // Clone inputs for async execution (Tensor is move-only)
        auto cloned_inputs = std::make_shared<std::vector<Tensor>>();
        cloned_inputs->reserve(inputs.size());
        for (const auto& t : inputs) {
            auto c = t.clone();
            if (c.ok()) cloned_inputs->push_back(std::move(c).value());
        }
        return std::async(std::launch::async,
            [this, handle, cloned_inputs]() {
                return infer(handle, *cloned_inputs);
            });
    }

    Result<std::vector<Tensor>> infer_zero_copy(
        NpuModelHandle handle,
        const std::vector<int>& ion_fds,
        const std::vector<std::vector<std::int64_t>>& shapes,
        const std::vector<DType>& dtypes) override {

        // Mock 零拷贝：将 ION fd 映射到 CPU 内存（模拟）
        std::vector<Tensor> inputs;
        for (std::size_t i = 0; i < ion_fds.size() && i < shapes.size(); ++i) {
            // 在真实环境中：mmap(ion_fds[i], ...) 获取 CPU 指针
            // Mock：创建空白张量
            auto t = Tensor::create(shapes[i],
                                     i < dtypes.size() ? dtypes[i] : DType::FLOAT32);
            if (t.ok()) inputs.push_back(std::move(t).value());
        }

        return infer(handle, inputs);
    }

    // ── 性能剖析 ─────────────────────────────────────────────────────
    std::optional<NpuProfilingData> last_profiling() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        return last_profiling_;
    }

    void reset_profiling() override {
        std::lock_guard<std::mutex> lock(mutex_);
        last_profiling_ = NpuProfilingData{};
    }

    // ── 电源管理 ─────────────────────────────────────────────────────
    Result<void> set_power_mode(int mode) override {
        std::lock_guard<std::mutex> lock(mutex_);
        config_.power_mode = mode;

        switch (mode) {
            case 0: // balanced
                power_ = 1.0f;
                break;
            case 1: // high_performance
                power_ = 3.0f;
                break;
            case 2: // power_saver
                power_ = 0.3f;
                break;
            default:
                return Error(ErrorCode::INVALID_ARGUMENT,
                             "Invalid power mode: " + std::to_string(mode));
        }

        spdlog::info("MockNpuHal power mode set to {}", mode);
        return Ok();
    }

    std::optional<int> get_temperature() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        return temperature_;
    }

    // ── 诊断 ─────────────────────────────────────────────────────────
    std::string diagnostic_info() const override {
        std::lock_guard<std::mutex> lock(mutex_);
        return "{"
               "\"vendor\": \"Mock\","
               "\"chip\": \"Mock-NPU-v1.0\","
               "\"initialized\": " + std::string(initialized_ ? "true" : "false") + ","
               "\"loaded_models\": " + std::to_string(loaded_models_.size()) + ","
               "\"temperature_c\": " + std::to_string(temperature_) + ","
               "\"utilization\": " + std::to_string(npu_util_) + ","
               "\"power_w\": " + std::to_string(power_) +
               "}";
    }

private:
    struct LoadedModel {
        std::string name;
        std::vector<std::uint8_t> data;
        std::size_t data_size{0};
    };

    void simulate_compute_load(const std::vector<Tensor>& inputs) {
        // 模拟推理延迟：基于输入大小计算
        std::size_t total_elements = 0;
        for (const auto& t : inputs) {
            total_elements += t.meta().num_elements();
        }

        // 基准：1M 元素 ≈ 1ms（模拟 ~1 TOPS NPU）
        double base_ms = static_cast<double>(total_elements) / 1'000'000.0;
        base_ms = std::max(0.1, std::min(base_ms, 100.0));  // clamp [0.1ms, 100ms]

        // 添加随机噪声（模拟真实硬件波动）
        static thread_local std::mt19937 rng(std::random_device{}());
        std::normal_distribution<double> noise(0.0, base_ms * 0.05);  // 5% 噪声
        double jitter = noise(rng);

        last_infer_time_ms_ = base_ms + jitter;
    }

    mutable std::mutex mutex_;
    NpuConfig config_;
    bool initialized_{false};

    std::unordered_map<NpuModelHandle, LoadedModel> loaded_models_;
    std::uint64_t next_handle_{1};

    // 模拟硬件状态
    float npu_util_{0.0f};
    int temperature_{45};
    float power_{0.5f};

    // 性能记录
    NpuProfilingData last_profiling_;
    double last_infer_time_ms_{0.0};
};

// ── 导出符号（供 NpuHalLoader 动态加载）─────────────────────────────
extern "C" {

NpuHal* create_qoocore_npu_hal() {
    spdlog::info("Creating MockNpuHal instance");
    return new MockNpuHal();
}

void destroy_qoocore_npu_hal(NpuHal* hal) {
    spdlog::info("Destroying MockNpuHal instance");
    delete hal;
}

}  // extern "C"

}  // namespace qoocore
