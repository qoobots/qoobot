/**
 * @file multimodal_ops.cpp
 * @brief 多模态融合算子实现
 *
 * 实现视觉-激光雷达-IMU 等多传感器融合加速原语。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/operators/multimodal_ops.h"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace qoocore {
namespace operators {

namespace {

float l2_norm(const float* data, std::size_t n) {
    float sum = 0.0f;
    for (std::size_t i = 0; i < n; ++i) sum += data[i] * data[i];
    return std::sqrt(std::max(sum, 1e-12f));
}

} // anonymous namespace

// ═══════════════════════════════════════════════════════════════════════════════
//  Concat Fusion
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> concat_fusion(
    const std::vector<Tensor>& features,
    const FusionConfig& config)
{
    if (features.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Features empty");
    }

    // 验证空间维度一致
    const auto& f0_shape = features[0].shape();
    if (f0_shape.size() != 4) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Features must be 4D [N][C][H][W]");
    }

    std::uint32_t H = static_cast<std::uint32_t>(f0_shape[2]);
    std::uint32_t W = static_cast<std::uint32_t>(f0_shape[3]);
    std::uint32_t total_C = 0;

    for (const auto& f : features) {
        const auto& s = f.shape();
        if (s[2] != H || s[3] != W) {
            return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
                "Spatial dimensions must match for concat fusion");
        }
        total_C += static_cast<std::uint32_t>(s[1]);
    }

    std::vector<std::size_t> out_shape = {1, total_C, H, W};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create fusion output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    std::uint32_t c_offset = 0;
    for (const auto& f : features) {
        const auto& s = f.shape();
        std::uint32_t C = static_cast<std::uint32_t>(s[1]);
        const float* f_data = static_cast<const float*>(f.data());

        for (std::uint32_t c = 0; c < C; ++c) {
            for (std::uint32_t h = 0; h < H; ++h) {
                for (std::uint32_t w = 0; w < W; ++w) {
                    std::size_t src_idx = static_cast<std::size_t>(c) * H * W +
                                          static_cast<std::size_t>(h) * W + w;
                    std::size_t dst_idx = static_cast<std::size_t>(c_offset + c) * H * W +
                                          static_cast<std::size_t>(h) * W + w;
                    out_data[dst_idx] = f_data[src_idx];
                }
            }
        }
        c_offset += C;
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Add Fusion
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> add_fusion(
    const std::vector<Tensor>& features,
    const std::vector<float>& weights,
    const FusionConfig& config)
{
    if (features.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Features empty");
    }

    const auto& f0_shape = features[0].shape();
    std::uint32_t C = static_cast<std::uint32_t>(f0_shape[1]);
    std::uint32_t H = static_cast<std::uint32_t>(f0_shape[2]);
    std::uint32_t W = static_cast<std::uint32_t>(f0_shape[3]);
    std::size_t total = static_cast<std::size_t>(C) * H * W;

    std::vector<float> w = weights;
    if (w.empty()) {
        w.assign(features.size(), 1.0f / static_cast<float>(features.size()));
    }
    if (w.size() != features.size()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Weights count must match features count");
    }

    std::vector<std::size_t> out_shape = {1, C, H, W};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create add fusion output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());
    std::memset(out_data, 0, total * sizeof(float));

    for (std::size_t i = 0; i < features.size(); ++i) {
        const auto& s = features[i].shape();
        if (s[1] != C || s[2] != H || s[3] != W) {
            return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
                "All features must have same shape for add fusion");
        }
        const float* f_data = static_cast<const float*>(features[i].data());
        for (std::size_t j = 0; j < total; ++j) {
            out_data[j] += w[i] * f_data[j];
        }
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Gated Fusion
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> gated_fusion(
    const std::vector<Tensor>& features,
    const FusionConfig& config)
{
    if (features.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Features empty");
    }

    const auto& f0_shape = features[0].shape();
    std::uint32_t C = static_cast<std::uint32_t>(f0_shape[1]);
    std::uint32_t H = static_cast<std::uint32_t>(f0_shape[2]);
    std::uint32_t W = static_cast<std::uint32_t>(f0_shape[3]);
    std::size_t total = static_cast<std::size_t>(C) * H * W;

    // 自适应门控权重（基于特征激活值）
    std::vector<float> gate_weights(features.size());
    float total_energy = 0.0f;

    for (std::size_t i = 0; i < features.size(); ++i) {
        const float* f_data = static_cast<const float*>(features[i].data());
        float energy = 0.0f;
        for (std::size_t j = 0; j < total; ++j) {
            energy += std::abs(f_data[j]);
        }
        gate_weights[i] = energy;
        total_energy += energy;
    }

    if (total_energy > 0.0f) {
        for (auto& g : gate_weights) g /= total_energy;
    } else {
        for (auto& g : gate_weights) g = 1.0f / static_cast<float>(features.size());
    }

    // 门控融合：sigmoid(gate) * feature
    std::vector<std::size_t> out_shape = {1, C, H, W};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create gated fusion output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());
    std::memset(out_data, 0, total * sizeof(float));

    for (std::size_t i = 0; i < features.size(); ++i) {
        float gate = 1.0f / (1.0f + std::exp(-5.0f * (gate_weights[i] - 0.5f)));
        const float* f_data = static_cast<const float*>(features[i].data());
        for (std::size_t j = 0; j < total; ++j) {
            out_data[j] += gate * f_data[j];
        }
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Cross-Modal Attention
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> cross_modal_attention(
    const Tensor& primary,
    const Tensor& secondary,
    const FusionConfig& config)
{
    const auto& p_shape = primary.shape();
    const auto& s_shape = secondary.shape();

    if (p_shape.size() != 4 || s_shape.size() != 4) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Features must be 4D");
    }

    std::uint32_t Cp = static_cast<std::uint32_t>(p_shape[1]);
    std::uint32_t Cs = static_cast<std::uint32_t>(s_shape[1]);
    std::uint32_t H = static_cast<std::uint32_t>(p_shape[2]);
    std::uint32_t W = static_cast<std::uint32_t>(p_shape[3]);

    if (s_shape[2] != H || s_shape[3] != W) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Spatial dimensions must match for cross-modal attention");
    }

    const float* p_data = static_cast<const float*>(primary.data());
    const float* s_data = static_cast<const float*>(secondary.data());

    std::vector<std::size_t> out_shape = {1, Cp, H, W};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create attention fusion output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    // 简化的 Cross-Attention：primary 的每个空间位置 attention over secondary
    for (std::uint32_t h = 0; h < H; ++h) {
        for (std::uint32_t w = 0; w < W; ++w) {
            // 计算注意力分数
            float attn_sum = 0.0f;
            std::vector<float> attn_scores(H * W);

            for (std::uint32_t sh = 0; sh < H; ++sh) {
                for (std::uint32_t sw = 0; sw < W; ++sw) {
                    float dot = 0.0f;
                    for (std::uint32_t c = 0; c < std::min(Cp, Cs); ++c) {
                        std::size_t p_idx = static_cast<std::size_t>(c) * H * W +
                            static_cast<std::size_t>(h) * W + w;
                        std::size_t s_idx = static_cast<std::size_t>(c) * H * W +
                            static_cast<std::size_t>(sh) * W + sw;
                        dot += p_data[p_idx] * s_data[s_idx];
                    }
                    dot /= std::sqrt(static_cast<float>(std::min(Cp, Cs)));
                    float score = std::exp(dot);
                    attn_scores[sh * W + sw] = score;
                    attn_sum += score;
                }
            }

            if (attn_sum > 0.0f) {
                for (auto& s : attn_scores) s /= attn_sum;
            }

            // 加权聚合
            for (std::uint32_t c = 0; c < Cp; ++c) {
                float val = 0.0f;
                for (std::uint32_t sh = 0; sh < H; ++sh) {
                    for (std::uint32_t sw = 0; sw < W; ++sw) {
                        std::size_t s_idx = static_cast<std::size_t>(
                            std::min(c, Cs - 1)) * H * W +
                            static_cast<std::size_t>(sh) * W + sw;
                        val += attn_scores[sh * W + sw] * s_data[s_idx];
                    }
                }
                std::size_t out_idx = static_cast<std::size_t>(c) * H * W +
                    static_cast<std::size_t>(h) * W + w;
                out_data[out_idx] = val;
            }
        }
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Vision-LiDAR Fusion
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> vision_lidar_fusion(
    const std::vector<Tensor>& image_features,
    const Tensor& lidar_features,
    const FusionConfig& config)
{
    if (image_features.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Image features empty");
    }

    const auto& l_shape = lidar_features.shape();
    std::uint32_t C_lidar = static_cast<std::uint32_t>(l_shape[1]);
    std::uint32_t H_bev = static_cast<std::uint32_t>(l_shape[2]);
    std::uint32_t W_bev = static_cast<std::uint32_t>(l_shape[3]);

    // 将多相机图像特征平均池化到 BEV 尺寸
    std::uint32_t C_img = static_cast<std::uint32_t>(image_features[0].shape()[1]);
    std::vector<float> img_bev(C_img * H_bev * W_bev, 0.0f);

    for (const auto& feat : image_features) {
        const auto& s = feat.shape();
        std::uint32_t iH = static_cast<std::uint32_t>(s[2]);
        std::uint32_t iW = static_cast<std::uint32_t>(s[3]);
        const float* f_data = static_cast<const float*>(feat.data());

        for (std::uint32_t c = 0; c < C_img; ++c) {
            for (std::uint32_t bh = 0; bh < H_bev; ++bh) {
                for (std::uint32_t bw = 0; bw < W_bev; ++bw) {
                    // 简单最近邻下采样
                    std::uint32_t ih = bh * iH / H_bev;
                    std::uint32_t iw = bw * iW / W_bev;
                    std::size_t src_idx = static_cast<std::size_t>(c) * iH * iW +
                        static_cast<std::size_t>(ih) * iW + iw;
                    std::size_t dst_idx = static_cast<std::size_t>(c) * H_bev * W_bev +
                        static_cast<std::size_t>(bh) * W_bev + bw;
                    img_bev[dst_idx] += f_data[src_idx];
                }
            }
        }
    }

    float norm = 1.0f / static_cast<float>(image_features.size());
    for (auto& v : img_bev) v *= norm;

    // 融合
    std::uint32_t out_C = C_img + C_lidar;
    const float* lidar_data = static_cast<const float*>(lidar_features.data());

    std::vector<std::size_t> out_shape = {1, out_C, H_bev, W_bev};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create vision-lidar fusion output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    for (std::uint32_t c = 0; c < C_img; ++c) {
        for (std::uint32_t h = 0; h < H_bev; ++h) {
            for (std::uint32_t w = 0; w < W_bev; ++w) {
                std::size_t dst = static_cast<std::size_t>(c) * H_bev * W_bev +
                    static_cast<std::size_t>(h) * W_bev + w;
                std::size_t src = static_cast<std::size_t>(c) * H_bev * W_bev +
                    static_cast<std::size_t>(h) * W_bev + w;
                out_data[dst] = img_bev[src];
            }
        }
    }

    for (std::uint32_t c = 0; c < C_lidar; ++c) {
        for (std::uint32_t h = 0; h < H_bev; ++h) {
            for (std::uint32_t w = 0; w < W_bev; ++w) {
                std::size_t dst = static_cast<std::size_t>(C_img + c) * H_bev * W_bev +
                    static_cast<std::size_t>(h) * W_bev + w;
                std::size_t src = static_cast<std::size_t>(c) * H_bev * W_bev +
                    static_cast<std::size_t>(h) * W_bev + w;
                out_data[dst] = lidar_data[src];
            }
        }
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  IMU-Visual Fusion
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> imu_visual_fusion(
    const Tensor& visual_features,
    const Tensor& imu_data,
    const FusionConfig& config)
{
    const auto& v_shape = visual_features.shape();
    if (v_shape.size() != 4) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Visual features must be 4D");
    }

    std::uint32_t C = static_cast<std::uint32_t>(v_shape[1]);
    std::uint32_t H = static_cast<std::uint32_t>(v_shape[2]);
    std::uint32_t W = static_cast<std::uint32_t>(v_shape[3]);

    const float* v_data = static_cast<const float*>(visual_features.data());
    const float* imu = static_cast<const float*>(imu_data.data());
    const auto& i_shape = imu_data.shape();

    // 取最新 IMU 数据
    std::uint32_t T = static_cast<std::uint32_t>(i_shape[0]);
    std::uint32_t last = T - 1;

    float acc_mag = std::sqrt(
        imu[last * 6 + 0] * imu[last * 6 + 0] +
        imu[last * 6 + 1] * imu[last * 6 + 1] +
        imu[last * 6 + 2] * imu[last * 6 + 2]);

    float gyro_mag = std::sqrt(
        imu[last * 6 + 3] * imu[last * 6 + 3] +
        imu[last * 6 + 4] * imu[last * 6 + 4] +
        imu[last * 6 + 5] * imu[last * 6 + 5]);

    // IMU 运动强度作为调制因子
    float motion_scale = std::min(1.0f, (acc_mag + gyro_mag) * 0.1f);
    float static_scale = 1.0f - motion_scale;

    std::vector<std::size_t> out_shape = {1, C, H, W};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create IMU-visual fusion output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    std::size_t total = static_cast<std::size_t>(C) * H * W;
    for (std::size_t i = 0; i < total; ++i) {
        // 运动时增强特征，静止时保持原样
        out_data[i] = v_data[i] * (1.0f + motion_scale * 0.2f);
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Temporal Multimodal Fusion
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> temporal_multimodal_fusion(
    const std::vector<std::vector<Tensor>>& temporal_features,
    const FusionConfig& config)
{
    if (temporal_features.empty() || temporal_features[0].empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Temporal features empty");
    }

    // 对每帧做多模态融合，然后时间加权平均
    std::uint32_t T = static_cast<std::uint32_t>(temporal_features.size());

    // 融合第一帧
    auto first_fused = concat_fusion(temporal_features[0], config);
    if (!first_fused.ok()) return first_fused;

    const auto& f0_shape = first_fused.value().shape();
    std::uint32_t C = static_cast<std::uint32_t>(f0_shape[1]);
    std::uint32_t H = static_cast<std::uint32_t>(f0_shape[2]);
    std::uint32_t W = static_cast<std::uint32_t>(f0_shape[3]);
    std::size_t total = static_cast<std::size_t>(C) * H * W;

    std::vector<double> accum(total, 0.0);
    const float* f0_data = static_cast<const float*>(first_fused.value().data());

    // 指数衰减权重
    float total_weight = 0.0f;
    for (std::uint32_t t = 0; t < T; ++t) {
        float w = std::exp(-static_cast<float>(T - 1 - t) * 0.5f);
        total_weight += w;

        if (t == 0) {
            for (std::size_t i = 0; i < total; ++i)
                accum[i] += w * static_cast<double>(f0_data[i]);
        } else {
            auto fused = concat_fusion(temporal_features[t], config);
            if (fused.ok()) {
                const float* f_data = static_cast<const float*>(fused.value().data());
                for (std::size_t i = 0; i < total; ++i)
                    accum[i] += w * static_cast<double>(f_data[i]);
            }
        }
    }

    std::vector<std::size_t> out_shape = {1, C, H, W};
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return Error<Tensor>(ErrorCode::INFER_FAILED, "Failed to create temporal fusion output");

    auto& out = result.value();
    float* out_data = static_cast<float*>(out.data());

    if (total_weight > 0.0f) {
        for (std::size_t i = 0; i < total; ++i)
            out_data[i] = static_cast<float>(accum[i] / total_weight);
    }

    return std::move(out);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Adaptive Fusion Weights
// ═══════════════════════════════════════════════════════════════════════════════

std::vector<float> adaptive_fusion_weights(
    const std::vector<Tensor>& features)
{
    if (features.empty()) return {};

    std::vector<float> weights(features.size());
    float total = 0.0f;

    for (std::size_t i = 0; i < features.size(); ++i) {
        const auto& s = features[i].shape();
        std::size_t n = 1;
        for (auto d : s) n *= d;
        const float* data = static_cast<const float*>(features[i].data());

        // 基于特征方差计算权重（高方差 = 更重要的信息）
        float mean = 0.0f, var = 0.0f;
        for (std::size_t j = 0; j < n; ++j) mean += data[j];
        mean /= static_cast<float>(n);
        for (std::size_t j = 0; j < n; ++j) {
            float diff = data[j] - mean;
            var += diff * diff;
        }
        var /= static_cast<float>(n);

        weights[i] = var + 1e-6f;
        total += weights[i];
    }

    if (total > 0.0f) {
        for (auto& w : weights) w /= total;
    }

    return weights;
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Normalize Features
// ═══════════════════════════════════════════════════════════════════════════════

std::vector<Tensor> normalize_features(
    const std::vector<Tensor>& features,
    const std::string& method)
{
    std::vector<Tensor> normalized;
    normalized.reserve(features.size());

    for (const auto& feat : features) {
        const auto& s = feat.shape();
        std::size_t n = 1;
        for (auto d : s) n *= d;
        const float* src = static_cast<const float*>(feat.data());

        auto result = Tensor::create(std::vector<std::size_t>(s.begin(), s.end()), DType::FLOAT32);
        if (!result.ok()) continue;

        auto& out = result.value();
        float* dst = static_cast<float*>(out.data());

        if (method == "l2") {
            float norm = l2_norm(src, n);
            for (std::size_t i = 0; i < n; ++i) dst[i] = src[i] / norm;
        } else if (method == "batch" || method == "layer") {
            // 简化：全局均值方差归一化
            float mean = 0.0f, var = 0.0f;
            for (std::size_t i = 0; i < n; ++i) mean += src[i];
            mean /= static_cast<float>(n);
            for (std::size_t i = 0; i < n; ++i) {
                float diff = src[i] - mean;
                var += diff * diff;
            }
            var /= static_cast<float>(n);
            float stddev = std::sqrt(var + 1e-5f);
            for (std::size_t i = 0; i < n; ++i) dst[i] = (src[i] - mean) / stddev;
        } else {
            // instance norm: 不做额外归一化
            std::memcpy(dst, src, n * sizeof(float));
        }

        normalized.push_back(std::move(out));
    }

    return normalized;
}

} // namespace operators
} // namespace qoocore
