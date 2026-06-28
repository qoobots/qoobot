/**
 * @file multimodal_ops.h
 * @brief 多模态融合算子
 *
 * 视觉-激光雷达-IMU 等多传感器融合加速原语，包括：
 *  - 早期融合（Early Fusion）：原始数据级融合
 *  - 晚期融合（Late Fusion）：决策级融合
 *  - 中间融合（Middle Fusion）：特征级融合
 *  - 注意力融合：Cross-Modal Attention
 *
 * 应用场景：自动驾驶/机器人多传感器感知融合。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <cstdint>
#include <vector>

namespace qoocore {
namespace operators {

// ─────────────────────────────────────────────────────────────────────────────
//  融合配置
// ─────────────────────────────────────────────────────────────────────────────

enum class FusionType : std::uint8_t {
    EARLY    = 0,  ///< 早期融合（原始数据级）
    MIDDLE   = 1,  ///< 中间融合（特征级）
    LATE     = 2,  ///< 晚期融合（决策级）
    ATTENTION= 3,  ///< 跨模态注意力融合
};

enum class FusionMethod : std::uint8_t {
    CONCAT    = 0,  ///< 通道拼接
    ADD       = 1,  ///< 逐元素加法
    GATED     = 2,  ///< 门控融合
    TRANSFORMER=3,  ///< Transformer 融合
};

struct FusionConfig {
    FusionType type{FusionType::MIDDLE};
    FusionMethod method{FusionMethod::CONCAT};
    float dropout{0.1f};
    std::uint32_t num_heads{8};
    bool use_fp16{false};
    bool normalize_inputs{true};
};

// ─────────────────────────────────────────────────────────────────────────────
//  多模态融合函数
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 特征级拼接融合
 *
 * 将多个模态的特征沿通道维度拼接。
 *
 * @param features 各模态特征张量列表（需匹配空间维度 H,W）
 * @param config   融合配置
 * @return Result<Tensor> [1][sum_C][H][W] 融合特征
 */
Result<Tensor> concat_fusion(
    const std::vector<Tensor>& features,
    const FusionConfig& config);

/**
 * @brief 逐元素加法融合
 *
 * 将多个模态的特征逐元素相加（需通道数一致）。
 *
 * @param features 各模态特征张量列表（需匹配所有维度）
 * @param weights  各模态权重（可选，默认均匀）
 * @param config   融合配置
 * @return Result<Tensor> [1][C][H][W] 融合特征
 */
Result<Tensor> add_fusion(
    const std::vector<Tensor>& features,
    const std::vector<float>& weights,
    const FusionConfig& config);

/**
 * @brief 门控融合
 *
 * 使用可学习的门控机制动态融合多模态特征。
 *
 * @param features 各模态特征张量列表
 * @param config   融合配置
 * @return Result<Tensor> [1][C][H][W] 融合特征
 */
Result<Tensor> gated_fusion(
    const std::vector<Tensor>& features,
    const FusionConfig& config);

/**
 * @brief 跨模态注意力融合
 *
 * 使用 Cross-Attention 在不同模态之间进行特征交互。
 *
 * @param primary   主模态特征 [1][C][H][W]
 * @param secondary 辅助模态特征 [1][C2][H][W]
 * @param config    融合配置
 * @return Result<Tensor> [1][C][H][W] 融合特征
 */
Result<Tensor> cross_modal_attention(
    const Tensor& primary,
    const Tensor& secondary,
    const FusionConfig& config);

/**
 * @brief 视觉-激光雷达融合（BEV 空间）
 *
 * 将相机图像特征和 LiDAR 点云特征在 BEV 空间进行融合。
 *
 * @param image_features  [N][C_img][H_img][W_img] 多相机图像特征
 * @param lidar_features   [1][C_lidar][H_bev][W_bev] LiDAR BEV 特征
 * @param config           融合配置
 * @return Result<Tensor> [1][C_out][H_bev][W_bev] 融合 BEV 特征
 */
Result<Tensor> vision_lidar_fusion(
    const std::vector<Tensor>& image_features,
    const Tensor& lidar_features,
    const FusionConfig& config);

/**
 * @brief IMU-视觉融合
 *
 * 将 IMU 数据与视觉特征融合，用于位姿估计增强。
 *
 * @param visual_features [1][C][H][W] 视觉特征
 * @param imu_data        [T][6] IMU 数据 (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z)
 * @param config          融合配置
 * @return Result<Tensor> [1][C][H][W] 融合特征
 */
Result<Tensor> imu_visual_fusion(
    const Tensor& visual_features,
    const Tensor& imu_data,
    const FusionConfig& config);

/**
 * @brief 时间-空间多模态融合
 *
 * 融合多帧多模态数据，结合时间上下文。
 *
 * @param temporal_features [T][modalities][C][H][W] 时间序列多模态特征
 * @param config            融合配置
 * @return Result<Tensor> [1][C][H][W] 融合特征
 */
Result<Tensor> temporal_multimodal_fusion(
    const std::vector<std::vector<Tensor>>& temporal_features,
    const FusionConfig& config);

/**
 * @brief 自适应融合权重学习
 *
 * 基于特征统计自动学习各模态的融合权重。
 *
 * @param features 各模态特征
 * @return std::vector<float> 归一化权重
 */
std::vector<float> adaptive_fusion_weights(
    const std::vector<Tensor>& features);

/**
 * @brief 特征归一化（用于融合前预处理）
 *
 * @param features 输入特征列表
 * @param method   归一化方法 ("l2", "batch", "layer", "instance")
 * @return std::vector<Tensor> 归一化特征
 */
std::vector<Tensor> normalize_features(
    const std::vector<Tensor>& features,
    const std::string& method = "l2");

} // namespace operators
} // namespace qoocore
