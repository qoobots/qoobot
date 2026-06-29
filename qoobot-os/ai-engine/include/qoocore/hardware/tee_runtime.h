/**
 * @file tee_runtime.h
 * @brief 安全执行环境 — TEE 推理（模型/IP 保护）、安全内存区域
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include "qoocore/tensor.h"
#include <cstdint>
#include <string>
#include <vector>

namespace qoocore {
namespace hardware {

enum class TEELevel : std::uint8_t {
    NONE      = 0,
    TRUSTZONE = 1,  ///< ARM TrustZone
    SGX       = 2,  ///< Intel SGX
    SEV       = 3,  ///< AMD SEV
};

struct TEEConfig {
    TEELevel level{TEELevel::NONE};
    std::size_t secure_memory_mb{128};
    bool encrypt_weights{true};
    bool encrypt_activations{false};
    bool verify_integrity{true};
    std::string attestation_key_path;
};

struct TEESession {
    std::string session_id;
    bool active{false};
    std::size_t secure_memory_used{0};
};

class TEERuntime {
public:
    explicit TEERuntime(const TEEConfig& config);
    ~TEERuntime();

    bool initialize();
    void shutdown();

    ErrorCode create_session(TEESession& session);
    ErrorCode destroy_session(const std::string& session_id);

    ErrorCode encrypt_model(const Tensor& plaintext, const std::string& session_id,
                            Tensor& ciphertext);
    ErrorCode decrypt_model(const Tensor& ciphertext, const std::string& session_id,
                            Tensor& plaintext);

    ErrorCode secure_infer(const Tensor& input, const std::string& session_id,
                           Tensor& output);

    bool verify_attestation(const std::string& session_id) const;

    std::size_t secure_memory_available() const;

private:
    TEEConfig config_;
    std::vector<TEESession> sessions_;
    bool initialized_{false};
};

} // namespace hardware
} // namespace qoocore
