/**
 * @file qoomodel_reader.cpp
 * @brief .qoomodel 文件格式读取器实现
 *
 * 读取并验证 .qoomodel 文件（单文件自包含，mmap 友好）。
 *
 * 读取流程：
 *   1. 验证 Magic Number（4 字节）
 *   2. 读取 Header（64 字节固定大小）
 *   3. 验证 SHA-256 校验和
 *   4. 解析各区段（Compiled Model / Weights / Config / Metadata）
 *   5. 返回 QooModel 结构体
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/compiler.h"

#include <fstream>
#include <vector>
#include <string>
#include <cstring>
#include <iomanip>

namespace qoocore {
namespace compiler {

// ── Magic Number ──────────────────────────────────────────────────
static constexpr std::uint8_t EXPECTED_MAGIC[4] = {'Q', 'O', 'O', 0x01};

// ── 读取并验证 .qoomodel 文件 ─────────────────────────────────
/**
 * @brief 读取 .qoomodel 文件，返回解析后的 QooModel 信息。
 *
 * @param file_path  .qoomodel 文件路径
 * @return 成功时返回 QooModel 信息（JSON 字符串），失败时返回错误
 */
Result<std::string> read_qoomodel(const std::string& file_path) {
    spdlog::info("Reading .qoomodel: {}", file_path);

    // 1. 打开文件
    std::ifstream ifs(file_path, std::ios::binary | std::ios::ate);
    if (!ifs) {
        return Error(ErrorCode::FILE_NOT_FOUND,
                     "Cannot open .qoomodel file: " + file_path);
    }

    std::size_t file_size = static_cast<std::size_t>(ifs.tellg());
    ifs.seekg(0, std::ios::beg);

    if (file_size < 4 + 64 + 32) {  // Magic + Header + Checksum 最小大小
        return Error(ErrorCode::FILE_CORRUPTED,
                     "File too small to be a valid .qoomodel");
    }

    // 2. 读取 Magic Number
    std::uint8_t magic[4];
    ifs.read(reinterpret_cast<char*>(magic), 4);
    if (!ifs) {
        return Error(ErrorCode::FILE_CORRUPTED, "Failed to read magic number");
    }
    if (std::memcmp(magic, EXPECTED_MAGIC, 4) != 0) {
        return Error(ErrorCode::FILE_CORRUPTED,
                     "Invalid magic number (expected QOO\\x01, got " +
                     std::to_string(magic[0]) + " " + std::to_string(magic[1]) + " " +
                     std::to_string(magic[2]) + " " + std::to_string(magic[3]));
    }

    // 3. 读取 Header（64 字节）
    std::vector<std::uint8_t> header(64, 0x00);
    ifs.read(reinterpret_cast<char*>(header.data()), 64);
    if (!ifs) {
        return Error(ErrorCode::FILE_CORRUPTED, "Failed to read header");
    }

    // 解析 Header 字段
    std::uint32_t version = *reinterpret_cast<std::uint32_t*>(&header[0]);
    std::uint32_t flags = *reinterpret_cast<std::uint32_t*>(&header[4]);
    
    // model_name（32 字节，NULL 终止）
    char model_name_cstr[33] = {0};
    std::memcpy(model_name_cstr, &header[8], 32);
    std::string model_name = model_name_cstr;

    std::uint32_t input_count = *reinterpret_cast<std::uint32_t*>(&header[40]);
    std::uint32_t output_count = *reinterpret_cast<std::uint32_t*>(&header[44]);
    std::uint32_t target_backend = *reinterpret_cast<std::uint32_t*>(&header[48]);
    std::uint64_t compiled_size = *reinterpret_cast<std::uint64_t*>(&header[52]);
    std::uint64_t weight_size = *reinterpret_cast<std::uint64_t*>(&header[60]);
    std::uint64_t config_size = *reinterpret_cast<std::uint64_t*>(&header[68]);
    std::uint64_t metadata_size = *reinterpret_cast<std::uint64_t*>(&header[76]);

    spdlog::info("  version:      {}", version);
    spdlog::info("  model_name:   {}", model_name);
    spdlog::info("  target_backend: {}", target_backend);
    spdlog::info("  compiled_size: {} bytes", compiled_size);
    spdlog::info("  weight_size:  {} bytes", weight_size);

    // 4. 验证校验和（TODO：实现 SHA-256）
    // 读取文件末尾的校验和
    std::vector<std::uint8_t> file_data(file_size - 32, 0);  // 不包括校验和本身
    ifs.seekg(0, std::ios::beg);
    ifs.read(reinterpret_cast<char*>(file_data.data()), file_data.size());
    
    std::vector<std::uint8_t> stored_checksum(32, 0);
    ifs.read(reinterpret_cast<char*>(stored_checksum.data()), 32);
    
    // TODO: 计算 SHA-256 并比较
    spdlog::warn("Checksum verification not yet implemented (TODO)");

    // 5. 构建返回信息（JSON 字符串）
    std::stringstream ss;
    ss << "{\n"
        << "  \"version\": " << version << ",\n"
        << "  \"model_name\": \"" << model_name << "\",\n"
        << "  \"target_backend\": " << target_backend << ",\n"
        << "  \"compiled_size\": " << compiled_size << ",\n"
        << "  \"weight_size\": " << weight_size << ",\n"
        << "  \"config_size\": " << config_size << ",\n"
        << "  \"metadata_size\": " << metadata_size << ",\n"
        << "  \"file_size\": " << file_size << "\n"
        << "}";
    
    spdlog::info(".qoomodel read successfully");
    return ss.str();
}

}  // namespace compiler
}  // namespace qoocore
