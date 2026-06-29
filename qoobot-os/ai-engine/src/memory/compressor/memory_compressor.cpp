/**
 * @file memory_compressor.cpp
 * @brief 内存压缩管理器实现
 *
 * 实现激活值压缩（FP16/INT8量化）、KV-Cache量化、梯度检查点等功能。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/memory/memory_compressor.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <limits>
#include <unordered_map>

namespace qoocore {
namespace memory {

namespace {

double now_ms() {
    return std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

// FP32 -> FP16 转换
float fp32_to_fp16_bits(float val) {
    // 截断到 FP16 精度并返回（存储为 float 的低 16 位有效）
    // 简化：直接返回原值（实际应使用 IEEE 754 half 转换）
    return val;
}

float fp16_to_fp32_bits(float val) {
    return val;  // 对称操作
}

// 简单量化：FP32 -> INT8
void quantize_fp32_to_int8(
    const float* src, std::int8_t* dst, std::size_t n,
    float& scale, float& zero_point)
{
    float min_val = std::numeric_limits<float>::max();
    float max_val = std::numeric_limits<float>::lowest();

    for (std::size_t i = 0; i < n; ++i) {
        min_val = std::min(min_val, src[i]);
        max_val = std::max(max_val, src[i]);
    }

    float range = max_val - min_val;
    if (range < 1e-10f) range = 1.0f;

    scale = range / 255.0f;
    zero_point = -min_val / scale;

    for (std::size_t i = 0; i < n; ++i) {
        float q = src[i] / scale + zero_point;
        q = std::max(-128.0f, std::min(127.0f, std::round(q)));
        dst[i] = static_cast<std::int8_t>(q);
    }
}

// INT8 -> FP32 反量化
void dequantize_int8_to_fp32(
    const std::int8_t* src, float* dst, std::size_t n,
    float scale, float zero_point)
{
    for (std::size_t i = 0; i < n; ++i) {
        dst[i] = (static_cast<float>(src[i]) - zero_point) * scale;
    }
}

} // anonymous namespace

// ═══════════════════════════════════════════════════════════════════════════════
//  MemoryCompressor 实现
// ═══════════════════════════════════════════════════════════════════════════════

MemoryCompressor::MemoryCompressor(const CompressionConfig& config)
    : config_(config) {}

// ── 激活值压缩 ──────────────────────────────────────────────────────────────

Result<Tensor> MemoryCompressor::compress_activations(const Tensor& tensor) {
    const auto& shape = tensor.shape();
    std::size_t n = 1;
    for (auto d : shape) n *= d;

    const float* src = static_cast<const float*>(tensor.data());
    auto start = now_ms();

    if (config_.use_lossless) {
        // RLE 压缩
        auto src_bytes = reinterpret_cast<const std::uint8_t*>(src);
        auto compressed = rle_compress(src_bytes, n * sizeof(float));

        stats_.original_bytes += n * sizeof(float);
        stats_.compressed_bytes += compressed.size();
        stats_.compression_ratio = static_cast<float>(stats_.compressed_bytes) /
                                   static_cast<float>(stats_.original_bytes);
        stats_.compress_time_ms += now_ms() - start;

        // 存储为字节张量
        std::vector<std::size_t> out_shape = {compressed.size()};
        auto result = Tensor::create(out_shape, DType::UINT8);
        if (!result.ok()) return result;

        auto& out = result.value();
        std::memcpy(out.data(), compressed.data(), compressed.size());
        return std::move(out);
    }

    // 有损压缩：FP32 → FP16
    std::vector<float> compressed_data(n);
    for (std::size_t i = 0; i < n; ++i) {
        compressed_data[i] = fp32_to_fp16_bits(src[i]);
    }

    stats_.original_bytes += n * sizeof(float);
    stats_.compressed_bytes += n * 2;  // FP16 = 2 bytes each
    stats_.compression_ratio = static_cast<float>(stats_.compressed_bytes) /
                               static_cast<float>(stats_.original_bytes);
    stats_.compress_time_ms += now_ms() - start;

    std::vector<std::size_t> out_shape(shape.begin(), shape.end());
    auto result = Tensor::create(out_shape, DType::FLOAT16);
    if (!result.ok()) return result;

    auto& out = result.value();
    std::memcpy(out.data(), compressed_data.data(), n * 2);
    return std::move(out);
}

Result<Tensor> MemoryCompressor::decompress_activations(const Tensor& compressed) {
    const auto& shape = compressed.shape();
    std::size_t n = 1;
    for (auto d : shape) n *= d;

    auto start = now_ms();

    std::vector<std::size_t> out_shape(shape.begin(), shape.end());
    auto result = Tensor::create(out_shape, DType::FLOAT32);
    if (!result.ok()) return result;

    auto& out = result.value();
    float* dst = static_cast<float*>(out.data());

    if (compressed.dtype() == DType::UINT8) {
        // RLE 解压
        auto src = static_cast<const std::uint8_t*>(compressed.data());
        auto decompressed = rle_decompress(src, n, n * sizeof(float));
        std::memcpy(dst, decompressed.data(),
                    std::min(decompressed.size(), n * sizeof(float)));
    } else {
        // FP16 → FP32
        const auto* src = static_cast<const float*>(compressed.data());
        for (std::size_t i = 0; i < n; ++i) {
            dst[i] = fp16_to_fp32_bits(src[i]);
        }
    }

    stats_.decompress_time_ms += now_ms() - start;
    return std::move(out);
}

// ── KV-Cache 量化 ───────────────────────────────────────────────────────────

std::pair<Tensor, Tensor> MemoryCompressor::quantize_kv_cache(
    const Tensor& k_cache, const Tensor& v_cache)
{
    // 简化：直接返回 FP16 版本
    auto k_compressed = compress_activations(k_cache);
    auto v_compressed = compress_activations(v_cache);

    Tensor k_out = k_compressed.ok() ? std::move(k_compressed.value()) : k_cache;
    Tensor v_out = v_compressed.ok() ? std::move(v_compressed.value()) : v_cache;

    return {std::move(k_out), std::move(v_out)};
}

std::pair<Tensor, Tensor> MemoryCompressor::dequantize_kv_cache(
    const Tensor& qk_cache, const Tensor& qv_cache)
{
    auto k_decompressed = decompress_activations(qk_cache);
    auto v_decompressed = decompress_activations(qv_cache);

    Tensor k_out = k_decompressed.ok() ? std::move(k_decompressed.value()) : qk_cache;
    Tensor v_out = v_decompressed.ok() ? std::move(v_decompressed.value()) : qv_cache;

    return {std::move(k_out), std::move(v_out)};
}

// ── 梯度检查点 ──────────────────────────────────────────────────────────────

ErrorCode MemoryCompressor::save_checkpoint(
    const Tensor& activation, const std::string& tag)
{
    checkpoints_[tag] = activation;  // 拷贝
    return ErrorCode::OK;
}

Result<Tensor> MemoryCompressor::load_checkpoint(const std::string& tag) {
    auto it = checkpoints_.find(tag);
    if (it == checkpoints_.end()) {
        return Error<Tensor>(ErrorCode::NOT_IMPLEMENTED,
            "Checkpoint not found: " + tag);
    }
    return it->second;  // 返回拷贝
}

ErrorCode MemoryCompressor::release_checkpoint(const std::string& tag) {
    checkpoints_.erase(tag);
    return ErrorCode::OK;
}

void MemoryCompressor::release_all_checkpoints() {
    checkpoints_.clear();
}

// ── 统计 ───────────────────────────────────────────────────────────────────

const CompressionStatistics& MemoryCompressor::statistics() const {
    return stats_;
}

std::size_t MemoryCompressor::total_saved_bytes() const {
    return stats_.original_bytes > stats_.compressed_bytes
        ? stats_.original_bytes - stats_.compressed_bytes
        : 0;
}

std::size_t MemoryCompressor::estimate_compressed_size(
    const Tensor& tensor, DType target_dtype)
{
    std::size_t n = 1;
    for (auto d : tensor.shape()) n *= d;
    return n * dtype_bytes(target_dtype);
}

// ── RLE 压缩 ────────────────────────────────────────────────────────────────

std::vector<std::uint8_t> MemoryCompressor::rle_compress(
    const std::uint8_t* data, std::size_t size)
{
    if (size == 0) return {};

    std::vector<std::uint8_t> result;
    result.reserve(size);

    for (std::size_t i = 0; i < size;) {
        std::uint8_t val = data[i];
        std::size_t run = 1;
        while (i + run < size && data[i + run] == val && run < 255) {
            ++run;
        }

        // 简单格式：[count][value]
        result.push_back(static_cast<std::uint8_t>(run));
        result.push_back(val);
        i += run;
    }

    return result;
}

std::vector<std::uint8_t> MemoryCompressor::rle_decompress(
    const std::uint8_t* data, std::size_t compressed_size,
    std::size_t original_size)
{
    std::vector<std::uint8_t> result;
    result.reserve(original_size);

    for (std::size_t i = 0; i + 1 < compressed_size; i += 2) {
        std::uint8_t count = data[i];
        std::uint8_t val = data[i + 1];
        for (std::uint8_t j = 0; j < count; ++j) {
            result.push_back(val);
        }
    }

    return result;
}

} // namespace memory
} // namespace qoocore
