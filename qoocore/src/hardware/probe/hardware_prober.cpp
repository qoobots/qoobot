/**
 * @file hardware_prober.cpp
 * @brief 硬件特性探测器实现
 *
 * 运行时探测系统上的可用硬件（NPU/GPU/DSP/CPU），
 * 返回各硬件的能力描述，供推理引擎选择合适的后端。
 *
 * 探测策略：
 *   - NPU：检查设备文件（/dev/npu*）和厂商标识
 *   - GPU：检查 CUDA/OpenCL/Vulkan 可用性
 *   - CPU：读取 /proc/cpuinfo（Linux）或 CPUID（Windows）
 *   - 内存：读取 /proc/meminfo 或 GlobalMemoryStatusEx
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/hardware/hardware_probe.h"

#include <spdlog/spdlog.h>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

namespace qoocore {
namespace hardware {

// ── 平台无关辅助函数 ──────────────────────────────────────────────────

#ifdef _WIN32

static std::size_t probe_total_memory_impl() {
    MEMORYSTATUSEX mem;
    mem.dwLength = sizeof(mem);
    if (GlobalMemoryStatusEx(&mem)) {
        return static_cast<std::size_t>(mem.ullTotalPhys);
    }
    return 0;
}

static CpuInfo probe_cpu_impl() {
    CpuInfo info;
    SYSTEM_INFO si;
    GetSystemInfo(&si);
    info.cores = si.dwNumberOfProcessors;

    // 简单模型名称
    info.model = "x86_64";
    info.supports_avx512 = false;  // TODO: 通过 CPUID 检测

    return info;
}

static std::vector<NpuCandidate> probe_npu_impl() {
    // Windows 上通常没有嵌入式 NPU
    // 检查 Qualcomm Snapdragon NPU（Windows on ARM）
    std::vector<NpuCandidate> candidates;

    // 尝试检测 QNN SDK 路径
    const char* qnn_sdk = std::getenv("QNN_SDK_ROOT");
    if (qnn_sdk) {
        NpuCandidate c;
        c.vendor = "Qualcomm";
        c.chip_model = "Snapdragon (WoA)";
        c.device_path = "QNN_SDK";
        c.available = std::filesystem::exists(qnn_sdk);
        if (c.available) candidates.push_back(c);
    }

    return candidates;
}

static std::vector<GpuCandidate> probe_gpu_impl() {
    std::vector<GpuCandidate> candidates;

    // CUDA 探测
    GpuCandidate cuda;
    cuda.vendor = "NVIDIA";
    cuda.compute_api = "CUDA";
    cuda.available = false;
    // 检查 CUDA_PATH 环境变量
    const char* cuda_path = std::getenv("CUDA_PATH");
    if (cuda_path && std::filesystem::exists(cuda_path)) {
        cuda.available = true;
        cuda.model = "NVIDIA GPU (CUDA)";
    }
    candidates.push_back(cuda);

    return candidates;
}

#else  // Linux / Android

static std::size_t probe_total_memory_impl() {
    std::ifstream meminfo("/proc/meminfo");
    if (!meminfo) return 0;

    std::string line;
    while (std::getline(meminfo, line)) {
        if (line.find("MemTotal:") == 0) {
            std::istringstream iss(line);
            std::string label;
            std::size_t kb;
            iss >> label >> kb;
            return kb * 1024;  // KB → Bytes
        }
    }
    return 0;
}

static CpuInfo probe_cpu_impl() {
    CpuInfo info;
    info.supports_neon = false;  // 默认 ARM 都有 NEON
    info.supports_avx512 = false;
    info.supports_fp16 = false;

    std::ifstream cpuinfo("/proc/cpuinfo");
    if (!cpuinfo) return info;

    std::string line;
    while (std::getline(cpuinfo, line)) {
        if (line.find("model name") == 0 || line.find("Model") == 0) {
            auto pos = line.find(':');
            if (pos != std::string::npos) {
                info.model = line.substr(pos + 2);
            }
        }
        if (line.find("processor") == 0) {
            info.cores++;
        }
        if (line.find("Features") != std::string::npos ||
            line.find("flags") != std::string::npos) {
            if (line.find("neon") != std::string::npos) info.supports_neon = true;
            if (line.find("asimdhp") != std::string::npos) info.supports_fp16 = true;
            if (line.find("avx512") != std::string::npos) info.supports_avx512 = true;
        }
    }

    // ARM 架构通常默认支持 NEON（ARMv8+）
    if (info.model.find("ARM") != std::string::npos ||
        info.model.find("AArch64") != std::string::npos) {
        info.supports_neon = true;
    }

    return info;
}

static std::vector<NpuCandidate> probe_npu_impl() {
    std::vector<NpuCandidate> candidates;

    // ── Qualcomm Snapdragon NPU ──────────────────────────────────
    if (std::filesystem::exists("/dev/msm_npu") ||
        std::filesystem::exists("/dev/kgsl-3d0")) {
        NpuCandidate c;
        c.vendor = "Qualcomm";
        c.chip_model = "Snapdragon";
        c.device_path = "/dev/msm_npu";
        c.available = true;

        // 尝试从 sysfs 读取芯片型号
        std::ifstream soc("/sys/devices/soc0/machine");
        if (soc) {
            std::string soc_name;
            std::getline(soc, soc_name);
            if (!soc_name.empty()) c.chip_model = soc_name;
        }
        candidates.push_back(c);
    }

    // ── Horizon Journey BPU ─────────────────────────────────────
    if (std::filesystem::exists("/dev/bpu_dev0") ||
        std::filesystem::exists("/sys/class/bpu")) {
        NpuCandidate c;
        c.vendor = "Horizon";
        c.chip_model = "Journey";
        c.device_path = "/dev/bpu_dev0";
        c.available = true;

        // 尝试读取芯片型号
        std::ifstream chip("/sys/class/bpu/version");
        if (chip) {
            std::string ver;
            std::getline(chip, ver);
            if (!ver.empty()) c.chip_model = "Journey " + ver;
        }
        candidates.push_back(c);
    }

    // ── Rockchip RKNN NPU ───────────────────────────────────────
    if (std::filesystem::exists("/dev/rknpu") ||
        std::filesystem::exists("/dev/galcore")) {
        NpuCandidate c;
        c.vendor = "Rockchip";
        c.chip_model = "RK3588";
        c.device_path = "/dev/rknpu";
        c.available = true;

        // 尝试从 socinfo 读取
        std::ifstream soc("/proc/device-tree/compatible");
        if (soc) {
            std::string compat;
            std::getline(soc, compat);
            if (compat.find("rk3588") != std::string::npos) c.chip_model = "RK3588";
            else if (compat.find("rk3568") != std::string::npos) c.chip_model = "RK3568";
        }
        candidates.push_back(c);
    }

    // ── VeriSilicon VIP9000 NPU ─────────────────────────────────
    if (std::filesystem::exists("/dev/vip") ||
        std::filesystem::exists("/dev/vsi_npu")) {
        NpuCandidate c;
        c.vendor = "VeriSilicon";
        c.chip_model = "VIP9000";
        c.device_path = "/dev/vsi_npu";
        c.available = true;
        candidates.push_back(c);
    }

    // ── 通用：检查是否有任何 NPU 设备（通过 sysfs）──────────────
    // 许多 SoC 会在 /sys/class/ 下暴露 NPU 节点
    for (const auto& entry : std::filesystem::directory_iterator("/sys/class")) {
        std::string name = entry.path().filename().string();
        if (name.find("npu") != std::string::npos ||
            name.find("bpu") != std::string::npos) {
            // 已探测到
            break;
        }
    }

    return candidates;
}

static std::vector<GpuCandidate> probe_gpu_impl() {
    std::vector<GpuCandidate> candidates;

    // ── NVIDIA CUDA ──────────────────────────────────────────────
    {
        GpuCandidate c;
        c.vendor = "NVIDIA";
        c.compute_api = "CUDA";
        c.available = false;

        // 检查 nvidia-smi 或 CUDA 库
        if (std::filesystem::exists("/usr/local/cuda") ||
            std::filesystem::exists("/usr/lib/aarch64-linux-gnu/libcuda.so") ||
            std::filesystem::exists("/usr/lib/x86_64-linux-gnu/libcuda.so")) {
            c.available = true;
            c.model = "NVIDIA GPU (CUDA)";
        }
        candidates.push_back(c);
    }

    // ── ARM Mali (OpenCL) ───────────────────────────────────────
    if (std::filesystem::exists("/dev/mali0") ||
        std::filesystem::exists("/dev/mali")) {
        GpuCandidate c;
        c.vendor = "ARM";
        c.model = "Mali GPU";
        c.compute_api = "OpenCL";
        c.available = std::filesystem::exists("/usr/lib/libOpenCL.so") ||
                      std::filesystem::exists("/vendor/lib64/libOpenCL.so");
        candidates.push_back(c);
    }

    // ── Qualcomm Adreno (OpenCL) ────────────────────────────────
    if (std::filesystem::exists("/dev/kgsl-3d0")) {
        GpuCandidate c;
        c.vendor = "Qualcomm";
        c.model = "Adreno";
        c.compute_api = "OpenCL";
        c.available = std::filesystem::exists("/vendor/lib64/libOpenCL.so");
        candidates.push_back(c);
    }

    return candidates;
}

#endif  // _WIN32

// ── HardwareProber 公共接口 ───────────────────────────────────────────

Result<HardwareProfile> HardwareProber::probe() {
    HardwareProfile profile;

    try {
        // 探测 NPU
        profile.npu_candidates = probe_npu_impl();
        spdlog::info("Hardware probe: {} NPU candidate(s) found",
                      profile.npu_candidates.size());
        for (const auto& npu : profile.npu_candidates) {
            spdlog::debug("  NPU: {} {} ({}) [{}]",
                           npu.vendor, npu.chip_model,
                           npu.device_path,
                           npu.available ? "available" : "unavailable");
        }

        // 探测 GPU
        profile.gpu_candidates = probe_gpu_impl();
        spdlog::info("Hardware probe: {} GPU candidate(s) found",
                      profile.gpu_candidates.size());
        for (const auto& gpu : profile.gpu_candidates) {
            spdlog::debug("  GPU: {} {} ({}) [{}]",
                           gpu.vendor, gpu.model,
                           gpu.compute_api,
                           gpu.available ? "available" : "unavailable");
        }

        // 探测 CPU
        profile.cpu_info = probe_cpu_impl();
        spdlog::info("Hardware probe: CPU {} ({} cores, NEON={}, AVX512={}, FP16={})",
                      profile.cpu_info.model,
                      profile.cpu_info.cores,
                      profile.cpu_info.supports_neon,
                      profile.cpu_info.supports_avx512,
                      profile.cpu_info.supports_fp16);

        // 探测总内存
        profile.total_memory_bytes = probe_total_memory_impl();
        spdlog::info("Hardware probe: {} MB total memory",
                      profile.total_memory_bytes / (1024 * 1024));

    } catch (const std::exception& e) {
        return Error<HardwareProfile>(ErrorCode::UNKNOWN_ERROR,
                                       std::string("Hardware probe failed: ") + e.what());
    }

    return profile;
}

std::size_t HardwareProber::probe_total_memory() {
    return probe_total_memory_impl();
}

}  // namespace hardware
}  // namespace qoocore
