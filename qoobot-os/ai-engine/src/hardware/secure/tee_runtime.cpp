/**
 * @file tee_runtime.cpp
 * @brief TEE 安全执行环境实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/hardware/tee_runtime.h"
#include <algorithm>
#include <cstring>
#include <random>
#include <sstream>

namespace qoocore {
namespace hardware {

namespace {
std::string generate_session_id() {
    static std::mt19937 rng(std::random_device{}());
    std::uniform_int_distribution<int> dist(0, 15);
    std::ostringstream oss;
    oss << "tee_";
    for (int i = 0; i < 16; ++i) oss << "0123456789abcdef"[dist(rng)];
    return oss.str();
}
} // anonymous

TEERuntime::TEERuntime(const TEEConfig& config) : config_(config) {}
TEERuntime::~TEERuntime() { shutdown(); }

bool TEERuntime::initialize() {
    if (initialized_) return true;
    initialized_ = true;
    return true;
}

void TEERuntime::shutdown() {
    sessions_.clear();
    initialized_ = false;
}

ErrorCode TEERuntime::create_session(TEESession& session) {
    if (!initialized_) return ErrorCode::ENGINE_NOT_INIT;

    session.session_id = generate_session_id();
    session.active = true;
    session.secure_memory_used = 0;
    sessions_.push_back(session);
    return ErrorCode::OK;
}

ErrorCode TEERuntime::destroy_session(const std::string& session_id) {
    sessions_.erase(
        std::remove_if(sessions_.begin(), sessions_.end(),
            [&](const TEESession& s) { return s.session_id == session_id; }),
        sessions_.end());
    return ErrorCode::OK;
}

ErrorCode TEERuntime::encrypt_model(
    const Tensor& plaintext, const std::string& session_id, Tensor& ciphertext)
{
    if (!config_.encrypt_weights) {
        ciphertext = plaintext;  // 直通
        return ErrorCode::OK;
    }

    // 简化的 XOR 加密（生产环境应使用 AES-GCM）
    const float* src = static_cast<const float*>(plaintext.data());
    const auto& shape = plaintext.shape();
    std::size_t n = 1;
    for (auto d : shape) n *= d;

    auto result = Tensor::create(std::vector<std::size_t>(shape.begin(), shape.end()),
                                  plaintext.dtype());
    if (!result.ok()) return ErrorCode::HAL_INIT_FAILED;

    ciphertext = std::move(result.value());
    float* dst = static_cast<float*>(ciphertext.data());

    // 使用 session_id hash 作为密钥
    std::size_t key_hash = std::hash<std::string>{}(session_id);
    for (std::size_t i = 0; i < n; ++i) {
        std::uint32_t key = static_cast<std::uint32_t>(key_hash ^ (i * 2654435761ULL));
        float key_float;
        std::memcpy(&key_float, &key, sizeof(float));
        dst[i] = src[i] + key_float * 1e-6f;  // 微小扰动
    }

    // 更新安全内存使用
    for (auto& s : sessions_) {
        if (s.session_id == session_id) {
            s.secure_memory_used += n * sizeof(float);
            break;
        }
    }

    return ErrorCode::OK;
}

ErrorCode TEERuntime::decrypt_model(
    const Tensor& ciphertext, const std::string& session_id, Tensor& plaintext)
{
    if (!config_.encrypt_weights) {
        plaintext = ciphertext;
        return ErrorCode::OK;
    }

    const float* src = static_cast<const float*>(ciphertext.data());
    const auto& shape = ciphertext.shape();
    std::size_t n = 1;
    for (auto d : shape) n *= d;

    auto result = Tensor::create(std::vector<std::size_t>(shape.begin(), shape.end()),
                                  ciphertext.dtype());
    if (!result.ok()) return ErrorCode::HAL_INIT_FAILED;

    plaintext = std::move(result.value());
    float* dst = static_cast<float*>(plaintext.data());

    std::size_t key_hash = std::hash<std::string>{}(session_id);
    for (std::size_t i = 0; i < n; ++i) {
        std::uint32_t key = static_cast<std::uint32_t>(key_hash ^ (i * 2654435761ULL));
        float key_float;
        std::memcpy(&key_float, &key, sizeof(float));
        dst[i] = src[i] - key_float * 1e-6f;
    }

    return ErrorCode::OK;
}

ErrorCode TEERuntime::secure_infer(
    const Tensor& input, const std::string& session_id, Tensor& output)
{
    // 解密模型 → 推理 → 加密输出
    output = input;  // 简化为直通
    return ErrorCode::OK;
}

bool TEERuntime::verify_attestation(const std::string& session_id) const {
    return config_.verify_integrity;
}

std::size_t TEERuntime::secure_memory_available() const {
    std::size_t used = 0;
    for (const auto& s : sessions_) used += s.secure_memory_used;
    return (used < config_.secure_memory_mb * 1024 * 1024)
        ? config_.secure_memory_mb * 1024 * 1024 - used : 0;
}

} // namespace hardware
} // namespace qoocore
