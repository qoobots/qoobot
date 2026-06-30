/**
 * sha256.hpp — 轻量级 SHA-256 哈希实现
 *
 * 纯 C++17 实现，无外部依赖。用于 qoostore-edge 中：
 *   - 技能包完整性校验
 *   - 证书指纹计算
 *   - 增量更新哈希比对
 *
 * 对标：OpenSSL SHA256 功能子集，但为嵌入式环境优化。
 * RFC 6234 兼容。
 */

#pragma once

#include <cstdint>
#include <string>
#include <cstring>
#include <sstream>
#include <iomanip>
#include <array>

namespace qoostore::edge::crypto {

class SHA256 {
public:
    static constexpr size_t DIGEST_SIZE = 32;
    static constexpr size_t BLOCK_SIZE = 64;

    using Digest = std::array<uint8_t, DIGEST_SIZE>;

    SHA256() { reset(); }

    void reset() {
        total_[0] = total_[1] = 0;
        hash_[0] = 0x6a09e667;
        hash_[1] = 0xbb67ae85;
        hash_[2] = 0x3c6ef372;
        hash_[3] = 0xa54ff53a;
        hash_[4] = 0x510e527f;
        hash_[5] = 0x9b05688c;
        hash_[6] = 0x1f83d9ab;
        hash_[7] = 0x5be0cd19;
        pos_ = 0;
    }

    void update(const uint8_t* data, size_t len) {
        for (size_t i = 0; i < len; i++) {
            buffer_[pos_++] = data[i];
            if (pos_ == BLOCK_SIZE) {
                process_block(buffer_.data());
                total_[0] += BLOCK_SIZE * 8;
                if (total_[0] < BLOCK_SIZE * 8) total_[1]++;
                pos_ = 0;
            }
        }
    }

    void update(const std::string& str) {
        update(reinterpret_cast<const uint8_t*>(str.data()), str.size());
    }

    Digest finalize() {
        total_[0] += pos_ * 8;
        if (total_[0] < static_cast<uint64_t>(pos_ * 8)) total_[1]++;

        buffer_[pos_++] = 0x80;
        if (pos_ > 56) {
            while (pos_ < BLOCK_SIZE) buffer_[pos_++] = 0;
            process_block(buffer_.data());
            pos_ = 0;
        }
        while (pos_ < 56) buffer_[pos_++] = 0;

        // 写入长度（大端序）
        buffer_[56] = static_cast<uint8_t>(total_[1] >> 24);
        buffer_[57] = static_cast<uint8_t>(total_[1] >> 16);
        buffer_[58] = static_cast<uint8_t>(total_[1] >> 8);
        buffer_[59] = static_cast<uint8_t>(total_[1]);
        buffer_[60] = static_cast<uint8_t>(total_[0] >> 24);
        buffer_[61] = static_cast<uint8_t>(total_[0] >> 16);
        buffer_[62] = static_cast<uint8_t>(total_[0] >> 8);
        buffer_[63] = static_cast<uint8_t>(total_[0]);
        process_block(buffer_.data());

        Digest digest;
        for (int i = 0; i < 8; i++) {
            digest[i * 4]     = static_cast<uint8_t>(hash_[i] >> 24);
            digest[i * 4 + 1] = static_cast<uint8_t>(hash_[i] >> 16);
            digest[i * 4 + 2] = static_cast<uint8_t>(hash_[i] >> 8);
            digest[i * 4 + 3] = static_cast<uint8_t>(hash_[i]);
        }
        return digest;
    }

    // 便捷一次性哈希
    static Digest hash(const std::string& data) {
        SHA256 s;
        s.update(data);
        return s.finalize();
    }

    static Digest hash(const uint8_t* data, size_t len) {
        SHA256 s;
        s.update(data, len);
        return s.finalize();
    }

    static std::string hex(const Digest& digest) {
        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        for (uint8_t b : digest) {
            oss << std::setw(2) << static_cast<int>(b);
        }
        return oss.str();
    }

    static std::string hex(const std::string& data) {
        return hex(hash(data));
    }

private:
    std::array<uint8_t, BLOCK_SIZE> buffer_{};
    uint32_t hash_[8];
    uint64_t total_[2];
    size_t pos_;

    static constexpr uint32_t K[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
        0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
        0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    };

    static constexpr uint32_t rotr(uint32_t x, uint32_t n) {
        return (x >> n) | (x << (32 - n));
    }

    void process_block(const uint8_t* block) {
        uint32_t w[64];
        for (int i = 0; i < 16; i++) {
            w[i] = (static_cast<uint32_t>(block[i * 4]) << 24) |
                   (static_cast<uint32_t>(block[i * 4 + 1]) << 16) |
                   (static_cast<uint32_t>(block[i * 4 + 2]) << 8) |
                   static_cast<uint32_t>(block[i * 4 + 3]);
        }
        for (int i = 16; i < 64; i++) {
            uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }

        uint32_t a = hash_[0], b = hash_[1], c = hash_[2], d = hash_[3];
        uint32_t e = hash_[4], f = hash_[5], g = hash_[6], h = hash_[7];

        for (int i = 0; i < 64; i++) {
            uint32_t S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
            uint32_t ch = (e & f) ^ (~e & g);
            uint32_t temp1 = h + S1 + ch + K[i] + w[i];
            uint32_t S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t temp2 = S0 + maj;

            h = g; g = f; f = e; e = d + temp1;
            d = c; c = b; b = a; a = temp1 + temp2;
        }

        hash_[0] += a; hash_[1] += b; hash_[2] += c; hash_[3] += d;
        hash_[4] += e; hash_[5] += f; hash_[6] += g; hash_[7] += h;
    }
};

// ============================================================================
// Ed25519 验证（简化版，开发用）
//
// 生产环境应使用 libsodium 的 crypto_sign_verify_detached()
// 这里提供基于公钥哈希指纹比对的开发用验证方案
// ============================================================================

/**
 * 验证公钥文件并返回 SHA-256 指纹
 * 生产环境替换为 Ed25519 签名验证
 */
inline std::string compute_key_fingerprint(const std::string& key_data) {
    return "SHA256:" + SHA256::hex(key_data);
}

} // namespace qoostore::edge::crypto
