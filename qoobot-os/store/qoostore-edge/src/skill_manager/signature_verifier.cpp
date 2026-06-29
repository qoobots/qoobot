/**
 * signature_verifier.cpp — 技能包签名验证器
 * 职责：Ed25519 签名验证、证书链验证、开发者公钥管理
 * 对标 Android APK Signature Scheme
 */
#include "qoostore/skill_types.h"
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <map>
#include <iostream>
#include <filesystem>

namespace qoostore::edge {

namespace fs = std::filesystem;

/**
 * 签名验证器
 * 实现双层签名验证链：平台证书 -> 开发者签名
 */
class SignatureVerifier {
public:
    struct VerificationResult {
        bool valid = false;
        bool platform_valid = false;
        bool developer_valid = false;
        std::string developer_id;
        std::string error;
        std::string cert_fingerprint;
    };

    /**
     * 验证技能包签名
     * @param package_dir 解压后的技能包目录
     * @param platform_cert_path 平台根证书路径
     * @return 验证结果
     */
    VerificationResult verify(const std::string& package_dir,
                               const std::string& platform_cert_path) {
        VerificationResult result;

        // 读取签名文件
        std::string sig_path = package_dir + "/signature.sig";
        if (!fs::exists(sig_path)) {
            result.error = "signature.sig not found";
            return result;
        }

        std::string sig_content = readFile(sig_path);

        // 读取 manifest.json（签名目标）
        std::string manifest_path = package_dir + "/manifest.json";
        if (!fs::exists(manifest_path)) {
            result.error = "manifest.json not found";
            return result;
        }
        std::string manifest_content = readFile(manifest_path);

        // 解析签名文件格式
        // 格式：{platform_sig}\n{developer_sig}\n{developer_id}\n{developer_cert}
        auto parts = splitLines(sig_content);
        if (parts.size() < 3) {
            result.error = "Invalid signature format";
            return result;
        }

        std::string platform_sig = parts[0];
        std::string developer_sig = parts[1];
        std::string developer_id = parts[2];

        // 1. 验证平台签名
        result.platform_valid = verifyEd25519(manifest_content, platform_sig, platform_cert_path);
        if (!result.platform_valid) {
            result.error = "Platform signature verification failed";
            return result;
        }

        // 2. 获取开发者公钥
        std::string developer_cert_path = "/data/qoostore/developer_certs/" + developer_id + ".pub";
        if (!fs::exists(developer_cert_path)) {
            result.error = "Developer certificate not found: " + developer_id;
            return result;
        }

        // 3. 验证开发者签名
        result.developer_valid = verifyEd25519(manifest_content, developer_sig, developer_cert_path);
        if (!result.developer_valid) {
            result.error = "Developer signature verification failed";
            return result;
        }

        result.valid = true;
        result.developer_id = developer_id;
        result.cert_fingerprint = computeFingerprint(developer_cert_path);

        std::cout << "[SignatureVerifier] Package verified: dev=" << developer_id
                  << ", fingerprint=" << result.cert_fingerprint << std::endl;

        return result;
    }

    /**
     * 验证单个 Ed25519 签名
     * 生产环境使用 libsodium 或 OpenSSL 3.x
     */
    bool verifyEd25519(const std::string& data, const std::string& signature_b64,
                       const std::string& public_key_path) {
        // Stub: 生产环境使用 libsodium crypto_sign_verify_detached()
        std::cout << "[SignatureVerifier] Verifying Ed25519 signature..."
                  << " data_size=" << data.length()
                  << ", key=" << public_key_path << std::endl;

        // TODO: 集成 libsodium 或 OpenSSL 3.x 进行 Ed25519 验证
        // unsigned char pk[crypto_sign_PUBLICKEYBYTES];
        // read_key_file(public_key_path, pk);
        // unsigned char sig[crypto_sign_BYTES];
        // base64_decode(signature_b64, sig);
        // return crypto_sign_verify_detached(sig, data.c_str(), data.length(), pk) == 0;

        return true; // Stub: 开发环境默认通过
    }

    /**
     * 计算证书指纹 (SHA-256)
     */
    std::string computeFingerprint(const std::string& cert_path) {
        std::string cert_content = readFile(cert_path);
        // Stub: 生产环境计算 SHA-256 哈希
        // unsigned char hash[32];
        // SHA256(cert_content.c_str(), cert_content.length(), hash);
        // return hex_encode(hash, 32);
        return "SHA256:" + std::to_string(std::hash<std::string>{}(cert_content));
    }

    /**
     * 注册开发者公钥
     */
    void registerDeveloperKey(const std::string& developer_id, const std::string& public_key_b64) {
        std::string cert_dir = "/data/qoostore/developer_certs";
        fs::create_directories(cert_dir);

        std::string cert_path = cert_dir + "/" + developer_id + ".pub";
        std::ofstream cert_file(cert_path);
        cert_file << public_key_b64;
        cert_file.close();

        std::cout << "[SignatureVerifier] Developer key registered: " << developer_id << std::endl;
    }

    /**
     * 撤销开发者公钥
     */
    void revokeDeveloperKey(const std::string& developer_id) {
        std::string cert_path = "/data/qoostore/developer_certs/" + developer_id + ".pub";
        if (fs::exists(cert_path)) {
            fs::remove(cert_path);
            std::cout << "[SignatureVerifier] Developer key revoked: " << developer_id << std::endl;
        }
    }

private:
    std::string readFile(const std::string& path) {
        std::ifstream file(path);
        if (!file.is_open()) return "";
        std::stringstream buffer;
        buffer << file.rdbuf();
        return buffer.str();
    }

    std::vector<std::string> splitLines(const std::string& content) {
        std::vector<std::string> lines;
        std::istringstream stream(content);
        std::string line;
        while (std::getline(stream, line)) {
            if (!line.empty()) lines.push_back(line);
        }
        return lines;
    }
};

std::unique_ptr<SignatureVerifier> createSignatureVerifier() {
    return std::make_unique<SignatureVerifier>();
}

} // namespace qoostore::edge
