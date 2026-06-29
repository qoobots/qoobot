/**
 * @file backend.h
 * @brief 硬件后端抽象接口 — 所有推理后端的统一抽象
 *
 * 后端是推理引擎与具体硬件之间的桥梁：
 *   - NPUBackend  → 神经网络加速芯片
 *   - GPUBackend   → CUDA / OpenCL / Vulkan
 *   - DSPBackend   → Hexagon / CEVA
 *   - CPUBackend   → ARM Neon / x86 AVX512
 *
 * 所有后端实现此接口，推理引擎通过 BackendPtr 动态调度。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "core.h"
#include "tensor.h"

#include <future>
#include <memory>
#include <string>
#include <vector>

namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  BackendCapabilities — 后端能力描述
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 描述一个后端的计算能力和限制。
 *
 * 推理引擎根据此结构选择合适后端（或 fallback）。
 */
struct BackendCapabilities {
    BackendType type{BackendType::AUTO};

    // 计算能力
    float peak_tops{0.0f};           ///< 峰值算力（TOPS）
    std::size_t max_memory_bytes{0};  ///< 最大可用内存（字节）
    int max_concurrent_models{1};     ///< 最大并发模型数

    // 支持的精度
    bool supports_fp32{false};
    bool supports_fp16{false};
    bool supports_int8{false};
    bool supports_int4{false};

    // 特殊能力
    bool supports_zero_copy{false};    ///< 支持 ION/DMA-BUF 零拷贝
    bool supports_async{false};        ///< 支持异步推理
    bool supports_dynamic_batch{false};
    bool supports_perf_hint{false};   ///< 支持性能模式提示

    // 限制
    std::size_t max_tensor_dims{8};   ///< 最大张量维度
    std::size_t max_input_count{16};  ///< 最大输入张量数
    std::size_t max_output_count{16}; ///< 最大输出张量数

    // 性能特征（典型值，用于调度决策）
    double typical_latency_ms{0.0};    ///< 典型模型推理延迟
    double typical_power_w{0.0};       ///< 典型功耗（瓦特）
};

// ─────────────────────────────────────────────────────────────────────────────
//  BackendConfig — 后端配置
// ─────────────────────────────────────────────────────────────────────────────
struct BackendConfig {
    // 通用配置
    std::size_t max_memory_bytes{0}; ///< 0 = 使用后端默认值
    int priority{0};                 ///< 调度优先级（-10 ~ 10，越高越优先）
    bool enable_profiling{false};

    // 性能模式
    enum class PerformanceMode {
        BALANCED,        ///< 平衡模式
        HIGH_PERFORMANCE, ///< 高性能模式（最高频率）
        POWER_SAVER,     ///< 省电模式（降频）
    };
    PerformanceMode perf_mode{PerformanceMode::BALANCED};

    // NPU 特定
    struct {
        int power_level{0}; ///< 0-3，NPU 功耗等级
        bool use_hw_quant{true}; ///< 使用硬件量化单元
    } npu;

    // GPU 特定
    struct {
        std::size_t cuda_streams{1}; ///< CUDA 流数（并发 kernel）
        bool allow_fp16_acc{true};   ///< 允许 FP16 累积
    } gpu;

    // CPU 特定
    struct {
        int num_threads{0}; ///< 0 = 自动检测
        bool use_simd{true};
    } cpu;
};

// ─────────────────────────────────────────────────────────────────────────────
//  Backend — 后端抽象基类
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 所有硬件后端的抽象基类。
 *
 * 设计要点：
 *   - 纯虚接口，具体后端（NPU/GPU/DSP/CPU）override 对应方法
 *   - 支持同步和异步推理
 *   - 支持零拷贝（ION/DMA-BUF）
 *   - 线程安全：load_model / infer 可并发调用（具体后端需保证）
 */
class Backend {
public:
    virtual ~Backend() = default;

    // ── 后端元信息 ─────────────────────────────────────────────────────
    /** @brief 返回后端类型。 */
    virtual BackendType type() const noexcept = 0;

    /** @brief 返回后端名称（如 "qnn", "cuda", "hexagon"）。 */
    virtual std::string name() const noexcept = 0;

    /** @brief 返回后端能力描述。 */
    virtual BackendCapabilities capabilities() const = 0;

    // ── 生命周期 ───────────────────────────────────────────────────────
    /** @brief 初始化后端（分配硬件资源）。 */
    virtual Result<void> init(const BackendConfig& config = {}) = 0;

    /** @brief 关闭后端（释放硬件资源）。 */
    virtual void deinit() = 0;

    /** @brief 是否已初始化。 */
    virtual bool is_initialized() const noexcept = 0;

    // ── 模型管理 ───────────────────────────────────────────────────────
    /**
     * @brief 加载编译后的模型。
     * @param model_data  编译后的模型二进制（.qoomodel 中 Compiled Model 段）
     * @return 模型句柄（用于后续 infer / unload）
     */
    virtual Result<std::uint64_t> load_model(
        const std::vector<std::uint8_t>& model_data,
        const std::optional<ModelInfo>& info = std::nullopt) = 0;

    /**
     * @brief 卸载模型。
     * @param model_handle  load_model 返回的句柄
     */
    virtual Result<void> unload_model(std::uint64_t model_handle) = 0;

    /**
     * @brief 查询已加载模型数量。
     */
    virtual std::size_t loaded_model_count() const = 0;

    // ── 推理 ───────────────────────────────────────────────────────────
    /**
     * @brief 同步推理。
     * @param model_handle  模型句柄
     * @param inputs        输入张量（数量/形状/类型需与模型匹配）
     * @return 输出张量列表
     */
    virtual Result<std::vector<Tensor>> infer(
        std::uint64_t model_handle,
        const std::vector<Tensor>& inputs) = 0;

    /**
     * @brief 异步推理。
     * @return Future，推理完成后返回结果
     */
    virtual std::future<Result<std::vector<Tensor>>> infer_async(
        std::uint64_t model_handle,
        const std::vector<Tensor>& inputs) = 0;

    /**
     * @brief 批量推理（动态批处理）。
     * @param batch_inputs  批量输入，每个元素是一个 batch 的输入张量列表
     */
    virtual Result<std::vector<std::vector<Tensor>>> infer_batch(
        std::uint64_t model_handle,
        const std::vector<std::vector<Tensor>>& batch_inputs) = 0;

    // ── 零拷贝推理（可选实现）────────────────────────────────────────
    /**
     * @brief 使用 ION/DMA-BUF 文件描述符进行零拷贝推理。
     * @param ion_fds  每个输入张量对应的 ION 文件描述符
     *
     * 默认实现：将 ION 内存映射到普通内存，再调用 infer()。
     * 具体后端可 override 以实现真正的零拷贝。
     */
    virtual Result<std::vector<Tensor>> infer_zero_copy(
        std::uint64_t model_handle,
        const std::vector<int>& ion_fds) {
        (void)model_handle;
        (void)ion_fds;
        return Error<std::vector<Tensor>>(ErrorCode::NOT_IMPLEMENTED,
                     "Zero-copy inference not supported by " + name());
    }

    // ── 性能剖析 ───────────────────────────────────────────────────────
    /** @brief 返回最近一次推理的性能数据。 */
    virtual std::optional<ProfilingInfo> last_profiling() const {
        return std::nullopt;
    }

    /** @brief 重置性能计数器。 */
    virtual void reset_profiling() {}

    // ── 诊断 ───────────────────────────────────────────────────────────
    /** @brief 返回后端特定诊断信息（JSON 字符串）。 */
    virtual std::string diagnostic_info() const { return "{}"; }
};

using BackendPtr = std::shared_ptr<Backend>;

// ─────────────────────────────────────────────────────────────────────────────
//  BackendRegistry — 后端注册表（工厂模式）
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 全局后端注册表，支持运行时动态注册/创建后端。
 *
 * 用法：
 * ```cpp
 * // 注册后端创建函数
 * BackendRegistry::instance().register_factory(
 *     BackendType::NPU, "qnn",
 *     [](const BackendConfig& cfg) -> BackendPtr {
 *         return std::make_shared<QnnBackend>(cfg);
 *     });
 *
 * // 创建后端
 * auto backend = BackendRegistry::instance().create(BackendType::NPU, "qnn");
 * ```
 */
class BackendRegistry {
public:
    using Factory = std::function<BackendPtr(const BackendConfig&)>;

    static BackendRegistry& instance();

    /**
     * @brief 注册后端工厂。
     * @param type      后端类型
     * @param name      后端名称（如 "qnn", "cuda"）
     * @param factory   创建函数
     */
    void register_factory(BackendType type,
                          const std::string& name,
                          Factory factory);

    /**
     * @brief 创建后端实例。
     * @param type  后端类型（AUTO 时自动选择）
     * @param name  指定名称（空 = 使用默认）
     * @param config 后端配置
     * @return 后端实例，失败返回 nullptr
     */
    BackendPtr create(BackendType type,
                       const std::string& name = "",
                       const BackendConfig& config = {});

    /**
     * @brief 列出所有已注册的后端。
     */
    std::vector<std::pair<BackendType, std::string>> list() const;

    /**
     * @brief 探测并注册系统上可用的后端（自动检测）。
     */
    Result<void> probe_and_register();

private:
    BackendRegistry() = default;
    std::unordered_map<BackendType,
                       std::unordered_map<std::string, Factory>> factories_;
};

} // namespace qoocore
