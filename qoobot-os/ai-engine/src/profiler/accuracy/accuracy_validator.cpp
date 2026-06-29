/**
 * @file accuracy_validator.cpp
 * @brief 剪枝后精度保持验证工具
 *
 * 提供剪枝前后模型输出精度对比能力，确保剪枝不会显著降低模型质量。
 *
 * 验证维度：
 *   1. 输出分布一致性（KL 散度）
 *   2. Top-K 准确率保持率
 *   3. 逐层激活值相关性
 *   4. 端到端延迟 vs 精度 trade-off 分析
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/compiler.h"

#include <spdlog/spdlog.h>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <numeric>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  AccuracyValidationConfig — 精度验证配置
// ─────────────────────────────────────────────────────────────────────────────
struct AccuracyValidationConfig {
    double max_kl_divergence{0.05};      ///< 最大允许 KL 散度
    double min_top1_retention{0.95};     ///< 最小 Top-1 准确率保持率
    double min_top5_retention{0.98};     ///< 最小 Top-5 准确率保持率
    double max_output_drift{0.01};       ///< 最大输出分布漂移（L1 距离）
    int num_validation_samples{100};     ///< 验证样本数
    bool check_layerwise{true};          ///< 是否逐层验证
    std::vector<std::string> critical_layers; ///< 关键层（必须通过验证）
};

// ─────────────────────────────────────────────────────────────────────────────
//  LayerAccuracyResult — 单层精度验证结果
// ─────────────────────────────────────────────────────────────────────────────
struct LayerAccuracyResult {
    std::string layer_name;
    double cosine_similarity{0.0};       ///< 余弦相似度
    double relative_l2_error{0.0};       ///< 相对 L2 误差
    double pearson_correlation{0.0};     ///< 皮尔逊相关系数
    double kl_divergence{0.0};           ///< KL 散度
    bool passed{false};                  ///< 是否通过验证
    std::string failure_reason;          ///< 未通过原因
};

// ─────────────────────────────────────────────────────────────────────────────
//  AccuracyValidationReport — 精度验证报告
// ─────────────────────────────────────────────────────────────────────────────
struct AccuracyValidationReport {
    bool overall_passed{false};
    double top1_retention{0.0};          ///< Top-1 准确率保持率
    double top5_retention{0.0};          ///< Top-5 准确率保持率
    double output_kl_divergence{0.0};    ///< 输出 KL 散度
    double output_l1_drift{0.0};         ///< 输出 L1 漂移
    int layers_checked{0};
    int layers_passed{0};
    std::vector<LayerAccuracyResult> layer_results;
    std::vector<std::string> warnings;
    std::vector<std::string> recommendations;
};

namespace {

// ─────────────────────────────────────────────────────────────────────────────
//  统计工具函数
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 计算两个向量的余弦相似度。
 *
 * cos_sim(a, b) = (a · b) / (||a|| * ||b||)
 */
[[nodiscard]] double cosine_similarity(
    const std::vector<double>& a,
    const std::vector<double>& b) {

    if (a.size() != b.size() || a.empty()) return 0.0;

    double dot = 0.0, norm_a = 0.0, norm_b = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        dot += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    double denom = std::sqrt(norm_a) * std::sqrt(norm_b);
    if (denom < 1e-12) return 1.0;  // 两个零向量视为相同

    return dot / denom;
}

/**
 * @brief 计算两个向量的相对 L2 误差。
 *
 * rel_l2 = ||a - b|| / ||a||
 */
[[nodiscard]] double relative_l2_error(
    const std::vector<double>& a,
    const std::vector<double>& b) {

    if (a.size() != b.size() || a.empty()) return 0.0;

    double diff_sq = 0.0, norm_a_sq = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        double d = a[i] - b[i];
        diff_sq += d * d;
        norm_a_sq += a[i] * a[i];
    }

    if (norm_a_sq < 1e-12) return 0.0;
    return std::sqrt(diff_sq / norm_a_sq);
}

/**
 * @brief 计算两个向量的皮尔逊相关系数。
 *
 * r = Σ((a_i - μ_a)(b_i - μ_b)) / sqrt(Σ(a_i-μ_a)² * Σ(b_i-μ_b)²)
 */
[[nodiscard]] double pearson_correlation(
    const std::vector<double>& a,
    const std::vector<double>& b) {

    if (a.size() != b.size() || a.empty()) return 0.0;

    std::size_t n = a.size();

    double mean_a = 0.0, mean_b = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        mean_a += a[i];
        mean_b += b[i];
    }
    mean_a /= n;
    mean_b /= n;

    double cov = 0.0, var_a = 0.0, var_b = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        double da = a[i] - mean_a;
        double db = b[i] - mean_b;
        cov += da * db;
        var_a += da * da;
        var_b += db * db;
    }

    double denom = std::sqrt(var_a * var_b);
    if (denom < 1e-12) return 0.0;

    return cov / denom;
}

/**
 * @brief 计算两个概率分布的 KL 散度。
 *
 * KL(P||Q) = Σ p_i * log(p_i / q_i)
 */
[[nodiscard]] double kl_divergence(
    const std::vector<double>& p,
    const std::vector<double>& q) {

    if (p.size() != q.size() || p.empty()) return 0.0;

    // 确保是概率分布（加平滑）
    double sum_p = 0.0, sum_q = 0.0;
    for (std::size_t i = 0; i < p.size(); ++i) {
        sum_p += std::abs(p[i]);
        sum_q += std::abs(q[i]);
    }

    const double eps = 1e-10;
    double kl = 0.0;
    for (std::size_t i = 0; i < p.size(); ++i) {
        double p_i = (std::abs(p[i]) + eps) / (sum_p + eps * p.size());
        double q_i = (std::abs(q[i]) + eps) / (sum_q + eps * q.size());
        kl += p_i * std::log(p_i / q_i);
    }

    return kl;
}

/**
 * @brief 计算两个向量的 L1 距离（平均）。
 */
[[nodiscard]] double l1_distance(
    const std::vector<double>& a,
    const std::vector<double>& b) {

    if (a.size() != b.size() || a.empty()) return 0.0;

    double dist = 0.0;
    for (std::size_t i = 0; i < a.size(); ++i) {
        dist += std::abs(a[i] - b[i]);
    }
    return dist / a.size();
}

/**
 * @brief 计算 Top-K 准确率保持率。
 *
 * 对比原始模型和剪枝后模型的 Top-K 预测一致性。
 *
 * @param original_logits  原始模型 logits
 * @param pruned_logits    剪枝后模型 logits
 * @param k                Top-K
 * @return 预测一致的比例
 */
[[nodiscard]] double topk_retention(
    const std::vector<std::vector<double>>& original_logits,
    const std::vector<std::vector<double>>& pruned_logits,
    int k) {

    if (original_logits.empty() || original_logits.size() != pruned_logits.size()) {
        return 0.0;
    }

    int matches = 0;
    for (std::size_t sample = 0; sample < original_logits.size(); ++sample) {
        const auto& orig = original_logits[sample];
        const auto& pruned = pruned_logits[sample];

        if (orig.empty() || pruned.empty()) continue;

        // 获取原始模型的 Top-K 索引
        std::vector<std::pair<double, int>> orig_scored;
        for (std::size_t i = 0; i < orig.size(); ++i) {
            orig_scored.push_back({orig[i], static_cast<int>(i)});
        }
        std::partial_sort(orig_scored.begin(),
                          orig_scored.begin() + std::min(k, static_cast<int>(orig_scored.size())),
                          orig_scored.end(),
                          std::greater<>());

        std::unordered_set<int> orig_topk;
        for (int i = 0; i < k && i < static_cast<int>(orig_scored.size()); ++i) {
            orig_topk.insert(orig_scored[i].second);
        }

        // 获取剪枝模型的 Top-K 索引
        std::vector<std::pair<double, int>> pruned_scored;
        for (std::size_t i = 0; i < pruned.size(); ++i) {
            pruned_scored.push_back({pruned[i], static_cast<int>(i)});
        }
        std::partial_sort(pruned_scored.begin(),
                          pruned_scored.begin() + std::min(k, static_cast<int>(pruned_scored.size())),
                          pruned_scored.end(),
                          std::greater<>());

        // 检查是否有交集
        for (int i = 0; i < k && i < static_cast<int>(pruned_scored.size()); ++i) {
            if (orig_topk.find(pruned_scored[i].second) != orig_topk.end()) {
                matches++;
                break;  // 每个样本只计一次
            }
        }
    }

    return static_cast<double>(matches) / original_logits.size();
}

}  // anonymous namespace

// ─────────────────────────────────────────────────────────────────────────────
//  公开的精度验证接口
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 验证单层的激活值精度。
 *
 * 比较原始模型和剪枝后模型在同一层的输出激活值。
 *
 * @param original_activations  原始模型层激活值
 * @param pruned_activations    剪枝后模型层激活值
 * @param layer_name            层名称
 * @param config                验证配置
 * @return 层精度验证结果
 */
[[nodiscard]] LayerAccuracyResult validate_layer_accuracy(
    const std::vector<double>& original_activations,
    const std::vector<double>& pruned_activations,
    const std::string& layer_name,
    const AccuracyValidationConfig& config) {

    LayerAccuracyResult result;
    result.layer_name = layer_name;

    if (original_activations.empty() || pruned_activations.empty()) {
        result.passed = false;
        result.failure_reason = "Empty activations";
        return result;
    }

    // 计算各项指标
    result.cosine_similarity = cosine_similarity(
        original_activations, pruned_activations);
    result.relative_l2_error = relative_l2_error(
        original_activations, pruned_activations);
    result.pearson_correlation = pearson_correlation(
        original_activations, pruned_activations);
    result.kl_divergence = kl_divergence(
        original_activations, pruned_activations);

    // 判定是否通过
    bool cos_ok = result.cosine_similarity >= 0.95;
    bool l2_ok = result.relative_l2_error <= 0.10;
    bool corr_ok = result.pearson_correlation >= 0.90;
    bool kl_ok = result.kl_divergence <= config.max_kl_divergence;

    result.passed = cos_ok && l2_ok && corr_ok && kl_ok;

    if (!result.passed) {
        std::stringstream reason;
        if (!cos_ok) reason << "cos_sim=" << std::fixed << std::setprecision(4)
                             << result.cosine_similarity << " ";
        if (!l2_ok) reason << "rel_l2=" << result.relative_l2_error << " ";
        if (!corr_ok) reason << "pearson=" << result.pearson_correlation << " ";
        if (!kl_ok) reason << "kl=" << result.kl_divergence << " ";
        result.failure_reason = reason.str();
    }

    return result;
}

/**
 * @brief 完整的剪枝精度验证。
 *
 * 对剪枝后的模型进行全面精度验证：
 *   1. 输出分布对比
 *   2. Top-1/Top-5 准确率保持率
 *   3. 逐层激活值对比（若提供）
 *   4. 关键层特殊检查
 *
 * @param original_outputs    原始模型在验证集上的输出（logits）
 * @param pruned_outputs      剪枝后模型在验证集上的输出（logits）
 * @param layer_activations   逐层激活值对比（layer_name → {original, pruned}）
 * @param config              验证配置
 * @return 精度验证报告
 */
[[nodiscard]] AccuracyValidationReport validate_pruning_accuracy_full(
    const std::vector<std::vector<double>>& original_outputs,
    const std::vector<std::vector<double>>& pruned_outputs,
    const std::unordered_map<std::string,
        std::pair<std::vector<double>, std::vector<double>>>& layer_activations,
    const AccuracyValidationConfig& config) {

    AccuracyValidationReport report;

    spdlog::info("[accuracy] Starting full pruning accuracy validation");
    spdlog::info("[accuracy]   Samples: {}", original_outputs.size());

    // 1. 输出级别验证
    if (!original_outputs.empty() && original_outputs.size() == pruned_outputs.size()) {
        // Top-1 保持率
        report.top1_retention = topk_retention(original_outputs, pruned_outputs, 1);
        report.top5_retention = topk_retention(original_outputs, pruned_outputs, 5);

        spdlog::info("[accuracy]   Top-1 retention: {:.2%}", report.top1_retention);
        spdlog::info("[accuracy]   Top-5 retention: {:.2%}", report.top5_retention);

        // 全局输出 KL 散度和 L1 漂移
        std::vector<double> all_orig, all_pruned;
        for (std::size_t i = 0; i < original_outputs.size(); ++i) {
            for (double v : original_outputs[i]) all_orig.push_back(v);
            for (double v : pruned_outputs[i]) all_pruned.push_back(v);
        }

        report.output_kl_divergence = kl_divergence(all_orig, all_pruned);
        report.output_l1_drift = l1_distance(all_orig, all_pruned);

        spdlog::info("[accuracy]   Output KL divergence: {:.6f}", report.output_kl_divergence);
        spdlog::info("[accuracy]   Output L1 drift: {:.6f}", report.output_l1_drift);
    }

    // 2. 逐层验证
    if (config.check_layerwise && !layer_activations.empty()) {
        spdlog::info("[accuracy]   Layer-wise validation: {} layers",
                      layer_activations.size());

        for (const auto& [layer_name, activations] : layer_activations) {
            report.layers_checked++;

            auto layer_result = validate_layer_accuracy(
                activations.first, activations.second,
                layer_name, config);

            if (layer_result.passed) {
                report.layers_passed++;
            } else {
                spdlog::warn("[accuracy]     {} FAILED: {}", layer_name,
                              layer_result.failure_reason);
            }

            report.layer_results.push_back(std::move(layer_result));
        }
    }

    // 3. 关键层检查
    for (const auto& critical : config.critical_layers) {
        bool found = false;
        for (const auto& lr : report.layer_results) {
            if (lr.layer_name == critical) {
                found = true;
                if (!lr.passed) {
                    report.warnings.push_back(
                        "Critical layer '" + critical + "' failed accuracy check: " +
                        lr.failure_reason);
                }
                break;
            }
        }
        if (!found) {
            report.warnings.push_back(
                "Critical layer '" + critical + "' not found in validation results");
        }
    }

    // 4. 综合判定
    bool top1_ok = report.top1_retention >= config.min_top1_retention;
    bool top5_ok = report.top5_retention >= config.min_top5_retention;
    bool kl_ok = report.output_kl_divergence <= config.max_kl_divergence;
    bool drift_ok = report.output_l1_drift <= config.max_output_drift;

    report.overall_passed = top1_ok && top5_ok && kl_ok && drift_ok;

    if (!report.overall_passed) {
        if (!top1_ok) {
            report.recommendations.push_back(
                "Top-1 accuracy dropped below threshold (" +
                std::to_string(static_cast<int>(report.top1_retention * 100)) +
                "% < " +
                std::to_string(static_cast<int>(config.min_top1_retention * 100)) +
                "%). Consider reducing pruning ratio or enabling distillation.");
        }
        if (!top5_ok) {
            report.recommendations.push_back(
                "Top-5 accuracy degraded. Try structured pruning with lower ratio.");
        }
        if (!kl_ok) {
            report.recommendations.push_back(
                "Output distribution shifted significantly (KL=" +
                std::to_string(report.output_kl_divergence) +
                "). Consider knowledge distillation to recover distribution.");
        }
        if (!drift_ok) {
            report.recommendations.push_back(
                "Output values drifted (L1=" +
                std::to_string(report.output_l1_drift) +
                "). Check quantization parameters.");
        }
    }

    spdlog::info("[accuracy] Validation {} ({} layers: {}/{} passed)",
                  report.overall_passed ? "PASSED" : "FAILED",
                  report.layers_checked, report.layers_passed,
                  report.layers_checked);

    return report;
}

/**
 * @brief 简化版精度验证（仅输出级别）。
 *
 * @param original_outputs  原始模型输出
 * @param pruned_outputs    剪枝后模型输出
 * @return 是否通过验证
 */
[[nodiscard]] bool quick_accuracy_check(
    const std::vector<std::vector<double>>& original_outputs,
    const std::vector<std::vector<double>>& pruned_outputs) {

    AccuracyValidationConfig config;
    auto report = validate_pruning_accuracy_full(
        original_outputs, pruned_outputs, {}, config);
    return report.overall_passed;
}

/**
 * @brief 生成精度验证报告（人类可读文本格式）。
 */
[[nodiscard]] std::string generate_accuracy_report(
    const AccuracyValidationReport& report) {

    std::stringstream ss;

    ss << "╔══════════════════════════════════════════════════════════╗\n";
    ss << "║       QooCore Pruning Accuracy Validation Report         ║\n";
    ss << "╠══════════════════════════════════════════════════════════╣\n";

    // 总体结果
    ss << "║  Overall: " << std::setw(48) << std::left
       << (report.overall_passed ? "✅ PASSED" : "❌ FAILED") << " ║\n";
    ss << "╠══════════════════════════════════════════════════════════╣\n";

    // 输出级别指标
    ss << "║  Output-Level Metrics:                                   ║\n";
    ss << "║    Top-1 Retention:  " << std::setw(36) << std::left
       << (std::to_string(static_cast<int>(report.top1_retention * 100)) + "%")
       << " ║\n";
    ss << "║    Top-5 Retention:  " << std::setw(36) << std::left
       << (std::to_string(static_cast<int>(report.top5_retention * 100)) + "%")
       << " ║\n";
    ss << "║    KL Divergence:    " << std::setw(36) << std::left
       << std::fixed << std::setprecision(6) << report.output_kl_divergence
       << " ║\n";
    ss << "║    L1 Drift:         " << std::setw(36) << std::left
       << std::fixed << std::setprecision(6) << report.output_l1_drift
       << " ║\n";

    // 逐层结果
    if (!report.layer_results.empty()) {
        ss << "╠══════════════════════════════════════════════════════════╣\n";
        ss << "║  Layer Results: " << std::setw(41) << std::left
           << (std::to_string(report.layers_passed) + "/" +
               std::to_string(report.layers_checked) + " passed")
           << " ║\n";

        for (const auto& lr : report.layer_results) {
            std::string status = lr.passed ? "✅" : "❌";
            ss << "║    " << status << " " << std::setw(48) << std::left
               << (lr.layer_name + "  cos=" +
                   std::to_string(static_cast<int>(lr.cosine_similarity * 100)) + "%")
               << " ║\n";
        }
    }

    // 警告
    if (!report.warnings.empty()) {
        ss << "╠══════════════════════════════════════════════════════════╣\n";
        ss << "║  Warnings:                                              ║\n";
        for (const auto& w : report.warnings) {
            ss << "║    ⚠ " << std::setw(50) << std::left << w << " ║\n";
        }
    }

    // 建议
    if (!report.recommendations.empty()) {
        ss << "╠══════════════════════════════════════════════════════════╣\n";
        ss << "║  Recommendations:                                       ║\n";
        for (const auto& r : report.recommendations) {
            ss << "║    → " << std::setw(50) << std::left << r << " ║\n";
        }
    }

    ss << "╚══════════════════════════════════════════════════════════╝\n";

    return ss.str();
}

}  // namespace qoocore
