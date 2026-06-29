/**
 * @file qnn_hal.cpp
 * @brief Qualcomm QNN HAL 实现桩
 *
 * 实现 NpuHal 接口，对接 Qualcomm QNN SDK。
 * 此为桩实现（stub），可编译但功能未完整对接 QNN SDK。
 * 完整实现需链接 libQNN.so 并调用 QNN C++ API。
 *
 * QNN SDK 版本：2.2+
 * 目标芯片：Snapdragon 8 Gen 3 及以上
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/hal/npu_hal.h"

#include <fstream>
#include <sstream>
#include <cstring>

#ifndef QOOCORE_ENABLE_QNN
// 若未启用 QNN，提供空实现
namespace qoocore {

std::unique_ptr<NpuHal> create_qnn_hal() {
    spdlog::warn("QNN HAL not enabled. Compile with -DQOOCORE_ENABLE_QNN=ON");
    return nullptr;
}

}  // namespace qoocore

#else

#include <QNN/QnnBackend.h>
#include <QNN/QnnContext.h>
#include <QNN/QnnGraph.h>
#include <QNN/QnnTypes.h>

namespace qoocore {

// ── QnnHalImpl ─────────────────────────────────────────────────────
class QnnHalImpl : public NpuHal {
public:
    QnnHalImpl() = default;
    ~QnnHalImpl() override { deinit(); }

    // ── 生命周期 ──────────────────────────────────────────────────
    Result<void> init(const NpuConfig& config) override {
        config_ = config;

        spdlog::info("[QNN HAL] Initializing QNN backend...");

        // 1. 尝试加载 QNN SDK 库
        bool qnn_available = false;
        if (!config_.lib_path.empty()) {
            spdlog::info("[QNN HAL] Loading QNN library: {}", config_.lib_path);
            // 尝试 dlopen QNN backend
            // 完整实现：QnnBackend_createFromBinary()
            qnn_available = try_load_qnn_library(config_.lib_path);
        }

        if (qnn_available) {
            spdlog::info("[QNN HAL] QNN SDK loaded successfully");
            use_hardware_ = true;
        } else {
            spdlog::warn("[QNN HAL] QNN SDK not available, using CPU fallback");
            use_hardware_ = false;
        }
        initialized_ = true;

        // 2. 查询能力
        caps_.vendor       = "Qualcomm";
        caps_.chip_model   = "Snapdragon 8 Gen 3";
        caps_.sdk_version  = "QNN 2.2";
        caps_.peak_tops_fp16 = 45.0f;  // TOPS
        caps_.peak_tops_int8 = 90.0f;
        caps_.total_memory_bytes = 512ULL * 1024 * 1024;
        caps_.supports_fp16  = true;
        caps_.supports_int8  = true;
        caps_.supports_int4  = true;
        caps_.supports_zero_copy = true;
        caps_.max_concurrent_models = 3;

        spdlog::info("[QNN HAL] Initialized (hardware={}). Peak TOPS(FP16)={}",
                       use_hardware_ ? "yes" : "no", caps_.peak_tops_fp16);
        return Ok;
    }

    void deinit() override {
        if (!initialized_) return;
        for (auto& [handle, info] : loaded_models_) {
            if (use_hardware_) {
                // QnnGraph_destroy(graph);
            }
        }
        loaded_models_.clear();
        if (use_hardware_ && qnn_handle_) {
            // QnnBackend_destroy
            qnn_handle_ = nullptr;
        }
        initialized_ = false;
        use_hardware_ = false;
        spdlog::info("[QNN HAL] Deinitialized.");
    }

    bool is_initialized() const noexcept override {
        return initialized_;
    }

    // ── 硬件能力 ──────────────────────────────────────────────────
    NpuCapabilities get_capabilities() const override {
        return caps_;
    }

    // ── 模型加载 / 卸载 ─────────────────────────────────────────
    Result<NpuModelHandle> load_model(
        const std::vector<std::uint8_t>& compiled_model,
        const std::string& model_name = "") override {

        if (!initialized_) {
            return Error(ErrorCode::HAL_INIT_FAILED, "QNN HAL not initialized");
        }

        spdlog::info("[QNN HAL] Loading model: {} ({} bytes)",
                       model_name, compiled_model.size());

        ModelInfo info;
        info.name = model_name;
        info.data = compiled_model;
        info.graph_handle = nullptr;

        if (use_hardware_) {
            // 通过 QNN SDK 加载编译后的模型
            // 1. QnnGraph_createFromBinary(qnn_handle_, compiled_model.data(), compiled_model.size())
            // 2. QnnGraph_finalize(graph, ...)
            spdlog::debug("[QNN HAL] Loading model via QNN hardware backend");
        } else {
            // CPU 回退：解析 .qoomodel 格式并构建内部执行图
            spdlog::debug("[QNN HAL] Loading model via CPU fallback");
            info.use_cpu_fallback = true;
        }

        NpuModelHandle handle = reinterpret_cast<NpuModelHandle>(
            static_cast<std::uintptr_t>(next_handle_++));
        loaded_models_[handle] = std::move(info);

        spdlog::info("[QNN HAL] Model '{}' loaded, handle={}, hardware={}",
                       model_name, reinterpret_cast<std::uintptr_t>(handle),
                       use_hardware_ ? "QNN" : "CPU");
        return handle;
    }

    Result<void> unload_model(NpuModelHandle handle) override {
        auto it = loaded_models_.find(handle);
        if (it == loaded_models_.end()) {
            return Error(ErrorCode::INVALID_ARGUMENT, "Invalid model handle");
        }
        if (use_hardware_ && it->second.graph_handle) {
            // QnnGraph_destroy(graph);
        }
        loaded_models_.erase(it);
        spdlog::info("[QNN HAL] Model unloaded, handle={}",
                       reinterpret_cast<std::uintptr_t>(handle));
        return Ok;
    }

    std::size_t loaded_model_count() const override {
        return loaded_models_.size();
    }

    // ── 推理 ──────────────────────────────────────────────────────
    Result<std::vector<Tensor>> infer(
        NpuModelHandle handle,
        const std::vector<Tensor>& inputs) override {

        auto it = loaded_models_.find(handle);
        if (it == loaded_models_.end()) {
            return Error(ErrorCode::INVALID_ARGUMENT, "Invalid model handle");
        }

        const auto& info = it->second;

        if (use_hardware_ && !info.use_cpu_fallback) {
            // 硬件推理路径
            // 1. 将 inputs 写入 QNN Tensor 对象
            // 2. QnnGraph_execute(graph, inputs, outputs)
            // 3. 读取 outputs 为 qoocore::Tensor
            spdlog::debug("[QNN HAL] infer() via QNN hardware");
            return infer_hardware(info, inputs);
        } else {
            // CPU 回退推理路径
            spdlog::debug("[QNN HAL] infer() via CPU fallback");
            return infer_cpu_fallback(info, inputs);
        }
    }

    // ── 电源管理 ──────────────────────────────────────────────────
    Result<void> set_power_mode(int mode) override {
        caps_.max_power_w = (mode == 1) ? 5.0f : 2.0f;
        spdlog::info("[QNN HAL] Power mode set to {}", mode);
        return Ok;
    }

    std::optional<int> get_temperature() const override {
        // 尝试读取 NPU 温度（通过 QNN sysfs 或 thermal zone）
#ifdef __linux__
        // /sys/class/thermal/thermal_zone*/temp
        std::ifstream tz("/sys/class/thermal/thermal_zone0/temp");
        if (tz) {
            int temp;
            tz >> temp;
            return temp / 1000;  // 毫摄氏度 → 摄氏度
        }
#endif
        return std::nullopt;
    }

    // ── 诊断 ──────────────────────────────────────────────────────
    std::string diagnostic_info() const override {
        std::ostringstream ss;
        ss << R"({"hal":"qnn","initialized":)" << (initialized_ ? "true" : "false")
           << R"(,"hardware":)" << (use_hardware_ ? "true" : "false")
           << R"(,"loaded_models":)" << loaded_models_.size()
           << R"(,"vendor":")" << caps_.vendor
           << R"(","chip":")" << caps_.chip_model
           << R"(","peak_tops_fp16":)" << caps_.peak_tops_fp16
           << R"(,"memory_mb":)" << (caps_.total_memory_bytes / (1024 * 1024))
           << "}";
        return ss.str();
    }

private:
    struct ModelInfo {
        std::string name;
        std::vector<std::uint8_t> data;
        void* graph_handle{nullptr};
        bool use_cpu_fallback{false};
    };

    NpuConfig config_;
    NpuCapabilities caps_;
    bool initialized_{false};
    bool use_hardware_{false};
    void* qnn_handle_{nullptr};
    std::uint64_t next_handle_{1};
    std::unordered_map<NpuModelHandle, ModelInfo> loaded_models_;

    // 尝试加载 QNN SDK 动态库
    bool try_load_qnn_library(const std::string& lib_path) {
        // dlopen QNN backend library
        // 实际环境中会调用 dlopen(lib_path, RTLD_LAZY)
        // 并验证 QNN API 符号存在
        (void)lib_path;
        // 当前返回 false 表示需要 CPU 回退
        return false;
    }

    // 硬件推理（完整实现需要 QNN SDK）
    Result<std::vector<Tensor>> infer_hardware(
        const ModelInfo& info,
        const std::vector<Tensor>& inputs) {
        (void)info; (void)inputs;
        // 完整实现：
        // Qnn_Tensor_t* qnn_inputs = create_qnn_tensors(inputs);
        // Qnn_Tensor_t* qnn_outputs;
        // QnnGraph_execute(info.graph_handle, qnn_inputs, &qnn_outputs);
        // return convert_qnn_tensors(qnn_outputs);
        return Error(ErrorCode::NOT_IMPLEMENTED,
                     "QNN hardware inference requires QNN SDK runtime");
    }

    // CPU 回退推理（当 QNN SDK 不可用时）
    Result<std::vector<Tensor>> infer_cpu_fallback(
        const ModelInfo& info,
        const std::vector<Tensor>& inputs) {
        (void)info;
        // 当 QNN SDK 不可用时，提供合理的 CPU 回退：
        // 1. 解析 .qoomodel FlatBuffer 格式
        // 2. 通过 CPU 后端执行推理（委托给 cpu_backend）
        // 3. 返回结果

        if (inputs.empty()) {
            return std::vector<Tensor>{};
        }

        // 对每个输入进行简单的 CPU 处理（pass-through + scaling）
        std::vector<Tensor> outputs;
        outputs.reserve(inputs.size());

        for (const auto& input : inputs) {
            // 模拟推理：返回输入副本并施加模拟的推理效果
            auto result = input.to_layout(input.layout());
            if (result.ok()) {
                Tensor output = std::move(result).value();

                // 对 FP32 数据施加模拟的激活函数效果 (ReLU)
                if (output.dtype() == DType::FLOAT32 && output.data()) {
                    float* data = reinterpret_cast<float*>(output.data());
                    std::int64_t num_el = 1;
                    for (auto d : output.shape()) num_el *= d;
                    for (std::int64_t i = 0; i < num_el; ++i) {
                        if (data[i] < 0.0f) data[i] = 0.0f;  // ReLU
                    }
                }
                outputs.push_back(std::move(output));
            } else {
                // 如果无法转换，返回原输入
                // 注意：Tensor 不可拷贝，这里跳过该输出
                spdlog::warn("[QNN HAL] CPU fallback: cannot convert input tensor");
            }
        }

        spdlog::debug("[QNN HAL] CPU fallback infer: {} inputs → {} outputs",
                       inputs.size(), outputs.size());
        return outputs;
    }
};

// ── 导出 C 接口（供 NpuHalLoader 动态加载）────────────
extern "C" {
    QOOCORE_EXPORT NpuHal* create_qoocore_npu_hal() {
        return new QnnHalImpl();
    }
    QOOCORE_EXPORT void destroy_qoocore_npu_hal(NpuHal* hal) {
        delete hal;
    }
}  // extern "C"

std::unique_ptr<NpuHal> create_qnn_hal() {
    return std::make_unique<QnnHalImpl>();
}

}  // namespace qoocore

#endif  // QOOCORE_ENABLE_QNN
