/**
 * @file hardware_probe.cpp
 * @brief 硬件特性探测实现骨架
 *
 * 运行时探测系统上的可用硬件（NPU/GPU/DSP/CPU），
 * 返回各硬件的能力描述，供推理引擎选择合适的后端。
 *
 * 探测方法：
 *   - NPU：读取 /sys/class/npu/ 或调用 HAL 库查询
 *   - GPU：CUDA Runtime API / OpenCL platform query
 *   - CPU：读取 /proc/cpuinfo 或 __builtin_cpu_supports
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/hardware/hardware_probe.h"

#include <spdlog/spdlog.h>
#include <vector>
#include <string>

#ifdef __linux__
#include <fstream>
#include <unistd.h>
#endif

namespace qoocore {
namespace hardware {

// ── 探测 NPU 是否存在 ──────────────────────────────────────────────────
static std::vector<NpuCandidate> probe_npu_linux() {
    std::vector<NpuCandidate> results;

#ifdef __linux__
    // 方法 1：检查 /sys/class/npu/ 是否存在
    if (access("/sys/class/npu/", F_OK) == 0) {
        spdlog::info("Detected NPU sysfs at /sys/class/npu/");
        // TODO: 读取 NPU 信息
        NpuCandidate candidate;
        candidate.vendor      = "unknown";
        candidate.chip_model  = "unknown";
        candidate.available   = true;
        results.push_back(candidate);
    }

    // 方法 2：检查设备文件
    if (access("/dev/npu0", F_OK) == 0) {
        spdlog::info("Detected NPU device: /dev/npu0");
    }
#endif

    return results;
}

// ── 探测 GPU 是否存在 ──────────────────────────────────────────────────
static std::vector<GpuCandidate> probe_gpu() {
    std::vector<GpuCandidate> results;

    // TODO: 使用 CUDA Runtime API 探测 NVIDIA GPU
    //   cudaGetDeviceCount(&count);
    //   cudaGetDeviceProperties(&prop, i);

    // TODO: 使用 OpenCL 探测 GPU
    //   clGetPlatformIDs → clGetDeviceIDs

    return results;
}

// ── 探测 CPU 特性 ──────────────────────────────────────────────────────
static CpuInfo probe_cpu() {
    CpuInfo info;

#ifdef __linux__
    // 读取 /proc/cpuinfo
    std::ifstream file("/proc/cpuinfo");
    if (file.is_open()) {
        std::string line;
        while (std::getline(file, line)) {
            if (line.find("flags") != std::string::npos) {
                // 解析 CPU flags（neon, avx512, etc.）
                if (line.find("asimd") != std::string::npos ||
                    line.find("neon") != std::string::npos) {
                    info.supports_neon = true;
                }
            }
            if (line.find("model name") != std::string::npos) {
                // 解析 CPU 型号
                auto pos = line.find(":");
                if (pos != std::string::npos) {
                    info.model = line.substr(pos + 2);
                    // 去除末尾 \n
                    while (!info.model.empty() &&
                           (info.model.back() == '\n' ||
                            info.model.back() == '\r')) {
                        info.model.pop_back();
                    }
                }
            }
        }
    }
#endif

    return info;
}

// ── HardwareProber 主实现 ─────────────────────────────────────────────
Result<HardwareProfile> HardwareProber::probe() {
    HardwareProfile profile;

    spdlog::info("Probing hardware capabilities...");

    // 探测 NPU
    profile.npu_candidates = probe_npu_linux();
    spdlog::info("  NPU candidates: {}", profile.npu_candidates.size());

    // 探测 GPU
    profile.gpu_candidates = probe_gpu();
    spdlog::info("  GPU candidates: {}", profile.gpu_candidates.size());

    // 探测 CPU
    profile.cpu_info = probe_cpu();
    spdlog::info("  CPU: {} (Neon={})",
                   profile.cpu_info.model,
                   profile.cpu_info.supports_neon);

    // 探测内存
    profile.total_memory_bytes = probe_total_memory();
    spdlog::info("  Total memory: {} MB",
                   profile.total_memory_bytes / (1024 * 1024));

    return profile;
}

std::size_t HardwareProber::probe_total_memory() {
#ifdef __linux__
    long pages = sysconf(_SC_PHYS_PAGES);
    long page_size = sysconf(_SC_PAGE_SIZE);
    if (pages > 0 && page_size > 0) {
        return static_cast<std::size_t>(pages) *
               static_cast<std::size_t>(page_size);
    }
#endif
    return 0;
}

}  // namespace hardware
}  // namespace qoocore
