/**
 * @file npu_hal.h
 * @brief NPU 硬件抽象层接口 — 插件化 NPU 后端的基础
 *
 * HAL（Hardware Abstraction Layer）使得 qoocore 可支持多家 NPU 厂商：
 *   - Qualcomm Snapdragon（QNN SDK）
 *   - Horizon Journey（BPU SDK）
 *   - Rockchip RK3588（RKNN SDK）
 *   - 未来：NVIDIA Thor、MediaTek Dimensity 等
 *
 * 各厂商实现 NpuHal 纯虚接口，编译为独立 .so/.dll，
 * qoocore 运行时动态加载（dlopen/LoadLibrary）。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <future>
#include <memory>
#include <string>
#include <vector>

namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  NpuConfig — NPU 初始化配置
// ─────────────────────────────────────────────────────────────────────────────
struct NpuConfig {
    std::string device_name;          ///< 设备名称（如 "/dev/npu0"）
    int power_mode{0};                ///< 0=balanced, 1=high_performance, 2=power_saver
    std::size_t max_memory_bytes{     ///< NPU DDR 最大可用字节数
        512ULL * 1024 * 1024};     ///< 默认 512MB
    bool enable_profiling{false};
    std::optional<std::string> log_path; ///< NPU SDK 日志路径

    // 性能模式参数（Qualcomm QNN 特定）
    struct {
        int context_priority{0};     ///< -1=sensor, 0=normal, 1=high
        bool use_dsp_fallback{true}; ///< NPU 不可用时回退到 DSP
    } qnn;
};

// ─────────────────────────────────────────────────────────────────────────────
//  NpuCapabilities — NPU 硬件能力
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 描述 NPU 硬件的计算能力、内存、支持的精度等。
 *
 * 推理引擎根据此结构选择合适 NPU 后端，或决策是否 fallback 到 GPU/CPU。
 */
struct NpuCapabilities {
    // 厂商信息
    std::string vendor;               ///< "Qualcomm" / "Horizon" / "Rockchip" / ...
    std::string chip_model;           ///< "Snapdragon 8 Gen 3" / "J5" / "RK3588"
    std::string sdk_version;          ///< SDK 版本字符串
    std::string driver_version;        ///< 驱动版本

    // 计算能力
    float peak_tops_fp16{0.0f};   ///< FP16 峰值算力（TOPS）
    float peak_tops_int8{0.0f};    ///< INT8 峰值算力（TOPS）
    float peak_tops_int4{0.0f};    ///< INT4 峰值算力（TOPS）

    // 内存
    std::size_t total_memory_bytes{0};    ///< NPU 专用 DDR 总量
    std::size_t max_model_size_bytes{0};  ///< 单模型最大可加载大小

    // 支持的精度（位掩码）
    bool supports_fp32{false};
    bool supports_fp16{true};        ///< 大多数 NPU 支持 FP16
    bool supports_int8{true};
    bool supports_int4{false};       ///< 新一代 NPU 支持（如 Snapdragon 8 Gen 3）

    // 特殊能力
    bool supports_zero_copy{false};   ///< 支持 ION/DMA-BUF 零拷贝
    bool supports_perf_hint{false};  ///< 支持性能模式 hint
    bool supports_batch{false};       ///< 支持硬件级 batch 推理
    int max_concurrent_models{1};    ///< 最大并发模型数

    // 功耗
    std::optional<float> max_power_w;    ///< 最大功耗（瓦特）
    std::optional<float> typical_power_w; ///< 典型功耗

    // 温度
    std::optional<int> max_temperature_c;  ///< 热节流温度阈值
};

// ─────────────────────────────────────────────────────────────────────────────
//  NpuModelHandle — NPU 模型句柄（厂商 SDK 内部类型擦除）
// ─────────────────────────────────────────────────────────────────────────────
using NpuModelHandle = void*;  ///< 厂商 SDK 模型句柄的不透明指针
static constexpr NpuModelHandle NPU_INVALID_HANDLE = nullptr;

// ─────────────────────────────────────────────────────────────────────────────
//  NpuProfilingData — NPU 推理性能数据
// ─────────────────────────────────────────────────────────────────────────────
struct NpuProfilingData {
    double infer_ms{0.0};           ///< NPU 推理耗时（毫秒）
    std::size_t input_bytes{0};      ///< 输入数据量（字节）
    std::size_t output_bytes{0};     ///< 输出数据量（字节）
    float npu_utilization{0.0f};    ///< NPU 利用率（0.0~1.0）
    std::optional<float> power_w;     ///< 推理期间功耗（瓦特）
    std::optional<int> temperature_c; ///< NPU 温度（摄氏度）
};

// ─────────────────────────────────────────────────────────────────────────────
//  NpuHal — NPU 硬件抽象层接口（纯虚类）
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 所有 NPU 厂商 SDK 的统一抽象接口。
 *
 * 厂商适配步骤：
 *   1. 继承 NpuHal，实现所有纯虚方法
 *   2. 在 npu_hal_loader.cpp 中注册创建函数
 *   3. 编译为独立共享库（如 libqoocore_hal_qnn.so）
 *   4. qoocore 运行时 dlopen 加载
 *
 * 线程安全：init() 必须在其他方法前调用；infer() 可并发。
 */
class NpuHal {
public:
    virtual ~NpuHal() = default;

    // ── 生命周期 ─────────────────────────────────────────────────────────
    /**
     * @brief 初始化 NPU 硬件（打开设备、分配资源）。
     * @param config  初始化配置
     * @return 成功或错误
     *
     * 此函数：
     *   - 打开 NPU 设备文件（如 /dev/npu0）
     *   - 初始化厂商 SDK（如 QNN Backend）
     *   - 查询硬件能力
     *   - 分配命令缓冲区、共享内存等
     */
    virtual Result<void> init(const NpuConfig& config) = 0;

    /**
     * @brief 关闭 NPU，释放所有资源。
     */
    virtual void deinit() = 0;

    /**
     * @brief 是否已初始化。
     */
    virtual bool is_initialized() const noexcept = 0;

    // ── 硬件能力查询 ───────────────────────────────────────────────────
    /**
     * @brief 返回 NPU 硬件能力描述。
     * @note 必须在 init() 后调用。
     */
    virtual NpuCapabilities get_capabilities() const = 0;

    /**
     * @brief 返回 NPU 当前状态（温度、利用率等动态信息）。
     * @note 可选实现，默认返回空 map。
     */
    virtual std::unordered_map<std::string, double> get_dynamic_status() const {
        return {};
    }

    // ── 模型加载 / 卸载 ───────────────────────────────────────────────
    /**
     * @brief 加载编译后的模型二进制到 NPU。
     *
     * @param compiled_model  编译后的模型数据（.qoomodel 中 Compiled Model 段）
     * @param model_name     模型名称（用于日志 / 调试）
     * @return NPU 模型句柄
     *
     * 各厂商实现：
     *   - QNN:  调用 QNN backend_createGraph() 等
     *   - BPU:  调用 HB_UWM_model_load_from_memory()
     *   - RKNN: 调用 rknn_load_model()
     */
    virtual Result<NpuModelHandle> load_model(
        const std::vector<std::uint8_t>& compiled_model,
        const std::string& model_name = "") = 0;

    /**
     * @brief 卸载模型，释放 NPU 内部资源。
     */
    virtual Result<void> unload_model(NpuModelHandle handle) = 0;

    /**
     * @brief 返回已加载模型数量。
     */
    virtual std::size_t loaded_model_count() const = 0;

    // ── 推理 ───────────────────────────────────────────────────────────
    /**
     * @brief 同步推理。
     *
     * @param handle  NPU 模型句柄
     * @param inputs  输入张量列表（数据需在 CPU 内存或 ION 中）
     * @return 输出张量列表
     *
     * 流程：
     *   1. 若输入在 CPU 内存，先拷贝到 NPU 共享内存（或零拷贝 ION）
     *   2. 调用厂商 SDK 执行推理
     *   3. 将 NPU 输出拷贝到 Tensor（CPU 内存）
     *   4. 返回输出张量
     */
    virtual Result<std::vector<Tensor>> infer(
        NpuModelHandle handle,
        const std::vector<Tensor>& inputs) = 0;

    /**
     * @brief 异步推理（底层可能使用 NPU 硬件队列）。
     *
     * 默认实现：在独立线程中调用同步 infer()。
     * 具体 HAL 可 override 以使用硬件异步接口（如 QNN async execute）。
     */
    virtual std::future<Result<std::vector<Tensor>>> infer_async(
        NpuModelHandle handle,
        const std::vector<Tensor>& inputs) {
        return std::async(std::launch::async,
            [this, handle, &inputs]() {
                return infer(handle, inputs);
            });
    }

    /**
     * @brief 零拷贝推理（ION/DMA-BUF）。
     *
     * @param handle   NPU 模型句柄
     * @param ion_fds 每个输入张量对应的 ION 文件描述符
     * @param shapes   每个输入张量的形状
     * @param dtypes  每个输入张量的数据类型
     *
     * 默认实现：从 ION fd 映射到 CPU 内存，再调用 infer()。
     * 具体 HAL 应 override 以实现真正的零拷贝（NPU 直接从 ION 读取）。
     */
    virtual Result<std::vector<Tensor>> infer_zero_copy(
        NpuModelHandle handle,
        const std::vector<int>& ion_fds,
        const std::vector<std::vector<std::int64_t>>& shapes,
        const std::vector<DType>& dtypes) {
        (void)handle; (void)ion_fds; (void)shapes; (void)dtypes;
        return Error<std::vector<Tensor>>(ErrorCode::NOT_IMPLEMENTED,
                     "Zero-copy not implemented by this HAL");
    }

    // ── 性能剖析 ───────────────────────────────────────────────────────
    /**
     * @brief 返回最近一次推理的性能数据。
     */
    virtual std::optional<NpuProfilingData> last_profiling() const {
        return std::nullopt;
    }

    /**
     * @brief 重置性能计数器。
     */
    virtual void reset_profiling() {}

    // ── 电源管理 ───────────────────────────────────────────────────────
    /**
     * @brief 设置 NPU 功耗模式。
     * @param mode  0=balanced, 1=high_performance, 2=power_saver
     */
    virtual Result<void> set_power_mode(int mode) {
        (void)mode;
        return Error(ErrorCode::NOT_IMPLEMENTED, "set_power_mode not supported");
    }

    /**
     * @brief 返回 NPU 当前温度（摄氏度）。
     * @note 可选实现
     */
    virtual std::optional<int> get_temperature() const {
        return std::nullopt;
    }

    // ── 诊断 ───────────────────────────────────────────────────────────
    /**
     * @brief 返回 HAL 特定诊断信息（JSON 字符串）。
     */
    virtual std::string diagnostic_info() const { return "{}"; }
};

// ─────────────────────────────────────────────────────────────────────────────
//  NpuHalLoader — HAL 动态加载器
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 动态加载 NPU HAL 共享库（插件化架构）。
 *
 * 用法：
 * ```cpp
 * auto loader = NpuHalLoader::instance();
 *
 * // 加载 Qualcomm QNN HAL
 * auto result = loader.load("qnn", "/usr/lib/libqoocore_hal_qnn.so");
 * if (result.ok()) {
 *     auto hal = loader.get("qnn");
 *     hal->init(NpuConfig{});
 * }
 * ```
 */
class NpuHalLoader {
public:
    static NpuHalLoader& instance();

    /**
     * @brief 加载 HAL 共享库。
     * @param name          HAL 名称（如 "qnn", "bpu", "rknn"）
     * @param library_path  .so/.dll 路径
     * @return 成功或错误
     *
     * 共享库必须导出：
     *   extern "C" NpuHal* create_qoocore_npu_hal();
     *   extern "C" void destroy_qoocore_npu_hal(NpuHal*);
     */
    Result<void> load(const std::string& name, const std::string& library_path);

    /**
     * @brief 卸载 HAL。
     */
    Result<void> unload(const std::string& name);

    /**
     * @brief 获取已加载的 HAL。
     */
    Result<NpuHal*> get(const std::string& name);

    /**
     * @brief 列出所有已加载的 HAL 名称。
     */
    std::vector<std::string> list() const;

    /**
     * @brief 自动探测并加载系统上可用的 NPU HAL。
     *
     * 探测路径（Linux）：
     *   - /usr/lib/libqoocore_hal_*.so
     *   - ~/.local/lib/libqoocore_hal_*.so
     */
    Result<std::vector<std::string>> auto_probe();

private:
    NpuHalLoader();
    ~NpuHalLoader();
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoocore
