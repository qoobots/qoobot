/**
 * @file qoomodel_writer.cpp
 * @brief .qoomodel 文件格式写入器实现
 *
 * 将编译后的模型（权重 + 编译代码 + 配置 + 元数据）
 * 打包为 .qoomodel 文件（单文件自包含，mmap 友好）。
 *
 * 文件二进制布局：
 *   [0] Magic Number (4B)     QOO\x01
 *   [1] Header (64B)        固定大小头
 *   [2] Compiled Model (变长)  编译后的模型执行代码
 *   [3] Model Weights (变长)  量化后的权重数据
 *   [4] Model Config  (变长)  YAML 格式，zstd 压缩
 *   [5] Metadata     (变长)  JSON 格式，zstd 压缩
 *   [6] Checksum     (32B)  SHA-256 校验和
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/compiler.h"
#include "qoocore/core.h"

#include <fstream>
#include <vector>
#include <string>
#include <cstring>
#include <iomanip>
#include <sstream>

namespace qoocore {
namespace compiler {

// ── Magic Number ─────────────────────────────────────────────────────
static constexpr std::uint8_t MAGIC[4] = {'Q', 'O', 'O', 0x01};
static constexpr std::size_t HEADER_SIZE = 64;
static constexpr std::size_t CHECKSUM_SIZE = 32;

// ── 字节序辅助 ──────────────────────────────────────────────────
static void write_u16(std::vector<std::uint8_t>& buf, std::uint16_t v) {
    buf.push_back(v & 0xFF);
    buf.push_back((v >> 8) & 0xFF);
}
static void write_u32(std::vector<std::uint8_t>& buf, std::uint32_t v) {
    buf.push_back(v & 0xFF);
    buf.push_back((v >> 8) & 0xFF);
    buf.push_back((v >> 16) & 0xFF);
    buf.push_back((v >> 24) & 0xFF);
}
static void write_u64(std::vector<std::uint8_t>& buf, std::uint64_t v) {
    for (int i = 0; i < 8; ++i) {
        buf.push_back((v >> (i * 8)) & 0xFF);
    }
}

// ── zstd 压缩辅助（骨架，完整实现需链接 libzstd）─────────
static Result<std::vector<std::uint8_t>> compress_zstd(
    const std::string& input) {
    (void)input;
    // TODO: 链接 libzstd，调用 ZSTD_compress()
    // 当前返回未压缩数据
    std::vector<std::uint8_t> result(input.begin(), input.end());
    return result;
}

// ── SHA-256 辅助（骨架）─────────────────────────────────────
static std::vector<std::uint8_t> compute_sha256(
    const std::vector<std::uint8_t>& data) {
    (void)data;
    // TODO: 链接 OpenSSL 或 mbedTLS，计算 SHA-256
    // 当前返回全零（校验和失败）
    return std::vector<std::uint8_t>(CHECKSUM_SIZE, 0x00);
}

// ── 写入 .qoomodel 文件 ─────────────────────────────────────
/**
 * @brief 将编译结果打包为 .qoomodel 文件。
 *
 * @param compiled_data  编译后的模型执行代码（NPU: QNN graph 等）
 * @param weights_data  量化后的权重数据
 * @param config_yaml  模型配置（YAML 字符串）
 * @param metadata_json 元数据（JSON 字符串）
 * @param output_path  输出文件路径
 * @return 成功或错误
 */
Result<void> package_qoomodel(
    const std::vector<std::uint8_t>& compiled_data,
    const std::vector<std::uint8_t>& weights_data,
    const std::string& config_yaml,
    const std::string& metadata_json,
    const std::string& output_path) {

    spdlog::info("Packaging .qoomodel: {}", output_path);

    // 1. 压缩配置和元数据
    auto config_compressed = compress_zstd(config_yaml);
    if (!config_compressed.ok()) {
        return Error(config_compressed.error().code,
                     "Config compression failed: " + config_compressed.error().message);
    }

    auto metadata_compressed = compress_zstd(metadata_json);
    if (!metadata_compressed.ok()) {
        return Error(metadata_compressed.error().code,
                     "Metadata compression failed: " + metadata_compressed.error().message);
    }

    // 2. 组装文件内容（不带校验和）
    std::vector<std::uint8_t> file_data;
    file_data.reserve(HEADER_SIZE + compiled_data.size() +
                      weights_data.size() +
                      config_compressed.value().size() +
                      metadata_compressed.value().size() +
                      CHECKSUM_SIZE);

    // [0] Magic Number
    file_data.insert(file_data.end(), MAGIC, MAGIC + 4);

    // [1] Header（先占坑，最后回填）
    std::size_t header_start = file_data.size();
    file_data.resize(header_start + HEADER_SIZE, 0x00);

    // [2] Compiled Model
    file_data.insert(file_data.end(), compiled_data.begin(), compiled_data.end());

    // [3] Model Weights
    file_data.insert(file_data.end(), weights_data.begin(), weights_data.end());

    // [4] Model Config（压缩后）
    file_data.insert(file_data.end(),
                      config_compressed.value().begin(),
                      config_compressed.value().end());

    // [5] Metadata（压缩后）
    file_data.insert(file_data.end(),
                      metadata_compressed.value().begin(),
                      metadata_compressed.value().end());

    // 3. 回填 Header
    {
        std::size_t offset = header_start;

        // version (u32)
        std::uint32_t version = 1;
        std::memcpy(&file_data[offset], &version, 4);
        offset += 4;

        // flags (u32)
        std::uint32_t flags = 0x02;  // bit 1: 已量化
        std::memcpy(&file_data[offset], &flags, 4);
        offset += 4;

        // model_name (32 bytes)
        std::string name = "model";
        std::memset(&file_data[offset], 0, 32);
        std::memcpy(&file_data[offset], name.c_str(),
                   std::min(name.size(), static_cast<std::size_t>(31)));
        offset += 32;

        // input_count (u32) + output_count (u32)
        std::uint32_t input_count = 1;
        std::uint32_t output_count = 1;
        std::memcpy(&file_data[offset], &input_count, 4);
        offset += 4;
        std::memcpy(&file_data[offset], &output_count, 4);
        offset += 4;

        // target_backend (u32)
        std::uint32_t target_backend = static_cast<std::uint32_t>(BackendType::NPU);
        std::memcpy(&file_data[offset], &target_backend, 4);
        offset += 4;

        // compiled_size (u64)
        std::uint64_t compiled_size = compiled_data.size();
        std::memcpy(&file_data[offset], &compiled_size, 8);
        offset += 8;

        // weight_size (u64)
        std::uint64_t weight_size = weights_data.size();
        std::memcpy(&file_data[offset], &weight_size, 8);
        offset += 8;

        // config_size (u64) + metadata_size (u64)
        std::uint64_t config_size = config_compressed.value().size();
        std::uint64_t metadata_size = metadata_compressed.value().size();
        std::memcpy(&file_data[offset], &config_size, 8);
        offset += 8;
        std::memcpy(&file_data[offset], &metadata_size, 8);
        offset += 8;
    }

    // 4. 计算校验和（覆盖 [0]~[5]）
    std::vector<std::uint8_t> checksum = compute_sha256(file_data);

    // 5. 写入校验和 [6]
    file_data.insert(file_data.end(), checksum.begin(), checksum.end());

    // 6. 写入文件
    std::ofstream ofs(output_path, std::ios::binary);
    if (!ofs) {
        return Error(ErrorCode::FILE_NOT_FOUND,
                     "Cannot open output file: " + output_path);
    }
    ofs.write(reinterpret_cast<const char*>(file_data.data()),
               file_data.size());
    if (!ofs) {
        return Error(ErrorCode::FILE_CORRUPTED,
                     "Failed to write .qoomodel file");
    }

    spdlog::info(".qoomodel packaged: {} bytes written to {}",
                   file_data.size(), output_path);
    return Ok;
}

}  // namespace compiler
}  // namespace qoocore
