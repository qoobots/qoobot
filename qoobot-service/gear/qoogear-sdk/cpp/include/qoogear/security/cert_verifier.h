#pragma once

/**
 * @file cert_verifier.h
 * @brief MFQ 证书验证器 — C++17
 */

#include <cstdint>
#include <string>
#include <unordered_map>

namespace qoogear {
namespace security {

struct CertInfo {
    std::string cert_number;
    std::string cert_level;
    std::string product_name;
    std::string vendor_name;
    std::string issued_at;
    std::string expires_at;
    bool is_valid = false;
    bool is_expired = false;
    bool is_revoked = false;
};

class CertVerifier {
public:
    explicit CertVerifier(bool cache_enabled = true, uint32_t cache_ttl_seconds = 3600);

    CertInfo verify_cert_hash(const std::string& cert_hash);
    CertInfo verify_cert_number(const std::string& cert_number);
    bool verify_signature(const std::vector<uint8_t>& payload,
                          const std::vector<uint8_t>& signature,
                          const std::string& public_key_pem);

    static std::string compute_cert_hash(const std::string& cert_json);
    void clear_cache();

private:
    bool cache_enabled_;
    uint32_t cache_ttl_;
    std::unordered_map<std::string, CertInfo> cache_;
};

} // namespace security
} // namespace qoogear
