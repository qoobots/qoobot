/**
 * @file feature_probe.cpp
 * @brief 硬件特性探测 — 运行时检测 NPU/GPU 算子支持、内存带宽、频率等能力
 *
 * 在硬件初始化阶段，探测芯片的真实能力，用于：
 *   1. 算子兼容性检查：模型中的算子是否被当前 NPU/GPU 支持
 *   2. 性能预估：基于实测带宽/频率估计推理延迟
 *   3. 内存容量检测：确定模型最大可用内存
 *   4. 最佳后端选择：根据模型需求自动选择最优后端
 *
 * 探测方法：
 *   - NPU: 查询 QNN/BPU/RKNN SDK API
 *   - GPU: OpenCL clGetDeviceInfo / CUDA cudaGetDeviceProperties / Vulkan
 *   - CPU: /proc/cpuinfo + cpuid + NEON 指令检测
 *   - 内存: /proc/meminfo + ION heap 查询
 *   - 频率: /sys/devices/system/cpu/cpu*/cpufreq/
 *
 * @copyright QooBot Project
 * @version 0.3.0
 */

#include "qoocore/core.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#ifdef __linux__
#include <unistd.h>
#endif

namespace qoocore {
namespace hardware {

// ═══════════════════════════════════════════════════════════════════════════════
// 1. 算子支持探测
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 算子支持矩阵 — 描述硬件对各类算子的支持情况
 */
struct OperatorSupport {
    /// 支持的算子集合
    std::set<std::string> supported_ops;

    /// 对特定算子的限制（如最大 kernel size）
    struct OpConstraint {
        std::string op_name;
        std::map<std::string, int32_t> max_values;  ///< e.g. {"kernel_size": 7, "channels": 2048}
    };
    std::vector<OpConstraint> constraints;

    /// FP16 支持的算子集合
    std::set<std::string> fp16_supported_ops;

    /// INT8 支持的算子集合
    std::set<std::string> int8_supported_ops;

    /// 不支持的算子 → 替代方案
    std::map<std::string, std::string> op_fallbacks;

    /**
     * @brief 检查算子是否被支持。
     */
    [[nodiscard]] bool is_supported(const std::string& op_name,
                                     const std::string& dtype = "float32") const {
        if (dtype == "float16" || dtype == "fp16") {
            return fp16_supported_ops.count(op_name) > 0;
        }
        if (dtype == "int8" || dtype == "qint8") {
            return int8_supported_ops.count(op_name) > 0;
        }
        return supported_ops.count(op_name) > 0;
    }

    /**
     * @brief 获取算子的备选方案。
     */
    [[nodiscard]] std::string fallback_for(const std::string& op_name) const {
        auto it = op_fallbacks.find(op_name);
        return (it != op_fallbacks.end()) ? it->second : "";
    }
};

// ── 各 NPU 厂商的算子支持数据库 ──────────────────────────────────────────

/// Qualcomm QNN (SDK 2.x) 算子支持列表
static const OperatorSupport kQnnOperatorSupport = {
    // FP32 支持
    .supported_ops = {
        "Conv2D", "DepthwiseConv2D", "TransposeConv2D",
        "MatMul", "FullyConnected",
        "Add", "Sub", "Mul", "Div",
        "Relu", "Relu6", "LeakyRelu", "PRelu",
        "Sigmoid", "Tanh", "Softmax", "LogSoftmax",
        "BatchNormalization", "LayerNormalization", "GroupNormalization",
        "MaxPool2D", "AvgPool2D", "GlobalAveragePool",
        "Concat", "Reshape", "Transpose", "Squeeze", "Unsqueeze",
        "Pad", "Resize", "ResizeNearest", "ResizeBilinear",
        "Split", "Slice", "StridedSlice",
        "ReduceMean", "ReduceSum", "ReduceMax", "ReduceMin",
        "Gather", "GatherND", "ScatterND",
        "Cast", "Identity",
        "GELU", "HardSwish", "HardSigmoid",
        "ElementWiseMultiply", "ElementWiseAdd",
        "ChannelShuffle", "GridSample",
        "InstanceNormalization",
    },

    // FP16 支持（QNN 广泛支持 FP16）
    .fp16_supported_ops = {
        "Conv2D", "DepthwiseConv2D", "MatMul", "FullyConnected",
        "Add", "Mul", "Relu", "Relu6", "Sigmoid", "Tanh", "Softmax",
        "BatchNormalization", "LayerNormalization",
        "MaxPool2D", "AvgPool2D", "GlobalAveragePool",
        "Concat", "Reshape", "Transpose", "Resize",
        "GELU", "HardSwish",
    },

    // INT8 支持
    .int8_supported_ops = {
        "Conv2D", "DepthwiseConv2D", "MatMul", "FullyConnected",
        "Add", "Mul", "Relu", "Relu6", "Sigmoid", "Softmax",
        "BatchNormalization", "MaxPool2D", "AvgPool2D", "GlobalAveragePool",
        "Concat", "Reshape", "Transpose", "Resize",
    },

    // 不支持算子的替代方案
    .op_fallbacks = {
        {"MultiHeadAttention", "MatMul+Softmax"},  // QNN 无原生 MHA
        {"FlashAttention", "MatMul+Softmax"},
        {"RoPE", "Sin+Cos+Mul"},                   // 需手动分解
        {"RMSNorm", "Mul+ReduceMean+Sqrt"},
        {"SiLU", "Sigmoid+Mul"},
    },

    // 约束
    .constraints = {
        {"Conv2D", {{"kernel_size", 7}, {"channels", 8192}, {"groups", 32}}},
        {"MatMul", {{"M", 8192}, {"N", 8192}, {"K", 8192}}},
        {"Resize", {{"scale_factor", 8}}},
    },
};

/// 地平线 BPU (Journey 6) 算子支持列表
static const OperatorSupport kBpuOperatorSupport = {
    .supported_ops = {
        "Conv2D", "DepthwiseConv2D", "Deconv2D",
        "MatMul",
        "Add", "Sub", "Mul",
        "Relu", "Relu6", "LeakyRelu", "PRelu",
        "Sigmoid", "Tanh", "Softmax",
        "BatchNormalization", "LayerNormalization",
        "MaxPool2D", "AvgPool2D", "GlobalAveragePool",
        "Concat", "Reshape", "Transpose",
        "Pad", "Resize",
        "Split", "Slice",
        "ReduceMean", "ReduceSum", "ReduceMax",
        "Correlation", "GridSample", "WarpAffine",
        "LRN", "ReduceL2",
        "GroupNorm",
    },
    .fp16_supported_ops = {},  // BPU 主要使用 INT8
    .int8_supported_ops = {
        "Conv2D", "DepthwiseConv2D", "MatMul",
        "Add", "Mul", "Relu", "Relu6", "Sigmoid",
        "BatchNormalization", "MaxPool2D", "AvgPool2D",
        "Concat", "Reshape", "Transpose", "Resize",
    },
    .op_fallbacks = {
        {"GELU", "Sigmoid+Mul+Add"},
        {"HardSwish", "Relu6+Mul+Div"},
        {"MultiHeadAttention", "MatMul+Softmax"},
    },
    .constraints = {
        {"Conv2D", {{"kernel_size", 7}, {"channels", 2048}}},
        {"MatMul", {{"M", 4096}, {"N", 4096}, {"K", 4096}}},
    },
};

/// Rockchip RKNN (RK3588) 算子支持列表
static const OperatorSupport kRknnOperatorSupport = {
    .supported_ops = {
        "Conv2D", "DepthwiseConv2D", "TransposeConv2D",
        "MatMul", "FullyConnected",
        "Add", "Sub", "Mul", "Div",
        "Relu", "Relu6", "LeakyRelu",
        "Sigmoid", "Tanh", "Softmax",
        "BatchNormalization",
        "MaxPool2D", "AvgPool2D", "GlobalAveragePool",
        "Concat", "Reshape", "Transpose", "Squeeze",
        "Pad", "Resize",
        "Split", "Slice",
        "ReduceMean", "ReduceSum",
        "Mish", "HardSigmoid", "HardSwish",
        "LSTM", "GRU",
        "Clip", "Exp", "Log",
    },
    .fp16_supported_ops = {
        "Conv2D", "DepthwiseConv2D", "MatMul",
        "Add", "Mul", "Relu", "Sigmoid", "Softmax",
        "MaxPool2D", "AvgPool2D", "Concat", "Resize",
    },
    .int8_supported_ops = {
        "Conv2D", "DepthwiseConv2D", "MatMul",
        "Add", "Mul", "Relu", "Sigmoid",
        "BatchNormalization", "MaxPool2D", "AvgPool2D",
        "Concat", "Reshape", "Resize",
    },
    .op_fallbacks = {
        {"LayerNormalization", "ReduceMean+Sub+Mul+Add"},
        {"GELU", "Tanh+Mul+Add"},
        {"MultiHeadAttention", "MatMul+Softmax"},
        {"GroupNormalization", "Reshape+ReduceMean+Sub+Mul+Add"},
    },
    .constraints = {
        {"Conv2D", {{"kernel_size", 5}, {"channels", 4096}}},
        {"MatMul", {{"M", 4096}, {"N", 4096}, {"K", 4096}}},
    },
};

// ═══════════════════════════════════════════════════════════════════════════════
// 2. 内存带宽探测
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 内存子系统信息
 */
struct MemoryInfo {
    uint64_t total_ram_bytes{0};
    uint64_t available_ram_bytes{0};
    uint64_t total_swap_bytes{0};

    // NPU 专用内存
    uint64_t npu_ddr_bytes{0};
    uint64_t npu_sram_bytes{0};
    uint64_t npu_tcm_bytes{0};

    // GPU 显存
    uint64_t gpu_memory_bytes{0};

    // ION/DMA-BUF heap 信息
    struct HeapInfo {
        std::string name;
        uint64_t total_bytes{0};
        uint64_t available_bytes{0};
    };
    std::vector<HeapInfo> ion_heaps;

    // 带宽估算（GB/s）
    float memory_bandwidth_gbps{0.0f};
    float npu_bandwidth_gbps{0.0f};
    float gpu_bandwidth_gbps{0.0f};
};

/**
 * @brief 探测内存信息
 */
static MemoryInfo probe_memory_info() {
    MemoryInfo info;

#ifdef __linux__
    // 读取 /proc/meminfo
    std::ifstream meminfo("/proc/meminfo");
    if (meminfo.is_open()) {
        std::string line;
        while (std::getline(meminfo, line)) {
            if (line.find("MemTotal:") == 0) {
                std::sscanf(line.c_str(), "MemTotal: %lu kB", &info.total_ram_bytes);
                info.total_ram_bytes *= 1024;
            } else if (line.find("MemAvailable:") == 0) {
                std::sscanf(line.c_str(), "MemAvailable: %lu kB", &info.available_ram_bytes);
                info.available_ram_bytes *= 1024;
            } else if (line.find("SwapTotal:") == 0) {
                std::sscanf(line.c_str(), "SwapTotal: %lu kB", &info.total_swap_bytes);
                info.total_swap_bytes *= 1024;
            }
        }
    }

    // 探测 ION heap 信息
    const char* heap_paths[] = {
        "/sys/kernel/debug/ion/heaps/system",
        "/sys/kernel/debug/ion/heaps/carveout",
        "/sys/kernel/debug/ion/heaps/cma",
    };
    for (const char* path : heap_paths) {
        std::ifstream heap_info(path);
        if (heap_info.is_open()) {
            MemoryInfo::HeapInfo hi;
            hi.name = path;
            std::string content((std::istreambuf_iterator<char>(heap_info)),
                                 std::istreambuf_iterator<char>());
            // 简化解析
            info.ion_heaps.push_back(hi);
        }
    }

    // 带宽估算（基于已知芯片数据）
    // Snapdragon 8 Gen3: 77 GB/s LPDDR5x
    // Dimensity 9300: 64 GB/s LPDDR5T
    // RK3588: 32 GB/s LPDDR4x
    info.memory_bandwidth_gbps = 32.0f;  // 保守默认值
    info.npu_bandwidth_gbps = info.memory_bandwidth_gbps * 0.8f;  // 80% 可用
    info.gpu_bandwidth_gbps = info.memory_bandwidth_gbps * 0.7f;

#endif

    return info;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 3. CPU 频率探测
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief CPU 核心频率信息
 */
struct CpuFrequencyInfo {
    uint32_t core_id{0};
    std::string governor;         ///< 调度器策略
    uint64_t current_freq_khz{0};
    uint64_t min_freq_khz{0};
    uint64_t max_freq_khz{0};
    uint64_t available_freqs_count{0};
    std::vector<uint64_t> available_freqs;  ///< 所有可用频率
};

/**
 * @brief DVFS (Dynamic Voltage and Frequency Scaling) 信息
 */
struct DvfsInfo {
    std::vector<CpuFrequencyInfo> cpu_freqs;
    uint64_t npu_freq_khz{0};
    uint64_t gpu_freq_khz{0};
    uint64_t dsp_freq_khz{0};

    // 热降频阈值
    struct ThermalThrottle {
        uint32_t temp_celsius{0};
        float freq_reduction_ratio{0.0f};  ///< 频率降低比例
    };
    std::vector<ThermalThrottle> thermal_throttles;
};

/**
 * @brief 探测 CPU/NPU/GPU/DSP 频率
 */
static DvfsInfo probe_frequencies() {
    DvfsInfo info;

#ifdef __linux__
    // CPU 频率（从 sysfs）
    for (int cpu = 0; cpu < 8; ++cpu) {
        CpuFrequencyInfo cpu_info;
        cpu_info.core_id = cpu;

        std::string base = "/sys/devices/system/cpu/cpu" + std::to_string(cpu) + "/cpufreq/";

        // Governor
        std::ifstream gov_file(base + "scaling_governor");
        if (gov_file.is_open()) {
            std::getline(gov_file, cpu_info.governor);
        }

        // 当前频率
        std::ifstream cur_file(base + "scaling_cur_freq");
        if (cur_file.is_open()) {
            cur_file >> cpu_info.current_freq_khz;
        }

        // 最小/最大频率
        std::ifstream min_file(base + "scaling_min_freq");
        if (min_file.is_open()) min_file >> cpu_info.min_freq_khz;

        std::ifstream max_file(base + "scaling_max_freq");
        if (max_file.is_open()) max_file >> cpu_info.max_freq_khz;

        // 可用频率列表
        std::ifstream avail_file(base + "scaling_available_frequencies");
        if (avail_file.is_open()) {
            uint64_t freq;
            while (avail_file >> freq) {
                cpu_info.available_freqs.push_back(freq);
            }
            cpu_info.available_freqs_count = cpu_info.available_freqs.size();
        }

        if (cpu_info.max_freq_khz > 0) {
            info.cpu_freqs.push_back(cpu_info);
        }
    }

    // NPU 频率（厂商特定路径）
    std::ifstream npu_freq("/sys/class/devfreq/npu/cur_freq");
    if (npu_freq.is_open()) {
        npu_freq >> info.npu_freq_khz;
    }

    // GPU 频率
    std::ifstream gpu_freq("/sys/class/devfreq/gpu/cur_freq");
    if (gpu_freq.is_open()) {
        gpu_freq >> info.gpu_freq_khz;
    }

#endif

    // 热降频阈值（芯片特定）
    info.thermal_throttles = {
        {60, 1.0f},   // <60°C：无降频
        {75, 0.8f},   // 60-75°C：降至 80%
        {85, 0.6f},   // 75-85°C：降至 60%
        {95, 0.4f},   // 85-95°C：降至 40%
        {105, 0.0f},  // >95°C：紧急关机
    };

    return info;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 4. GPU 能力探测 (OpenCL)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief GPU 能力信息
 */
struct GpuFeatureInfo {
    std::string vendor;             ///< "Qualcomm" | "ARM" | "NVIDIA" | "Intel"
    std::string renderer;           ///< "Adreno 750" | "Mali G710" | "Orin GPU"
    std::string api_version;        ///< "OpenCL 3.0" | "Vulkan 1.3" | "CUDA 12"
    uint32_t compute_units{0};
    uint64_t max_workgroup_size{256};
    uint64_t max_global_memory{0};
    uint64_t max_constant_memory{0};
    uint64_t max_local_memory{0};
    uint32_t max_work_item_dims{3};
    std::array<uint64_t, 3> max_work_item_sizes{};

    // 扩展支持
    std::set<std::string> extensions;
    bool has_fp16{false};
    bool has_fp64{false};
    bool has_int8_dot{false};      ///< INT8 dot product
    bool has_tensor_cores{false};

    // 纹理支持
    uint32_t max_texture_2d_width{0};
    uint32_t max_texture_2d_height{0};
    uint32_t max_texture_3d_size{0};
};

/**
 * @brief 通过 OpenCL 探测 GPU 能力
 *
 * 注意：需要链接 OpenCL 库。
 * 如果系统没有 OpenCL，返回空的 GpuFeatureInfo。
 */
static GpuFeatureInfo probe_gpu_opencl() {
    GpuFeatureInfo info;

#ifdef __linux__
    // 尝试加载 OpenCL
    void* handle = ::dlopen("libOpenCL.so", RTLD_NOW | RTLD_GLOBAL);
    if (!handle) {
        handle = ::dlopen("libOpenCL.so.1", RTLD_NOW);
    }
    if (!handle) {
        info.vendor = "unknown";
        info.renderer = "OpenCL not available";
        return info;
    }

    // OpenCL API 函数指针
    using clGetPlatformIDs_t = int (*)(unsigned int, void*, unsigned int*);
    using clGetDeviceIDs_t = int (*)(void*, unsigned long, unsigned int, void*, unsigned int*);
    using clGetDeviceInfo_t = int (*)(void*, unsigned int, size_t, void*, size_t*);

    auto clGetPlatformIDs = reinterpret_cast<clGetPlatformIDs_t>(
        ::dlsym(handle, "clGetPlatformIDs"));
    auto clGetDeviceIDs = reinterpret_cast<clGetDeviceIDs_t>(
        ::dlsym(handle, "clGetDeviceIDs"));
    auto clGetDeviceInfo = reinterpret_cast<clGetDeviceInfo_t>(
        ::dlsym(handle, "clGetDeviceInfo"));

    if (!clGetPlatformIDs || !clGetDeviceIDs || !clGetDeviceInfo) {
        ::dlclose(handle);
        return info;
    }

    // 获取平台
    unsigned int num_platforms = 0;
    clGetPlatformIDs(0, nullptr, &num_platforms);
    if (num_platforms == 0) {
        ::dlclose(handle);
        return info;
    }

    std::vector<void*> platforms(num_platforms);
    clGetPlatformIDs(num_platforms, platforms.data(), nullptr);

    // 获取第一个 GPU 设备
    for (auto platform : platforms) {
        unsigned int num_devices = 0;
        clGetDeviceIDs(platform, 0x1000000, 0, nullptr, &num_devices); // CL_DEVICE_TYPE_GPU

        if (num_devices > 0) {
            std::vector<void*> devices(num_devices);
            clGetDeviceIDs(platform, 0x1000000, num_devices, devices.data(), nullptr);

            auto& device = devices[0];

            // 读取设备属性
            char buf[256];
            size_t ret_size = 0;

            // CL_DEVICE_VENDOR = 0x1022
            if (clGetDeviceInfo(device, 0x1022, sizeof(buf), buf, &ret_size) == 0) {
                info.vendor = buf;
            }
            // CL_DEVICE_NAME = 0x102B
            if (clGetDeviceInfo(device, 0x102B, sizeof(buf), buf, &ret_size) == 0) {
                info.renderer = buf;
            }
            // CL_DEVICE_VERSION = 0x102C
            if (clGetDeviceInfo(device, 0x102C, sizeof(buf), buf, &ret_size) == 0) {
                info.api_version = buf;
            }

            // CL_DEVICE_MAX_COMPUTE_UNITS = 0x1002
            clGetDeviceInfo(device, 0x1002, sizeof(info.compute_units),
                           &info.compute_units, nullptr);

            // CL_DEVICE_MAX_WORK_GROUP_SIZE = 0x1004
            clGetDeviceInfo(device, 0x1004, sizeof(info.max_workgroup_size),
                           &info.max_workgroup_size, nullptr);

            // CL_DEVICE_GLOBAL_MEM_SIZE = 0x101F
            clGetDeviceInfo(device, 0x101F, sizeof(info.max_global_memory),
                           &info.max_global_memory, nullptr);

            // CL_DEVICE_LOCAL_MEM_SIZE = 0x1020
            clGetDeviceInfo(device, 0x1020, sizeof(info.max_local_memory),
                           &info.max_local_memory, nullptr);

            // CL_DEVICE_MAX_WORK_ITEM_SIZES = 0x1005
            clGetDeviceInfo(device, 0x1005, sizeof(info.max_work_item_sizes),
                           info.max_work_item_sizes.data(), nullptr);

            // CL_DEVICE_EXTENSIONS = 0x1028
            if (clGetDeviceInfo(device, 0x1028, sizeof(buf), buf, &ret_size) == 0) {
                std::string ext_str(buf, ret_size);
                std::istringstream iss(ext_str);
                std::string ext;
                while (iss >> ext) {
                    info.extensions.insert(ext);
                }
                info.has_fp16 = ext_str.find("cl_khr_fp16") != std::string::npos;
                info.has_fp64 = ext_str.find("cl_khr_fp64") != std::string::npos;
            }

            break;  // 只取第一个 GPU
        }
    }

    ::dlclose(handle);
#endif

    return info;
}

// ═══════════════════════════════════════════════════════════════════════════════
// 5. 综合硬件特性探测器
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 完整的硬件特性报告
 */
struct HardwareFeatureReport {
    // 算子支持
    OperatorSupport op_support;

    // 内存
    MemoryInfo memory;

    // 频率/DVFS
    DvfsInfo dvfs;

    // GPU
    GpuFeatureInfo gpu;

    // CPU SIMD
    struct CpuSimdInfo {
        bool has_neon{false};
        bool has_neon_fp16{false};
        bool has_neon_dotprod{false};
        bool has_sve{false};       ///< ARM SVE (Scalable Vector Extension)
        bool has_sve2{false};
        bool has_sse42{false};
        bool has_avx2{false};
        bool has_avx512f{false};
        bool has_avx512_vnni{false};
    } cpu_simd;

    // 总结
    struct Recommendation {
        BackendType recommended_backend{BackendType::AUTO};
        std::string recommended_vendor;
        std::string recommended_precision;  ///< "float32" | "float16" | "int8"
        float estimated_tops{0.0f};
        float estimated_efficiency{0.0f};  ///< TOPS/W
    } recommendation;

    // 时间戳
    std::string probe_timestamp;
};

/**
 * @brief 硬件特性探测器
 *
 * 运行时综合探测硬件能力，返回完整报告。
 */
class HardwareFeatureProber {
public:
    /**
     * @brief 执行全面硬件探测。
     */
    HardwareFeatureReport probe_all(const std::string& chip_hint = "") {
        HardwareFeatureReport report;

        // 1. 算子支持
        if (!chip_hint.empty()) {
            report.op_support = get_op_support_for_chip(chip_hint);
        }

        // 2. 内存信息
        report.memory = probe_memory_info();

        // 3. 频率信息
        report.dvfs = probe_frequencies();

        // 4. GPU 信息
        report.gpu = probe_gpu_opencl();

        // 5. CPU SIMD 信息
        report.cpu_simd = probe_cpu_simd();

        // 6. 生成推荐
        report.recommendation = generate_recommendation(report, chip_hint);

        // 7. 时间戳
        report.probe_timestamp = current_timestamp();

        return report;
    }

    /**
     * @brief 将探测报告导出为 JSON。
     */
    static std::string report_to_json(const HardwareFeatureReport& report) {
        std::ostringstream json;
        json << "{\n";
        json << "  \"probe_timestamp\": \"" << report.probe_timestamp << "\",\n";
        json << "  \"op_support\": {\n";
        json << "    \"fp32_ops\": " << report.op_support.supported_ops.size() << ",\n";
        json << "    \"fp16_ops\": " << report.op_support.fp16_supported_ops.size() << ",\n";
        json << "    \"int8_ops\": " << report.op_support.int8_supported_ops.size() << "\n";
        json << "  },\n";
        json << "  \"memory\": {\n";
        json << "    \"total_ram_gb\": " << (report.memory.total_ram_bytes / 1e9) << ",\n";
        json << "    \"available_ram_gb\": " << (report.memory.available_ram_bytes / 1e9) << ",\n";
        json << "    \"bandwidth_gbps\": " << report.memory.memory_bandwidth_gbps << "\n";
        json << "  },\n";
        json << "  \"dvfs\": {\n";
        json << "    \"cpu_cores\": " << report.dvfs.cpu_freqs.size() << ",\n";
        json << "    \"max_cpu_freq_ghz\": "
             << (report.dvfs.cpu_freqs.empty() ? 0 :
                 report.dvfs.cpu_freqs[0].max_freq_khz / 1e6) << ",\n";
        json << "    \"npu_freq_mhz\": " << (report.dvfs.npu_freq_khz / 1000.0) << ",\n";
        json << "    \"gpu_freq_mhz\": " << (report.dvfs.gpu_freq_khz / 1000.0) << "\n";
        json << "  },\n";
        json << "  \"gpu\": {\n";
        json << "    \"vendor\": \"" << report.gpu.vendor << "\",\n";
        json << "    \"renderer\": \"" << report.gpu.renderer << "\",\n";
        json << "    \"compute_units\": " << report.gpu.compute_units << ",\n";
        json << "    \"global_memory_gb\": " << (report.gpu.max_global_memory / 1e9) << ",\n";
        json << "    \"has_fp16\": " << (report.gpu.has_fp16 ? "true" : "false") << "\n";
        json << "  },\n";
        json << "  \"cpu_simd\": {\n";
        json << "    \"neon\": " << (report.cpu_simd.has_neon ? "true" : "false") << ",\n";
        json << "    \"neon_fp16\": " << (report.cpu_simd.has_neon_fp16 ? "true" : "false") << ",\n";
        json << "    \"avx2\": " << (report.cpu_simd.has_avx2 ? "true" : "false") << ",\n";
        json << "    \"avx512\": " << (report.cpu_simd.has_avx512f ? "true" : "false") << "\n";
        json << "  },\n";
        json << "  \"recommendation\": {\n";
        json << "    \"backend\": \"" << backend_to_string(report.recommendation.recommended_backend) << "\",\n";
        json << "    \"vendor\": \"" << report.recommendation.recommended_vendor << "\",\n";
        json << "    \"precision\": \"" << report.recommendation.recommended_precision << "\",\n";
        json << "    \"estimated_tops\": " << report.recommendation.estimated_tops << "\n";
        json << "  }\n}";
        return json.str();
    }

private:
    static OperatorSupport get_op_support_for_chip(const std::string& chip) {
        if (chip.find("sdm") != std::string::npos ||
            chip.find("sm") != std::string::npos) {
            return kQnnOperatorSupport;
        } else if (chip.find("j") == 0 || chip.find("journey") != std::string::npos) {
            return kBpuOperatorSupport;
        } else if (chip.find("rk") == 0) {
            return kRknnOperatorSupport;
        }
        return kQnnOperatorSupport;  // 默认高通
    }

    static HardwareFeatureReport::CpuSimdInfo probe_cpu_simd() {
        HardwareFeatureReport::CpuSimdInfo info;

#ifdef __linux__
        // 读取 /proc/cpuinfo 检测 CPU features
        std::ifstream cpuinfo("/proc/cpuinfo");
        if (cpuinfo.is_open()) {
            std::string content((std::istreambuf_iterator<char>(cpuinfo)),
                                 std::istreambuf_iterator<char>());

            info.has_neon = content.find("neon") != std::string::npos ||
                           content.find("asimd") != std::string::npos;
            info.has_neon_fp16 = content.find("fp16") != std::string::npos ||
                                content.find("asimdhp") != std::string::npos;
            info.has_neon_dotprod = content.find("asimddp") != std::string::npos;
            info.has_sve = content.find("sve") != std::string::npos;
            info.has_sve2 = content.find("sve2") != std::string::npos;

            info.has_sse42 = content.find("sse4_2") != std::string::npos;
            info.has_avx2 = content.find("avx2") != std::string::npos;
            info.has_avx512f = content.find("avx512f") != std::string::npos;
            info.has_avx512_vnni = content.find("avx512_vnni") != std::string::npos;
        }
#endif

        return info;
    }

    static HardwareFeatureReport::Recommendation generate_recommendation(
        const HardwareFeatureReport& report, const std::string& chip_hint) {

        HardwareFeatureReport::Recommendation rec;

        // 默认推荐 NPU（端侧最优）
        if (chip_hint.find("sdm") != std::string::npos ||
            chip_hint.find("sm") != std::string::npos) {
            rec.recommended_backend = BackendType::NPU;
            rec.recommended_vendor = "qcom";
            rec.recommended_precision = "int8";
            rec.estimated_tops = 45.0f;  // Snapdragon 8 Gen3: ~45 INT8 TOPS
        } else if (chip_hint.find("j") == 0) {
            rec.recommended_backend = BackendType::NPU;
            rec.recommended_vendor = "horizon";
            rec.recommended_precision = "int8";
            rec.estimated_tops = 35.0f;  // Journey 6: ~35 INT8 TOPS
        } else if (chip_hint.find("rk") == 0) {
            rec.recommended_backend = BackendType::NPU;
            rec.recommended_vendor = "rockchip";
            rec.recommended_precision = "int8";
            rec.estimated_tops = 6.0f;   // RK3588: 6 INT8 TOPS
        } else if (chip_hint.find("orin") != std::string::npos) {
            rec.recommended_backend = BackendType::GPU;
            rec.recommended_vendor = "nvidia";
            rec.recommended_precision = "float16";
            rec.estimated_tops = 170.0f; // Orin AGX: 170 FP16 TFLOPS (sparse)
        } else if (report.gpu.compute_units > 0) {
            rec.recommended_backend = BackendType::GPU;
            rec.recommended_vendor = report.gpu.vendor;
            rec.recommended_precision = report.gpu.has_fp16 ? "float16" : "float32";
        } else {
            rec.recommended_backend = BackendType::CPU;
            rec.recommended_vendor = "generic";
            rec.recommended_precision = "float32";
        }

        rec.estimated_efficiency = rec.estimated_tops / 10.0f;  // 简化的 TOPS/W 估算

        return rec;
    }

    static std::string current_timestamp() {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::ostringstream oss;
        oss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%SZ");
        return oss.str();
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 全局单例
// ═══════════════════════════════════════════════════════════════════════════════

static std::unique_ptr<HardwareFeatureProber> g_prober;
static std::mutex g_prober_mutex;

HardwareFeatureProber& global_feature_prober() {
    std::lock_guard<std::mutex> lock(g_prober_mutex);
    if (!g_prober) {
        g_prober = std::make_unique<HardwareFeatureProber>();
    }
    return *g_prober;
}

}  // namespace hardware
}  // namespace qoocore
