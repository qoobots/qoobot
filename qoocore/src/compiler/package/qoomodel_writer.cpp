/**
 * @file qoomodel_writer.cpp
 * @brief .qoomodel 文件格式写入器实现
 *
 * 将编译后的模型打包为 .qoomodel 单文件格式。
 *
 * .qoomodel 文件结构：
 *   [Magic: 4 bytes] QOO\x01
 *   [Header: 128 bytes] 版本/标志/模型名/区段大小等
 *   [Compiled Data: variable] 编译后的后端代码
 *   [Weights: variable] 量化后的权重数据
 *   [Config YAML: variable] 编译配置（zstd 压缩）
 *   [Metadata JSON: variable] 元数据（zstd 压缩）
 *   [Checksum: 32 bytes] SHA-256 校验和（覆盖以上所有内容）
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/compiler.h"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <vector>

namespace qoocore {

// ── Magic Number ──────────────────────────────────────────────────────
static constexpr std::uint8_t QOOMODEL_MAGIC[4] = {'Q', 'O', 'O', 0x01};

// ── Header 结构（128 字节，固定大小）────────────────────────────────
#pragma pack(push, 1)
struct QooModelHeader {
    std::uint8_t  magic[4];          // 0-3:   QOO\x01
    std::uint32_t version;           // 4-7:   格式版本
    std::uint32_t flags;             // 8-11:  标志位
    char          model_name[64];    // 12-75: 模型名称（NULL 终止）
    std::uint32_t target_backend;    // 76-79: 目标后端类型
    std::uint64_t compiled_size;     // 80-87: 编译代码大小
    std::uint64_t weight_size;       // 88-95: 权重数据大小
    std::uint64_t config_size;       // 96-103: 配置 YAML 大小
    std::uint64_t metadata_size;     // 104-111: 元数据 JSON 大小
    std::uint8_t  reserved[16];      // 112-127: 保留
};
#pragma pack(pop)

static_assert(sizeof(QooModelHeader) == 128, "QooModelHeader must be 128 bytes");

// ── 标志位 ────────────────────────────────────────────────────────────
enum QooModelFlags : std::uint32_t {
    FLAG_ENCRYPTED     = (1u << 0),  // AES-256-GCM 加密
    FLAG_QUANTIZED     = (1u << 1),  // 模型已量化
    FLAG_ZEROCOPY      = (1u << 2),  // 零拷贝友好
    FLAG_COMPRESSED    = (1u << 3),  // Config/Metadata 使用 zstd 压缩
};

// ── 写入 .qoomodel 文件 ──────────────────────────────────────────────
Result<void> write_qoomodel(
    const std::string& output_path,
    const std::string& model_name,
    BackendType target_backend,
    const std::vector<std::uint8_t>& compiled_data,
    const std::vector<std::uint8_t>& weight_data,
    const std::string& config_yaml,
    const std::string& metadata_json,
    bool is_quantized,
    bool is_zerocopy_friendly,
    bool overwrite) {

    // 检查文件是否存在
    if (!overwrite) {
        std::ifstream check(output_path);
        if (check.good()) {
            return Error(ErrorCode::FILE_NOT_FOUND,
                         "Output file already exists: " + output_path +
                         " (use overwrite=true to replace)");
        }
    }

    spdlog::info("Writing .qoomodel to: {}", output_path);
    spdlog::info("  model_name:      {}", model_name);
    spdlog::info("  target_backend:  {}", static_cast<int>(target_backend));
    spdlog::info("  compiled_data:   {} bytes", compiled_data.size());
    spdlog::info("  weight_data:     {} bytes", weight_data.size());
    spdlog::info("  config_yaml:     {} bytes", config_yaml.size());
    spdlog::info("  metadata_json:   {} bytes", metadata_json.size());

    // 构建 Header
    QooModelHeader header = {};
    std::memcpy(header.magic, QOOMODEL_MAGIC, 4);
    header.version = 1;
    header.flags = 0;
    if (is_quantized) header.flags |= FLAG_QUANTIZED;
    if (is_zerocopy_friendly) header.flags |= FLAG_ZEROCOPY;

    // 复制模型名称（截断到 63 字符 + NULL）
    std::strncpy(header.model_name, model_name.c_str(), 63);
    header.model_name[63] = '\0';

    header.target_backend = static_cast<std::uint32_t>(target_backend);
    header.compiled_size = compiled_data.size();
    header.weight_size = weight_data.size();
    header.config_size = config_yaml.size();
    header.metadata_size = metadata_json.size();
    std::memset(header.reserved, 0, sizeof(header.reserved));

    // 写入文件
    std::ofstream ofs(output_path, std::ios::binary | std::ios::trunc);
    if (!ofs) {
        return Error(ErrorCode::FILE_NOT_FOUND,
                     "Cannot create output file: " + output_path);
    }

    // 写入各区段
    ofs.write(reinterpret_cast<const char*>(&header), sizeof(header));
    if (!compiled_data.empty()) {
        ofs.write(reinterpret_cast<const char*>(compiled_data.data()),
                  compiled_data.size());
    }
    if (!weight_data.empty()) {
        ofs.write(reinterpret_cast<const char*>(weight_data.data()),
                  weight_data.size());
    }
    if (!config_yaml.empty()) {
        ofs.write(config_yaml.data(), config_yaml.size());
    }
    if (!metadata_json.empty()) {
        ofs.write(metadata_json.data(), metadata_json.size());
    }

    // TODO: 计算并写入 SHA-256 校验和（覆盖 Header + 所有区段）
    // 当前写入占位校验和
    std::vector<std::uint8_t> placeholder_checksum(32, 0xAA);
    ofs.write(reinterpret_cast<const char*>(placeholder_checksum.data()), 32);

    if (!ofs) {
        return Error(ErrorCode::FILE_CORRUPTED,
                     "Failed to write .qoomodel file: " + output_path);
    }

    std::size_t total_size = sizeof(header) + compiled_data.size() +
                             weight_data.size() + config_yaml.size() +
                             metadata_json.size() + 32;

    spdlog::info(".qoomodel written successfully ({} bytes total)", total_size);
    return Ok();
}

}  // namespace qoocore
