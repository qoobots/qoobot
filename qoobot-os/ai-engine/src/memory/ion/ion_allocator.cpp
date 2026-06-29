/**
 * @file ion_allocator.cpp
 * @brief ION/DMA-BUF 零拷贝内存分配器实现
 *
 * 提供跨硬件（相机 ISP → NPU → GPU）零拷贝内存共享能力。
 *
 * 实现策略：
 *   - Linux/Android：使用 ION ioctl 或 dma_heap（Linux 5.10+）
 *   - 其他平台（Windows/macOS/无 ION）：回退到普通 malloc/mmap
 *
 * 零拷贝是机器人推理的关键优化——避免 CPU 在硬件间搬运数据。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/memory/ion_allocator.h"

#include <spdlog/spdlog.h>
#include <algorithm>
#include <cstring>
#include <mutex>

#ifdef __linux__
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

// ION ioctl 定义（Linux kernel ION API）
#ifndef ION_IOC_ALLOC
#define ION_IOC_MAGIC 'I'
#define ION_IOC_ALLOC    _IOWR(ION_IOC_MAGIC, 0, struct ion_allocation_data)
#define ION_IOC_FREE     _IOW(ION_IOC_MAGIC, 1, struct ion_handle_data)
#define ION_IOC_SHARE    _IOWR(ION_IOC_MAGIC, 4, struct ion_fd_data)

struct ion_allocation_data {
    std::size_t len;
    std::size_t align;
    unsigned int heap_id_mask;
    unsigned int flags;
    int handle;
};

struct ion_handle_data {
    int handle;
};

struct ion_fd_data {
    int handle;
    int fd;
};

// 常见 heap ID
#define ION_HEAP_SYSTEM_MASK        (1 << 0)
#define ION_HEAP_SYSTEM_CONTIG_MASK (1 << 1)
#define ION_HEAP_CARVEOUT_MASK      (1 << 2)
#endif

// dma_heap (Linux 5.10+) 路径
static constexpr const char* DMA_HEAP_PATH = "/dev/dma_heap/";

#endif  // __linux__

namespace qoocore {
namespace memory {

// ── 对齐辅助 ──────────────────────────────────────────────────────────
static std::size_t align_up(std::size_t size, std::size_t align) {
    if (align == 0) align = 4096;
    return (size + align - 1) & ~(align - 1);
}

// ── ION 实现（Linux）─────────────────────────────────────────────────
#ifdef __linux__

static int open_ion_device() {
    // 优先尝试 dma_heap（Linux 5.10+）
    // 然后回退到传统 /dev/ion
    static const char* paths[] = {
        "/dev/ion",
        "/dev/dma_heap/system",
        "/dev/dma_heap/system-uncached",
    };

    for (const char* path : paths) {
        int fd = ::open(path, O_RDWR);
        if (fd >= 0) {
            spdlog::debug("ION device opened: {}", path);
            return fd;
        }
    }

    spdlog::warn("No ION device found (not an embedded platform?)");
    return -1;
}

static int s_ion_fd = -1;
static std::once_flag s_ion_init_flag;

static int get_ion_fd() {
    std::call_once(s_ion_init_flag, []() {
        s_ion_fd = open_ion_device();
    });
    return s_ion_fd;
}

#endif  // __linux__

// ── IonAllocator::alloc ───────────────────────────────────────────────
Result<IonBuffer> IonAllocator::alloc(std::size_t size,
                                        std::size_t align,
                                        IonFlags flags) {
    if (size == 0) {
        return Error<IonBuffer>(ErrorCode::INVALID_ARGUMENT, "Zero-size ION allocation");
    }

    size = align_up(size, align);

#ifdef __linux__
    int ion_fd = get_ion_fd();

    if (ion_fd >= 0) {
        // ── 使用 ION 分配 ─────────────────────────────────────────
        ion_allocation_data alloc_data = {};
        alloc_data.len = size;
        alloc_data.align = align;
        alloc_data.heap_id_mask = ION_HEAP_SYSTEM_MASK;
        alloc_data.flags = 0;

        if (flags == IonFlags::CACHED) {
            alloc_data.flags |= (1u << 0);  // ION_FLAG_CACHED
        }

        if (::ioctl(ion_fd, ION_IOC_ALLOC, &alloc_data) < 0) {
            spdlog::warn("ION allocation failed (size={}): {} (errno={}), falling back to malloc",
                          size, strerror(errno), errno);
            goto fallback;
        }

        // 获取 DMA-BUF fd
        ion_fd_data fd_data = {};
        fd_data.handle = alloc_data.handle;
        if (::ioctl(ion_fd, ION_IOC_SHARE, &fd_data) < 0) {
            // 释放 ION handle
            ion_handle_data free_data = {alloc_data.handle};
            ::ioctl(ion_fd, ION_IOC_FREE, &free_data);
            spdlog::warn("ION share failed, falling back to malloc");
            goto fallback;
        }

        // mmap 到用户空间
        void* ptr = ::mmap(nullptr, size, PROT_READ | PROT_WRITE,
                           MAP_SHARED, fd_data.fd, 0);
        if (ptr == MAP_FAILED) {
            ::close(fd_data.fd);
            ion_handle_data free_data = {alloc_data.handle};
            ::ioctl(ion_fd, ION_IOC_FREE, &free_data);
            spdlog::warn("ION mmap failed, falling back to malloc");
            goto fallback;
        }

        IonBuffer buf;
        buf.fd = fd_data.fd;
        buf.cpu_ptr = ptr;
        buf.size = size;
        buf.ion_fd = ion_fd;

        spdlog::debug("ION allocated: {} bytes, fd={}, ptr={}",
                       size, buf.fd, buf.cpu_ptr);
        return buf;
    }
#endif  // __linux__

fallback:
    // ── Fallback：普通 malloc ─────────────────────────────────────
    {
        void* ptr = std::aligned_alloc(std::max(align, alignof(std::max_align_t)), size);
        if (!ptr) {
            return Error<IonBuffer>(ErrorCode::OUT_OF_MEMORY,
                                     "Failed to allocate " + std::to_string(size) + " bytes");
        }

        IonBuffer buf;
        buf.fd = -1;
        buf.cpu_ptr = ptr;
        buf.size = size;
        buf.ion_fd = -1;

        spdlog::debug("Fallback malloc allocated: {} bytes, ptr={}", size, ptr);
        return buf;
    }
}

// ── IonAllocator::free ────────────────────────────────────────────────
void IonAllocator::free(IonBuffer& buffer) {
    if (!buffer.cpu_ptr) return;

#ifdef __linux__
    if (buffer.fd >= 0) {
        // ION 分配：munmap + close fd
        ::munmap(buffer.cpu_ptr, buffer.size);
        ::close(buffer.fd);
        spdlog::debug("ION freed: {} bytes, fd={}", buffer.size, buffer.fd);
    } else
#endif
    {
        // Fallback：free
        std::free(buffer.cpu_ptr);
        spdlog::debug("Fallback freed: {} bytes", buffer.size);
    }

    buffer.cpu_ptr = nullptr;
    buffer.fd = -1;
    buffer.size = 0;
    buffer.ion_fd = -1;
}

// ── IonAllocator::share_fd ────────────────────────────────────────────
Result<int> IonAllocator::share_fd(const IonBuffer& buffer) {
    if (buffer.fd < 0) {
        return Error<int>(ErrorCode::DMA_BUF_ERROR,
                           "Buffer does not have a shareable fd (not ION-allocated)");
    }
    return buffer.fd;
}

// ── IonAllocator::import_fd ───────────────────────────────────────────
Result<IonBuffer> IonAllocator::import_fd(int fd) {
    if (fd < 0) {
        return Error<IonBuffer>(ErrorCode::INVALID_ARGUMENT, "Invalid fd");
    }

#ifdef __linux__
    // 获取 DMA-BUF 大小
    off_t size = ::lseek(fd, 0, SEEK_END);
    if (size < 0) {
        return Error<IonBuffer>(ErrorCode::DMA_BUF_ERROR,
                                 "Cannot determine DMA-BUF size (fd=" +
                                 std::to_string(fd) + ")");
    }
    ::lseek(fd, 0, SEEK_SET);

    void* ptr = ::mmap(nullptr, static_cast<std::size_t>(size),
                       PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (ptr == MAP_FAILED) {
        return Error<IonBuffer>(ErrorCode::DMA_BUF_ERROR,
                                 "mmap failed for imported fd " +
                                 std::to_string(fd) + ": " +
                                 strerror(errno));
    }

    IonBuffer buf;
    buf.fd = fd;
    buf.cpu_ptr = ptr;
    buf.size = static_cast<std::size_t>(size);
    buf.ion_fd = -1;  // 导入的 fd 不管理 ION 设备

    spdlog::debug("ION buffer imported: fd={}, size={}, ptr={}", fd, size, ptr);
    return buf;
#else
    return Error<IonBuffer>(ErrorCode::NOT_IMPLEMENTED,
                             "DMA-BUF import not supported on this platform");
#endif
}

// ── IonAllocator::map ─────────────────────────────────────────────────
Result<void*> IonAllocator::map(const IonBuffer& buffer) {
    if (buffer.cpu_ptr) return buffer.cpu_ptr;

    if (buffer.fd < 0) {
        return Error<void*>(ErrorCode::INVALID_ARGUMENT,
                             "Cannot map: buffer has no fd");
    }

#ifdef __linux__
    void* ptr = ::mmap(nullptr, buffer.size, PROT_READ | PROT_WRITE,
                       MAP_SHARED, buffer.fd, 0);
    if (ptr == MAP_FAILED) {
        return Error<void*>(ErrorCode::DMA_BUF_ERROR,
                             "mmap failed: " + std::string(strerror(errno)));
    }
    return ptr;
#else
    return Error<void*>(ErrorCode::NOT_IMPLEMENTED,
                         "mmap not supported on this platform");
#endif
}

// ── IonAllocator::cache_flush / cache_invalidate ──────────────────────
Result<void> IonAllocator::cache_flush(const IonBuffer& buffer) {
    if (!buffer.cpu_ptr) {
        return Error(ErrorCode::INVALID_ARGUMENT, "Null buffer");
    }

#ifdef __linux__
    // 使用 __builtin___clear_cache 或 cacheflush syscall
    // 对于 DMA，通常使用 DMA-BUF sync ioctl
    // 简化实现：msync
    if (::msync(buffer.cpu_ptr, buffer.size, MS_SYNC) < 0) {
        spdlog::warn("msync failed during cache_flush: {}", strerror(errno));
    }
#endif

    // Fallback：无操作（malloc 内存不需要 flush）
    return Ok();
}

Result<void> IonAllocator::cache_invalidate(const IonBuffer& buffer) {
    if (!buffer.cpu_ptr) {
        return Error(ErrorCode::INVALID_ARGUMENT, "Null buffer");
    }

#ifdef __linux__
    if (::msync(buffer.cpu_ptr, buffer.size, MS_INVALIDATE) < 0) {
        spdlog::warn("msync failed during cache_invalidate: {}", strerror(errno));
    }
#endif

    return Ok();
}

}  // namespace memory
}  // namespace qoocore
