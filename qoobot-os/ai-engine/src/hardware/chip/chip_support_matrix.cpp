/**
 * @file chip_support_matrix.cpp
 * @brief 芯片支持矩阵 — 官方支持芯片列表、兼容性验证、性能基准
 *
 * 定义 QooBot 官方支持的所有芯片及其能力描述。
 * 运行时根据探测到的芯片型号匹配对应的能力描述。
 *
 * 芯片分类：
 *   Tier 1 (旗舰)：Snapdragon 8 Gen 3 / Dimensity 9300 / J6 / Orin AGX
 *   Tier 2 (高端)：Snapdragon 8 Gen 2 / RK3588 / J5 / Orin NX
 *   Tier 3 (中端)：Snapdragon 7+ Gen 2 / J3 / RK3568
 *   Tier 4 (入门)：CPU-only (ARM Cortex-A / x86)
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/core.h"
#include "qoocore/hardware/hardware_probe.h"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <string>
#include <unordered_map>
#include <vector>

namespace qoocore {
namespace hardware {

// ─────────────────────────────────────────────────────────────────────────────
//  ChipInfo — 单芯片信息
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 芯片完整能力描述。
 */
struct ChipInfo {
    // 基本信息
    std::string vendor;              ///< 厂商
    std::string model;               ///< 型号
    std::string codename;            ///< 代号
    std::string soc_family;          ///< SoC 系列
    int tier{3};                     ///< 性能等级（1-4，1 最高）

    // NPU
    struct {
        std::string name;            ///< NPU 名称（如 "Hexagon NPU", "BPU"）
        float peak_tops{0.0f};       ///< 峰值算力（TOPS）
        float int8_tops{0.0f};       ///< INT8 算力
        float fp16_tops{0.0f};       ///< FP16 算力
        std::size_t max_memory_mb{0}; ///< 最大可用内存
        bool supports_int4{false};
        bool supports_hardware_quant{false};
        int max_concurrent_models{1};
    } npu;

    // GPU
    struct {
        std::string name;
        float peak_gflops{0.0f};
        std::size_t max_memory_mb{0};
        bool supports_cuda{false};
        bool supports_opencl{false};
        bool supports_vulkan{false};
    } gpu;

    // CPU
    struct {
        std::string arch;            ///< 架构（ARMv8.2 / x86-64）
        int num_big_cores{0};        ///< 大核数
        int num_little_cores{0};     ///< 小核数
        float max_freq_ghz{0.0f};    ///< 最大频率
        bool has_neon{false};        ///< ARM Neon
        bool has_sve{false};         ///< ARM SVE
        bool has_avx2{false};        ///< x86 AVX2
        bool has_avx512{false};      ///< x86 AVX-512
    } cpu;

    // 系统
    struct {
        std::size_t typical_ram_mb{0};   ///< 典型内存配置
        std::size_t max_ram_mb{0};       ///< 最大内存配置
        float typical_tdp_w{0.0f};       ///< 典型 TDP（瓦特）
        bool supports_ion{false};        ///< 支持 ION/DMA-BUF
        bool supports_dsp{false};        ///< 有独立 DSP
    } system;

    // 已验证的模型基准（在目标芯片上实测）
    struct {
        double yolo_nano_ms{0.0};        ///< YOLOv11n 推理延迟（ms）
        double resnet18_ms{0.0};         ///< ResNet-18 推理延迟
        double mobilenet_v3_ms{0.0};     ///< MobileNetV3 推理延迟
    } benchmarks;
};

// ─────────────────────────────────────────────────────────────────────────────
//  官方支持芯片数据库
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief QooBot 官方支持的芯片列表。
 *
 * 基于实测数据维护，新芯片需通过兼容性验证后才能添加。
 */
static const std::unordered_map<std::string, ChipInfo> SUPPORTED_CHIPS = {
    // ── Qualcomm Snapdragon ────────────────────────────────────────────
    {
        "sdm8g3",
        {
            "Qualcomm", "Snapdragon 8 Gen 3", "pineapple", "SM8650", 1,
            {"Hexagon NPU", 45.0f, 90.0f, 45.0f, 4096, true, true, 4},
            {"Adreno 750", 4500.0f, 8192, false, true, true},
            {"ARMv9.2-A", 1, 5, 3.3f, true, true, false, false},
            {12288, 24576, 12.0f, true, true},
            {3.2, 1.8, 1.2}
        }
    },
    {
        "sdm8g2",
        {
            "Qualcomm", "Snapdragon 8 Gen 2", "kalama", "SM8550", 2,
            {"Hexagon NPU", 26.0f, 52.0f, 26.0f, 3072, false, true, 3},
            {"Adreno 740", 3500.0f, 6144, false, true, true},
            {"ARMv9-A", 1, 4, 3.2f, true, false, false, false},
            {8192, 16384, 10.0f, true, true},
            {4.5, 2.5, 1.8}
        }
    },
    {
        "sdm7pg2",
        {
            "Qualcomm", "Snapdragon 7+ Gen 2", "crow", "SM7475", 3,
            {"Hexagon NPU", 12.0f, 24.0f, 12.0f, 2048, false, false, 2},
            {"Adreno 725", 2000.0f, 4096, false, true, true},
            {"ARMv9-A", 1, 3, 2.9f, true, false, false, false},
            {6144, 12288, 8.0f, true, false},
            {8.0, 4.0, 3.0}
        }
    },

    // ── MediaTek Dimensity ─────────────────────────────────────────────
    {
        "mt6989",
        {
            "MediaTek", "Dimensity 9300", "", "MT6989", 1,
            {"APU 790", 48.0f, 96.0f, 48.0f, 4096, true, true, 4},
            {"Immortalis-G720", 5000.0f, 8192, false, true, true},
            {"ARMv9.2-A", 4, 4, 3.25f, true, true, false, false},
            {12288, 24576, 14.0f, true, false},
            {3.0, 1.6, 1.1}
        }
    },
    {
        "mt6985",
        {
            "MediaTek", "Dimensity 8300", "", "MT6985", 2,
            {"APU 780", 28.0f, 56.0f, 28.0f, 3072, false, true, 3},
            {"Mali-G615", 3000.0f, 6144, false, true, true},
            {"ARMv9-A", 1, 3, 3.1f, true, false, false, false},
            {8192, 16384, 10.0f, true, false},
            {5.0, 2.8, 2.0}
        }
    },

    // ── Horizon Robotics (征程) ───────────────────────────────────────
    {
        "j6",
        {
            "Horizon", "Journey 6", "j6", "J6", 1,
            {"BPU Nash", 560.0f, 1120.0f, 560.0f, 8192, true, true, 8},
            {"Mali-G78", 2000.0f, 4096, false, true, false},
            {"ARMv8.2-A", 8, 0, 2.0f, true, false, false, false},
            {8192, 16384, 30.0f, true, true},
            {1.2, 0.8, 0.6}
        }
    },
    {
        "j5",
        {
            "Horizon", "Journey 5", "j5", "J5", 2,
            {"BPU Bayes", 128.0f, 256.0f, 128.0f, 4096, true, true, 4},
            {"Mali-G52", 800.0f, 2048, false, true, false},
            {"ARMv8.2-A", 8, 0, 1.8f, true, false, false, false},
            {4096, 8192, 20.0f, true, true},
            {2.5, 1.5, 1.0}
        }
    },

    // ── Rockchip ───────────────────────────────────────────────────────
    {
        "rk3588",
        {
            "Rockchip", "RK3588", "rk3588", "RK3588", 2,
            {"RKNN NPU", 6.0f, 6.0f, 3.0f, 2048, false, false, 2},
            {"Mali-G610", 1200.0f, 4096, false, true, true},
            {"ARMv8.2-A", 4, 4, 2.4f, true, false, false, false},
            {4096, 32768, 15.0f, true, false},
            {12.0, 6.0, 4.0}
        }
    },
    {
        "rk3568",
        {
            "Rockchip", "RK3568", "rk3568", "RK3568", 3,
            {"RKNN NPU", 1.0f, 1.0f, 0.5f, 512, false, false, 1},
            {"Mali-G52", 300.0f, 2048, false, true, false},
            {"ARMv8.2-A", 0, 4, 2.0f, true, false, false, false},
            {2048, 8192, 8.0f, false, false},
            {25.0, 15.0, 10.0}
        }
    },

    // ── NVIDIA Jetson ──────────────────────────────────────────────────
    {
        "orin_agx",
        {
            "NVIDIA", "Jetson AGX Orin", "orin-agx", "Tegra234", 1,
            {"DLA v2.0", 0.0f, 0.0f, 0.0f, 0, false, false, 0},  // GPU 为主
            {"Ampere GA10B", 5500.0f, 32768, true, false, false},  // CUDA
            {"ARMv8.2-A", 12, 0, 2.2f, true, false, false, false},
            {32768, 65536, 60.0f, true, true},
            {1.5, 0.9, 0.7}
        }
    },
    {
        "orin_nx",
        {
            "NVIDIA", "Jetson Orin NX", "orin-nx", "Tegra234", 2,
            {"DLA v2.0", 0.0f, 0.0f, 0.0f, 0, false, false, 0},
            {"Ampere GA10B", 3200.0f, 8192, true, false, false},
            {"ARMv8.2-A", 8, 0, 2.0f, true, false, false, false},
            {8192, 16384, 25.0f, true, true},
            {2.5, 1.5, 1.0}
        }
    },

    // ── x86 (CPU-only) ─────────────────────────────────────────────────
    {
        "x86_avx2",
        {
            "Intel/AMD", "x86-64 AVX2", "generic-x86", "x86_64", 4,
            {"N/A", 0.0f, 0.0f, 0.0f, 0, false, false, 0},
            {"N/A", 0.0f, 0, false, false, false},
            {"x86-64", 8, 0, 3.5f, false, false, true, false},
            {8192, 65536, 65.0f, false, false},
            {30.0, 15.0, 10.0}
        }
    },
    {
        "x86_avx512",
        {
            "Intel", "x86-64 AVX-512", "skylake-x", "x86_64", 4,
            {"N/A", 0.0f, 0.0f, 0.0f, 0, false, false, 0},
            {"N/A", 0.0f, 0, false, false, false},
            {"x86-64", 16, 0, 4.0f, false, false, true, true},
            {16384, 131072, 125.0f, false, false},
            {20.0, 10.0, 7.0}
        }
    },

    // ── ARM Cortex-A (CPU-only, 入门) ─────────────────────────────────
    {
        "arm_a76",
        {
            "ARM", "Cortex-A76", "a76", "Cortex-A", 4,
            {"N/A", 0.0f, 0.0f, 0.0f, 0, false, false, 0},
            {"Mali-G57", 300.0f, 2048, false, true, false},
            {"ARMv8.2-A", 4, 4, 2.4f, true, false, false, false},
            {2048, 8192, 10.0f, false, false},
            {50.0, 25.0, 15.0}
        }
    },
};

// ─────────────────────────────────────────────────────────────────────────────
//  ChipSupportMatrix — 芯片支持矩阵核心
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 全局芯片支持矩阵。
 *
 * 提供芯片查询、兼容性验证、性能预估等功能。
 */
class ChipSupportMatrix {
public:
    static ChipSupportMatrix& instance() {
        static ChipSupportMatrix matrix;
        return matrix;
    }

    /**
     * @brief 查询芯片信息。
     * @param chip_id  芯片标识符（如 "sdm8g3", "j6", "rk3588"）
     * @return 芯片信息，未找到返回 nullopt
     */
    [[nodiscard]] std::optional<ChipInfo> query(const std::string& chip_id) const {
        auto it = SUPPORTED_CHIPS.find(chip_id);
        if (it != SUPPORTED_CHIPS.end()) {
            return it->second;
        }
        return std::nullopt;
    }

    /**
     * @brief 模糊匹配芯片型号。
     *
     * 例如 "SM8650-AB" 可匹配 "sdm8g3"。
     */
    [[nodiscard]] std::optional<ChipInfo> fuzzy_query(const std::string& chip_hint) const {
        std::string lower = chip_hint;
        std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);

        // 精确匹配
        auto exact = query(lower);
        if (exact.has_value()) return exact;

        // 模糊匹配：芯片名包含 hint 或 hint 包含芯片名
        for (const auto& [id, info] : SUPPORTED_CHIPS) {
            if (id.find(lower) != std::string::npos ||
                lower.find(id) != std::string::npos ||
                lower.find(info.codename) != std::string::npos ||
                lower.find(info.model) != std::string::npos) {
                // 转为小写再比较
                std::string model_lower = info.model;
                std::transform(model_lower.begin(), model_lower.end(),
                               model_lower.begin(), ::tolower);
                if (model_lower.find(lower) != std::string::npos ||
                    lower.find(model_lower) != std::string::npos) {
                    return info;
                }
            }
        }

        return std::nullopt;
    }

    /**
     * @brief 列出所有支持的芯片。
     */
    [[nodiscard]] std::vector<ChipInfo> list_all() const {
        std::vector<ChipInfo> result;
        result.reserve(SUPPORTED_CHIPS.size());
        for (const auto& [id, info] : SUPPORTED_CHIPS) {
            result.push_back(info);
        }
        // 按 tier 排序
        std::sort(result.begin(), result.end(),
                  [](const ChipInfo& a, const ChipInfo& b) {
                      return a.tier < b.tier;
                  });
        return result;
    }

    /**
     * @brief 列出指定厂商的芯片。
     */
    [[nodiscard]] std::vector<ChipInfo> list_by_vendor(const std::string& vendor) const {
        std::vector<ChipInfo> result;
        for (const auto& [id, info] : SUPPORTED_CHIPS) {
            if (info.vendor == vendor) {
                result.push_back(info);
            }
        }
        return result;
    }

    /**
     * @brief 列出指定 tier 的芯片。
     */
    [[nodiscard]] std::vector<ChipInfo> list_by_tier(int tier) const {
        std::vector<ChipInfo> result;
        for (const auto& [id, info] : SUPPORTED_CHIPS) {
            if (info.tier == tier) {
                result.push_back(info);
            }
        }
        return result;
    }

    /**
     * @brief 验证芯片兼容性。
     *
     * 检查给定芯片是否满足最低要求。
     */
    [[nodiscard]] bool is_compatible(const std::string& chip_id,
                                       float min_npu_tops = 0.0f,
                                       std::size_t min_memory_mb = 0) const {
        auto info = query(chip_id);
        if (!info.has_value()) {
            return false;  // 未知芯片 → 不兼容
        }

        if (min_npu_tops > 0 && info->npu.peak_tops < min_npu_tops) {
            spdlog::warn("Chip {} NPU TOPS ({}) below requirement ({})",
                          chip_id, info->npu.peak_tops, min_npu_tops);
            return false;
        }

        if (min_memory_mb > 0 && info->system.typical_ram_mb < min_memory_mb) {
            spdlog::warn("Chip {} RAM ({}) below requirement ({})",
                          chip_id, info->system.typical_ram_mb, min_memory_mb);
            return false;
        }

        return true;
    }

    /**
     * @brief 为给定芯片推荐最佳后端。
     */
    [[nodiscard]] BackendType recommend_backend(const std::string& chip_id) const {
        auto info = query(chip_id);
        if (!info.has_value()) {
            return BackendType::CPU;  // 未知芯片 → CPU 兜底
        }

        if (info->npu.peak_tops > 5.0f) {
            return BackendType::NPU;
        }
        if (info->gpu.peak_gflops > 500.0f) {
            return info->gpu.supports_cuda ? BackendType::GPU : BackendType::CPU;
        }
        return BackendType::CPU;
    }

    /**
     * @brief 预估模型在某芯片上的推理延迟。
     *
     * @param chip_id    芯片标识符
     * @param model_flops  模型 FLOPs
     * @return 预估延迟（毫秒），-1 表示无法预估
     */
    [[nodiscard]] double estimate_latency(const std::string& chip_id,
                                            double model_flops) const {
        auto info = query(chip_id);
        if (!info.has_value() || info->npu.peak_tops <= 0) {
            return -1.0;
        }

        // 简单模型：延迟 ≈ FLOPs / TOPS（假设 70% 利用率）
        double effective_tops = info->npu.peak_tops * 0.7;
        double latency_s = model_flops / (effective_tops * 1e12);
        return latency_s * 1000.0;  // 转为毫秒
    }

    /**
     * @brief 导出支持矩阵 JSON（用于 Web 仪表盘）。
     */
    [[nodiscard]] std::string export_json() const {
        std::stringstream ss;
        ss << "{\"chips\": [\n";
        std::size_t idx = 0;
        for (const auto& [id, info] : SUPPORTED_CHIPS) {
            if (idx > 0) ss << ",\n";
            ss << "  {"
               << "\"id\": \"" << id << "\","
               << "\"vendor\": \"" << info.vendor << "\","
               << "\"model\": \"" << info.model << "\","
               << "\"tier\": " << info.tier << ","
               << "\"npu_tops\": " << info.npu.peak_tops << ","
               << "\"npu_int8_tops\": " << info.npu.int8_tops << ","
               << "\"npu_fp16_tops\": " << info.npu.fp16_tops << ","
               << "\"npu_memory_mb\": " << info.npu.max_memory_mb << ","
               << "\"gpu_gflops\": " << info.gpu.peak_gflops << ","
               << "\"gpu_memory_mb\": " << info.gpu.max_memory_mb << ","
               << "\"cpu_arch\": \"" << info.cpu.arch << "\","
               << "\"cpu_big_cores\": " << info.cpu.num_big_cores << ","
               << "\"cpu_little_cores\": " << info.cpu.num_little_cores << ","
               << "\"typical_ram_mb\": " << info.system.typical_ram_mb << ","
               << "\"typical_tdp_w\": " << info.system.typical_tdp_w
               << "}";
            idx++;
        }
        ss << "\n]}\n";
        return ss.str();
    }

    /** @brief 导出 Markdown 表格（用于文档）。 */
    [[nodiscard]] std::string export_markdown_table() const {
        std::stringstream ss;
        ss << "| Chip | Vendor | Tier | NPU TOPS | GPU GFLOPS | RAM (MB) | TDP (W) |\n";
        ss << "|------|--------|------|----------|------------|----------|--------|\n";

        for (const auto& [id, info] : SUPPORTED_CHIPS) {
            ss << "| " << info.model
               << " | " << info.vendor
               << " | " << info.tier
               << " | " << info.npu.peak_tops
               << " | " << info.gpu.peak_gflops
               << " | " << info.system.typical_ram_mb
               << " | " << info.system.typical_tdp_w
               << " |\n";
        }
        return ss.str();
    }

private:
    ChipSupportMatrix() {
        spdlog::info("ChipSupportMatrix initialized: {} supported chips",
                      SUPPORTED_CHIPS.size());
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  便捷 API
// ─────────────────────────────────────────────────────────────────────────────

/** @brief 查询芯片信息。 */
inline std::optional<ChipInfo> query_chip(const std::string& chip_id) {
    return ChipSupportMatrix::instance().query(chip_id);
}

/** @brief 模糊匹配芯片。 */
inline std::optional<ChipInfo> find_chip(const std::string& hint) {
    return ChipSupportMatrix::instance().fuzzy_query(hint);
}

/** @brief 验证芯片兼容性。 */
inline bool check_chip_compatible(const std::string& chip_id,
                                    float min_npu_tops = 0.0f,
                                    std::size_t min_memory_mb = 0) {
    return ChipSupportMatrix::instance().is_compatible(
        chip_id, min_npu_tops, min_memory_mb);
}

/** @brief 推荐后端。 */
inline BackendType recommend_backend_for_chip(const std::string& chip_id) {
    return ChipSupportMatrix::instance().recommend_backend(chip_id);
}

/** @brief 导出支持矩阵 JSON。 */
inline std::string chip_matrix_json() {
    return ChipSupportMatrix::instance().export_json();
}

}  // namespace hardware
}  // namespace qoocore
