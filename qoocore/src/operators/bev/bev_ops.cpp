/**
 * @file bev_ops.cpp
 * @brief BEV 变换算子实现
 *
 * 实现 LSS（Lift-Splat-Shoot）、Cross-Attention、IPM 三种 BEV 变换方法，
 * 以及体素池化、多相机投影拼接、时间融合等辅助算子。
 *
 * 算法参考：
 *  - LSS: "Lift, Splat, Shoot" (Philion & Fidler, ECCV 2020)
 *  - BEVFormer: "BEVFormer: Learning Bird's-Eye-View..." (Li et al., ECCV 2022)
 *  - BEVFusion: "BEVFusion: Multi-Task Multi-Sensor Fusion..." (Liu et al., ICRA 2023)
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/operators/bev_ops.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <numeric>
#include <unordered_map>

#ifdef QOOCORE_ENABLE_PROFILING
#  include <chrono>
#endif

namespace qoocore {
namespace operators {

// ═══════════════════════════════════════════════════════════════════════════════
//  内部辅助函数
// ═══════════════════════════════════════════════════════════════════════════════

namespace {

/**
 * @brief 安全分配并清零张量数据缓冲区
 */
template<typename T>
std::unique_ptr<T[]> allocate_zeros(std::size_t count) {
    auto buf = std::make_unique<T[]>(count);
    std::memset(buf.get(), 0, count * sizeof(T));
    return buf;
}

/**
 * @brief 3D 索引 → 1D 偏移（NCHW 布局）
 */
[[nodiscard]] inline std::size_t nchw_idx(
    std::uint32_t n, std::uint32_t c,
    std::uint32_t h, std::uint32_t w,
    std::uint32_t C, std::uint32_t H, std::uint32_t W) noexcept
{
    return (static_cast<std::size_t>(n) * C * H * W) +
           (static_cast<std::size_t>(c) * H * W) +
           (static_cast<std::size_t>(h) * W) +
           static_cast<std::size_t>(w);
}

/**
 * @brief 5D 索引 → 1D 偏移（NCDHW 布局）
 */
[[nodiscard]] inline std::size_t ncdhw_idx(
    std::uint32_t n, std::uint32_t c,
    std::uint32_t d, std::uint32_t h, std::uint32_t w,
    std::uint32_t C, std::uint32_t D, std::uint32_t H, std::uint32_t W) noexcept
{
    return (static_cast<std::size_t>(n) * C * D * H * W) +
           (static_cast<std::size_t>(c) * D * H * W) +
           (static_cast<std::size_t>(d) * H * W) +
           (static_cast<std::size_t>(h) * W) +
           static_cast<std::size_t>(w);
}

/**
 * @brief 安全裁剪值到有效范围
 */
[[nodiscard]] inline float clamp_val(float v, float lo, float hi) noexcept {
    return std::max(lo, std::min(hi, v));
}

/**
 * @brief 双线性插值（2D 特征图采样）
 *
 * @param data   特征数据指针
 * @param C      通道数
 * @param H      高度
 * @param W      宽度
 * @param x      归一化 x 坐标 [0, W-1]
 * @param y      归一化 y 坐标 [0, H-1]
 * @param out    输出通道值数组 [C]
 */
void bilinear_sample_2d(
    const float* data, std::uint32_t C, std::uint32_t H, std::uint32_t W,
    float x, float y, float* out)
{
    // 边界处理
    x = clamp_val(x, 0.0f, static_cast<float>(W - 1));
    y = clamp_val(y, 0.0f, static_cast<float>(H - 1));

    std::uint32_t x0 = static_cast<std::uint32_t>(x);
    std::uint32_t y0 = static_cast<std::uint32_t>(y);
    std::uint32_t x1 = std::min(x0 + 1, W - 1);
    std::uint32_t y1 = std::min(y0 + 1, H - 1);

    float dx = x - static_cast<float>(x0);
    float dy = y - static_cast<float>(y0);

    for (std::uint32_t c = 0; c < C; ++c) {
        float v00 = data[nchw_idx(0, c, y0, x0, C, H, W)];
        float v01 = data[nchw_idx(0, c, y0, x1, C, H, W)];
        float v10 = data[nchw_idx(0, c, y1, x0, C, H, W)];
        float v11 = data[nchw_idx(0, c, y1, x1, C, H, W)];

        // 双线性插值
        float top    = v00 * (1.0f - dx) + v01 * dx;
        float bottom = v10 * (1.0f - dx) + v11 * dx;
        out[c]       = top  * (1.0f - dy) + bottom * dy;
    }
}

/**
 * @brief 世界坐标 → 像素坐标（使用相机内外参）
 */
std::pair<float, float> world_to_pixel(
    float wx, float wy, float wz,
    const CameraIntrinsics& intr, const CameraExtrinsics& extr)
{
    // 世界坐标 → 相机坐标
    float cx = extr.R[0]*wx + extr.R[1]*wy + extr.R[2]*wz + extr.t[0];
    float cy = extr.R[3]*wx + extr.R[4]*wy + extr.R[5]*wz + extr.t[1];
    float cz = extr.R[6]*wx + extr.R[7]*wy + extr.R[8]*wz + extr.t[2];

    // 相机坐标 → 像素坐标
    if (cz <= 0.0f) return {-1.0f, -1.0f};

    float u = intr.fx * cx / cz + intr.cx;
    float v = intr.fy * cy / cz + intr.cy;

    // 畸变校正（简化径向畸变模型）
    float r2 = (u - intr.cx) * (u - intr.cx) / (intr.fx * intr.fx) +
               (v - intr.cy) * (v - intr.cy) / (intr.fy * intr.fy);
    float k_radial = 1.0f + intr.k1 * r2 + intr.k2 * r2 * r2;
    u = intr.cx + (u - intr.cx) * k_radial;
    v = intr.cy + (v - intr.cy) * k_radial;

    return {u, v};
}

/**
 * @brief 像素坐标 → 归一化相机坐标
 */
std::pair<float, float> pixel_to_normalized(
    float u, float v, const CameraIntrinsics& intr)
{
    float nx = (u - intr.cx) / intr.fx;
    float ny = (v - intr.cy) / intr.fy;
    return {nx, ny};
}

} // anonymous namespace

// ═══════════════════════════════════════════════════════════════════════════════
//  LSS Lift-Splat-Shoot 实现
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> lss_transform(
    const std::vector<Tensor>& camera_features,
    const std::vector<Tensor>& depth_probs,
    const std::vector<CameraIntrinsics>& camera_intrinsics,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config)
{
    if (camera_features.empty() || depth_probs.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Camera features or depth probabilities are empty");
    }

    if (camera_features.size() != camera_intrinsics.size() ||
        camera_features.size() != camera_extrinsics.size() ||
        camera_features.size() != depth_probs.size()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Mismatched camera/intrinsics/extrinsics/depth count");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(camera_features.size());
    const std::uint32_t C = camera_features[0].shape()[1];   // 特征通道
    const std::uint32_t H = camera_features[0].shape()[2];   // 图像高度
    const std::uint32_t W = camera_features[0].shape()[3];   // 图像宽度
    const std::uint32_t D = config.depth_bins;                // 深度 bins

    const std::uint32_t bev_H = config.bev_height();
    const std::uint32_t bev_W = config.bev_width();
    const std::uint32_t bev_C = config.bev_dim;

    // ══ 阶段 1: Lift — 深度估计与特征提升 ══
    // 为每个相机生成 [1][C][D][H][W] 的提升特征
    std::vector<std::unique_ptr<float[]>> lifted_features(N);
    std::vector<std::unique_ptr<std::uint32_t[]>> lifted_counts(N);

    for (std::uint32_t n = 0; n < N; ++n) {
        const float* feat_data = static_cast<const float*>(camera_features[n].data());
        const float* depth_data = static_cast<const float*>(depth_probs[n].data());

        auto lifted = allocate_zeros<float>(C * D * H * W);
        auto counts = allocate_zeros<std::uint32_t>(D * H * W);

        for (std::uint32_t d = 0; d < D; ++d) {
            for (std::uint32_t h = 0; h < H; ++h) {
                for (std::uint32_t w = 0; w < W; ++w) {
                    float prob = depth_data[nchw_idx(0, d, h, w, D, H, W)];
                    if (prob < 1e-6f) continue;

                    std::size_t base_idx = static_cast<std::size_t>(d) * H * W +
                                           static_cast<std::size_t>(h) * W + w;
                    counts[base_idx] = 1;

                    for (std::uint32_t c = 0; c < C; ++c) {
                        float feat_val = feat_data[nchw_idx(0, c, h, w, C, H, W)];
                        lifted[ncdhw_idx(0, c, d, h, w, C, D, H, W)] =
                            feat_val * prob;
                    }
                }
            }
        }

        lifted_features[n] = std::move(lifted);
        lifted_counts[n] = std::move(counts);
    }

    // ══ 阶段 2: Splat — 投影到 BEV 空间 ══
    auto bev_data = allocate_zeros<float>(bev_C * bev_H * bev_W);
    auto bev_counts = allocate_zeros<std::uint32_t>(bev_H * bev_W);

    // 深度值映射到实际距离
    float depth_step = (config.depth_max - config.depth_min) /
                       static_cast<float>(D - 1);

    for (std::uint32_t n = 0; n < N; ++n) {
        const auto& intr = camera_intrinsics[n];
        const auto& extr = camera_extrinsics[n];
        const float* lifted = lifted_features[n].get();

        // 相机中心在世界坐标系中的位置
        float cam_x = -extr.R[0]*extr.t[0] - extr.R[3]*extr.t[1] - extr.R[6]*extr.t[2];
        float cam_y = -extr.R[1]*extr.t[0] - extr.R[4]*extr.t[1] - extr.R[7]*extr.t[2];
        float cam_z = -extr.R[2]*extr.t[0] - extr.R[5]*extr.t[1] - extr.R[8]*extr.t[2];

        for (std::uint32_t d = 0; d < D; ++d) {
            float depth = config.depth_min + depth_step * static_cast<float>(d);

            for (std::uint32_t h = 0; h < H; h += 2) {   // 步长 2 加速
                for (std::uint32_t w = 0; w < W; w += 2) {
                    // 像素 → 归一化坐标 → 相机坐标 → 世界坐标
                    auto [nx, ny] = pixel_to_normalized(
                        static_cast<float>(w), static_cast<float>(h), intr);

                    float cx_cam = nx * depth;
                    float cy_cam = ny * depth;
                    float cz_cam = depth;

                    // 相机坐标 → 世界坐标（逆变换）
                    float wx = extr.R[0]*cx_cam + extr.R[3]*cy_cam +
                               extr.R[6]*cz_cam + cam_x;
                    float wy = extr.R[1]*cx_cam + extr.R[4]*cy_cam +
                               extr.R[7]*cz_cam + cam_y;
                    float wz = extr.R[2]*cx_cam + extr.R[5]*cy_cam +
                               extr.R[8]*cz_cam + cam_z;

                    auto [gx, gy] = world_to_bev_grid(wx, wy, config);
                    if (gx < 0 || gy < 0) continue;

                    std::uint32_t ugx = static_cast<std::uint32_t>(gx);
                    std::uint32_t ugy = static_cast<std::uint32_t>(gy);
                    if (ugx >= bev_W || ugy >= bev_H) continue;

                    // 累加特征到 BEV
                    std::size_t bev_idx = static_cast<std::size_t>(ugy) * bev_W + ugx;
                    bev_counts[bev_idx]++;

                    for (std::uint32_t c = 0; c < std::min(C, bev_C); ++c) {
                        float feat = lifted[ncdhw_idx(0, c, d, h, w, C, D, H, W)];
                        bev_data[static_cast<std::size_t>(c) * bev_H * bev_W + bev_idx] += feat;
                    }
                }
            }
        }
    }

    // 归一化：除以计数
    for (std::uint32_t gy = 0; gy < bev_H; ++gy) {
        for (std::uint32_t gx = 0; gx < bev_W; ++gx) {
            std::size_t idx = static_cast<std::size_t>(gy) * bev_W + gx;
            std::uint32_t cnt = bev_counts[idx];
            if (cnt > 0) {
                float inv = 1.0f / static_cast<float>(cnt);
                for (std::uint32_t c = 0; c < bev_C; ++c) {
                    bev_data[static_cast<std::size_t>(c) * bev_H * bev_W + idx] *= inv;
                }
            }
        }
    }

    // ══ 阶段 3: Shoot — 构建输出张量 ══
    std::vector<std::size_t> bev_shape = {1, bev_C, bev_H, bev_W};
    auto result = Tensor::create(bev_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create BEV output tensor");
    }

    auto& tensor = result.value();
    std::memcpy(tensor.data(), bev_data.get(),
                bev_C * bev_H * bev_W * sizeof(float));

    return std::move(tensor);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Cross-Attention BEV 实现
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> cross_attention_bev(
    const std::vector<Tensor>& camera_features,
    const Tensor& bev_queries,
    const std::vector<CameraIntrinsics>& camera_intrinsics,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config)
{
    if (camera_features.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Camera features are empty");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(camera_features.size());
    const std::uint32_t bev_H = config.bev_height();
    const std::uint32_t bev_W = config.bev_width();
    const std::uint32_t bev_C = config.bev_dim;
    const std::uint32_t num_heads = config.num_heads;
    const std::uint32_t head_dim = bev_C / num_heads;

    if (bev_C % num_heads != 0) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "BEV dim must be divisible by num_heads");
    }

    const auto& q_shape = bev_queries.shape();
    if (q_shape.size() != 2 || q_shape[1] != bev_C) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "BEV queries shape must be [Q, bev_dim]");
    }

    const std::uint32_t Q = static_cast<std::uint32_t>(q_shape[0]);
    const float* q_data = static_cast<const float*>(bev_queries.data());

    // 初始化 BEV 特征（全零）
    auto bev_data = allocate_zeros<float>(bev_C * bev_H * bev_W);

    // 对每个 BEV 网格位置执行 Cross-Attention
    for (std::uint32_t gy = 0; gy < bev_H; ++gy) {
        for (std::uint32_t gx = 0; gx < bev_W; ++gx) {
            // 获取 BEV 网格对应的世界坐标
            auto [world_x, world_y] = bev_grid_to_world(gx, gy, config);

            // 收集所有相机中可见的参考点特征
            std::vector<std::pair<std::uint32_t, std::vector<float>>> ref_features;

            for (std::uint32_t n = 0; n < N; ++n) {
                const auto& intr = camera_intrinsics[n];
                const auto& extr = camera_extrinsics[n];

                // 将世界坐标投影到相机像素坐标
                auto [u, v] = world_to_pixel(world_x, world_y, 0.0f, intr, extr);

                if (u < 0 || v < 0 || u >= intr.width || v >= intr.height) {
                    continue;  // 不在该相机视野内
                }

                // 从相机特征中采样
                const float* cam_data = static_cast<const float*>(
                    camera_features[n].data());
                const auto& c_shape = camera_features[n].shape();
                std::uint32_t cam_C = static_cast<std::uint32_t>(c_shape[1]);
                std::uint32_t cam_H = static_cast<std::uint32_t>(c_shape[2]);
                std::uint32_t cam_W = static_cast<std::uint32_t>(c_shape[3]);

                // 双线性采样
                float nx = u / static_cast<float>(intr.width) *
                           static_cast<float>(cam_W);
                float ny = v / static_cast<float>(intr.height) *
                           static_cast<float>(cam_H);

                std::vector<float> sampled(cam_C);
                bilinear_sample_2d(cam_data, cam_C, cam_H, cam_W, nx, ny,
                                   sampled.data());

                ref_features.emplace_back(n, std::move(sampled));
            }

            if (ref_features.empty()) continue;

            // ── 简化的 Cross-Attention 计算 ──
            // Q: BEV query [1][bev_C]
            // K: 参考点特征 [R][bev_C]
            // V: 参考点特征 [R][bev_C]
            //
            // 对每个注意力头执行 scaled dot-product attention

            std::vector<float> output(bev_C, 0.0f);
            const std::uint32_t R = static_cast<std::uint32_t>(ref_features.size());
            float scale = 1.0f / std::sqrt(static_cast<float>(head_dim));

            for (std::uint32_t h = 0; h < num_heads; ++h) {
                std::uint32_t h_offset = h * head_dim;

                // 计算每个参考点的注意力分数
                std::vector<float> attn_scores(R);
                float max_score = -1e9f;

                for (std::uint32_t r = 0; r < R; ++r) {
                    float score = 0.0f;
                    const auto& ref = ref_features[r].second;
                    for (std::uint32_t d = 0; d < head_dim; ++d) {
                        score += q_data[h_offset + d] * ref[std::min(h_offset + d,
                                 static_cast<std::uint32_t>(ref.size() - 1))];
                    }
                    score *= scale;
                    attn_scores[r] = score;
                    max_score = std::max(max_score, score);
                }

                // Softmax
                float sum_exp = 0.0f;
                for (std::uint32_t r = 0; r < R; ++r) {
                    attn_scores[r] = std::exp(attn_scores[r] - max_score);
                    sum_exp += attn_scores[r];
                }

                if (sum_exp > 0.0f) {
                    for (std::uint32_t r = 0; r < R; ++r) {
                        attn_scores[r] /= sum_exp;
                    }
                }

                // 加权聚合
                for (std::uint32_t d = 0; d < head_dim; ++d) {
                    float sum = 0.0f;
                    for (std::uint32_t r = 0; r < R; ++r) {
                        const auto& ref = ref_features[r].second;
                        sum += attn_scores[r] * ref[std::min(h_offset + d,
                                     static_cast<std::uint32_t>(ref.size() - 1))];
                    }
                    output[h_offset + d] = sum;
                }
            }

            // 写入 BEV 特征
            std::size_t bev_offset = static_cast<std::size_t>(gy) * bev_W + gx;
            for (std::uint32_t c = 0; c < bev_C; ++c) {
                bev_data[static_cast<std::size_t>(c) * bev_H * bev_W + bev_offset] =
                    output[c];
            }
        }
    }

    // 构建输出张量
    std::vector<std::size_t> bev_shape = {1, bev_C, bev_H, bev_W};
    auto result = Tensor::create(bev_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create BEV output tensor");
    }

    auto& tensor = result.value();
    std::memcpy(tensor.data(), bev_data.get(),
                bev_C * bev_H * bev_W * sizeof(float));

    return std::move(tensor);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  IPM 逆透视变换实现
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> ipm_transform(
    const std::vector<Tensor>& camera_features,
    const std::vector<CameraIntrinsics>& camera_intrinsics,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config)
{
    if (camera_features.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Camera features are empty");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(camera_features.size());
    const std::uint32_t bev_H = config.bev_height();
    const std::uint32_t bev_W = config.bev_width();

    // 使用第一个相机特征的通道数作为 BEV 特征维度
    const auto& c0_shape = camera_features[0].shape();
    const std::uint32_t bev_C = static_cast<std::uint32_t>(c0_shape[1]);

    auto bev_data = allocate_zeros<float>(bev_C * bev_H * bev_W);
    auto bev_counts = allocate_zeros<std::uint32_t>(bev_H * bev_W);

    // 对每个 BEV 网格点，通过 IPM 映射到每个相机图像采样
    for (std::uint32_t gy = 0; gy < bev_H; ++gy) {
        for (std::uint32_t gx = 0; gx < bev_W; ++gx) {
            auto [wx, wy] = bev_grid_to_world(gx, gy, config);
            // 地面平面假设 z = 0
            float wz = 0.0f;

            for (std::uint32_t n = 0; n < N; ++n) {
                const auto& intr = camera_intrinsics[n];
                const auto& extr = camera_extrinsics[n];

                auto [u, v] = world_to_pixel(wx, wy, wz, intr, extr);

                if (u < 0 || v < 0 || u >= intr.width || v >= intr.height) {
                    continue;
                }

                const float* cam_data = static_cast<const float*>(
                    camera_features[n].data());
                const auto& c_shape = camera_features[n].shape();
                std::uint32_t cam_C = static_cast<std::uint32_t>(c_shape[1]);
                std::uint32_t cam_H = static_cast<std::uint32_t>(c_shape[2]);
                std::uint32_t cam_W = static_cast<std::uint32_t>(c_shape[3]);

                float nx = u / static_cast<float>(intr.width) *
                           static_cast<float>(cam_W);
                float ny = v / static_cast<float>(intr.height) *
                           static_cast<float>(cam_H);

                std::vector<float> sampled(cam_C);
                bilinear_sample_2d(cam_data, cam_C, cam_H, cam_W, nx, ny,
                                   sampled.data());

                std::size_t bev_idx = static_cast<std::size_t>(gy) * bev_W + gx;
                bev_counts[bev_idx]++;

                for (std::uint32_t c = 0; c < std::min(cam_C, bev_C); ++c) {
                    bev_data[static_cast<std::size_t>(c) * bev_H * bev_W + bev_idx] +=
                        sampled[c];
                }
            }
        }
    }

    // 归一化
    for (std::uint32_t gy = 0; gy < bev_H; ++gy) {
        for (std::uint32_t gx = 0; gx < bev_W; ++gx) {
            std::size_t idx = static_cast<std::size_t>(gy) * bev_W + gx;
            if (bev_counts[idx] > 0) {
                float inv = 1.0f / static_cast<float>(bev_counts[idx]);
                for (std::uint32_t c = 0; c < bev_C; ++c) {
                    bev_data[static_cast<std::size_t>(c) * bev_H * bev_W + idx] *= inv;
                }
            }
        }
    }

    std::vector<std::size_t> bev_shape = {1, bev_C, bev_H, bev_W};
    auto result = Tensor::create(bev_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create BEV output tensor");
    }

    auto& tensor = result.value();
    std::memcpy(tensor.data(), bev_data.get(),
                bev_C * bev_H * bev_W * sizeof(float));

    return std::move(tensor);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  BEV 体素池化实现
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> bev_voxel_pooling(
    const Tensor& voxel_features,
    const BEVConfig& bev_config,
    const std::string& pool_type)
{
    const auto& shape = voxel_features.shape();
    if (shape.size() != 5) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Voxel features must be 5D: [N][C][D][H][W]");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(shape[0]);
    const std::uint32_t C = static_cast<std::uint32_t>(shape[1]);
    const std::uint32_t D = static_cast<std::uint32_t>(shape[2]);
    const std::uint32_t H = static_cast<std::uint32_t>(shape[3]);
    const std::uint32_t W = static_cast<std::uint32_t>(shape[4]);

    const float* data = static_cast<const float*>(voxel_features.data());

    auto bev_data = allocate_zeros<float>(C * H * W);
    auto bev_counts = (pool_type == "mean")
        ? std::make_unique<std::uint32_t[]>(H * W) : nullptr;

    if (pool_type == "max") {
        // Max pooling: 对每个 (c,h,w) 沿 D 维度取最大值
        for (std::uint32_t c = 0; c < C; ++c) {
            for (std::uint32_t h = 0; h < H; ++h) {
                for (std::uint32_t w = 0; w < W; ++w) {
                    float max_val = -1e9f;
                    for (std::uint32_t d = 0; d < D; ++d) {
                        float val = data[ncdhw_idx(0, c, d, h, w, C, D, H, W)];
                        max_val = std::max(max_val, val);
                    }
                    bev_data[nchw_idx(0, c, h, w, C, H, W)] = max_val;
                }
            }
        }
    } else {
        // Mean pooling: 对每个 (c,h,w) 沿 D 维度取平均值
        for (std::uint32_t c = 0; c < C; ++c) {
            for (std::uint32_t h = 0; h < H; ++h) {
                for (std::uint32_t w = 0; w < W; ++w) {
                    float sum = 0.0f;
                    for (std::uint32_t d = 0; d < D; ++d) {
                        sum += data[ncdhw_idx(0, c, d, h, w, C, D, H, W)];
                    }
                    bev_data[nchw_idx(0, c, h, w, C, H, W)] =
                        sum / static_cast<float>(D);
                }
            }
        }
    }

    std::vector<std::size_t> bev_shape = {N, C, H, W};
    auto result = Tensor::create(bev_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create BEV pooling output tensor");
    }

    auto& tensor = result.value();
    std::memcpy(tensor.data(), bev_data.get(),
                N * C * H * W * sizeof(float));

    return std::move(tensor);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  BEV 多相机投影拼接
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> bev_concat_project(
    const std::vector<Tensor>& camera_features,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config)
{
    if (camera_features.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Camera features are empty");
    }

    const std::uint32_t N = static_cast<std::uint32_t>(camera_features.size());
    const std::uint32_t bev_H = config.bev_height();
    const std::uint32_t bev_W = config.bev_width();

    // 计算总通道数
    std::uint32_t total_C = 0;
    for (std::uint32_t n = 0; n < N; ++n) {
        total_C += static_cast<std::uint32_t>(camera_features[n].shape()[1]);
    }

    auto bev_data = allocate_zeros<float>(total_C * bev_H * bev_W);

    std::uint32_t c_offset = 0;
    for (std::uint32_t n = 0; n < N; ++n) {
        const float* cam_data = static_cast<const float*>(
            camera_features[n].data());
        const auto& c_shape = camera_features[n].shape();
        std::uint32_t cam_C = static_cast<std::uint32_t>(c_shape[1]);
        std::uint32_t cam_H = static_cast<std::uint32_t>(c_shape[2]);
        std::uint32_t cam_W = static_cast<std::uint32_t>(c_shape[3]);

        // 相机中心在世界坐标中的位置
        const auto& extr = camera_extrinsics[n];
        float cam_x = -extr.R[0]*extr.t[0] - extr.R[3]*extr.t[1] - extr.R[6]*extr.t[2];
        float cam_y = -extr.R[1]*extr.t[0] - extr.R[4]*extr.t[1] - extr.R[7]*extr.t[2];

        // 相机朝向（简化：使用相机位置到 BEV 中心的方向）
        float center_x = (config.x_max + config.x_min) * 0.5f;
        float center_y = (config.y_max + config.y_min) * 0.5f;

        // 将每个 BEV 网格点投影到相机特征图
        for (std::uint32_t gy = 0; gy < bev_H; ++gy) {
            for (std::uint32_t gx = 0; gx < bev_W; ++gx) {
                auto [wx, wy] = bev_grid_to_world(gx, gy, config);

                // 使用简化的径向投影（假设相机朝向 BEV 中心区域）
                float dx = wx - cam_x;
                float dy = wy - cam_y;
                float dist = std::sqrt(dx*dx + dy*dy);

                if (dist < 0.1f) continue;

                // 映射到特征图坐标（径向→像素）
                float angle = std::atan2(dy, dx);
                float normalized_angle = (angle + 3.14159265f) /
                                         (2.0f * 3.14159265f);

                float nx = normalized_angle * static_cast<float>(cam_W);
                float ny = (1.0f - std::min(dist / 20.0f, 1.0f)) *
                           static_cast<float>(cam_H);

                std::vector<float> sampled(cam_C);
                bilinear_sample_2d(cam_data, cam_C, cam_H, cam_W, nx, ny,
                                   sampled.data());

                std::size_t bev_idx = static_cast<std::size_t>(gy) * bev_W + gx;
                for (std::uint32_t c = 0; c < cam_C; ++c) {
                    bev_data[static_cast<std::size_t>(c_offset + c) * bev_H * bev_W +
                             bev_idx] = sampled[c];
                }
            }
        }

        c_offset += cam_C;
    }

    std::vector<std::size_t> bev_shape = {1, total_C, bev_H, bev_W};
    auto result = Tensor::create(bev_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create BEV concat output tensor");
    }

    auto& tensor = result.value();
    std::memcpy(tensor.data(), bev_data.get(),
                total_C * bev_H * bev_W * sizeof(float));

    return std::move(tensor);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  BEV 时间融合
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> bev_temporal_fusion(
    const Tensor& current_bev,
    const Tensor& prev_bev,
    float decay_factor)
{
    const auto& curr_shape = current_bev.shape();
    const auto& prev_shape = prev_bev.shape();

    if (curr_shape != prev_shape) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "Current and previous BEV shapes must match");
    }

    if (curr_shape.size() != 4) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
            "BEV tensor must be 4D: [1][C][H][W]");
    }

    const std::uint32_t C = static_cast<std::uint32_t>(curr_shape[1]);
    const std::uint32_t H = static_cast<std::uint32_t>(curr_shape[2]);
    const std::uint32_t W = static_cast<std::uint32_t>(curr_shape[3]);
    const std::size_t total = static_cast<std::size_t>(C) * H * W;

    const float* curr_data = static_cast<const float*>(current_bev.data());
    const float* prev_data = static_cast<const float*>(prev_bev.data());

    float alpha = clamp_val(decay_factor, 0.0f, 1.0f);
    float beta  = 1.0f - alpha;

    auto fused_data = std::make_unique<float[]>(total);
    for (std::size_t i = 0; i < total; ++i) {
        fused_data[i] = alpha * curr_data[i] + beta * prev_data[i];
    }

    std::vector<std::size_t> out_shape(curr_shape.begin(), curr_shape.end());
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) {
        return Error<Tensor>(ErrorCode::INFER_FAILED,
            "Failed to create temporal fusion output tensor");
    }

    auto& tensor = result.value();
    std::memcpy(tensor.data(), fused_data.get(), total * sizeof(float));

    return std::move(tensor);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  BEV 变换总入口
// ═══════════════════════════════════════════════════════════════════════════════

Result<Tensor> bev_transform(
    const std::vector<Tensor>& camera_features,
    const std::vector<CameraIntrinsics>& camera_intrinsics,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config)
{
    switch (config.method) {
        case BEVMethod::LSS: {
            // LSS 需要深度概率，这里生成一个均匀深度分布作为默认值
            const std::uint32_t N = static_cast<std::uint32_t>(camera_features.size());
            std::vector<Tensor> depth_probs;
            depth_probs.reserve(N);

            const auto& c0_shape = camera_features[0].shape();
            std::uint32_t H = static_cast<std::uint32_t>(c0_shape[2]);
            std::uint32_t W = static_cast<std::uint32_t>(c0_shape[3]);
            std::uint32_t D = config.depth_bins;

            std::vector<std::size_t> depth_shape = {1, D, H, W};
            for (std::uint32_t n = 0; n < N; ++n) {
                auto dp = Tensor::create(depth_shape, DType::FLOAT32);
                if (!dp.ok()) {
                    return Error<Tensor>(ErrorCode::INFER_FAILED,
                        "Failed to create default depth prob tensor");
                }
                auto& dpt = dp.value();
                float* d_data = static_cast<float*>(dpt.data());
                float uniform = 1.0f / static_cast<float>(D);
                for (std::size_t i = 0; i < static_cast<std::size_t>(D) * H * W; ++i) {
                    d_data[i] = uniform;
                }
                depth_probs.push_back(std::move(dpt));
            }

            return lss_transform(camera_features, depth_probs,
                                 camera_intrinsics, camera_extrinsics, config);
        }
        case BEVMethod::CROSS_ATTENTION: {
            // Cross-Attention 需要 BEV queries，生成可学习的位置编码
            const std::uint32_t bev_H = config.bev_height();
            const std::uint32_t bev_W = config.bev_width();
            const std::uint32_t Q = bev_H * bev_W;
            const std::uint32_t bev_C = config.bev_dim;

            std::vector<std::size_t> q_shape = {Q, bev_C};
            auto q_result = Tensor::create(q_shape, DType::FLOAT32);
            if (!q_result.ok()) {
                return Error<Tensor>(ErrorCode::INFER_FAILED,
                    "Failed to create BEV queries tensor");
            }
            auto& queries = q_result.value();
            float* q_data = static_cast<float*>(queries.data());

            // 使用位置编码初始化 queries
            for (std::uint32_t gy = 0; gy < bev_H; ++gy) {
                for (std::uint32_t gx = 0; gx < bev_W; ++gx) {
                    auto [wx, wy] = bev_grid_to_world(gx, gy, config);
                    std::size_t q_idx = (static_cast<std::size_t>(gy) * bev_W + gx) * bev_C;

                    for (std::uint32_t c = 0; c < bev_C; ++c) {
                        float pos_enc;
                        if (c % 2 == 0) {
                            pos_enc = std::sin(wx / std::pow(10000.0f,
                                static_cast<float>(c) / static_cast<float>(bev_C)));
                        } else {
                            pos_enc = std::cos(wy / std::pow(10000.0f,
                                static_cast<float>(c-1) / static_cast<float>(bev_C)));
                        }
                        q_data[q_idx + c] = pos_enc * 0.1f;
                    }
                }
            }

            return cross_attention_bev(camera_features, queries,
                                       camera_intrinsics, camera_extrinsics, config);
        }
        case BEVMethod::IPM:
            return ipm_transform(camera_features, camera_intrinsics,
                                 camera_extrinsics, config);
        case BEVMethod::TRANSFORMER:
            // Transformer 方法目前回退到 Cross-Attention
            {
                const std::uint32_t bev_H = config.bev_height();
                const std::uint32_t bev_W = config.bev_width();
                const std::uint32_t Q = bev_H * bev_W;
                const std::uint32_t bev_C = config.bev_dim;

                std::vector<std::size_t> q_shape = {Q, bev_C};
                auto q_result = Tensor::create(q_shape, DType::FLOAT32);
                if (!q_result.ok()) {
                    return Error<Tensor>(ErrorCode::INFER_FAILED,
                        "Failed to create BEV queries tensor");
                }
                return cross_attention_bev(camera_features, q_result.value(),
                                           camera_intrinsics, camera_extrinsics, config);
            }
        default:
            return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
                "Unknown BEV method: " + std::to_string(static_cast<int>(config.method)));
    }
}

} // namespace operators
} // namespace qoocore
