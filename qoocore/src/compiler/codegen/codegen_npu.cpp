/**
 * @file codegen_npu.cpp
 * @brief NPU 代码生成器 — 将 IR 图编译为各厂商 NPU 指令/模型格式
 *
 * 支持后端：
 *   - Qualcomm QNN (Snapdragon 8 Gen2/3, 8cx)
 *   - Horizon BPU (Journey 5/6)
 *   - Rockchip RKNN (RK3588, RK3568)
 *   - MediaTek NeuroPilot (Dimensity 9300/8300)
 *
 * 代码生成策略：
 *   1. 算子映射：IR Op → NPU 原生算子（如 Conv2D → QNN_Conv2d）
 *   2. 内存规划：输入/输出/中间张量地址分配
 *   3. 指令序列生成：调度顺序 + 依赖关系
 *   4. 量化感知：INT8/INT4 量化参数注入
 *   5. 序列化输出：厂商特定模型格式 (.bin/.so)
 *
 * @copyright QooBot Project
 * @version 0.3.0
 */

#include "qoocore/compiler.h"
#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <algorithm>
#include <cstring>
#include <fstream>
#include <map>
#include <memory>
#include <numeric>
#include <sstream>
#include <unordered_set>

namespace qoocore {
namespace codegen {

// ═══════════════════════════════════════════════════════════════════════════════
// NPU 指令类型定义
// ═══════════════════════════════════════════════════════════════════════════════

/// NPU 原生算子类型枚举
enum class NpuOpType : uint32_t {
    CONV_2D        = 0,
    DEPTHWISE_CONV = 1,
    POINTWISE_CONV = 2,
    TRANSPOSE_CONV = 3,
    MATMUL         = 10,
    ADD            = 20,
    MUL            = 21,
    RELU           = 30,
    RELU6          = 31,
    LEAKY_RELU     = 32,
    SIGMOID        = 33,
    TANH           = 34,
    SOFTMAX        = 35,
    BATCH_NORM     = 40,
    LAYER_NORM     = 41,
    POOL_MAX       = 50,
    POOL_AVG       = 51,
    CONCAT         = 60,
    RESHAPE        = 61,
    TRANSPOSE      = 62,
    PAD            = 63,
    RESIZE         = 64,
    CUSTOM_OP      = 0xFFFF,
};

/// NPU 内存区域类型
enum class NpuMemoryZone : uint8_t {
    SRAM,           ///< 片上 SRAM（最快，<2MB）
    TCM,            ///< 紧耦合内存（低延迟，<8MB）
    DDR,            ///< 外部 DDR（大容量）
    DDR_CACHED,     ///< 带缓存的 DDR
};

/// NPU 张量描述符（代码生成用）
struct NpuTensorDesc {
    std::string name;
    std::vector<int64_t> shape;
    DType dtype{DType::FLOAT32};
    NpuMemoryZone zone{NpuMemoryZone::DDR};
    std::optional<QuantParams> quant;
    uint32_t offset{0};         ///< 内存偏移（字节）
    uint32_t size_bytes{0};
    bool is_input{false};
    bool is_output{false};
    bool is_constant{false};    ///< 权重/常量
};

/// NPU 指令（一条 NPU 原生操作）
struct NpuInstruction {
    uint32_t id{0};
    NpuOpType op_type{NpuOpType::CUSTOM_OP};
    std::string op_name;
    std::vector<std::string> inputs;
    std::vector<std::string> outputs;
    std::map<std::string, std::string> params;  ///< 算子参数
    uint32_t flops{0};
    uint32_t memory_bytes{0};
};

/// NPU 子图（一组可独立执行的指令）
struct NpuSubgraph {
    std::string name;
    std::vector<NpuInstruction> instructions;
    std::vector<NpuTensorDesc> tensors;
};

/// NPU 编译产物
struct NpuCompiledModel {
    std::string vendor;
    std::string chip;
    std::vector<NpuSubgraph> subgraphs;
    std::vector<NpuTensorDesc> global_tensors;
    uint32_t total_weight_bytes{0};
    uint32_t total_code_bytes{0};
    std::string checksum;
};

// ═══════════════════════════════════════════════════════════════════════════════
// IR 算子 → NPU 算子映射表
// ═══════════════════════════════════════════════════════════════════════════════

/// 通用算子映射（所有 NPU 厂商支持的基础算子）
static const std::unordered_map<std::string, NpuOpType> kCommonOpMap = {
    {"Conv2D",       NpuOpType::CONV_2D},
    {"Conv",         NpuOpType::CONV_2D},
    {"DepthwiseConv", NpuOpType::DEPTHWISE_CONV},
    {"MatMul",       NpuOpType::MATMUL},
    {"Gemm",         NpuOpType::MATMUL},
    {"Add",          NpuOpType::ADD},
    {"Mul",          NpuOpType::MUL},
    {"Relu",         NpuOpType::RELU},
    {"Relu6",        NpuOpType::RELU6},
    {"LeakyRelu",    NpuOpType::LEAKY_RELU},
    {"Sigmoid",      NpuOpType::SIGMOID},
    {"Tanh",         NpuOpType::TANH},
    {"Softmax",      NpuOpType::SOFTMAX},
    {"BatchNormalization", NpuOpType::BATCH_NORM},
    {"LayerNormalization", NpuOpType::LAYER_NORM},
    {"MaxPool",      NpuOpType::POOL_MAX},
    {"AvgPool",      NpuOpType::POOL_AVG},
    {"GlobalAveragePool", NpuOpType::POOL_AVG},
    {"Concat",       NpuOpType::CONCAT},
    {"Reshape",      NpuOpType::RESHAPE},
    {"Transpose",    NpuOpType::TRANSPOSE},
    {"Pad",          NpuOpType::PAD},
    {"Resize",       NpuOpType::RESIZE},
    {"Upsample",     NpuOpType::RESIZE},
};

/// 高通 QNN 额外支持的算子
static const std::unordered_set<std::string> kQnnExtraOps = {
    "LayerNorm", "GELU", "HardSwish", "ChannelShuffle",
    "ReduceMean", "ReduceSum", "Split", "Slice",
};

/// 地平线 BPU 额外支持的算子
static const std::unordered_set<std::string> kBpuExtraOps = {
    "Correlation", "GridSample", "WarpAffine", "ReduceL2",
};

/// RK3588 NPU 额外支持的算子
static const std::unordered_set<std::string> kRknnExtraOps = {
    "Mish", "HardSigmoid", "LSTM", "GRU",
};

// ═══════════════════════════════════════════════════════════════════════════════
// 工具函数
// ═══════════════════════════════════════════════════════════════════════════════

static const char* npu_op_type_name(NpuOpType op) {
    switch (op) {
        case NpuOpType::CONV_2D:         return "Conv2D";
        case NpuOpType::DEPTHWISE_CONV:  return "DepthwiseConv";
        case NpuOpType::POINTWISE_CONV:  return "PointwiseConv";
        case NpuOpType::TRANSPOSE_CONV:  return "TransposeConv";
        case NpuOpType::MATMUL:          return "MatMul";
        case NpuOpType::ADD:             return "Add";
        case NpuOpType::MUL:             return "Mul";
        case NpuOpType::RELU:            return "Relu";
        case NpuOpType::RELU6:           return "Relu6";
        case NpuOpType::LEAKY_RELU:      return "LeakyRelu";
        case NpuOpType::SIGMOID:         return "Sigmoid";
        case NpuOpType::TANH:            return "Tanh";
        case NpuOpType::SOFTMAX:         return "Softmax";
        case NpuOpType::BATCH_NORM:      return "BatchNorm";
        case NpuOpType::LAYER_NORM:      return "LayerNorm";
        case NpuOpType::POOL_MAX:        return "MaxPool";
        case NpuOpType::POOL_AVG:        return "AvgPool";
        case NpuOpType::CONCAT:          return "Concat";
        case NpuOpType::RESHAPE:         return "Reshape";
        case NpuOpType::TRANSPOSE:       return "Transpose";
        case NpuOpType::PAD:             return "Pad";
        case NpuOpType::RESIZE:          return "Resize";
        default:                         return "Unknown";
    }
}

/// 估算 NPU 算子计算量 (FLOPs)
static uint32_t estimate_conv_flops(const std::vector<int64_t>& input_shape,
                                     const std::vector<int64_t>& weight_shape,
                                     const std::vector<int>& kernel,
                                     const std::vector<int>& stride) {
    if (input_shape.size() < 4 || weight_shape.size() < 4) return 0;
    int64_t N = input_shape[0], C_in = input_shape[1];
    int64_t H = input_shape[2], W = input_shape[3];
    int64_t C_out = weight_shape[0];
    int64_t KH = kernel.size() >= 2 ? kernel[0] : 3;
    int64_t KW = kernel.size() >= 2 ? kernel[1] : 3;
    int64_t SH = stride.size() >= 2 ? stride[0] : 1;
    int64_t SW = stride.size() >= 2 ? stride[1] : 1;

    int64_t H_out = (H - KH) / SH + 1;
    int64_t W_out = (W - KW) / SW + 1;

    // FLOPs = 2 * N * C_out * H_out * W_out * C_in * KH * KW (乘+加)
    return static_cast<uint32_t>(2 * N * C_out * H_out * W_out * C_in * KH * KW);
}

/// 对齐内存地址
static uint32_t align_up(uint32_t size, uint32_t alignment) {
    return (size + alignment - 1) & ~(alignment - 1);
}

// ═══════════════════════════════════════════════════════════════════════════════
// 厂商特定代码生成器
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 高通 QNN 代码生成器
 *
 * 生成 Qualcomm QNN (Qualcomm Neural Network) SDK 兼容的模型格式。
 * QNN 使用分层 API (QnnGraph_*)，支持 INT8/INT4/FP16。
 */
class QnnCodeGenerator {
public:
    explicit QnnCodeGenerator(const std::string& chip = "sdm8g3")
        : chip_(chip) {}

    /**
     * @brief 将 IR 节点列表编译为 QNN 子图。
     */
    NpuCompiledModel generate(const std::vector<IrNode>& ir_nodes,
                               const CompilationTarget& target) {
        NpuCompiledModel model;
        model.vendor = "qcom";
        model.chip = target.chip.empty() ? chip_ : target.chip;

        NpuSubgraph sg;
        sg.name = "qnn_graph_0";

        uint32_t tensor_id = 0;
        uint32_t offset = 0;

        for (const auto& node : ir_nodes) {
            // 映射算子
            auto it = kCommonOpMap.find(node.op_type);
            if (it == kCommonOpMap.end()) {
                if (kQnnExtraOps.count(node.op_type)) {
                    // QNN 原生支持的额外算子
                    sg.instructions.push_back(make_qnn_custom_op(node, tensor_id));
                } else {
                    continue;  // 不支持的算子跳过（应在此前被优化掉）
                }
                continue;
            }

            NpuInstruction inst;
            inst.id = static_cast<uint32_t>(sg.instructions.size());
            inst.op_type = it->second;
            inst.op_name = node.op_type;
            inst.inputs = node.inputs;
            inst.outputs = node.outputs;

            // 注入 QNN 特定参数
            for (const auto& [k, v] : node.attrs) {
                if (std::holds_alternative<int>(v)) {
                    inst.params[k] = std::to_string(std::get<int>(v));
                } else if (std::holds_alternative<float>(v)) {
                    inst.params[k] = std::to_string(std::get<float>(v));
                } else if (std::holds_alternative<std::string>(v)) {
                    inst.params[k] = std::get<std::string>(v);
                }
            }

            // QNN 量化参数注入
            if (node.quant_params.has_value()) {
                const auto& qp = node.quant_params.value();
                if (!qp.scales.empty()) {
                    inst.params["quant_scale"] = std::to_string(qp.scales[0]);
                    inst.params["quant_zero_point"] = std::to_string(qp.zero_points[0]);
                }
                inst.params["quant_scheme"] = qp.symmetric ? "symmetric" : "asymmetric";
            }

            // 计算资源使用
            if (it->second == NpuOpType::CONV_2D) {
                inst.flops = estimate_conv_flops({1, 64, 320, 320}, {32, 64, 3, 3}, {3, 3}, {1, 1});
            }
            inst.memory_bytes = node.memory_bytes.value_or(1024 * 1024);

            // 张量描述
            for (const auto& out_name : node.outputs) {
                NpuTensorDesc td;
                td.name = out_name;
                td.dtype = node.quant_params ? DType::QINT8 : DType::FLOAT32;
                td.offset = offset;
                td.size_bytes = inst.memory_bytes;
                td.is_output = true;
                if (node.quant_params) td.quant = node.quant_params;
                sg.tensors.push_back(td);
                offset += align_up(inst.memory_bytes, 128);
            }

            sg.instructions.push_back(std::move(inst));
            tensor_id++;
        }

        model.subgraphs.push_back(std::move(sg));
        model.total_code_bytes = static_cast<uint32_t>(sg.instructions.size() * 128);
        model.total_weight_bytes = offset;

        return model;
    }

private:
    std::string chip_;

    NpuInstruction make_qnn_custom_op(const IrNode& node, uint32_t tensor_id) {
        NpuInstruction inst;
        inst.id = tensor_id;
        inst.op_type = NpuOpType::CUSTOM_OP;
        inst.op_name = "qnn_" + node.op_type;
        inst.inputs = node.inputs;
        inst.outputs = node.outputs;
        inst.params["qnn_op"] = node.op_type;
        return inst;
    }
};

/**
 * @brief 地平线 BPU 代码生成器
 *
 * 地平线 Journey 5/6 使用 BPU (Bernoulli Processing Unit)。
 * BPU 编译器链：IR → HBDK (Horizon BPU Development Kit) → .bin
 */
class BpuCodeGenerator {
public:
    explicit BpuCodeGenerator(const std::string& chip = "j6")
        : chip_(chip) {}

    NpuCompiledModel generate(const std::vector<IrNode>& ir_nodes,
                               const CompilationTarget& target) {
        NpuCompiledModel model;
        model.vendor = "horizon";
        model.chip = target.chip.empty() ? chip_ : target.chip;

        NpuSubgraph sg;
        sg.name = "bpu_graph_0";

        uint32_t offset = 0;
        for (const auto& node : ir_nodes) {
            auto it = kCommonOpMap.find(node.op_type);
            if (it == kCommonOpMap.end() && !kBpuExtraOps.count(node.op_type)) {
                continue;
            }

            NpuInstruction inst;
            inst.id = static_cast<uint32_t>(sg.instructions.size());
            inst.op_type = it != kCommonOpMap.end() ? it->second : NpuOpType::CUSTOM_OP;
            inst.op_name = node.op_type;
            inst.inputs = node.inputs;
            inst.outputs = node.outputs;

            // BPU 特定参数（地平线 BPU 使用 16 字节对齐）
            inst.params["alignment"] = "16";
            inst.params["bpu_core"] = "0";  // 默认使用核心 0

            if (node.quant_params.has_value()) {
                const auto& qp = node.quant_params.value();
                if (!qp.scales.empty()) {
                    inst.params["bp_scale"] = std::to_string(qp.scales[0]);
                }
            }

            for (const auto& out_name : node.outputs) {
                NpuTensorDesc td;
                td.name = out_name;
                td.dtype = DType::QINT8;
                td.zone = NpuMemoryZone::DDR;
                td.offset = offset;
                td.size_bytes = node.memory_bytes.value_or(1024 * 1024);
                td.is_output = true;
                sg.tensors.push_back(td);
                offset += align_up(td.size_bytes, 16);
            }

            sg.instructions.push_back(std::move(inst));
        }

        model.subgraphs.push_back(std::move(sg));
        model.total_code_bytes = static_cast<uint32_t>(sg.instructions.size() * 96);
        model.total_weight_bytes = offset;

        return model;
    }

private:
    std::string chip_;
};

/**
 * @brief Rockchip RKNN 代码生成器
 *
 * RK3588/RK3568 使用 RKNN SDK v2.x。
 * 编译链：IR → RKNN-Toolkit2 → .rknn
 */
class RknnCodeGenerator {
public:
    explicit RknnCodeGenerator(const std::string& chip = "rk3588")
        : chip_(chip) {}

    NpuCompiledModel generate(const std::vector<IrNode>& ir_nodes,
                               const CompilationTarget& target) {
        NpuCompiledModel model;
        model.vendor = "rockchip";
        model.chip = target.chip.empty() ? chip_ : target.chip;

        NpuSubgraph sg;
        sg.name = "rknn_graph_0";

        uint32_t offset = 0;
        for (const auto& node : ir_nodes) {
            auto it = kCommonOpMap.find(node.op_type);
            if (it == kCommonOpMap.end() && !kRknnExtraOps.count(node.op_type)) {
                continue;
            }

            NpuInstruction inst;
            inst.id = static_cast<uint32_t>(sg.instructions.size());
            inst.op_type = it != kCommonOpMap.end() ? it->second : NpuOpType::CUSTOM_OP;
            inst.op_name = node.op_type;
            inst.inputs = node.inputs;
            inst.outputs = node.outputs;

            // RKNN 特定配置
            inst.params["target_platform"] = chip_;
            inst.params["optimization_level"] = "3";
            inst.params["do_sparse_network"] = "1";  // RK3588 支持稀疏推理

            for (const auto& out_name : node.outputs) {
                NpuTensorDesc td;
                td.name = out_name;
                td.dtype = DType::QINT8;
                td.offset = offset;
                td.size_bytes = node.memory_bytes.value_or(1024 * 1024);
                td.is_output = true;
                sg.tensors.push_back(td);
                offset += align_up(td.size_bytes, 64);  // RKNN 64 字节对齐
            }

            sg.instructions.push_back(std::move(inst));
        }

        model.subgraphs.push_back(std::move(sg));
        model.total_code_bytes = static_cast<uint32_t>(sg.instructions.size() * 64);
        model.total_weight_bytes = offset;

        return model;
    }

private:
    std::string chip_;
};

// ═══════════════════════════════════════════════════════════════════════════════
// NPU 代码生成器工厂 + 序列化
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief NPU 代码生成入口
 *
 * 根据 CompilationTarget 自动选择厂商生成器。
 */
Result<NpuCompiledModel> generate_npu_code(
    const std::vector<IrNode>& ir_nodes,
    const CompilationTarget& target) {

    std::string vendor = target.vendor;
    if (vendor.empty()) {
        // 根据后端类型推断厂商
        if (target.backend == BackendType::NPU) {
            vendor = "qcom";  // 默认高通
        } else {
            return Error<NpuCompiledModel>(ErrorCode::CODEGEN_FAILED,
                "Cannot determine NPU vendor for code generation");
        }
    }

    NpuCompiledModel result;

    if (vendor == "qcom" || vendor == "qualcomm") {
        QnnCodeGenerator gen(target.chip);
        result = gen.generate(ir_nodes, target);
    } else if (vendor == "horizon") {
        BpuCodeGenerator gen(target.chip);
        result = gen.generate(ir_nodes, target);
    } else if (vendor == "rockchip") {
        RknnCodeGenerator gen(target.chip);
        result = gen.generate(ir_nodes, target);
    } else if (vendor == "mediatek") {
        // MTK NeuroPilot 暂时使用通用映射
        QnnCodeGenerator gen(target.chip);
        result = gen.generate(ir_nodes, target);
        result.vendor = "mediatek";
    } else {
        return Error<NpuCompiledModel>(ErrorCode::CODEGEN_FAILED,
            "Unsupported NPU vendor: " + vendor);
    }

    return Ok(std::move(result));
}

/**
 * @brief 将 NPU 编译产物序列化为 JSON（用于 .qoomodel 的 codegen 段）
 */
std::string npu_model_to_json(const NpuCompiledModel& model) {
    std::ostringstream json;
    json << "{\n";
    json << "  \"vendor\": \"" << model.vendor << "\",\n";
    json << "  \"chip\": \"" << model.chip << "\",\n";
    json << "  \"total_weight_bytes\": " << model.total_weight_bytes << ",\n";
    json << "  \"total_code_bytes\": " << model.total_code_bytes << ",\n";
    json << "  \"subgraphs\": [\n";

    for (size_t si = 0; si < model.subgraphs.size(); ++si) {
        const auto& sg = model.subgraphs[si];
        json << "    {\n";
        json << "      \"name\": \"" << sg.name << "\",\n";
        json << "      \"instruction_count\": " << sg.instructions.size() << ",\n";
        json << "      \"instructions\": [\n";

        for (size_t ii = 0; ii < sg.instructions.size(); ++ii) {
            const auto& inst = sg.instructions[ii];
            json << "        {\"id\":" << inst.id
                 << ",\"op\":\"" << npu_op_type_name(inst.op_type)
                 << "\",\"flops\":" << inst.flops
                 << ",\"mem\":" << inst.memory_bytes << "}";
            if (ii + 1 < sg.instructions.size()) json << ",";
            json << "\n";
        }

        json << "      ]\n    }";
        if (si + 1 < model.subgraphs.size()) json << ",";
        json << "\n";
    }

    json << "  ]\n}";
    return json.str();
}

/**
 * @brief 验证 NPU 代码生成结果
 */
struct CodegenValidation {
    bool valid{false};
    std::vector<std::string> warnings;
    std::vector<std::string> errors;

    [[nodiscard]] bool ok() const { return errors.empty(); }
};

CodegenValidation validate_npu_codegen(const NpuCompiledModel& model) {
    CodegenValidation result;
    result.valid = true;

    if (model.subgraphs.empty()) {
        result.errors.push_back("No subgraphs generated");
        result.valid = false;
        return result;
    }

    for (const auto& sg : model.subgraphs) {
        if (sg.instructions.empty()) {
            result.warnings.push_back("Empty subgraph: " + sg.name);
        }

        // 检查张量引用完整性
        std::unordered_set<std::string> defined_tensors;
        for (const auto& t : sg.tensors) {
            defined_tensors.insert(t.name);
        }

        for (const auto& inst : sg.instructions) {
            for (const auto& inp : inst.inputs) {
                if (!defined_tensors.count(inp)) {
                    result.warnings.push_back(
                        "Instruction " + std::to_string(inst.id) +
                        " references undefined input: " + inp);
                }
            }
        }
    }

    // 检查总内存
    if (model.total_weight_bytes > 4ULL * 1024 * 1024 * 1024) {
        result.warnings.push_back("Total weight size exceeds 4GB");
    }

    return result;
}

} // namespace codegen
} // namespace qoocore
