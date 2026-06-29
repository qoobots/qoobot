/**
 * @file bev_ops.h
 * @brief BEV（Bird's-Eye-View）变换算子
 *
 * 多相机 BEV 特征变换：将多路环视相机图像从透视视图映射到鸟瞰图空间，
 * 支持 LSS（Lift-Splat-Shoot）加速和 Cross-Attention 变换。
 *
 * 应用场景：自动驾驶/机器人导航中从多相机 2D 特征生成统一 3D BEV 特征。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <cstddef>
#include <cstdint>
#include <vector>

namespace qoocore {
namespace operators {

// ─────────────────────────────────────────────────────────────────────────────
//  BEVConfig — BEV 变换配置
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief BEV 变换方法枚举
 */
enum class BEVMethod : std::uint8_t {
    LSS              = 0,  ///< Lift-Splat-Shoot（基于深度估计）
    CROSS_ATTENTION  = 1,  ///< 基于 Cross-Attention 的 BEV 变换
    IPM              = 2,  ///< 逆透视变换（平面假设）
    TRANSFORMER      = 3,  ///< 基于 Transformer 的 BEV 变换
};

/**
 * @brief BEV 投影参数
 */
struct BEVConfig {
    // ── BEV 网格参数 ─────────────────────────────────────────────────
    float x_min{-50.0f};          ///< BEV 网格 X 方向最小值（米）
    float x_max{50.0f};           ///< BEV 网格 X 方向最大值（米）
    float y_min{-50.0f};          ///< BEV 网格 Y 方向最小值（米）
    float y_max{50.0f};           ///< BEV 网格 Y 方向最大值（米）
    float z_min{-5.0f};           ///< Z 方向最小值（米）
    float z_max{3.0f};            ///< Z 方向最大值（米）
    float resolution{0.5f};       ///< BEV 网格分辨率（米/格）

    // ── 深度估计参数 ─────────────────────────────────────────────────
    float depth_min{1.0f};        ///< 深度估计最小值（米）
    float depth_max{60.0f};       ///< 深度估计最大值（米）
    std::uint32_t depth_bins{64}; ///< 深度离散化 bins 数量

    // ── 相机参数 ─────────────────────────────────────────────────────
    std::uint32_t num_cameras{6}; ///< 环视相机数量
    std::uint32_t feature_dim{256}; ///< 每个相机的特征维度
    std::uint32_t bev_dim{256};   ///< BEV 特征维度

    // ── 变换方法 ─────────────────────────────────────────────────────
    BEVMethod method{BEVMethod::LSS};

    // ── 性能选项 ─────────────────────────────────────────────────────
    bool use_fp16{false};         ///< 是否使用 FP16 计算
    bool use_voxel_pooling{true}; ///< 是否使用体素池化加速
    bool use_mlp_depth{true};     ///< 是否使用 MLP 深度估计

    // ── Cross-Attention 参数 ─────────────────────────────────────────
    std::uint32_t num_heads{8};   ///< 多头注意力头数
    std::uint32_t num_layers{6};  ///< Transformer 层数
    float dropout{0.1f};          ///< Dropout 比率

    /**
     * @brief 计算 BEV 网格尺寸
     */
    [[nodiscard]] std::uint32_t bev_width() const noexcept {
        return static_cast<std::uint32_t>((x_max - x_min) / resolution);
    }

    [[nodiscard]] std::uint32_t bev_height() const noexcept {
        return static_cast<std::uint32_t>((y_max - y_min) / resolution);
    }

    [[nodiscard]] std::uint32_t bev_depth() const noexcept {
        return static_cast<std::uint32_t>((z_max - z_min) / resolution);
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  CameraParams — 单相机外参/内参
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 相机内参矩阵（3x3）
 */
struct CameraIntrinsics {
    float fx{1.0f}, fy{1.0f};    ///< 焦距
    float cx{0.0f}, cy{0.0f};    ///< 主点
    float k1{0.0f}, k2{0.0f};    ///< 径向畸变
    float p1{0.0f}, p2{0.0f};    ///< 切向畸变
    std::uint32_t width{1920};
    std::uint32_t height{1080};
};

/**
 * @brief 相机外参（世界坐标系 → 相机坐标系 变换）
 *
 * T_world_cam = [R | t], 4x4 矩阵按行主序存储
 */
struct CameraExtrinsics {
    float R[9] = {1,0,0, 0,1,0, 0,0,1};  ///< 3x3 旋转矩阵（行主序）
    float t[3] = {0,0,0};                  ///< 平移向量

    /**
     * @brief 获取 4x4 变换矩阵（行主序）
     */
    void to_matrix(float m[16]) const noexcept {
        // Row 0
        m[0] = R[0]; m[1] = R[1]; m[2] = R[2]; m[3] = t[0];
        // Row 1
        m[4] = R[3]; m[5] = R[4]; m[6] = R[5]; m[7] = t[1];
        // Row 2
        m[8] = R[6]; m[9] = R[7]; m[10]= R[8]; m[11]= t[2];
        // Row 3
        m[12]= 0;    m[13]= 0;    m[14]= 0;    m[15]= 1;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  BEV 算子函数声明
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 多相机 BEV 特征变换
 *
 * 将 N 个环视相机图像特征投影到统一 BEV 空间。
 *
 * @param camera_features  [N][C][H][W] 多相机图像特征（NCHW 布局）
 * @param camera_intrinsics N 个相机的内参
 * @param camera_extrinsics N 个相机的外参
 * @param config           BEV 变换配置
 * @return Result<Tensor>  [1][bev_dim][bev_height][bev_width] BEV 特征
 */
Result<Tensor> bev_transform(
    const std::vector<Tensor>& camera_features,
    const std::vector<CameraIntrinsics>& camera_intrinsics,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config);

/**
 * @brief LSS Lift-Splat-Shoot BEV 变换
 *
 * 实现经典的 LSS 算法：Lift（深度估计+提升）→ Splat（投影到 BEV）→ Shoot（BEV 特征提取）
 *
 * @param camera_features  [N][C][H][W] 多相机图像特征
 * @param depth_probs      [N][D][H][W] 每个像素的深度概率分布
 * @param camera_intrinsics N 个相机的内参
 * @param camera_extrinsics N 个相机的外参
 * @param config           BEV 变换配置
 * @return Result<Tensor>  [1][bev_dim][bev_height][bev_width] BEV 特征
 */
Result<Tensor> lss_transform(
    const std::vector<Tensor>& camera_features,
    const std::vector<Tensor>& depth_probs,
    const std::vector<CameraIntrinsics>& camera_intrinsics,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config);

/**
 * @brief Cross-Attention BEV 变换
 *
 * 使用可学习的 BEV queries 通过 Cross-Attention 从多相机特征中聚合信息。
 *
 * @param camera_features  [N][C][H][W] 多相机图像特征
 * @param bev_queries      [Q][bev_dim] BEV query 向量
 * @param camera_intrinsics N 个相机的内参
 * @param camera_extrinsics N 个相机的外参
 * @param config           BEV 变换配置
 * @return Result<Tensor>  [1][bev_dim][bev_height][bev_width] BEV 特征
 */
Result<Tensor> cross_attention_bev(
    const std::vector<Tensor>& camera_features,
    const Tensor& bev_queries,
    const std::vector<CameraIntrinsics>& camera_intrinsics,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config);

/**
 * @brief IPM 逆透视变换 BEV（平面假设）
 *
 * 基于地面平面假设的快速逆透视变换，适用于平坦场景。
 *
 * @param camera_features  [N][C][H][W] 多相机图像特征
 * @param camera_intrinsics N 个相机的内参
 * @param camera_extrinsics N 个相机的外参
 * @param config           BEV 变换配置
 * @return Result<Tensor>  [1][bev_dim][bev_height][bev_width] BEV 特征
 */
Result<Tensor> ipm_transform(
    const std::vector<Tensor>& camera_features,
    const std::vector<CameraIntrinsics>& camera_intrinsics,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config);

/**
 * @brief BEV 体素池化（Voxel Pooling）
 *
 * 将提升到 3D 空间的体素特征池化到 BEV 平面。
 * 支持 max-pooling 和 mean-pooling。
 *
 * @param voxel_features   [1][C][D][H][W] 3D 体素特征
 * @param bev_config       BEV 配置
 * @param pool_type        "max" 或 "mean"
 * @return Result<Tensor>  [1][C][H][W] BEV 特征
 */
Result<Tensor> bev_voxel_pooling(
    const Tensor& voxel_features,
    const BEVConfig& bev_config,
    const std::string& pool_type = "max");

/**
 * @brief 多相机特征拼接（用于简单的 BEV 聚合）
 *
 * 将多相机特征通过外参投影后直接在 BEV 平面拼接。
 *
 * @param camera_features  [N][C][H][W] 多相机图像特征
 * @param camera_extrinsics N 个相机的外参
 * @param config           BEV 变换配置
 * @return Result<Tensor>  [1][C*N][bev_height][bev_width] 拼接 BEV 特征
 */
Result<Tensor> bev_concat_project(
    const std::vector<Tensor>& camera_features,
    const std::vector<CameraExtrinsics>& camera_extrinsics,
    const BEVConfig& config);

/**
 * @brief BEV 特征后处理：时间融合
 *
 * 将当前帧 BEV 特征与历史帧 BEV 特征进行时间融合。
 *
 * @param current_bev   [1][C][H][W] 当前帧 BEV 特征
 * @param prev_bev      [1][C][H][W] 上一帧 BEV 特征
 * @param decay_factor  时间衰减因子（0~1，越大越重视当前帧）
 * @return Result<Tensor> [1][C][H][W] 融合后 BEV 特征
 */
Result<Tensor> bev_temporal_fusion(
    const Tensor& current_bev,
    const Tensor& prev_bev,
    float decay_factor = 0.7f);

/**
 * @brief 将 BEV 网格坐标转换为世界坐标
 *
 * @param grid_x  BEV 网格 X 索引
 * @param grid_y  BEV 网格 Y 索引
 * @param config  BEV 配置
 * @return std::pair<float,float> {world_x, world_y}
 */
[[nodiscard]] inline std::pair<float, float> bev_grid_to_world(
    std::uint32_t grid_x, std::uint32_t grid_y,
    const BEVConfig& config) noexcept
{
    float world_x = config.x_min + (grid_x + 0.5f) * config.resolution;
    float world_y = config.y_min + (grid_y + 0.5f) * config.resolution;
    return {world_x, world_y};
}

/**
 * @brief 将世界坐标转换为 BEV 网格坐标
 *
 * @param world_x  世界 X 坐标（米）
 * @param world_y  世界 Y 坐标（米）
 * @param config   BEV 配置
 * @return std::pair<int,int> {grid_x, grid_y}，越界返回 {-1, -1}
 */
[[nodiscard]] inline std::pair<int, int> world_to_bev_grid(
    float world_x, float world_y,
    const BEVConfig& config) noexcept
{
    if (world_x < config.x_min || world_x > config.x_max ||
        world_y < config.y_min || world_y > config.y_max) {
        return {-1, -1};
    }
    int gx = static_cast<int>((world_x - config.x_min) / config.resolution);
    int gy = static_cast<int>((world_y - config.y_min) / config.resolution);
    return {gx, gy};
}

} // namespace operators
} // namespace qoocore
