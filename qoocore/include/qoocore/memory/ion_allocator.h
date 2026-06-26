/**
 * @file ion_allocator.h
 * @brief ION/DMA-BUF 零拷贝内存分配器接口
 *
 * 提供跨硬件（相机 ISP → NPU → GPU）零拷贝内存共享能力。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "core.h"

#include <cstdint>
#include <cstddef>

namespace qoocore {
namespace memory {

// ── IonFlags ────────────────────────────────────────────────────────
enum class IonFlags : std::uint32_t {
    CACHED      = (1u << 0),  // CPU 可缓存
    SECURE      = (1u << 1),  // 安全内存（TEE）
    VIDEO_FRAME = (1u << 2),  // 视频帧（ISP 友好）
};

// ── IonBuffer ────────────────────────────────────────────────────────
struct IonBuffer {
    int        fd      = -1;   // DMA-BUF 文件描述符（可共享）
    void*      cpu_ptr = nullptr;
    std::size_t size    = 0;
    int        ion_fd = -1;   // ION 设备 fd（用于释放）
};

// ── IonAllocator ─────────────────────────────────────────────────────
class IonAllocator {
public:
    /**
     * @brief 分配 ION/DMA-BUF 内存。
     * @param size   字节数（会按页对齐）
     * @param align  对齐字节数（0 = 默认 4096）
     * @param flags  分配标志（IonFlags 位掩码）
     */
    static Result<IonBuffer> alloc(std::size_t size,
                                    std::size_t align = 4096,
                                    IonFlags flags = IonFlags::CACHED);

    /**
     * @brief 释放 ION/DMA-BUF 内存。
     */
    static void free(IonBuffer& buffer);

    /**
     * @brief 获取可共享的文件描述符。
     * @note  返回的 fd 可在进程间传递（Unix domain socket）。
     */
    static Result<int> share_fd(const IonBuffer& buffer);

    /**
     * @brief 从共享 fd 导入（另一进程调用）。
     */
    static Result<IonBuffer> import_fd(int fd);

    /**
     * @brief CPU 映射（mmap）。
     */
    static Result<void*> map(const IonBuffer& buffer);

    /**
     * @brief Cache 同步（CPU 与硬件 DMA 之间）。
     */
    static Result<void> cache_flush(const IonBuffer& buffer);
    static Result<void> cache_invalidate(const IonBuffer& buffer);
};

}  // namespace memory
}  // namespace qoocore
