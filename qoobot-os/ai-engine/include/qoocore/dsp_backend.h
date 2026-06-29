/**
 * @file dsp_backend.h
 * @brief DSP 推理后端 — 高通 Hexagon / CEVA DSP 推理卸载
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/backend.h"
#include <cstdint>
#include <string>

namespace qoocore {

enum class DSPVendor : std::uint8_t {
    QUALCOMM_HEXAGON = 0,
    CEVA_TELEK_LITE  = 1,
    CADENCE_TENSILICA= 2,
    GENERIC          = 255,
};

struct DSPConfig {
    DSPVendor vendor{DSPVendor::QUALCOMM_HEXAGON};
    std::string lib_path;
    std::uint32_t num_cores{4};
    std::uint32_t l2_cache_kb{1024};
    bool enable_hvx{true};       ///< Hexagon Vector eXtensions
    bool enable_hmx{false};      ///< Hexagon Matrix eXtensions
    bool enable_fastrpc{true};   ///< Qualcomm FastRPC
};

class DSPBackend : public Backend {
public:
    explicit DSPBackend(const DSPConfig& config);
    ~DSPBackend() override;

    bool initialize() override;
    void shutdown() override;

    BackendType type() const override { return BackendType::DSP; }
    std::string name() const override;
    std::string version() const override;

    BackendCapabilities capabilities() const override;
    bool supports_dtype(DType dtype) const override;

    ErrorCode load_model(const ModelConfig& config) override;
    ErrorCode unload_model(ModelHandle handle) override;

    Result<Tensor> infer(ModelHandle handle, const Tensor& input) override;
    Result<std::vector<Tensor>> infer_batch(
        ModelHandle handle, const std::vector<Tensor>& inputs) override;

    ErrorCode synchronize() override;

    ErrorCode get_memory_usage(std::size_t& used, std::size_t& total) const override;

private:
    DSPConfig config_;
    bool initialized_{false};
};

} // namespace qoocore
