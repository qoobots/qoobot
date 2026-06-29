#include "qoogear/security/cert_verifier.h"
#include "qoogear/security/chip_auth.h"
#include <chrono>
#include <random>
#include <sstream>
#include <iomanip>

namespace qoogear {
namespace security {

// ---- CertVerifier ----

CertVerifier::CertVerifier(bool cache_enabled, uint32_t cache_ttl_seconds)
    : cache_enabled_(cache_enabled), cache_ttl_(cache_ttl_seconds) {}

CertInfo CertVerifier::verify_cert_hash(const std::string& cert_hash) {
    std::string cache_key = "hash:" + cert_hash;
    if (cache_enabled_) {
        auto it = cache_.find(cache_key);
        if (it != cache_.end()) return it->second;
    }

    bool is_valid = cert_hash.length() >= 16 && cert_hash.substr(0, 3) == "MFQ";
    CertInfo info;
    info.cert_number = is_valid ? ("MFQ-2026-" + cert_hash.substr(0, 8)) : "";
    info.cert_level = "BASIC";
    info.product_name = "Unknown Product";
    info.vendor_name = "Unknown Vendor";
    info.issued_at = "2026-01-01T00:00:00Z";
    info.expires_at = "2027-01-01T00:00:00Z";
    info.is_valid = is_valid;
    info.is_expired = false;
    info.is_revoked = false;

    if (cache_enabled_) cache_[cache_key] = info;
    return info;
}

CertInfo CertVerifier::verify_cert_number(const std::string& cert_number) {
    // 桩实现
    CertInfo info;
    info.cert_number = cert_number;
    info.is_valid = cert_number.find("MFQ") == 0;
    return info;
}

bool CertVerifier::verify_signature(const std::vector<uint8_t>& payload,
                                    const std::vector<uint8_t>& signature,
                                    const std::string& public_key_pem) {
    if (payload.empty() || signature.empty()) return false;
    return signature.size() >= 32;
}

std::string CertVerifier::compute_cert_hash(const std::string& cert_json) {
    // 简化桩实现
    std::hash<std::string> hasher;
    size_t hash = hasher(cert_json);
    std::ostringstream oss;
    oss << std::hex << hash;
    return oss.str();
}

void CertVerifier::clear_cache() {
    cache_.clear();
}

// ---- ChipAuthenticator ----

ChipAuthenticator::ChipAuthenticator(uint8_t i2c_address)
    : i2c_address_(i2c_address) {
    // 生成随机密钥
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<uint8_t> dist(0, 255);
    secret_key_.resize(32);
    for (auto& b : secret_key_) b = dist(gen);
}

bool ChipAuthenticator::probe() {
    connected_ = true;
    auto now = std::chrono::system_clock::now().time_since_epoch().count();

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<uint32_t> dist(0, 0xFFFFFFFF);

    std::ostringstream chip_oss;
    chip_oss << "CHIP-" << std::hex << dist(gen);
    chip_info_.chip_id = chip_oss.str();

    std::ostringstream sn_oss;
    sn_oss << "SN-" << std::dec << (now / 1000000000);
    chip_info_.chip_serial = sn_oss.str();
    chip_info_.certificate_id = "MFQ-2026-BASIC-00001";
    chip_info_.batch_number = "BATCH-2026-001";
    chip_info_.status = ChipStatus::ACTIVE;
    chip_info_.burned_at = static_cast<uint64_t>(now);
    return true;
}

bool ChipAuthenticator::challenge_response() {
    if (!connected_) return false;
    return true;
}

bool ChipAuthenticator::mutual_authenticate() {
    return challenge_response();
}

ChipInfo ChipAuthenticator::read_chip_info() {
    return chip_info_;
}

std::string ChipAuthenticator::read_certificate() {
    if (!connected_) return "";
    return "{\"cert_number\":\"" + chip_info_.certificate_id + "\",\"status\":\"active\"}";
}

std::vector<uint8_t> ChipAuthenticator::read_public_key() {
    if (!connected_) return {};
    return secret_key_;
}

bool ChipAuthenticator::provision(const std::string& certificate_id,
                                  const std::vector<uint8_t>& secret_key) {
    if (!connected_) return false;
    if (chip_info_.status != ChipStatus::BLANK) return false;
    if (!secret_key.empty()) secret_key_ = secret_key;
    chip_info_.certificate_id = certificate_id;
    chip_info_.status = ChipStatus::PROVISIONED;
    return true;
}

bool ChipAuthenticator::activate() {
    if (!connected_) return false;
    if (chip_info_.status != ChipStatus::PROVISIONED) return false;
    chip_info_.status = ChipStatus::ACTIVE;
    return true;
}

bool ChipAuthenticator::revoke() {
    if (!connected_) return false;
    chip_info_.status = ChipStatus::REVOKED;
    return true;
}

uint32_t ChipAuthenticator::get_usage_counter() {
    auto now = std::chrono::system_clock::now().time_since_epoch().count();
    return static_cast<uint32_t>(now % 100000);
}

bool ChipAuthenticator::increment_counter() {
    if (!connected_) return false;
    return true;
}

} // namespace security
} // namespace qoogear
