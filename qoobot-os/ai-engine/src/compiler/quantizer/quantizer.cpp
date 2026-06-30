/**
 * @file quantizer.cpp
 * @brief 模型量化编译器 — INT8/INT4/FP16 混合精度量化
 *
 * 量化流程：
 *   1. 解析 IR JSON 获取模型图结构
 *   2. 运行校准数据集收集激活值范围（PTQ 路径）
 *   3. 逐层计算 scale/zero_point
 *   4. 量化权重数据（FLOAT32 → INT8/INT4/FP16）
 *   5. 更新 IR JSON 中每个节点的 quant_params
 *
 * 支持方案：
 *   - INT8_PER_TENSOR   逐张量对称量化（默认）
 *   - INT8_PER_CHANNEL  逐通道非对称量化（更高精度）
 *   - INT4_PER_CHANNEL  极限压缩
 *   - FP16             半精度浮点
 *   - MIXED            混合精度（敏感层保留 FP16）
 *
 * 设计理念：
 *   对标 NVIDIA TensorRT / Qualcomm AIMET，支持 PTQ（校准）和 QAT（导入）。
 *   使用 nlohmann/json 进行 IR 解析和序列化。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/compiler.h"

#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <random>
#include <sstream>
#include <unordered_map>
#include <vector>

using json = nlohmann::json;

namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  量化统计信息（校准阶段收集）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 单张量的激活统计（校准数据集运行后收集）。
 */
struct ActivationStats {
    std::string tensor_name;       ///< 张量名称
    std::vector<std::int64_t> shape;
    DType original_dtype{DType::FLOAT32};

    // 范围统计
    float min_val{std::numeric_limits<float>::max()};
    float max_val{std::numeric_limits<float>::lowest()};
    double sum{0.0};
    double sum_sq{0.0};            ///< 平方和（用于计算标准差）
    std::size_t count{0};

    // 直方图（用于 KL 散度校准）
    std::vector<std::size_t> histogram;
    static constexpr std::size_t HIST_BINS = 2048;

    ActivationStats() : histogram(HIST_BINS, 0) {}

    /** @brief 更新统计（在线算法：Welford 单遍）。 */
    void update(float value) {
        min_val = std::min(min_val, value);
        max_val = std::max(max_val, value);
        sum += value;
        sum_sq += static_cast<double>(value) * value;
        count++;

        // 直方图（线性分箱）
        if (max_val > min_val) {
            float bin_width = (max_val - min_val) / HIST_BINS;
            if (bin_width > 0) {
                std::size_t bin = static_cast<std::size_t>(
                    (value - min_val) / bin_width);
                if (bin < HIST_BINS) {
                    histogram[bin]++;
                }
            }
        }
    }

    /** @brief 返回均值。 */
    [[nodiscard]] float mean() const {
        return count > 0 ? static_cast<float>(sum / count) : 0.0f;
    }

    /** @brief 返回标准差。 */
    [[nodiscard]] float stddev() const {
        if (count < 2) return 0.0f;
        double mean_val = sum / count;
        double variance = (sum_sq / count) - (mean_val * mean_val);
        return static_cast<float>(std::sqrt(std::max(0.0, variance)));
    }

    /** @brief 返回 range（max - min）。 */
    [[nodiscard]] float range() const {
        return max_val - min_val;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  量化参数计算
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 对称量化 scale 计算（INT8）。
 *
 * 对称量化：q = round(clip(x / scale, -128, 127))
 * 反量化：x' = q * scale
 *
 * scale = max(|min|, |max|) / 127
 */
static float compute_symmetric_scale(float min_val, float max_val) {
    float abs_max = std::max(std::abs(min_val), std::abs(max_val));
    if (abs_max < 1e-8f) abs_max = 1e-8f;
    return abs_max / 127.0f;
}

/**
 * @brief 非对称量化 scale/zero_point 计算（INT8）。
 *
 * 非对称量化：q = round(x / scale + zero_point)
 * 反量化：x' = (q - zero_point) * scale
 */
static std::pair<float, std::int32_t> compute_asymmetric_params(
    float min_val, float max_val) {
    // 扩展到 [0, 255] 范围
    float range = max_val - min_val;
    if (range < 1e-8f) range = 1e-8f;

    float scale = range / 255.0f;
    std::int32_t zero_point = static_cast<std::int32_t>(
        std::round(-min_val / scale));
    zero_point = std::clamp(zero_point, 0, 255);
    return {scale, zero_point};
}

/**
 * @brief 将 FLOAT32 值量化为 INT8。
 */
static std::int8_t quantize_f32_to_int8(float value, float scale,
                                          std::int32_t zero_point = 0) {
    float q = value / scale + static_cast<float>(zero_point);
    return static_cast<std::int8_t>(
        std::clamp(std::round(q), -128.0f, 127.0f));
}

/**
 * @brief 将 FLOAT32 值量化为 INT4（打包存储：每字节 2 个元素）。
 */
static std::pair<std::uint8_t, std::uint8_t> quantize_f32_to_int4_pair(
    float v0, float v1, float scale, std::int32_t zero_point = 0) {
    int q0 = static_cast<int>(std::round(v0 / scale)) + zero_point;
    int q1 = static_cast<int>(std::round(v1 / scale)) + zero_point;
    q0 = std::clamp(q0, -8, 7);
    q1 = std::clamp(q1, -8, 7);
    return {static_cast<std::uint8_t>(q0 & 0x0F),
            static_cast<std::uint8_t>(q1 & 0x0F)};
}

// ─────────────────────────────────────────────────────────────────────────────
//  校准数据集模拟（开发阶段使用随机数据代替真实数据集）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 模拟校准数据集运行，收集每个张量的激活统计。
 *
 * 完整实现需要：
 *   1. 加载真实校准数据集（图片/点云等）
 *   2. 在 CPU/FP32 上推理模型
 *   3. 捕获每个中间张量的值
 *
 * 此处使用随机模拟（开发阶段）。
 */
static std::unordered_map<std::string, ActivationStats>
simulate_calibration(const json& ir, std::size_t num_samples) {
    std::unordered_map<std::string, ActivationStats> stats_map;

    // 为每个有 "shape" 属性的节点创建统计
    if (ir.contains("nodes") && ir["nodes"].is_array()) {
        for (const auto& node : ir["nodes"]) {
            if (!node.contains("id")) continue;

            std::string tensor_name = node["id"].get<std::string>();
            ActivationStats stats;
            stats.tensor_name = tensor_name;

            // 解析 shape
            if (node.contains("attrs") && node["attrs"].contains("shape")) {
                const auto& shape_arr = node["attrs"]["shape"];
                if (shape_arr.is_array()) {
                    for (const auto& dim : shape_arr) {
                        stats.shape.push_back(
                            dim.is_number_integer() ? dim.get<std::int64_t>() : 1);
                    }
                }
            }

            // 随机数生成器模拟激活值
            std::mt19937 rng(static_cast<unsigned>(tensor_name[0] * 42));
            std::normal_distribution<float> dist(0.0f, 1.0f);

            for (std::size_t i = 0; i < num_samples; ++i) {
                float value = dist(rng);
                stats.update(value);
            }

            stats_map[tensor_name] = std::move(stats);
        }
    }

    return stats_map;
}

// ─────────────────────────────────────────────────────────────────────────────
//  量化策略：选择最佳方案
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 根据量化配置和节点特征选择量化精度。
 */
static DType select_quant_dtype(
    const std::string& node_id,
    const std::string& op_type,
    const ActivationStats& stats,
    const QuantizationConfig& config) {

    // 检查是否在白名单中（混合精度保留 FP16）
    for (const auto& layer : config.mixed_precision_whitelist) {
        if (node_id.find(layer) != std::string::npos) {
            return DType::FLOAT16;
        }
    }

    switch (config.scheme) {
        case QuantizationConfig::Scheme::INT8_PER_TENSOR:
            return DType::QINT8;
        case QuantizationConfig::Scheme::INT8_PER_CHANNEL:
            return DType::QINT8;
        case QuantizationConfig::Scheme::INT4_PER_CHANNEL:
            return DType::QINT4;
        case QuantizationConfig::Scheme::FP16:
            return DType::FLOAT16;
        case QuantizationConfig::Scheme::MIXED:
            // 敏感层（方差大、范围宽）保留 FP16
            if (stats.range() > 10.0f || stats.stddev() > 3.0f) {
                return DType::FLOAT16;
            }
            return DType::QINT8;
        default:
            return DType::QINT8;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  量化器主入口
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 对 IR JSON 执行量化。
 *
 * @param ir_json  输入 IR JSON 字符串
 * @param config   量化配置
 * @return 量化后的 IR JSON 字符串（含 quant_params）
 */
Result<std::string> quantize_ir(const std::string& ir_json,
                                  const QuantizationConfig& config) {
    spdlog::info("Starting quantization: scheme={}",
                  static_cast<int>(config.scheme));

    // 1. 解析 IR JSON
    json ir;
    try {
        ir = json::parse(ir_json);
    } catch (const json::parse_error& e) {
        return Error<std::string>(ErrorCode::COMPILE_FAILED,
                                    "Failed to parse IR JSON: " + std::string(e.what()));
    }

    if (!ir.contains("nodes") || !ir["nodes"].is_array()) {
        return Error<std::string>(ErrorCode::GRAPH_INVALID,
                                    "IR JSON missing 'nodes' array");
    }

    // 2. 运行校准（收集激活统计）
    std::size_t num_samples = config.calibration.num_samples;
    spdlog::info("  Running calibration with {} samples...", num_samples);

    auto stats_map = simulate_calibration(ir, num_samples);

    spdlog::info("  Collected stats for {} tensors", stats_map.size());

    // 3. 逐节点计算量化参数并更新 IR
    std::size_t quantized_nodes = 0;
    std::size_t fp16_nodes = 0;
    std::size_t skipped_nodes = 0;

    for (auto& node : ir["nodes"]) {
        if (!node.contains("id") || !node.contains("op_type")) {
            continue;
        }

        std::string node_id = node["id"].get<std::string>();
        std::string op_type = node["op_type"].get<std::string>();

        // 跳过输入/输出节点（保持 FP32）
        if (op_type == "Input" || op_type == "Output") {
            skipped_nodes++;
            continue;
        }

        // 获取该节点的激活统计
        auto stats_it = stats_map.find(node_id);
        if (stats_it == stats_map.end()) {
            // 无统计信息：使用默认量化参数
            QuantParams qp;
            qp.target_dtype = DType::QINT8;
            qp.scales = {0.007874f};  // 默认 INT8 scale
            qp.zero_points = {0};
            qp.per_channel = false;
            qp.symmetric = true;

            json qp_json;
            qp_json["target"] = dtype_to_string(qp.target_dtype);
            qp_json["scales"] = qp.scales;
            qp_json["zero_points"] = qp.zero_points;
            qp_json["per_channel"] = qp.per_channel;
            qp_json["symmetric"] = qp.symmetric;
            node["quant_params"] = qp_json;

            quantized_nodes++;
            continue;
        }

        const auto& stats = stats_it->second;

        // 选择量化精度
        DType quant_dtype = select_quant_dtype(node_id, op_type, stats, config);

        // 构建量化参数
        QuantParams qp;
        qp.target_dtype = quant_dtype;

        if (quant_dtype == DType::FLOAT16) {
            // FP16：无需 scale/zero_point
            qp.scales = {};
            qp.zero_points = {};
            qp.per_channel = false;
            qp.symmetric = false;
            fp16_nodes++;
        } else {
            // INT8/INT4：计算 scale/zero_point
            if (config.scheme == QuantizationConfig::Scheme::INT8_PER_CHANNEL ||
                config.scheme == QuantizationConfig::Scheme::INT4_PER_CHANNEL) {
                // 逐通道量化（假设通道在最后一维）
                std::size_t num_channels = 1;
                if (!stats.shape.empty()) {
                    num_channels = static_cast<std::size_t>(stats.shape.back());
                }
                qp.per_channel = true;

                for (std::size_t c = 0; c < num_channels; ++c) {
                    // 模拟每个通道的统计（开发阶段使用相同值）
                    float ch_scale = compute_symmetric_scale(stats.min_val, stats.max_val);
                    qp.scales.push_back(ch_scale);
                    qp.zero_points.push_back(0);
                }
            } else {
                // 逐张量量化
                qp.per_channel = false;
                float scale = compute_symmetric_scale(stats.min_val, stats.max_val);
                qp.scales = {scale};
                qp.zero_points = {0};
            }
            qp.symmetric = true;
            quantized_nodes++;
        }

        // 写入 IR JSON
        json qp_json;
        qp_json["target"] = dtype_to_string(qp.target_dtype);
        qp_json["scales"] = qp.scales;
        qp_json["zero_points"] = qp.zero_points;
        qp_json["per_channel"] = qp.per_channel;
        qp_json["symmetric"] = qp.symmetric;
        node["quant_params"] = qp_json;
    }

    // 4. 添加量化元信息
    ir["quantization"] = {
        {"scheme", static_cast<int>(config.scheme)},
        {"num_samples", config.calibration.num_samples},
        {"quantized_nodes", quantized_nodes},
        {"fp16_nodes", fp16_nodes},
        {"skipped_nodes", skipped_nodes},
        {"total_nodes", ir["nodes"].size()}
    };

    spdlog::info("Quantization complete: {} INT8/INT4, {} FP16, {} skipped (of {} total)",
                  quantized_nodes, fp16_nodes, skipped_nodes, ir["nodes"].size());

    return ir.dump(2);  // 格式化 JSON 输出
}

// ─────────────────────────────────────────────────────────────────────────────
//  权重量化工具函数（用于编译流程中实际量化权重数据）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 量化 FLOAT32 权重 buffer 为 INT8。
 *
 * @param fp32_data  输入 FP32 权重数据
 * @param quant_params  量化参数（per-tensor 或 per-channel）
 * @return 量化后的 INT8 数据
 */
Result<std::vector<std::int8_t>> quantize_weights_int8(
    const std::vector<float>& fp32_data,
    const QuantParams& quant_params) {

    std::vector<std::int8_t> int8_data(fp32_data.size());

    if (quant_params.per_channel && quant_params.scales.size() > 1) {
        // 逐通道量化
        std::size_t num_channels = quant_params.scales.size();
        std::size_t elements_per_channel = fp32_data.size() / num_channels;

        for (std::size_t c = 0; c < num_channels; ++c) {
            float scale = quant_params.scales[c];
            std::int32_t zp = c < quant_params.zero_points.size()
                                  ? quant_params.zero_points[c] : 0;

            for (std::size_t i = 0; i < elements_per_channel; ++i) {
                std::size_t idx = c * elements_per_channel + i;
                int8_data[idx] = quantize_f32_to_int8(fp32_data[idx], scale, zp);
            }
        }
    } else {
        // 逐张量量化
        float scale = quant_params.scales.empty() ? 1.0f : quant_params.scales[0];
        std::int32_t zp = quant_params.zero_points.empty() ? 0 : quant_params.zero_points[0];

        for (std::size_t i = 0; i < fp32_data.size(); ++i) {
            int8_data[i] = quantize_f32_to_int8(fp32_data[i], scale, zp);
        }
    }

    return int8_data;
}

/**
 * @brief 将 FLOAT32 权重转换为 FP16。
 */
Result<std::vector<std::uint16_t>> quantize_weights_fp16(
    const std::vector<float>& fp32_data) {

    std::vector<std::uint16_t> fp16_data(fp32_data.size());

    for (std::size_t i = 0; i < fp32_data.size(); ++i) {
        // IEEE 754 FP32 → FP16 转换（截断舍入）
        std::uint32_t bits;
        std::memcpy(&bits, &fp32_data[i], sizeof(float));

        std::uint32_t sign = (bits >> 16) & 0x8000;
        std::int32_t exponent = static_cast<std::int32_t>((bits >> 23) & 0xFF) - 127 + 15;
        std::uint32_t mantissa = (bits >> 13) & 0x3FF;

        if (exponent <= 0) {
            // 亚正常数 → 0
            fp16_data[i] = static_cast<std::uint16_t>(sign);
        } else if (exponent >= 31) {
            // 溢出 → Inf
            fp16_data[i] = static_cast<std::uint16_t>(sign | 0x7C00);
        } else {
            fp16_data[i] = static_cast<std::uint16_t>(sign | (exponent << 10) | mantissa);
        }
    }

    return fp16_data;
}

// ─────────────────────────────────────────────────────────────────────────────
//  校准数据集加载（占位，完整实现需实际数据集）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 加载校准数据集（占位实现）。
 *
 * 完整实现：
 *   1. 从 calibration.dataset_path 加载图片/点云
 *   2. 预处理（resize/normalize）
 *   3. 返回 Tensor 列表
 */
Result<std::vector<std::vector<float>>> load_calibration_data(
    const std::string& dataset_path,
    std::size_t num_samples) {
    (void)dataset_path;
    (void)num_samples;

    // 开发阶段：返回模拟数据
    std::vector<std::vector<float>> samples;
    std::mt19937 rng(42);
    std::normal_distribution<float> dist(0.0f, 1.0f);

    for (std::size_t s = 0; s < num_samples; ++s) {
        std::vector<float> sample(1024);  // 模拟 1024 维特征
        for (auto& v : sample) {
            v = dist(rng);
        }
        samples.push_back(std::move(sample));
    }

    return samples;
}

}  // namespace qoocore
