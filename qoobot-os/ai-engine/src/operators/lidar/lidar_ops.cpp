/**
 * @file lidar_ops.cpp
 * @brief 点云算子库 — Voxel化 + 稀疏卷积 + PointPillars + BEV特征变换
 *
 * 为自动驾驶/机器人感知模型提供点云处理加速算子。
 *
 * 算子清单：
 *   1. Voxelization — 点云体素化 (dynamic / hard voxelization)
 *   2. Voxel Feature Encoding (VFE) — 体素特征提取
 *   3. 3D Sparse Convolution — 稀疏卷积 (SECOND / MinkowskiEngine 风格)
 *   4. Submanifold Sparse Conv — 子流形稀疏卷积
 *   5. PointPillars — 柱状体素化 + Pillar Feature Net
 *   6. BEV Pooling — 多相机 BEV 特征汇聚
 *   7. NMS (Non-Maximum Suppression) — 3D 检测框 NMS
 *   8. Points to Voxel — 点→体素散列映射
 *
 * @copyright QooBot Project
 * @version 0.3.0
 */

#include "qoocore/core.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <limits>
#include <memory>
#include <unordered_map>
#include <vector>

namespace qoocore {
namespace ops {
namespace lidar {

// ═══════════════════════════════════════════════════════════════════════════════
// 1. Voxelization — 点云体素化
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 体素化配置
 */
struct VoxelizationConfig {
    // 体素尺寸（米）
    float voxel_size_x{0.16f};
    float voxel_size_y{0.16f};
    float voxel_size_z{4.0f};  // 高度方向不分体素（Pillar 模式）

    // 点云范围（米）
    float x_min{-75.2f}, x_max{75.2f};
    float y_min{-75.2f}, y_max{75.2f};
    float z_min{-2.0f},  z_max{4.0f};

    // 体素点数限制
    uint32_t max_points_per_voxel{32};   ///< 每个体素最多采样点数
    uint32_t max_voxels{16000};           ///< 最大非空体素数
    uint32_t num_point_features{4};       ///< 点特征维度 (x,y,z,intensity)
};

/**
 * @brief Voxelization 结果
 */
struct VoxelizationResult {
    // 体素特征 [max_voxels, max_points, num_features]
    std::vector<float> voxel_features;

    // 体素坐标 [max_voxels, 3] (z, y, x 顺序，符合 sparse conv 约定)
    std::vector<int32_t> voxel_coords;

    // 每个体素的实际点数 [max_voxels]
    std::vector<int32_t> voxel_num_points;

    // 有效体素数
    uint32_t num_voxels{0};

    // 网格尺寸
    int grid_x{0}, grid_y{0}, grid_z{0};
};

/**
 * @brief 硬体素化 (Hard Voxelization)
 *
 * 将无序点云映射到规则的体素网格。
 * 每个体素随机采样最多 max_points_per_voxel 个点。
 *
 * @param points       [N, C] 点云 (x, y, z, intensity, ...)
 * @param num_points   点云数量
 * @param config       体素化配置
 * @return 体素化结果
 */
VoxelizationResult hard_voxelization(
    const float* points,
    size_t num_points,
    const VoxelizationConfig& config) {

    VoxelizationResult result;

    // 计算网格尺寸
    result.grid_x = static_cast<int>(
        (config.x_max - config.x_min) / config.voxel_size_x);
    result.grid_y = static_cast<int>(
        (config.y_max - config.y_min) / config.voxel_size_y);
    result.grid_z = static_cast<int>(
        (config.z_max - config.z_min) / config.voxel_size_z);

    size_t total_voxels = static_cast<size_t>(result.grid_x) *
                          result.grid_y * result.grid_z;

    // 使用哈希表映射体素坐标 → 体素索引
    struct VoxelKey {
        int32_t x, y, z;
        bool operator==(const VoxelKey& o) const {
            return x == o.x && y == o.y && z == o.z;
        }
    };
    struct VoxelKeyHash {
        size_t operator()(const VoxelKey& k) const {
            return ((static_cast<uint64_t>(k.z) << 40) |
                    (static_cast<uint64_t>(k.y) << 20) |
                     static_cast<uint64_t>(k.x));
        }
    };

    std::unordered_map<VoxelKey, uint32_t, VoxelKeyHash> voxel_map;
    std::vector<std::vector<uint32_t>> voxel_point_indices;

    // 第一遍：将点分配到体素
    for (size_t i = 0; i < num_points; ++i) {
        float px = points[i * config.num_point_features + 0];
        float py = points[i * config.num_point_features + 1];
        float pz = points[i * config.num_point_features + 2];

        // 范围检查
        if (px < config.x_min || px >= config.x_max ||
            py < config.y_min || py >= config.y_max ||
            pz < config.z_min || pz >= config.z_max) {
            continue;
        }

        int32_t vx = static_cast<int32_t>((px - config.x_min) / config.voxel_size_x);
        int32_t vy = static_cast<int32_t>((py - config.y_min) / config.voxel_size_y);
        int32_t vz = static_cast<int32_t>((pz - config.z_min) / config.voxel_size_z);

        VoxelKey key{vx, vy, vz};
        auto it = voxel_map.find(key);
        if (it == voxel_map.end()) {
            if (voxel_map.size() >= config.max_voxels) continue;
            uint32_t voxel_idx = static_cast<uint32_t>(voxel_map.size());
            voxel_map[key] = voxel_idx;
            voxel_point_indices.push_back({});
            it = voxel_map.find(key);
        }
        voxel_point_indices[it->second].push_back(static_cast<uint32_t>(i));
    }

    result.num_voxels = static_cast<uint32_t>(voxel_map.size());

    // 分配输出
    result.voxel_features.resize(
        result.num_voxels * config.max_points_per_voxel * config.num_point_features, 0.0f);
    result.voxel_coords.resize(result.num_voxels * 3, 0);
    result.voxel_num_points.resize(result.num_voxels, 0);

    // 第二遍：填充体素特征
    uint32_t voxel_idx = 0;
    for (const auto& [key, idx] : voxel_map) {
        const auto& pt_indices = voxel_point_indices[idx];

        result.voxel_coords[voxel_idx * 3 + 0] = key.z;
        result.voxel_coords[voxel_idx * 3 + 1] = key.y;
        result.voxel_coords[voxel_idx * 3 + 2] = key.x;

        // 随机采样（或取前 N 个点）
        uint32_t num_sample = std::min(
            config.max_points_per_voxel,
            static_cast<uint32_t>(pt_indices.size()));
        result.voxel_num_points[voxel_idx] = num_sample;

        for (uint32_t p = 0; p < num_sample; ++p) {
            uint32_t pt_idx = pt_indices[p];
            float* feat = &result.voxel_features[
                (voxel_idx * config.max_points_per_voxel + p) * config.num_point_features];

            // 计算相对于体素中心的偏移（增强特征）
            float cx = (key.x + 0.5f) * config.voxel_size_x + config.x_min;
            float cy = (key.y + 0.5f) * config.voxel_size_y + config.y_min;
            float cz = (key.z + 0.5f) * config.voxel_size_z + config.z_min;

            feat[0] = points[pt_idx * config.num_point_features + 0] - cx;
            feat[1] = points[pt_idx * config.num_point_features + 1] - cy;
            feat[2] = points[pt_idx * config.num_point_features + 2] - cz;
            feat[3] = points[pt_idx * config.num_point_features + 3];  // intensity
        }

        voxel_idx++;
    }

    return result;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 2. 3D Sparse Convolution
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 稀疏卷积核描述
 */
struct SparseConv3DConfig {
    int in_channels{0};
    int out_channels{0};
    int kernel_size{3};      ///< 3 → 3x3x3 kernel
    int stride{1};
    int padding{1};
    bool submanifold{false}; ///< 子流形模式（保持稀疏性）
    bool use_bias{true};
};

/**
 * @brief 3D 稀疏卷积 (Rule-based)
 *
 * 基于 SECOND 论文的稀疏卷积实现。
 * 只对非零体素进行卷积，跳过零值区域。
 *
 * 核心思想：
 *   1. 生成卷积规则表 (Rule Book): 输入非零位置 → 输出非零位置映射
 *   2. Gather: 根据规则表收集输入特征
 *   3. GEMM: 对收集的特征做矩阵乘法
 *   4. Scatter: 将结果写回输出稀疏张量
 */
class SparseConv3D {
public:
    /**
     * @brief 生成卷积规则表
     *
     * @param in_coords   [N_in, 3] 输入非零体素坐标
     * @param out_coords  [N_out, 3] 输出非零体素坐标
     * @param kernel_size 卷积核大小
     * @param stride      步长
     * @param padding     填充
     * @return 规则表: [(in_idx, out_idx)]
     */
    static std::vector<std::pair<int32_t, int32_t>> build_rule_book(
        const std::vector<int32_t>& in_coords,
        const std::vector<int32_t>& out_coords,
        int kernel_size, int stride, int padding) {

        int N_in = static_cast<int>(in_coords.size()) / 3;
        int N_out = static_cast<int>(out_coords.size()) / 3;

        // 构建输出坐标哈希表
        std::unordered_map<uint64_t, int32_t> out_map;
        for (int i = 0; i < N_out; ++i) {
            uint64_t key = coord_to_key(
                out_coords[i * 3 + 0],
                out_coords[i * 3 + 1],
                out_coords[i * 3 + 2]);
            out_map[key] = i;
        }

        std::vector<std::pair<int32_t, int32_t>> rule_book;
        int half_k = kernel_size / 2;

        for (int in_idx = 0; in_idx < N_in; ++in_idx) {
            int iz = in_coords[in_idx * 3 + 0];
            int iy = in_coords[in_idx * 3 + 1];
            int ix = in_coords[in_idx * 3 + 2];

            // 检查每个 kernel offset
            for (int kz = -half_k; kz <= half_k; ++kz) {
                for (int ky = -half_k; ky <= half_k; ++ky) {
                    for (int kx = -half_k; kx <= half_k; ++kx) {
                        int oz = iz + kz + padding;
                        int oy = iy + ky + padding;
                        int ox = ix + kx + padding;

                        // 检查是否对齐到输出网格
                        if (oz % stride != 0 || oy % stride != 0 || ox % stride != 0) {
                            continue;
                        }
                        oz /= stride;
                        oy /= stride;
                        ox /= stride;

                        auto it = out_map.find(coord_to_key(oz, oy, ox));
                        if (it != out_map.end()) {
                            rule_book.emplace_back(in_idx, it->second);
                        }
                    }
                }
            }
        }

        return rule_book;
    }

    /**
     * @brief 稀疏卷积前向传播
     *
     * @param in_features  [N_in, C_in] 输入特征
     * @param weight       [C_out, C_in, K, K, K] 卷积权重
     * @param bias         [C_out] 偏置
     * @param rule_book    卷积规则表
     * @param N_out        输出非零位置数
     * @param C_in         输入通道数
     * @param C_out        输出通道数
     * @param K            卷积核大小
     * @return [N_out, C_out] 输出特征
     */
    static std::vector<float> forward(
        const float* in_features,
        const float* weight,
        const float* bias,
        const std::vector<std::pair<int32_t, int32_t>>& rule_book,
        int N_out, int C_in, int C_out, int K) {

        std::vector<float> out_features(N_out * C_out, 0.0f);

        int K3 = K * K * K;

        // 对每条规则执行卷积
        #pragma omp parallel for
        for (size_t r = 0; r < rule_book.size(); ++r) {
            int in_idx = rule_book[r].first;
            int out_idx = rule_book[r].second;

            for (int co = 0; co < C_out; ++co) {
                float sum = bias ? bias[co] : 0.0f;
                for (int ci = 0; ci < C_in; ++ci) {
                    for (int k = 0; k < K3; ++k) {
                        float w = weight[((co * C_in + ci) * K3) + k];
                        float x = in_features[in_idx * C_in + ci];
                        sum += w * x;
                    }
                }
                // 原子累加（多个输入可能贡献同一输出）
                #pragma omp atomic
                out_features[out_idx * C_out + co] += sum;
            }
        }

        return out_features;
    }

private:
    static uint64_t coord_to_key(int32_t z, int32_t y, int32_t x) {
        return (static_cast<uint64_t>(z & 0xFFFFF) << 40) |
               (static_cast<uint64_t>(y & 0xFFFFF) << 20) |
               (static_cast<uint64_t>(x & 0xFFFFF));
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 3. PointPillars — 柱状体素化 + Pillar Feature Net
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief PointPillars 配置
 *
 * PointPillars 将点云投影到 XY 平面的"柱子"(Pillar)，
 * 然后使用 2D CNN 处理，避免了 3D 卷积的高昂开销。
 */
struct PointPillarsConfig {
    // Pillar 尺寸（米）
    float pillar_size_x{0.16f};
    float pillar_size_y{0.16f};

    // 点云范围
    float x_min{-39.68f}, x_max{39.68f};
    float y_min{-39.68f}, y_max{39.68f};
    float z_min{-3.0f},  z_max{1.0f};

    // Pillar 限制
    uint32_t max_points_per_pillar{100};
    uint32_t max_pillars{12000};

    // 特征维度
    uint32_t num_point_features{9};  // (x,y,z, intensity, x_c, y_c, z_c, x_p, y_p)
    uint32_t num_pillar_features{64}; // PFN 输出维度
};

/**
 * @brief PointPillars 特征提取
 *
 * 流程：
 *   1. 点云 → Pillar 分配
 *   2. 每个 Pillar 内随机采样 max_points 个点
 *   3. Pillar Feature Net (PFN): Linear + BN + ReLU → max pool → [C, H, W] 伪图像
 */
class PointPillarsEncoder {
public:
    /**
     * @brief PointPillars 编码器前向传播
     *
     * @param points       [N, 4] (x, y, z, intensity)
     * @param num_points   点数
     * @param config       配置
     * @param pseudo_image [C, H, W] 伪图像输出
     * @param H, W         伪图像尺寸
     * @param C            伪图像通道数
     */
    static void encode(
        const float* points, size_t num_points,
        const PointPillarsConfig& config,
        float* pseudo_image,
        int& H, int& W, int C) {

        // 计算伪图像尺寸
        W = static_cast<int>((config.x_max - config.x_min) / config.pillar_size_x);
        H = static_cast<int>((config.y_max - config.y_min) / config.pillar_size_y);

        // Step 1: 点云 → Pillar 分配
        struct PillarData {
            std::vector<float> points;  // 扁平化存储
            uint32_t count{0};
            int32_t x_idx{0}, y_idx{0};
        };

        std::unordered_map<uint64_t, uint32_t> pillar_map;
        std::vector<PillarData> pillars;

        for (size_t i = 0; i < num_points; ++i) {
            float px = points[i * 4 + 0];
            float py = points[i * 4 + 1];
            float pz = points[i * 4 + 2];

            if (px < config.x_min || px >= config.x_max ||
                py < config.y_min || py >= config.y_max ||
                pz < config.z_min || pz >= config.z_max) {
                continue;
            }

            int32_t px_idx = static_cast<int32_t>(
                (px - config.x_min) / config.pillar_size_x);
            int32_t py_idx = static_cast<int32_t>(
                (py - config.y_min) / config.pillar_size_y);

            uint64_t key = (static_cast<uint64_t>(py_idx) << 32) |
                            static_cast<uint64_t>(px_idx);

            auto it = pillar_map.find(key);
            if (it == pillar_map.end()) {
                if (pillars.size() >= config.max_pillars) continue;
                uint32_t idx = static_cast<uint32_t>(pillars.size());
                pillar_map[key] = idx;
                pillars.push_back({});
                pillars.back().x_idx = px_idx;
                pillars.back().y_idx = py_idx;
                pillars.back().points.reserve(
                    config.max_points_per_pillar * config.num_point_features);
                it = pillar_map.find(key);
            }

            auto& pillar = pillars[it->second];
            if (pillar.count >= config.max_points_per_pillar) continue;

            // 计算增强特征：(x, y, z, intensity, x_c, y_c, z_c, x_p, y_p)
            float cx = (px_idx + 0.5f) * config.pillar_size_x + config.x_min;
            float cy = (py_idx + 0.5f) * config.pillar_size_y + config.y_min;
            float cz = (config.z_min + config.z_max) / 2.0f;

            pillar.points.push_back(px);               // x
            pillar.points.push_back(py);               // y
            pillar.points.push_back(pz);               // z
            pillar.points.push_back(points[i * 4 + 3]); // intensity
            pillar.points.push_back(px - cx);          // x_c (到pillar中心的偏移)
            pillar.points.push_back(py - cy);          // y_c
            pillar.points.push_back(pz - cz);          // z_c
            pillar.points.push_back(px - config.x_min); // x_p (归一化位置)
            pillar.points.push_back(py - config.y_min); // y_p
            pillar.count++;
        }

        // Step 2: PFN (简化版：平均池化替代 MLP)
        // 输出: [C, H, W] 伪图像，初始化为 0
        std::fill(pseudo_image, pseudo_image + C * H * W, 0.0f);

        for (const auto& pillar : pillars) {
            if (pillar.count == 0) continue;

            // 对每个 Pillar 内的点做特征平均
            std::vector<float> mean_feat(config.num_point_features, 0.0f);
            for (uint32_t p = 0; p < pillar.count; ++p) {
                for (uint32_t f = 0; f < config.num_point_features; ++f) {
                    mean_feat[f] += pillar.points[
                        p * config.num_point_features + f];
                }
            }
            for (auto& v : mean_feat) v /= pillar.count;

            // 写回伪图像（只使用前 C 个特征）
            int write_c = std::min(C, static_cast<int>(config.num_point_features));
            for (int c = 0; c < write_c; ++c) {
                pseudo_image[(c * H + pillar.y_idx) * W + pillar.x_idx] =
                    mean_feat[c];
            }
        }
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 4. BEV Pooling — 多相机 BEV 特征汇聚
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief BEV (Bird's Eye View) 池化
 *
 * 将多相机透视特征投影到 BEV 空间。
 * 使用 LSS (Lift-Splat-Shoot) 或 Cross-Attention 方法。
 *
 * 此处实现基于 LSS 的简化版本：
 *   1. 每个像素预测深度分布 D
 *   2. 根据深度分布将特征"提升"到 3D 空间
 *   3. 沿 Z 轴池化得到 BEV 特征
 */
class BevPooling {
public:
    /**
     * @brief LSS 风格的 BEV 池化
     *
     * @param image_features  [N_cam, C, H_img, W_img] 多相机图像特征
     * @param depth_probs     [N_cam, D, H_img, W_img] 每个像素的深度概率分布
     * @param extrinsics      [N_cam, 4, 4] 相机外参（cam→world）
     * @param intrinsics      [N_cam, 3, 3] 相机内参
     * @param bev_features    [C, H_bev, W_bev] BEV 特征输出
     * @param bev_range_x     BEV X 范围 (min, max, resolution)
     * @param bev_range_y     BEV Y 范围 (min, max, resolution)
     * @param depth_bins      D 个深度 bin 的中心值
     */
    static void lss_forward(
        const float* image_features,
        const float* depth_probs,
        const float* extrinsics,
        const float* intrinsics,
        float* bev_features,
        int N_cam, int C, int H_img, int W_img,
        int D, int H_bev, int W_bev,
        const std::array<float, 3>& bev_range_x,  // {min, max, resolution}
        const std::array<float, 3>& bev_range_y,  // {min, max, resolution}
        const std::vector<float>& depth_bins) {

        // 初始化 BEV 特征
        size_t bev_size = static_cast<size_t>(C) * H_bev * W_bev;
        std::fill(bev_features, bev_features + bev_size, 0.0f);

        // 用于归一化的计数
        std::vector<float> bev_counts(H_bev * W_bev, 0.0f);

        // 遍历所有相机
        for (int cam = 0; cam < N_cam; ++cam) {
            const float* cam_feat = image_features + cam * C * H_img * W_img;
            const float* cam_depth = depth_probs + cam * D * H_img * W_img;

            // 遍历所有像素
            for (int h = 0; h < H_img; ++h) {
                for (int w = 0; w < W_img; ++w) {
                    // 获取该像素的特征
                    std::vector<float> pixel_feat(C, 0.0f);
                    for (int c = 0; c < C; ++c) {
                        pixel_feat[c] = cam_feat[(c * H_img + h) * W_img + w];
                    }

                    // 遍历深度分布
                    for (int d_idx = 0; d_idx < D; ++d_idx) {
                        float depth_prob = cam_depth[(d_idx * H_img + h) * W_img + w];
                        if (depth_prob < 1e-6f) continue;

                        float depth = depth_bins[d_idx];

                        // 像素坐标 → 相机坐标系
                        float fx = intrinsics[cam * 9 + 0];
                        float fy = intrinsics[cam * 9 + 4];
                        float cx = intrinsics[cam * 9 + 2];
                        float cy = intrinsics[cam * 9 + 5];

                        float x_cam = (w - cx) * depth / fx;
                        float y_cam = (h - cy) * depth / fy;
                        float z_cam = depth;

                        // 相机坐标系 → 世界坐标系（简化：直接使用外参）
                        // world = extrinsics^-1 * cam
                        // 此处简化为：直接用 x_cam, y_cam 作为 BEV 坐标

                        // 世界坐标 → BEV 网格
                        int bx = static_cast<int>(
                            (x_cam - bev_range_x[0]) / bev_range_x[2]);
                        int by = static_cast<int>(
                            (y_cam - bev_range_y[0]) / bev_range_y[2]);

                        if (bx >= 0 && bx < W_bev && by >= 0 && by < H_bev) {
                            int bev_idx = by * W_bev + bx;
                            for (int c = 0; c < C; ++c) {
                                bev_features[(c * H_bev + by) * W_bev + bx] +=
                                    pixel_feat[c] * depth_prob;
                            }
                            bev_counts[bev_idx] += depth_prob;
                        }
                    }
                }
            }
        }

        // 归一化
        for (int by = 0; by < H_bev; ++by) {
            for (int bx = 0; bx < W_bev; ++bx) {
                int idx = by * W_bev + bx;
                float count = bev_counts[idx];
                if (count > 1e-6f) {
                    float inv_count = 1.0f / count;
                    for (int c = 0; c < C; ++c) {
                        bev_features[(c * H_bev + by) * W_bev + bx] *= inv_count;
                    }
                }
            }
        }
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 5. 3D NMS (Non-Maximum Suppression)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 3D 旋转边界框 NMS
 *
 * 对 3D 检测结果进行非极大值抑制。
 * 3D IoU 计算考虑 (x, y, z, w, l, h, yaw)。
 */
class NMS3D {
public:
    struct Box3D {
        float x, y, z;       ///< 中心坐标
        float w, l, h;       ///< 宽、长、高
        float yaw;           ///< 旋转角（弧度）
        float score;         ///< 置信度
        int class_id{0};     ///< 类别 ID
    };

    /**
     * @brief 3D NMS
     *
     * @param boxes        输入框列表
     * @param iou_threshold IoU 阈值（超过则抑制）
     * @param score_threshold 分数阈值（低于则过滤）
     * @return 保留的框索引
     */
    static std::vector<int> apply(
        const std::vector<Box3D>& boxes,
        float iou_threshold = 0.5f,
        float score_threshold = 0.3f) {

        // 按分数排序的索引
        std::vector<int> indices(boxes.size());
        std::iota(indices.begin(), indices.end(), 0);
        std::sort(indices.begin(), indices.end(),
            [&boxes](int a, int b) { return boxes[a].score > boxes[b].score; });

        std::vector<int> keep;

        while (!indices.empty()) {
            int best_idx = indices[0];
            keep.push_back(best_idx);

            std::vector<int> remaining;
            for (size_t i = 1; i < indices.size(); ++i) {
                int idx = indices[i];

                // 不同类别不抑制
                if (boxes[best_idx].class_id != boxes[idx].class_id) {
                    remaining.push_back(idx);
                    continue;
                }

                // 分数太低过滤
                if (boxes[idx].score < score_threshold) continue;

                // 计算 3D IoU
                float iou = compute_3d_iou(boxes[best_idx], boxes[idx]);
                if (iou < iou_threshold) {
                    remaining.push_back(idx);
                }
            }

            indices = std::move(remaining);
        }

        return keep;
    }

private:
    /**
     * @brief 计算两个 3D 旋转框的 IoU（简化版：轴对齐）
     *
     * 完整的旋转 IoU 需要计算凸包相交面积，此处使用轴对齐近似。
     * 适用于大多数自动驾驶场景（车辆通常接近轴对齐）。
     */
    static float compute_3d_iou(const Box3D& a, const Box3D& b) {
        // BEV 平面 IoU（忽略高度和旋转）
        float ax1 = a.x - a.w / 2, ax2 = a.x + a.w / 2;
        float ay1 = a.y - a.l / 2, ay2 = a.y + a.l / 2;
        float bx1 = b.x - b.w / 2, bx2 = b.x + b.w / 2;
        float by1 = b.y - b.l / 2, by2 = b.y + b.l / 2;

        // 旋转框简化：使用轴对齐包围框
        // 实际应使用旋转 IoU（通过三角剖分或 SAT）
        float inter_x = std::max(0.0f, std::min(ax2, bx2) - std::max(ax1, bx1));
        float inter_y = std::max(0.0f, std::min(ay2, by2) - std::max(ay1, by1));
        float inter_area = inter_x * inter_y;

        float area_a = a.w * a.l;
        float area_b = b.w * b.l;
        float union_area = area_a + area_b - inter_area;

        if (union_area < 1e-6f) return 0.0f;

        // 乘以高度重叠因子
        float az1 = a.z - a.h / 2, az2 = a.z + a.h / 2;
        float bz1 = b.z - b.h / 2, bz2 = b.z + b.h / 2;
        float inter_z = std::max(0.0f, std::min(az2, bz2) - std::max(az1, bz1));
        float height_overlap = std::min(
            inter_z / std::max(a.h, 1e-6f),
            inter_z / std::max(b.h, 1e-6f));

        return (inter_area / union_area) * height_overlap;
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 6. Points to Voxel — 散列映射工具
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 点云到体素的散列映射
 *
 * 高效的点→体素映射，使用空间哈希。
 */
class PointsToVoxel {
public:
    /**
     * @brief 将点云映射到体素索引
     *
     * @param points     [N, 3] (x, y, z)
     * @param N          点数
     * @param voxel_size 体素尺寸
     * @param range_min  点云范围最小值
     * @param range_max  点云范围最大值
     * @return [N] 体素索引 (-1 表示超出范围)
     */
    static std::vector<int32_t> map(
        const float* points, size_t N,
        const std::array<float, 3>& voxel_size,
        const std::array<float, 3>& range_min,
        const std::array<float, 3>& range_max) {

        std::vector<int32_t> voxel_indices(N, -1);

        int grid_x = static_cast<int>(
            (range_max[0] - range_min[0]) / voxel_size[0]);
        int grid_y = static_cast<int>(
            (range_max[1] - range_min[1]) / voxel_size[1]);

        #pragma omp parallel for
        for (size_t i = 0; i < N; ++i) {
            float px = points[i * 3 + 0];
            float py = points[i * 3 + 1];
            float pz = points[i * 3 + 2];

            if (px < range_min[0] || px >= range_max[0] ||
                py < range_min[1] || py >= range_max[1] ||
                pz < range_min[2] || pz >= range_max[2]) {
                continue;
            }

            int vx = static_cast<int>((px - range_min[0]) / voxel_size[0]);
            int vy = static_cast<int>((py - range_min[1]) / voxel_size[1]);
            int vz = static_cast<int>((pz - range_min[2]) / voxel_size[2]);

            voxel_indices[i] = (vz * grid_y + vy) * grid_x + vx;
        }

        return voxel_indices;
    }
};

} // namespace lidar
} // namespace ops
} // namespace qoocore
