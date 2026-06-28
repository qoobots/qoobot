/**
 * @file memory_swapper.cpp
 * @brief 显存卸载管理器实现
 *
 * 实现 GPU 显存与系统 DDR 之间的模型权重迁移。
 * 基于 LRU 策略自动管理权重在显存和 DDR 之间的分配。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/memory/memory_swapper.h"

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <mutex>

#ifdef _WIN32
#  include <windows.h>
#else
#  include <sys/mman.h>
#  include <unistd.h>
#endif

namespace qoocore {
namespace memory {

namespace {

double now_seconds() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration<double>(clock::now().time_since_epoch()).count();
}

void* alloc_ddr(std::size_t size) {
#ifdef _WIN32
    return VirtualAlloc(nullptr, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
#else
    void* ptr = mmap(nullptr, size, PROT_READ | PROT_WRITE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (ptr == MAP_FAILED) return nullptr;
    return ptr;
#endif
}

void free_ddr(void* ptr, std::size_t size) {
#ifdef _WIN32
    VirtualFree(ptr, 0, MEM_RELEASE);
#else
    munmap(ptr, size);
#endif
}

void copy_memory(void* dst, const void* src, std::size_t size) {
    // 使用 memcpy（对于大块内存，理想情况下应该使用 DMA）
    std::memcpy(dst, src, size);
}

} // anonymous namespace

// ═══════════════════════════════════════════════════════════════════════════════
//  MemorySwapper 实现
// ═══════════════════════════════════════════════════════════════════════════════

MemorySwapper::MemorySwapper(const MemorySwapConfig& config)
    : config_(config) {}

MemorySwapper::~MemorySwapper() {
    shutdown();
}

bool MemorySwapper::initialize() {
    if (initialized_) return true;
    initialized_ = true;
    return true;
}

void MemorySwapper::shutdown() {
    if (!initialized_) return;

    // 将所有在 DDR 的权重释放
    for (auto& [name, entry] : weights_) {
        if (entry.ddr_ptr && !entry.in_vram) {
            // 确保数据在显存中（最后一次换入）
            if (entry.vram_ptr) {
                swap_in(name);
            }
        }
        if (entry.ddr_ptr) {
            free_ddr(entry.ddr_ptr, entry.size);
            entry.ddr_ptr = nullptr;
        }
    }

    weights_.clear();
    initialized_ = false;
}

ErrorCode MemorySwapper::register_weight(
    const std::string& name,
    void* vram_ptr,
    std::size_t size_bytes,
    int priority)
{
    if (!initialized_) return ErrorCode::ENGINE_NOT_INIT;
    if (!vram_ptr || size_bytes == 0) return ErrorCode::INVALID_ARGUMENT;

    WeightEntry entry;
    entry.name = name;
    entry.vram_ptr = vram_ptr;
    entry.size = size_bytes;
    entry.priority = priority;
    entry.in_vram = true;
    entry.last_access_time = now_seconds();

    weights_[name] = std::move(entry);
    stats_.vram_in_use_mb += size_bytes / (1024 * 1024);

    return ErrorCode::OK;
}

ErrorCode MemorySwapper::unregister_weight(const std::string& name) {
    auto it = weights_.find(name);
    if (it == weights_.end()) return ErrorCode::MODEL_NOT_LOADED;

    auto& entry = it->second;

    if (entry.in_vram) {
        stats_.vram_in_use_mb -= entry.size / (1024 * 1024);
    } else {
        stats_.ddr_in_use_mb -= entry.size / (1024 * 1024);
    }

    if (entry.ddr_ptr) {
        free_ddr(entry.ddr_ptr, entry.size);
    }

    weights_.erase(it);
    return ErrorCode::OK;
}

ErrorCode MemorySwapper::swap_out(const std::string& name) {
    auto it = weights_.find(name);
    if (it == weights_.end()) return ErrorCode::MODEL_NOT_LOADED;

    auto& entry = it->second;
    if (!entry.in_vram) return ErrorCode::OK;  // 已在 DDR

    // 检查 DDR 空间
    if (stats_.ddr_in_use_mb + entry.size / (1024 * 1024) > config_.ddr_limit_mb) {
        return ErrorCode::OUT_OF_MEMORY;
    }

    // 分配 DDR 空间
    void* ddr = alloc_ddr(entry.size);
    if (!ddr) return ErrorCode::OUT_OF_MEMORY;

    // 拷贝到 DDR
    auto start = now_seconds();
    copy_memory(ddr, entry.vram_ptr, entry.size);
    double elapsed = now_seconds() - start;

    entry.ddr_ptr = ddr;
    entry.in_vram = false;
    entry.last_swap_time = now_seconds();

    stats_.total_swaps_out++;
    stats_.total_bytes_swapped_out += entry.size;
    stats_.vram_in_use_mb -= entry.size / (1024 * 1024);
    stats_.ddr_in_use_mb += entry.size / (1024 * 1024);

    // 更新平均延迟
    double prev_avg = stats_.avg_swap_latency_ms;
    double count = static_cast<double>(stats_.total_swaps_out + stats_.total_swaps_in);
    stats_.avg_swap_latency_ms = (prev_avg * (count - 1) + elapsed * 1000.0) / count;

    if (callback_) callback_(name, false);

    return ErrorCode::OK;
}

ErrorCode MemorySwapper::swap_in(const std::string& name) {
    auto it = weights_.find(name);
    if (it == weights_.end()) return ErrorCode::MODEL_NOT_LOADED;

    auto& entry = it->second;
    if (entry.in_vram) {
        entry.last_access_time = now_seconds();
        return ErrorCode::OK;  // 已在显存
    }

    if (!entry.ddr_ptr || !entry.vram_ptr) {
        return ErrorCode::MEMORY_ALIGN_FAILED;
    }

    // 检查显存空间
    if (vram_available() * 1024 * 1024 < entry.size) {
        return ErrorCode::OUT_OF_MEMORY;
    }

    // 拷贝回显存
    auto start = now_seconds();
    copy_memory(entry.vram_ptr, entry.ddr_ptr, entry.size);
    double elapsed = now_seconds() - start;

    // 释放 DDR 缓存
    free_ddr(entry.ddr_ptr, entry.size);
    entry.ddr_ptr = nullptr;
    entry.in_vram = true;
    entry.last_access_time = now_seconds();
    entry.last_swap_time = now_seconds();

    stats_.total_swaps_in++;
    stats_.total_bytes_swapped_in += entry.size;
    stats_.vram_in_use_mb += entry.size / (1024 * 1024);
    stats_.ddr_in_use_mb -= entry.size / (1024 * 1024);

    double prev_avg = stats_.avg_swap_latency_ms;
    double count = static_cast<double>(stats_.total_swaps_out + stats_.total_swaps_in);
    stats_.avg_swap_latency_ms = (prev_avg * (count - 1) + elapsed * 1000.0) / count;

    if (callback_) callback_(name, true);

    return ErrorCode::OK;
}

ErrorCode MemorySwapper::manage(const std::vector<std::string>& active_names) {
    if (!initialized_) return ErrorCode::ENGINE_NOT_INIT;

    double now = now_seconds();

    // 标记活跃权重
    for (const auto& name : active_names) {
        auto it = weights_.find(name);
        if (it != weights_.end()) {
            it->second.last_access_time = now;
        }
    }

    // 确保活跃权重在显存中
    for (const auto& name : active_names) {
        auto ec = swap_in(name);
        if (ec != ErrorCode::OK && ec != ErrorCode::OUT_OF_MEMORY) {
            return ec;
        }
    }

    // LRU 淘汰：找出可换出的权重
    // 按优先级 + 最近访问时间排序
    std::vector<std::pair<double, std::string>> candidates;

    for (const auto& [name, entry] : weights_) {
        if (!entry.in_vram) continue;

        // 跳过活跃权重
        if (std::find(active_names.begin(), active_names.end(), name) != active_names.end()) {
            continue;
        }

        // 检查不活跃阈值
        double inactive_time = now - entry.last_access_time;
        if (inactive_time < config_.inactive_threshold_sec) continue;

        // 评分：低优先级 + 长时间未访问 = 更容易被淘汰
        double score = inactive_time / (1.0 + static_cast<double>(entry.priority));
        candidates.emplace_back(-score, name);  // 负号使大分数排前面
    }

    std::sort(candidates.begin(), candidates.end());

    // 换出直到满足显存限制
    for (const auto& [score, name] : candidates) {
        if (vram_available() >= config_.vram_limit_mb * 0.2) break;  // 保留 20% 余量
        swap_out(name);
    }

    return ErrorCode::OK;
}

ErrorCode MemorySwapper::prefetch(const std::vector<std::string>& names) {
    if (!config_.enable_prefetch) return ErrorCode::OK;

    for (const auto& name : names) {
        auto it = weights_.find(name);
        if (it != weights_.end() && !it->second.in_vram) {
            auto ec = swap_in(name);
            if (ec == ErrorCode::OK) {
                stats_.prefetch_hits++;
            } else {
                stats_.prefetch_misses++;
            }
        } else if (it != weights_.end()) {
            stats_.prefetch_hits++;
        }
    }

    return ErrorCode::OK;
}

bool MemorySwapper::is_in_vram(const std::string& name) const {
    auto it = weights_.find(name);
    return it != weights_.end() && it->second.in_vram;
}

std::size_t MemorySwapper::vram_available() const {
    std::size_t used = stats_.vram_in_use_mb;
    return (used < config_.vram_limit_mb) ? (config_.vram_limit_mb - used) : 0;
}

std::size_t MemorySwapper::ddr_available() const {
    std::size_t used = stats_.ddr_in_use_mb;
    return (used < config_.ddr_limit_mb) ? (config_.ddr_limit_mb - used) : 0;
}

const SwapStatistics& MemorySwapper::statistics() const {
    return stats_;
}

void MemorySwapper::set_swap_callback(SwapCallback cb) {
    callback_ = std::move(cb);
}

} // namespace memory
} // namespace qoocore
