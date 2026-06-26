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

        // 1. 创建 QNN Backend
        //    完整实现：QnnBackend_createFromBinary()
        //    此处为桩：记录配置
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

        spdlog::info("[QNN HAL] Initialized. Peak TOPS(FP16)={}",
                       caps_.peak_tops_fp16);
        return Ok;
    }

    void deinit() override {
        if (!initialized_) return;
        // TODO: 释放 QNN 资源
        for (auto& [handle, _] : loaded_models_) {
            // QnnGraph_destroy(graph);
        }
        loaded_models_.clear();
        initialized_ = false;
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

        // TODO: 完整实现
        //   1. QnnGraph_createFromBinary()
        //   2. QnnGraph_finalize()
        //   3. 返回 graph handle

        // 桩实现：返回伪句柄
        NpuModelHandle handle = reinterpret_cast<NpuModelHandle>(
            static_cast<std::uintptr_t>(next_handle_++));
        loaded_models_[handle] = model_name;

        spdlog::info("[QNN HAL] Model loaded, handle={}",
                       reinterpret_cast<std::uintptr_t>(handle));
        return handle;
    }

    Result<void> unload_model(NpuModelHandle handle) override {
        auto it = loaded_models_.find(handle);
        if (it == loaded_models_.end()) {
            return Error(ErrorCode::INVALID_ARGUMENT,
                         "Invalid model handle");
        }
        // TODO: QnnGraph_destroy(graph);
        loaded_models_.erase(it);
        spdlog::info("[QNN HAL] Model unloaded");
        return Ok;
    }

    std::size_t loaded_model_count() const override {
        return loaded_models_.size();
    }

    // ── 推理 ──────────────────────────────────────────────────────
    Result<std::vector<Tensor>> infer(
        NpuModelHandle handle,
        const std::vector<Tensor>& inputs) override {

        if (loaded_models_.find(handle) == loaded_models_.end()) {
            return Error(ErrorCode::INVALID_ARGUMENT, "Invalid model handle");
        }

        // TODO: 完整实现
        //   1. 将 inputs 写入 QNN Tensor
        //   2. QnnGraph_execute()
        //   3. 读取 outputs

        // 桩实现：返回空输出列表
        spdlog::debug("[QNN HAL] infer() called (stub)");
        return std::vector<Tensor>{};
    }

    // ── 电源管理 ──────────────────────────────────────────────────
    Result<void> set_power_mode(int mode) override {
        caps_.max_power_w = (mode == 1) ? 5.0f : 2.0f;
        spdlog::info("[QNN HAL] Power mode set to {}", mode);
        return Ok;
    }

    std::optional<int> get_temperature() const override {
        // TODO: 读取 NPU 温度（通过 QNN 或 sysfs）
        return std::nullopt;
    }

    // ── 诊断 ──────────────────────────────────────────────────────
    std::string diagnostic_info() const override {
        return R"({"hal":"qnn","initialized":)" +
               std::string(initialized_ ? "true" : "false") +
               R"(,"loaded_models":)" +
               std::to_string(loaded_models_.size()) + "}";
    }

private:
    NpuConfig config_;
    NpuCapabilities caps_;
    bool initialized_{false};
    std::uint64_t next_handle_{1};
    std::unordered_map<NpuModelHandle, std::string> loaded_models_;
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
