#pragma once

/**
 * @file chip_auth.h
 * @brief MFQ 认证芯片通信 — C++17
 */

#include <cstdint>
#include <string>
#include <vector>

namespace qoogear {
namespace security {

enum class ChipStatus : uint8_t {
    BLANK = 0,
    PROVISIONED = 1,
    ACTIVE = 2,
    REVOKED = 3,
    EXPIRED = 4,
};

struct ChipInfo {
    std::string chip_id;
    std::string chip_serial;
    std::string certificate_id;
    std::string batch_number;
    ChipStatus status{ChipStatus::BLANK};
    uint64_t burned_at = 0;
};

class ChipAuthenticator {
public:
    explicit ChipAuthenticator(uint8_t i2c_address = 0x50);

    bool is_connected() const { return connected_; }
    const ChipInfo& chip_info() const { return chip_info_; }

    // 探测
    bool probe();

    // 挑战-响应认证
    bool challenge_response();
    bool mutual_authenticate();

    // 数据读取
    ChipInfo read_chip_info();
    std::string read_certificate();
    std::vector<uint8_t> read_public_key();

    // 生命周期
    bool provision(const std::string& certificate_id,
                   const std::vector<uint8_t>& secret_key = {});
    bool activate();
    bool revoke();

    // 防克隆计数器
    uint32_t get_usage_counter();
    bool increment_counter();

private:
    uint8_t i2c_address_;
    bool connected_ = false;
    ChipInfo chip_info_;
    std::vector<uint8_t> secret_key_;
};

} // namespace security
} // namespace qoogear
