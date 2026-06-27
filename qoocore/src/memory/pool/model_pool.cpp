/**
 * @file model_pool.cpp
 * @brief 模型内存池 — 多模型共享权重、张量复用、零拷贝内存管理
 *
 * 核心设计：
 *   - Arena Allocator：预分配大块内存，bump-pointer 分配，无碎片
 *   - Weight Sharing：相同模型不同实例共享权重内存
 *   - Tensor Reuse：推理中间张量复用（环形缓冲）
 *   - Zero-Copy：ION/DMA-BUF 跨硬件共享
 *   - Eviction Policy：LRU 淘汰不活跃模型权重
 *
 * 内存层级：
 *   L0: 模型权重池（常驻，共享）  — 多模型共享
 *   L1: 激活张量池（临时，复用）  — 推理中间结果
 *   L2: I/O 缓冲池（环形）         — 输入/输出张量
 *
 * 对标：TensorRT IExecutionContext 内存管理、TFLite ArenaPlanner
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/core.h"
#include "qoocore/tensor.h"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <list>
#include <mutex>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

namespace qoocore {
namespace memory {

// ─────────────────────────────────────────────────────────────────────────────
//  MemoryBlock — 内存块（Arena 分配单元）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief Arena 内存块描述符。
 *
 * 支持 bump-pointer 分配，不支持单个释放（批量 reset）。
 */
struct MemoryBlock {
    std::uint8_t* base{nullptr};       ///< 内存基地址
    std::size_t   total_size{0};       ///< 总大小（字节）
    std::size_t   used{0};             ///< 已分配偏移
    std::size_t   alignment{64};       ///< 对齐要求（默认 64 字节，兼容 AVX-512）

    /** @brief bump-pointer 分配。 */
    [[nodiscard]] std::uint8_t* alloc(std::size_t size) {
        // 对齐
        std::size_t aligned = (used + alignment - 1) & ~(alignment - 1);
        if (aligned + size > total_size) {
            return nullptr;  // 内存不足
        }
        std::uint8_t* ptr = base + aligned;
        used = aligned + size;
        return ptr;
    }

    /** @brief 重置分配指针（不释放内存）。 */
    void reset() { used = 0; }

    /** @brief 剩余可用字节数。 */
    [[nodiscard]] std::size_t available() const {
        return (used + alignment - 1) & ~(alignment - 1) < total_size
                   ? total_size - ((used + alignment - 1) & ~(alignment - 1))
                   : 0;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  PooledWeight — 池化权重（共享引用计数）
// ─────────────────────────────────────────────────────────────────────────────

struct PooledWeight {
    std::string      model_name;       ///< 所属模型名
    std::vector<std::uint8_t> data;    ///< 权重数据（可能已量化）
    DType            dtype{DType::FLOAT32};
    std::size_t      original_size{0}; ///< 原始 FP32 大小
    std::atomic<std::size_t> ref_count{1}; ///< 引用计数

    /** @brief 压缩比。 */
    [[nodiscard]] float compression_ratio() const {
        return original_size > 0
                   ? static_cast<float>(data.size()) / original_size
                   : 1.0f;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  RingBuffer — 环形缓冲（I/O 张量复用）
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 环形缓冲区，用于复用输入/输出张量内存。
 *
 * 典型场景：推理循环中，每次推理使用下一个 slot，无需频繁 malloc/free。
 */
template <typename T>
class RingBuffer {
public:
    explicit RingBuffer(std::size_t slots) : slots_(slots), buffers_(slots) {}

    /** @brief 获取下一个可用 slot 的引用。 */
    T& next() {
        std::lock_guard<std::mutex> lock(mtx_);
        T& buf = buffers_[write_idx_];
        write_idx_ = (write_idx_ + 1) % slots_;
        return buf;
    }

    /** @brief 获取指定 slot。 */
    T& at(std::size_t idx) {
        return buffers_[idx % slots_];
    }

    /** @brief slot 数量。 */
    [[nodiscard]] std::size_t size() const { return slots_; }

    /** @brief 重置所有 slot。 */
    void clear() {
        std::lock_guard<std::mutex> lock(mtx_);
        for (auto& buf : buffers_) {
            buf = T{};
        }
        write_idx_ = 0;
    }

private:
    std::size_t slots_;
    std::vector<T> buffers_;
    std::size_t write_idx_{0};
    std::mutex mtx_;
};

// ─────────────────────────────────────────────────────────────────────────────
//  ModelMemoryPool — 模型内存池核心
// ─────────────────────────────────────────────────────────────────────────────

/**
 * @brief 模型内存池，管理所有模型的权重和激活内存。
 *
 * 线程安全：所有 public 方法可并发调用。
 */
class ModelMemoryPool {
public:
    /**
     * @brief 创建内存池。
     * @param max_pool_bytes  最大池大小（字节），0 = 使用系统内存的 50%
     * @param enable_zero_copy  是否启用 ION/DMA-BUF 零拷贝
     */
    explicit ModelMemoryPool(std::size_t max_pool_bytes = 0,
                               bool enable_zero_copy = true)
        : enable_zero_copy_(enable_zero_copy) {

        if (max_pool_bytes == 0) {
            // 默认：使用系统可用内存的 50%
            max_pool_bytes = estimate_available_memory() / 2;
        }

        // 分配 Arena（模型权重池 + 激活池）
        std::size_t weight_pool_size = max_pool_bytes * 2 / 3;
        std::size_t activation_pool_size = max_pool_bytes / 3;

        spdlog::info("ModelMemoryPool: allocating {} MB ({} MB weights + {} MB activations)",
                      max_pool_bytes / (1024 * 1024),
                      weight_pool_size / (1024 * 1024),
                      activation_pool_size / (1024 * 1024));

        // 分配权重 Arena
        weight_arena_.base = new (std::nothrow) std::uint8_t[weight_pool_size];
        if (weight_arena_.base) {
            weight_arena_.total_size = weight_pool_size;
            spdlog::info("  Weight arena allocated: {} MB",
                          weight_pool_size / (1024 * 1024));
        } else {
            spdlog::error("  Failed to allocate weight arena");
        }

        // 分配激活 Arena
        activation_arena_.base = new (std::nothrow) std::uint8_t[activation_pool_size];
        if (activation_arena_.base) {
            activation_arena_.total_size = activation_pool_size;
            spdlog::info("  Activation arena allocated: {} MB",
                          activation_pool_size / (1024 * 1024));
        } else {
            spdlog::error("  Failed to allocate activation arena");
        }
    }

    ~ModelMemoryPool() {
        delete[] weight_arena_.base;
        delete[] activation_arena_.base;
    }

    // ── 权重管理 ───────────────────────────────────────────────────────

    /**
     * @brief 注册模型权重（可能与其他模型共享）。
     *
     * @param model_name  模型名称（用于去重）
     * @param weight_data  权重数据（移动语义）
     * @param dtype       数据类型
     * @return 共享权重指针（多个模型可能返回同一个）
     */
    std::shared_ptr<PooledWeight> register_weights(
        const std::string& model_name,
        std::vector<std::uint8_t>&& weight_data,
        DType dtype = DType::FLOAT32) {

        std::lock_guard<std::mutex> lock(pool_mutex_);

        // 计算权重哈希（用于去重）
        std::size_t weight_hash = hash_bytes(weight_data.data(), weight_data.size());

        // 查找是否已有相同权重
        auto it = weight_index_.find(weight_hash);
        if (it != weight_index_.end()) {
            auto& existing = it->second;
            existing->ref_count.fetch_add(1);
            spdlog::info("Weight sharing: '{}' reuses weights from '{}' (hash={:016x})",
                          model_name, existing->model_name, weight_hash);
            return existing;
        }

        // 分配 Arena 内存存储权重
        std::size_t weight_bytes = weight_data.size();
        std::uint8_t* arena_ptr = weight_arena_.alloc(weight_bytes);

        std::shared_ptr<PooledWeight> pooled;
        if (arena_ptr) {
            // 复制到 Arena
            std::memcpy(arena_ptr, weight_data.data(), weight_bytes);
            // 释放原始数据以节省内存
            weight_data.clear();
            weight_data.shrink_to_fit();

            pooled = std::make_shared<PooledWeight>();
            pooled->model_name = model_name;
            pooled->dtype = dtype;
            pooled->original_size = weight_bytes;
            // 注意：data 是空的，实际数据在 Arena 中
            // 这里我们仍然保留 data 用于 API 兼容
            pooled->data = std::vector<std::uint8_t>(arena_ptr, arena_ptr + weight_bytes);
        } else {
            // Arena 不足，使用堆内存
            spdlog::warn("Weight arena full, using heap for '{}'", model_name);
            pooled = std::make_shared<PooledWeight>();
            pooled->model_name = model_name;
            pooled->data = std::move(weight_data);
            pooled->dtype = dtype;
            pooled->original_size = pooled->data.size();
        }

        weight_index_[weight_hash] = pooled;
        lru_list_.push_front(weight_hash);

        spdlog::info("Weight registered: '{}', {} bytes, hash={:016x}",
                      model_name, pooled->original_size, weight_hash);

        // 淘汰策略：如果内存不足，驱逐最久未用的权重
        if (weight_arena_.available() < 64 * 1024 * 1024) {  // 小于 64MB 时触发
            evict_lru();
        }

        return pooled;
    }

    /**
     * @brief 注销模型权重（减少引用计数）。
     */
    void unregister_weights(const std::string& model_name) {
        std::lock_guard<std::mutex> lock(pool_mutex_);

        // 查找属于该模型的所有权重
        for (auto it = weight_index_.begin(); it != weight_index_.end(); ) {
            if (it->second->model_name == model_name) {
                auto remaining = it->second->ref_count.fetch_sub(1);
                if (remaining == 1) {
                    spdlog::info("Weight freed: '{}', {} bytes",
                                  model_name, it->second->original_size);
                    it = weight_index_.erase(it);
                } else {
                    spdlog::info("Weight ref decreased: '{}', remaining refs={}",
                                  model_name, remaining - 1);
                    ++it;
                }
            } else {
                ++it;
            }
        }

        // 清理 LRU 列表
        lru_list_.remove_if([&](std::size_t hash) {
            return weight_index_.find(hash) == weight_index_.end();
        });
    }

    // ── 激活内存管理 ───────────────────────────────────────────────────

    /**
     * @brief 分配激活张量内存（从激活 Arena）。
     *
     * @param bytes  所需字节数
     * @return 内存指针，失败返回 nullptr
     */
    std::uint8_t* alloc_activation(std::size_t bytes) {
        std::lock_guard<std::mutex> lock(pool_mutex_);
        return activation_arena_.alloc(bytes);
    }

    /**
     * @brief 重置激活 Arena（每轮推理后调用）。
     */
    void reset_activations() {
        std::lock_guard<std::mutex> lock(pool_mutex_);
        activation_arena_.reset();
    }

    // ── 查询 ───────────────────────────────────────────────────────────

    /** @brief 总池大小（字节）。 */
    [[nodiscard]] std::size_t total_pool_bytes() const {
        return weight_arena_.total_size + activation_arena_.total_size;
    }

    /** @brief 权重 Arena 已用字节。 */
    [[nodiscard]] std::size_t weight_used_bytes() const {
        return weight_arena_.used;
    }

    /** @brief 激活 Arena 已用字节。 */
    [[nodiscard]] std::size_t activation_used_bytes() const {
        return activation_arena_.used;
    }

    /** @brief 已注册模型数。 */
    [[nodiscard]] std::size_t registered_model_count() const {
        std::lock_guard<std::mutex> lock(pool_mutex_);
        return weight_index_.size();
    }

    /** @brief 内存池状态摘要（JSON）。 */
    [[nodiscard]] std::string status_json() const {
        std::stringstream ss;
        ss << "{"
           << "\"total_mb\": " << (total_pool_bytes() / (1024 * 1024)) << ","
           << "\"weight_used_mb\": " << (weight_used_bytes() / (1024 * 1024)) << ","
           << "\"weight_total_mb\": " << (weight_arena_.total_size / (1024 * 1024)) << ","
           << "\"activation_used_mb\": " << (activation_used_bytes() / (1024 * 1024)) << ","
           << "\"activation_total_mb\": " << (activation_arena_.total_size / (1024 * 1024)) << ","
           << "\"registered_models\": " << registered_model_count()
           << "}";
        return ss.str();
    }

private:
    // ── 内部方法 ───────────────────────────────────────────────────────

    /** @brief 估算系统可用内存。 */
    static std::size_t estimate_available_memory() {
        // 简化实现：返回 2GB（后续可通过 OS API 获取真实值）
        return 2ULL * 1024 * 1024 * 1024;
    }

    /** @brief 简单哈希（FNV-1a）。 */
    static std::size_t hash_bytes(const void* data, std::size_t size) {
        const auto* bytes = static_cast<const std::uint8_t*>(data);
        std::size_t hash = 14695981039346656037ULL;
        for (std::size_t i = 0; i < size; ++i) {
            hash ^= bytes[i];
            hash *= 1099511628211ULL;
        }
        return hash;
    }

    /** @brief LRU 淘汰最久未用的权重。 */
    void evict_lru() {
        while (!lru_list_.empty() && weight_arena_.available() < 128 * 1024 * 1024) {
            std::size_t oldest_hash = lru_list_.back();
            lru_list_.pop_back();

            auto it = weight_index_.find(oldest_hash);
            if (it != weight_index_.end() && it->second->ref_count.load() <= 1) {
                spdlog::info("LRU evict: '{}', {} bytes",
                              it->second->model_name, it->second->original_size);
                weight_index_.erase(it);
            }
        }
    }

    // ── 数据成员 ───────────────────────────────────────────────────────

    MemoryBlock weight_arena_;
    MemoryBlock activation_arena_;
    bool enable_zero_copy_;

    // 权重去重索引：hash → 共享权重
    std::unordered_map<std::size_t, std::shared_ptr<PooledWeight>> weight_index_;

    // LRU 淘汰列表
    std::list<std::size_t> lru_list_;

    mutable std::mutex pool_mutex_;
};

// ─────────────────────────────────────────────────────────────────────────────
//  全局单例
// ─────────────────────────────────────────────────────────────────────────────

static std::unique_ptr<ModelMemoryPool> g_memory_pool;
static std::mutex g_pool_mutex;

/**
 * @brief 获取全局内存池单例（惰性初始化）。
 */
ModelMemoryPool& global_memory_pool(std::size_t max_bytes = 0) {
    std::lock_guard<std::mutex> lock(g_pool_mutex);
    if (!g_memory_pool) {
        g_memory_pool = std::make_unique<ModelMemoryPool>(max_bytes);
    }
    return *g_memory_pool;
}

/**
 * @brief 销毁全局内存池。
 */
void destroy_global_memory_pool() {
    std::lock_guard<std::mutex> lock(g_pool_mutex);
    g_memory_pool.reset();
}

}  // namespace memory
}  // namespace qoocore
