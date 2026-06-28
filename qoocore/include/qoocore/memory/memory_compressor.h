/**
 * @file memory_compressor.h
 * @brief 内存压缩 — 激活值压缩、KV-Cache 量化、梯度检查点
 *
 * 对标 NVIDIA Transformer Engine 的 FP8 训练/推理优化。
 * 在内存受限的端侧设备上压缩中间激活值和 KV-Cache。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <cstdint>
#include <string>
#include <vector>

namespace qoocore {
namespace memory {

// ─────────────────────────────────────────────────────────────────────────────
//  CompressionConfig
// ─────────────────────────────────────────────────────────────────────────────

struct CompressionConfig {
    bool enable_activation_compression{true};
    bool enable_kv_cache_quantization{true};
    bool enable_gradient_checkpoint{false};  // 仅训练时使用

    // 量化参数
    DType kv_cache_dtype{DType::FLOAT16};    ///< KV-Cache 存储类型
    bool kv_cache_per_channel{true};         ///< 逐通道量化
    float kv_cache_range_min{-16.0f};
    float kv_cache_range_max{16.0f};

    // 激活压缩参数
    float activation_compression_ratio{0.5f};///< 目标压缩率
    bool use_lossless{false};                ///< 是否使用无损压缩
};

// ─────────────────────────────────────────────────────────────────────────────
//  CompressionStatistics
// ─────────────────────────────────────────────────────────────────────────────

struct CompressionStatistics {
    std::size_t original_bytes{0};
    std::size_t compressed_bytes{0};
    float compression_ratio{0.0f};
    double compress_time_ms{0.0};
    double decompress_time_ms{0.0};
};

// ─────────────────────────────────────────────────────────────────────────────
//  MemoryCompressor
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 内存压缩管理器
 *
 * 提供激活值压缩、KV-Cache 量化和梯度检查点功能。
 * 在内存受限的端侧设备上减少推理内存占用。
 */
class MemoryCompressor {
public:
    explicit MemoryCompressor(const CompressionConfig& config);
    ~MemoryCompressor() = default;

    // ── 激活值压缩 ──────────────────────────────────────────────────
    /**
     * @brief 压缩激活值张量
     *
     * 使用 FP16/BF16 或 INT8 量化压缩激活值。
     *
     * @param tensor 输入张量（FP32）
     * @return Result<Tensor> 压缩后张量
     */
    Result<Tensor> compress_activations(const Tensor& tensor);

    /**
     * @brief 解压缩激活值张量
     */
    Result<Tensor> decompress_activations(const Tensor& compressed);

    // ── KV-Cache 量化 ───────────────────────────────────────────────
    /**
     * @brief 量化 KV-Cache
     *
     * 将 FP32 KV-Cache 量化为低精度格式（FP16/INT8/INT4）。
     *
     * @param k_cache [batch][heads][seq_len][head_dim] K cache
     * @param v_cache [batch][heads][seq_len][head_dim] V cache
     * @return std::pair<Tensor,Tensor> {quantized_K, quantized_V}
     */
    std::pair<Tensor, Tensor> quantize_kv_cache(
        const Tensor& k_cache, const Tensor& v_cache);

    /**
     * @brief 反量化 KV-Cache
     */
    std::pair<Tensor, Tensor> dequantize_kv_cache(
        const Tensor& qk_cache, const Tensor& qv_cache);

    // ── 梯度检查点 ──────────────────────────────────────────────────
    /**
     * @brief 创建检查点（保存中间激活值）
     *
     * @param activation 中间激活值
     * @param tag        检查点标签
     * @return ErrorCode
     */
    ErrorCode save_checkpoint(const Tensor& activation, const std::string& tag);

    /**
     * @brief 恢复检查点
     */
    Result<Tensor> load_checkpoint(const std::string& tag);

    /**
     * @brief 释放检查点
     */
    ErrorCode release_checkpoint(const std::string& tag);

    /**
     * @brief 释放所有检查点
     */
    void release_all_checkpoints();

    // ── 统计 ───────────────────────────────────────────────────────
    [[nodiscard]] const CompressionStatistics& statistics() const;
    [[nodiscard]] std::size_t total_saved_bytes() const;

    // ── 辅助 ───────────────────────────────────────────────────────
    /**
     * @brief 估计压缩后大小
     */
    [[nodiscard]] static std::size_t estimate_compressed_size(
        const Tensor& tensor, DType target_dtype);

    /**
     * @brief 运行长度编码（RLE）压缩（用于稀疏激活值）
     */
    static std::vector<std::uint8_t> rle_compress(
        const std::uint8_t* data, std::size_t size);

    /**
     * @brief RLE 解压
     */
    static std::vector<std::uint8_t> rle_decompress(
        const std::uint8_t* data, std::size_t compressed_size,
        std::size_t original_size);

private:
    CompressionConfig config_;
    CompressionStatistics stats_;
    std::unordered_map<std::string, Tensor> checkpoints_;
};

} // namespace memory
} // namespace qoocore
