/**
 * @file hardware_probe.h
 * @brief 硬件特性探测接口
 *
 * 运行时探测系统上的可用硬件（NPU/GPU/DSP/CPU），
 * 返回各硬件的能力描述，供推理引擎选择合适的后端。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "core.h"

#include <string>
#include <vector>

namespace qoocore {
namespace hardware {

// ── NpuCandidate — 探测到的 NPU 候选
// ─────────────────────────────────────────────────────────────────────
struct NpuCandidate {
    std::string vendor;       ///< "Qualcomm" / "Horizon" / "Rockchip"
    std::string chip_model;   ///< "Snapdragon 8 Gen 3" / "J5"
    std::string device_path;  ///< "/dev/npu0"
    bool available{false};
};

// ── GpuCandidate — 探测到的 GPU 候选
// ─────────────────────────────────────────────────────────────────────
struct GpuCandidate {
    std::string vendor;       ///< "NVIDIA" / "AMD" / "ARM"
    std::string model;        ///< "Jetson Orin" / "Mali-G715"
    std::string compute_api;  ///< "CUDA" / "OpenCL" / "Vulkan"
    bool available{false};
};

// ── CpuInfo — CPU 信息
// ─────────────────────────────────────────────────────────────────────
struct CpuInfo {
    std::string model;          ///< CPU 型号
    int cores{0};
    bool supports_neon{false};  ///< ARM NEON
    bool supports_avx512{false}; ///< x86 AVX-512
    bool supports_fp16{false};
};

// ── HardwareProfile — 完整硬件探测结果
// ─────────────────────────────────────────────────────────────────────
struct HardwareProfile {
    std::vector<NpuCandidate> npu_candidates;
    std::vector<GpuCandidate> gpu_candidates;
    CpuInfo cpu_info;
    std::size_t total_memory_bytes{0};
};

// ── HardwareProber — 硬件探测器
// ─────────────────────────────────────────────────────────────────────
class HardwareProber {
public:
    /**
     * @brief 探测所有硬件能力。
     */
    static Result<HardwareProfile> probe();

    /**
     * @brief 探测总内存大小（字节）。
     */
    static std::size_t probe_total_memory();

private:
    HardwareProber() = delete;
};

}  // namespace hardware
}  // namespace qoocore
