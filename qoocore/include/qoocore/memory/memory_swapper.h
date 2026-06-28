/**
 * @file memory_swapper.h
 * @brief 显存卸载 — 不活跃模型权重卸载至 DDR，按需换入
 *
 * 对标 CUDA UVM（Unified Virtual Memory）的简化实现。
 * 管理 GPU 显存与系统 DDR 之间的权重迁移，实现更大的有效模型容量。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>
#include <unordered_map>
#include <vector>

namespace qoocore {
namespace memory {

// ─────────────────────────────────────────────────────────────────────────────
//  MemorySwapConfig
// ─────────────────────────────────────────────────────────────────────────────

struct MemorySwapConfig {
    std::size_t vram_limit_mb{2048};        ///< 显存上限（MB）
    std::size_t ddr_limit_mb{8192};         ///< DDR 缓存上限（MB）
    float inactive_threshold_sec{30.0f};    ///< 不活跃阈值（秒），超过则卸载
    float prefetch_window_sec{5.0f};        ///< 预取窗口（秒）
    std::size_t swap_chunk_size_mb{64};     ///< 交换块大小（MB）
    bool enable_prefetch{true};             ///< 是否启用预取
    bool enable_compression{false};         ///< 是否启用压缩
    bool async_swap{true};                  ///< 是否异步交换
};

// ─────────────────────────────────────────────────────────────────────────────
//  SwapStatistics
// ─────────────────────────────────────────────────────────────────────────────

struct SwapStatistics {
    std::size_t total_swaps_out{0};
    std::size_t total_swaps_in{0};
    std::size_t total_bytes_swapped_out{0};
    std::size_t total_bytes_swapped_in{0};
    std::size_t vram_in_use_mb{0};
    std::size_t ddr_in_use_mb{0};
    std::size_t prefetch_hits{0};
    std::size_t prefetch_misses{0};
    float avg_swap_latency_ms{0.0f};
};

// ─────────────────────────────────────────────────────────────────────────────
//  MemorySwapper
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 显存卸载管理器
 *
 * 管理 GPU 显存与系统 DDR 之间的模型权重迁移。
 * 当显存不足时，将不活跃的权重块卸载到 DDR；
 * 当需要推理时，将权重块换入显存（支持预取）。
 */
class MemorySwapper {
public:
    explicit MemorySwapper(const MemorySwapConfig& config);
    ~MemorySwapper();

    // ── 生命周期 ─────────────────────────────────────────────────────
    bool initialize();
    void shutdown();

    // ── 权重注册 ─────────────────────────────────────────────────────
    /**
     * @brief 注册一个权重块
     *
     * @param name       权重名称
     * @param vram_ptr   显存中的指针
     * @param size_bytes 大小（字节）
     * @param priority   优先级（越高越不容易被卸载）
     * @return ErrorCode
     */
    ErrorCode register_weight(
        const std::string& name,
        void* vram_ptr,
        std::size_t size_bytes,
        int priority = 0);

    /**
     * @brief 注销权重块
     */
    ErrorCode unregister_weight(const std::string& name);

    // ── 交换操作 ─────────────────────────────────────────────────────
    /**
     * @brief 将指定权重换出到 DDR
     */
    ErrorCode swap_out(const std::string& name);

    /**
     * @brief 将指定权重从 DDR 换入显存
     */
    ErrorCode swap_in(const std::string& name);

    /**
     * @brief 自动管理：根据显存压力决定换出/换入
     *
     * @param active_names 当前活跃的权重名称列表
     */
    ErrorCode manage(const std::vector<std::string>& active_names);

    /**
     * @brief 预取即将需要的权重
     */
    ErrorCode prefetch(const std::vector<std::string>& names);

    // ── 查询 ─────────────────────────────────────────────────────────
    [[nodiscard]] bool is_in_vram(const std::string& name) const;
    [[nodiscard]] std::size_t vram_available() const;
    [[nodiscard]] std::size_t ddr_available() const;
    [[nodiscard]] const SwapStatistics& statistics() const;

    // ── 回调 ─────────────────────────────────────────────────────────
    using SwapCallback = std::function<void(const std::string& name, bool swapped_in)>;
    void set_swap_callback(SwapCallback cb);

private:
    struct WeightEntry {
        std::string name;
        void* vram_ptr{nullptr};
        void* ddr_ptr{nullptr};
        std::size_t size{0};
        int priority{0};
        bool in_vram{true};
        double last_access_time{0.0};
        double last_swap_time{0.0};
    };

    MemorySwapConfig config_;
    SwapStatistics stats_;
    std::unordered_map<std::string, WeightEntry> weights_;
    SwapCallback callback_;
    bool initialized_{false};
};

} // namespace memory
} // namespace qoocore
