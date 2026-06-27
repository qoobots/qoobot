/**
 * @file compiler.h
 * @brief 模型编译器接口 — 从 ONNX/Torch 到 .qoomodel 的完整编译流程
 *
 * 编译流程：
 *   ONNX/Torch → IR → 优化 → 量化 → 代码生成 → .qoomodel
 *
 * 编译器可独立使用（CLI compile 命令），也可由 InferenceEngine 运行时调用
 * （若模型尚未编译为目标后端格式）。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "core.h"
#include "tensor.h"  // 复用 DType, QuantParams

#include <chrono>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <vector>

namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  SourceFormat — 输入模型格式
// ─────────────────────────────────────────────────────────────────────────────
enum class SourceFormat : std::uint8_t {
    ONNX,       ///< ONNX (.onnx, opset 17+)
    PYTORCH,    ///< PyTorch (.pt, TorchScript)
    TENSORFLOW,  ///< TensorFlow (.pb, SavedModel)
    TFLITE,     ///< TFLite (.tflite)
    QOOLOOK,    ///< QooLook 导出格式（未来）
};

constexpr const char* source_format_to_string(SourceFormat f) noexcept {
    switch (f) {
        case SourceFormat::ONNX:       return "onnx";
        case SourceFormat::PYTORCH:    return "pytorch";
        case SourceFormat::TENSORFLOW: return "tensorflow";
        case SourceFormat::TFLITE:     return "tflite";
        default:                       return "unknown";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  CompilationTarget — 编译目标
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 编译目标后端（决定生成的代码格式）。
 */
struct CompilationTarget {
    BackendType backend{BackendType::AUTO}; ///< 目标后端类型
    std::string vendor;                      ///< 厂商名称（如 "qcom", "horizon"）
    std::string chip;                        ///< 芯片型号（如 "sdm8g3", "j5"）

    /**
     * @brief 返回目标标识符字符串（用于 .qoomodel 文件头）。
     */
    [[nodiscard]] std::string to_string() const {
        if (backend == BackendType::AUTO) return "auto";
        std::string s = backend_to_string(backend);
        if (!vendor.empty()) s += "_" + vendor;
        if (!chip.empty())   s += "_" + chip;
        return s;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  QuantizationConfig — 量化配置
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 量化方案配置。
 *
 * 量化是端侧推理的关键优化（减少模型大小 4x，提升速度 2-3x）。
 */
struct QuantizationConfig {
    // 量化精度
    enum class Scheme {
        INT8_PER_TENSOR,   ///< 逐张量 INT8（最快，精度损失 ~1%）
        INT8_PER_CHANNEL,   ///< 逐通道 INT8（更精准，支持 Conv 权重）
        INT4_PER_CHANNEL,   ///< 逐通道 INT4（极限压缩，精度损失 ~3%）
        FP16,              ///< FP16（几乎无精度损失，大小减半）
        MIXED,             ///< 混合精度（敏感层 FP16，其他 INT8）
    };
    Scheme scheme{Scheme::INT8_PER_TENSOR};

    // 校准数据集（PTQ 需要）
    struct {
        std::string dataset_path;          ///< 校准数据集路径
        std::size_t num_samples{100};     ///< 校准样本数
        bool use_cache{true};             ///< 缓存校准结果
    } calibration;

    // 量化感知训练（QAT）导入
    struct {
        bool from_qat{false};             ///< 模型是否已做 QAT
        std::string qat_checkpoint;        ///< QAT 检查点路径
    } qat;

    // 混合精度白名单（对这些层保持 FP16）
    std::vector<std::string> mixed_precision_whitelist;
};

// ─────────────────────────────────────────────────────────────────────────────
//  OptimizationLevel — 图优化等级
// ─────────────────────────────────────────────────────────────────────────────
enum class OptimizationLevel : std::uint8_t {
    O0,  ///< 无优化（调试用）
    O1,  ///< 基础优化（常量折叠、死代码消除）
    O2,  ///< 标准优化（算子融合、内存复用）
    O3,  ///< 激进优化（跨层融合、动态 shape 推导）
};

// ─────────────────────────────────────────────────────────────────────────────
//  CompilationConfig — 完整编译配置
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 模型编译的完整配置。
 */
struct CompilationConfig {
    // 输入
    SourceFormat source_format{SourceFormat::ONNX};
    std::string source_model_path;

    // 目标
    CompilationTarget target;

    // 优化
    OptimizationLevel opt_level{OptimizationLevel::O2};

    // 量化
    std::optional<QuantizationConfig> quantization;

    // 模型剪枝
    struct {
        bool enable{false};
        float pruning_ratio{0.5f};      ///< 权重稀疏度目标
        bool structured{false};          ///< 结构化剪枝（通道剪枝）
    } pruning;

    // 输出
    std::string output_path;              ///< .qoomodel 输出路径
    bool overwrite{false};

    // 高级
    struct {
        bool enable_sim2real{false};     ///< 注入域随机化参数（Sim2Real）
        bool export_ir{false};           ///< 导出 IR 文件（调试）
        bool enable_fp16_accum{false};  ///< 使用 FP16 累积（更快，略微不精确）
    } advanced;

    // 性能预期（用于后端代码生成策略）
    struct {
        bool prioritize_latency{true};   ///< true=速度优先，false=精度优先
        std::optional<std::size_t> max_memory_mb; ///< 内存上限
    } preference;
};

// ─────────────────────────────────────────────────────────────────────────────
//  CompilationResult — 编译结果
// ─────────────────────────────────────────────────────────────────────────────
struct CompilationResult {
    bool success{false};
    std::string output_path;              ///< 生成的 .qoomodel 路径
    std::string qoomodel_checksum;       ///< SHA-256 校验和

    // 模型统计
    struct {
        std::size_t original_size_bytes{0};
        std::size_t compiled_size_bytes{0};
        std::size_t weight_size_bytes{0};
        float compression_ratio{1.0f};  ///< compiled / original
    } size_info;

    // 精度信息
    struct {
        std::optional<float> top1_acc;    ///< 量化后 Top-1 精度（若可提供）
        std::optional<float> acc_drop;    ///< 精度损失（与 FP32 基线比）
    } accuracy_info;

    // 性能预估
    struct {
        std::optional<double> estimated_latency_ms;
        std::optional<std::size_t> estimated_memory_mb;
    } performance;

    // 时间
    std::chrono::milliseconds compile_time{0};

    // 警告（非致命问题）
    std::vector<std::string> warnings;
};

// ─────────────────────────────────────────────────────────────────────────────
//  IrNode — 设备 IR 节点（编译器内部表示）
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 编译器的内部 IR 节点。
 *
 * 基于 MLIR 的 QooCore Dialect，此处为 C++ 扁平化表示，
 * 便于不依赖 MLIR 时使用（轻量级编译模式）。
 */
struct IrNode {
    std::string id;              ///< 节点唯一 ID
    std::string op_type;         ///< 算子类型（"Conv2D", "MatMul", ...）
    std::vector<std::string> inputs;   ///< 输入节点 ID 列表
    std::vector<std::string> outputs;  ///< 输出节点 ID 列表

    // 属性（算子特定参数）
    std::unordered_map<std::string, std::variant<
        int, float, std::string, std::vector<int>>> attrs;

    // 量化信息
    std::optional<QuantParams> quant_params;

    // 计算成本预估（由优化器填充）
    std::optional<std::size_t> flops;
    std::optional<std::size_t> memory_bytes;
};

// ─────────────────────────────────────────────────────────────────────────────
//  ModelCompiler — 模型编译器（核心接口）
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 将通用模型格式编译为 .qoomodel。
 *
 * 设计要点：
 *   - 支持从 ONNX/Torch 导入
 *   - 编译过程不产生副作用（纯函数风格）
 *   - 可序列化编译配置（复现性）
 *   - 进度回调（用于 CLI 进度条）
 */
class ModelCompiler {
public:
    virtual ~ModelCompiler() = default;

    /**
     * @brief 编译模型（完整流程）。
     *
     * @param config  编译配置
     * @param progress_callback  进度回调（0.0~1.0, 描述字符串）
     * @return 编译结果
     *
     * 流程：
     *   1. import_model()  — 导入源模型 → IR
     *   2. optimize_ir()   — 图优化
     *   3. quantize()      — 量化（若配置）
     *   4. prune()         — 剪枝（若配置）
     *   5. codegen()       — 生成目标后端代码
     *   6. package()      — 打包为 .qoomodel
     */
    virtual Result<CompilationResult> compile(
        const CompilationConfig& config,
        const std::function<void(float, const std::string&)>& progress_callback = nullptr) = 0;

    // ── 分步接口（高级用法）───────────────────────────────────────────
    /**
     * @brief 仅导入模型到 IR（不优化、不编译）。
     * @return IR 节点的 JSON 字符串（用于调试 / 可视化）
     */
    virtual Result<std::string> import_only(
        const std::string& model_path,
        SourceFormat format) = 0;

    /**
     * @brief 仅执行图优化（用于分析）。
     */
    virtual Result<std::string> optimize_only(
        const std::string& ir_json,
        OptimizationLevel level) = 0;

    // ── 查询 ───────────────────────────────────────────────────────────
    /**
     * @brief 返回编译器版本。
     */
    virtual std::string version() const = 0;

    /**
     * @brief 列出支持的源格式。
     */
    virtual std::vector<SourceFormat> supported_formats() const = 0;
};

// ─────────────────────────────────────────────────────────────────────────────
//  create_compiler — 创建默认编译器实例
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 创建 ModelCompiler 实例。
 * @param use_mlir  是否使用 MLIR 作为 IR（需要 LLVM 依赖）
 */
std::unique_ptr<ModelCompiler> create_compiler(bool use_mlir = true);

} // namespace qoocore
