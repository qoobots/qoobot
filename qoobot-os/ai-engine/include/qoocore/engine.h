/**
 * @file engine.h
 * @brief 统一推理引擎 — qoocore 的核心 API
 *
 * InferenceEngine 是 qoocore 的入口点：
 *   - 单例模式（进程内唯一）
 *   - 管理多个后端（NPU/GPU/DSP/CPU 并发）
 *   - 自动模型加载/卸载、后端选择、推理调度
 *   - 支持同步/异步/批量推理
 *
 * 线程安全：所有 public 方法均可并发调用。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "backend.h"
#include "compiler.h"  // 前向声明：Compiler 接口
#include "config.h"
#include "core.h"
#include "tensor.h"

#include <future>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  EngineConfig — 推理引擎配置
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 推理引擎的全局配置。
 */
struct EngineConfig {
    // 后端选择
    std::vector<BackendType> allowed_backends{
        BackendType::NPU,
        BackendType::GPU,
        BackendType::CPU,
    };
    BackendType default_backend{BackendType::AUTO}; ///< AUTO = 根据模型自动选择

    // 内存限制
    std::size_t max_total_memory_bytes{
        2ULL * 1024 * 1024 * 1024}; ///< 2GB，多模型共享

    // 并发控制
    bool enable_multi_model{true};  ///< 允许多模型并发
    std::size_t max_loaded_models{8};

    // 性能剖析
    bool enable_profiling{false};
    std::optional<std::string> profile_log_path; ///< 剖析日志路径（空=标准输出）

    // 日志
    std::string log_level{"info"}; ///< "trace"|"debug"|"info"|"warn"|"error"

    // 零拷贝
    bool enable_zero_copy{true}; ///< 优先使用 ION/DMA-BUF

    // 异步推理线程池
    std::size_t async_threads{4}; ///< 异步推理线程数（0=自动）

    // CPU 回退
    bool enable_cpu_fallback{true}; ///< 当首选后端不可用时，回退到 CPU
};

// ─────────────────────────────────────────────────────────────────────────────
//  ModelConfig — 单模型配置
// ─────────────────────────────────────────────────────────────────────────────
struct ModelConfig {
    // 后端偏好
    std::optional<BackendType> preferred_backend;

    // 零拷贝
    bool enable_zero_copy{true};

    // 动态批处理
    bool enable_dynamic_batch{false};
    std::size_t max_batch_size{1};

    // 性能提示
    enum class Priority {
        REALTIME,  ///< 最低延迟（机器人控制）
        HIGH,       ///< 高优先级（感知）
        NORMAL,     ///< 普通（日志、诊断）
        LOW,        ///< 低优先级（后台任务）
    };
    Priority priority{Priority::NORMAL};

    // 超时（毫秒，0 = 无限）
    std::chrono::milliseconds timeout{0};
};

// ─────────────────────────────────────────────────────────────────────────────
//  ModelHandle — 模型句柄（引擎内唯一）
// ─────────────────────────────────────────────────────────────────────────────
using ModelHandle = std::uint64_t;
static constexpr ModelHandle INVALID_MODEL_HANDLE = 0;

// ─────────────────────────────────────────────────────────────────────────────
//  InferenceEngine — 统一推理引擎
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief qoocore 的统一推理引擎。
 *
 * 典型用法：
 * ```cpp
 * // 1. 初始化
 * auto& engine = InferenceEngine::instance();
 * engine.init(EngineConfig{});
 *
 * // 2. 加载模型
 * auto handle = engine.load_model("yolov11n.qoomodel");
 *
 * // 3. 推理
 * Tensor input = Tensor::create({1, 3, 640, 640}, DType::UINT8);
 * // ... 填充 input 数据 ...
 * auto output = engine.infer(handle, input);
 *
 * // 4. 卸载
 * engine.unload_model(handle);
 *
 * // 5. 关闭
 * engine.shutdown();
 * ```
 */
class InferenceEngine {
public:
    // ── 单例 ─────────────────────────────────────────────────────────────
    static InferenceEngine& instance();

    // 禁止拷贝/移动
    InferenceEngine(const InferenceEngine&) = delete;
    InferenceEngine& operator=(const InferenceEngine&) = delete;

    ~InferenceEngine();

    // ── 引擎生命周期 ───────────────────────────────────────────────────
    /**
     * @brief 初始化推理引擎。
     * @param config  全局配置（使用默认值如合适）
     * @return 成功或错误
     *
     * 此函数：
     *   1. 探测可用硬件（NPU/GPU/DSP/CPU）
     *   2. 注册并初始化可用后端
     *   3. 启动异步推理线程池
     *   4. 初始化内存池
     */
    Result<void> init(const EngineConfig& config = {});

    /**
     * @brief 关闭推理引擎，释放所有资源。
     */
    void shutdown();

    /**
     * @brief 是否已初始化。
     */
    [[nodiscard]] bool is_initialized() const noexcept;

    /**
     * @brief 返回当前配置。
     */
    [[nodiscard]] const EngineConfig& config() const noexcept;

    // ── 模型管理 ───────────────────────────────────────────────────────
    /**
     * @brief 加载 .qoomodel 模型文件。
     * @param qoomodel_path  .qoomodel 文件路径
     * @param model_config   模型特定配置
     * @return 模型句柄（用于后续 infer / unload）
     */
    Result<ModelHandle> load_model(
        const std::string& qoomodel_path,
        const ModelConfig& model_config = {});

    /**
     * @brief 从内存缓冲区加载模型（用于 OTA / 加密模型）。
     */
    Result<ModelHandle> load_model_from_buffer(
        const std::vector<std::uint8_t>& buffer,
        const ModelConfig& model_config = {});

    /**
     * @brief 卸载模型，释放占用的硬件资源。
     */
    Result<void> unload_model(ModelHandle handle);

    /**
     * @brief 卸载所有模型。
     */
    void unload_all_models();

    /**
     * @brief 查询模型元信息。
     */
    Result<ModelInfo> get_model_info(ModelHandle handle) const;

    /**
     * @brief 列出所有已加载模型句柄。
     */
    [[nodiscard]] std::vector<ModelHandle> list_loaded_models() const;

    // ── 推理 ───────────────────────────────────────────────────────────
    /**
     * @brief 同步推理（单输入 → 单输出）。
     * @note 若模型有多个输入，使用 infer_multi_input。
     */
    Result<Tensor> infer(ModelHandle handle, const Tensor& input);

    /**
     * @brief 同步推理（多输入 → 多输出）。
     */
    Result<std::vector<Tensor>> infer_multi_input(
        ModelHandle handle,
        const std::vector<Tensor>& inputs);

    /**
     * @brief 异步推理。
     * @return Future，可 .get() 等待结果
     */
    std::future<Result<Tensor>> infer_async(ModelHandle handle,
                                             Tensor input);

    /**
     * @brief 异步推理（多输入）。
     */
    std::future<Result<std::vector<Tensor>>> infer_async_multi_input(
        ModelHandle handle,
        std::vector<Tensor> inputs);

    /**
     * @brief 批量推理（动态批处理）。
     * @param batch_inputs 批量输入，每个元素是一个样本的输入张量列表
     */
    Result<std::vector<std::vector<Tensor>>> infer_batch(
        ModelHandle handle,
        const std::vector<std::vector<Tensor>>& batch_inputs);

    /**
     * @brief 多模型并发推理（自动调度到不同后端）。
     * @param requests  {模型句柄, 输入张量} 列表
     * @return         按相同顺序排列的输出
     */
    Result<std::vector<std::vector<Tensor>>> infer_multi_model(
        const std::vector<std::pair<ModelHandle, std::vector<Tensor>>>& requests);

    // ── 后端管理 ───────────────────────────────────────────────────────
    /**
     * @brief 注册自定义后端。
     */
    Result<void> register_backend(BackendPtr backend);

    /**
     * @brief 列出当前可用的后端。
     */
    [[nodiscard]] std::vector<BackendType> list_available_backends() const;

    /**
     * @brief 返回指定后端的引用（用于高级用法）。
     */
    Result<BackendPtr> get_backend(BackendType type) const;

    // ── 编译（可选，若需运行时编译）─────────────────────────────────
    /**
     * @brief 返回编译器接口（用于模型编译）。
     */
    [[nodiscard]] ModelCompiler* compiler();

    // ── 性能剖析 ───────────────────────────────────────────────────────
    /**
     * @brief 返回性能剖析报告（JSON 字符串）。
     * @note Profiler 子系统尚未实现，此处返回空串占位。
     */
    std::string profiling_summary() const;

    /**
     * @brief 导出所有模型的性能报告（JSON）。
     */
    Result<std::string> export_profiling_report() const;

    // ── 诊断 ───────────────────────────────────────────────────────────
    /**
     * @brief 返回引擎状态摘要（JSON 字符串，用于 Web 仪表盘）。
     */
    std::string status_json() const;

private:
    InferenceEngine() = default;

    // 内部实现（Pimpl 模式，减少头文件依赖）
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoocore
