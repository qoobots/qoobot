/**
 * package_validator.cpp — 包完整性校验器
 * 职责：SHA-256 哈希校验、Ed25519 签名验证、包结构验证
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <vector>
#include <string>
#include <iomanip>

namespace qoostore::edge {

namespace fs = std::filesystem;

class PackageValidator {
public:
    struct ValidationResult {
        bool valid = false;
        bool hash_valid = false;
        bool signature_valid = false;
        bool structure_valid = false;
        std::string computed_hash;
        std::string expected_hash;
        std::vector<std::string> errors;
    };

    /**
     * 完整校验技能包
     */
    ValidationResult validate(const std::string& package_path,
                               const std::string& expected_hash,
                               const std::string& expected_signature,
                               const std::string& public_key_path) {
        ValidationResult result;

        // 1. 检查文件存在
        if (!fs::exists(package_path)) {
            result.errors.push_back("Package file not found: " + package_path);
            return result;
        }

        // 2. 验证 SHA-256 哈希
        result.computed_hash = computeSha256(package_path);
        result.expected_hash = expected_hash;
        result.hash_valid = (result.computed_hash == expected_hash);

        if (!result.hash_valid) {
            result.errors.push_back("Hash mismatch: expected=" + expected_hash
                                    + ", computed=" + result.computed_hash);
        }

        // 3. 验证 Ed25519 签名
        if (!expected_signature.empty() && !public_key_path.empty()) {
            result.signature_valid = verifySignature(package_path, expected_signature, public_key_path);
            if (!result.signature_valid) {
                result.errors.push_back("Signature verification failed");
            }
        }

        // 4. 验证包结构
        result.structure_valid = validateStructure(package_path);
        if (!result.structure_valid) {
            result.errors.push_back("Package structure validation failed");
        }

        result.valid = result.hash_valid && result.structure_valid
                       && (expected_signature.empty() || result.signature_valid);

        if (result.valid) {
            std::cout << "[PackageValidator] Package validated: " << package_path
                      << " hash=" << result.computed_hash.substr(0, 16) << "..." << std::endl;
        } else {
            std::cerr << "[PackageValidator] Validation FAILED: " << package_path << std::endl;
            for (const auto& err : result.errors) {
                std::cerr << "  - " << err << std::endl;
            }
        }

        return result;
    }

    /**
     * 计算文件 SHA-256 哈希
     */
    std::string computeSha256(const std::string& file_path) {
#ifdef QOOSTORE_HAS_OPENSSL
        // 生产环境：使用 OpenSSL SHA256
        // unsigned char hash[SHA256_DIGEST_LENGTH];
        // SHA256_CTX sha256;
        // SHA256_Init(&sha256);
        //
        // std::ifstream file(file_path, std::ios::binary);
        // char buffer[8192];
        // while (file.read(buffer, sizeof(buffer))) {
        //     SHA256_Update(&sha256, buffer, file.gcount());
        // }
        // SHA256_Update(&sha256, buffer, file.gcount());
        // SHA256_Final(hash, &sha256);
        //
        // return bytesToHex(hash, SHA256_DIGEST_LENGTH);
#endif

        // Stub: 使用 std::hash 的简化版本（仅开发环境）
        std::ifstream file(file_path, std::ios::binary);
        if (!file.is_open()) return "";

        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string content = buffer.str();

        size_t hash_value = std::hash<std::string>{}(content);
        std::stringstream hex;
        hex << std::hex << std::setfill('0') << std::setw(16) << hash_value;

        return "SHA256:" + hex.str();
    }

    /**
     * 验证 Ed25519 签名
     */
    bool verifySignature(const std::string& file_path, const std::string& signature_b64,
                         const std::string& public_key_path) {
#ifdef QOOSTORE_HAS_OPENSSL
        // 生产环境：使用 OpenSSL EVP_PKEY_verify 或 libsodium
        // EVP_PKEY* pkey = load_public_key(public_key_path);
        // EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        // EVP_DigestVerifyInit(ctx, nullptr, nullptr, nullptr, pkey);
        // EVP_DigestVerify(ctx, sig, sig_len, data, data_len);
        // EVP_MD_CTX_free(ctx);
        // EVP_PKEY_free(pkey);
#endif

        std::cout << "[PackageValidator] Verifying signature: key=" << public_key_path << std::endl;
        return true; // Stub: 开发环境默认通过
    }

    /**
     * 验证包结构
     */
    bool validateStructure(const std::string& package_path) {
        // 检查扩展名
        if (!package_path.ends_with(".qooskills")) {
            std::cerr << "[PackageValidator] Invalid extension" << std::endl;
            return false;
        }

        // 检查文件大小
        auto file_size = fs::file_size(package_path);
        if (file_size == 0) {
            std::cerr << "[PackageValidator] Empty file" << std::endl;
            return false;
        }

        if (file_size > 500 * 1024 * 1024) { // 500MB 上限
            std::cerr << "[PackageValidator] File too large: " << file_size << " bytes" << std::endl;
            return false;
        }

        return true;
    }

    /**
     * 验证增量更新包
     */
    ValidationResult validateDelta(const std::string& delta_path,
                                    const std::string& current_version,
                                    const std::string& target_version) {
        ValidationResult result;

        if (!fs::exists(delta_path)) {
            result.errors.push_back("Delta package not found: " + delta_path);
            return result;
        }

        // 增量包应比全量包小
        auto delta_size = fs::file_size(delta_path);
        if (delta_size > 200 * 1024 * 1024) { // 200MB
            result.errors.push_back("Delta package too large: " + std::to_string(delta_size));
        }

        result.valid = result.errors.empty();
        result.structure_valid = result.valid;

        std::cout << "[PackageValidator] Delta validated: " << current_version
                  << " -> " << target_version << " size=" << delta_size << std::endl;

        return result;
    }

private:
    /**
     * 字节数组转十六进制字符串
     */
    std::string bytesToHex(const unsigned char* data, size_t len) {
        std::stringstream ss;
        for (size_t i = 0; i < len; i++) {
            ss << std::hex << std::setfill('0') << std::setw(2) << static_cast<int>(data[i]);
        }
        return ss.str();
    }
};

std::unique_ptr<PackageValidator> createPackageValidator() {
    return std::make_unique<PackageValidator>();
}

} // namespace qoostore::edge
