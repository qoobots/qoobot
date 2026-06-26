/**
 * @file ion_allocator.cpp
 * @brief ION/DMA-BUF 零拷贝内存分配器实现骨架
 *
 * ION（Input/Output Memory Allocator）是 Linux 提供的一块连续物理内存
 * 分配接口，多个硬件（相机 ISP、NPU、GPU）可共享同一块物理内存，
 * 避免 memcpy，实现真正的零拷贝流水线。
 *
 * 支持平台：
 *   - Linux：/dev/ion 设备（Android / 嵌入式 Linux）
 *   - Linux：DMA-BUF 子系统（现代 Linux 内核）
 *   - 未来：Windows：需要使用 WDM 或 DirectX Shared Memory
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/memory/ion_allocator.h"

#ifdef QOOCORE_ENABLE_ION

#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <cstring>
#include <string>

// ── ION 内核接口定义（避免依赖 Linux 内核头文件）─────────────
// 这些定义需与内核 ion.h 保持一致
#define ION_IOC_MAGIC 'I'

struct ion_allocation_data {
    std::size_t len;
    std::size_t align;
    unsigned int heap_id_mask;
    unsigned int flags;
    std::intptr_t handle;
};

#define ION_IOC_ALLOC _IOWR(ION_IOC_MAGIC, 0, struct ion_allocation_data)
#define ION_IOC_MAP   _IOWR(ION_IOC_MAGIC, 2, struct ion_allocation_data)
#define ION_IOC_SHARE _IOWR(ION_IOC_MAGIC, 4, int)

namespace qoocore {
namespace memory {

// ── IonAllocator 实现 ────────────────────────────────────────────────
class IonAllocator::Impl {
public:
    Impl() : ion_fd(-1) {}
    int ion_fd;
};

Result<IonBuffer> IonAllocator::alloc(std::size_t size,
                                        std::size_t align,
                                        IonFlags flags) {
    (void)flags;

    // 1. 打开 ION 设备
    int ion_fd = open("/dev/ion", O_RDWR);
    if (ion_fd < 0) {
        return Error(ErrorCode::ION_ALLOC_FAILED,
                     "Failed to open /dev/ion: " + std::string(strerror(errno)));
    }

    // 2. 分配 ION 内存
    struct ion_allocation_data alloc_data{};
    alloc_data.len   = size;
    alloc_data.align = (align == 0 ? 4096 : align);
    alloc_data.heap_id_mask = 1;  // 默认 heap
    alloc_data.flags = 0;

    int ret = ioctl(ion_fd, ION_IOC_ALLOC, &alloc_data);
    if (ret < 0) {
        close(ion_fd);
        return Error(ErrorCode::ION_ALLOC_FAILED,
                     "ION allocation failed (size=" + std::to_string(size) + "): " +
                     std::string(strerror(errno)));
    }

    // 3. 获取文件描述符（用于共享）
    int share_fd = -1;
    ret = ioctl(ion_fd, ION_IOC_SHARE, &share_fd);
    if (ret < 0) {
        // 新版内核使用 DMA-BUF
        // TODO: 尝试 DMA-BUF 接口
        close(ion_fd);
        return Error(ErrorCode::ION_ALLOC_FAILED,
                     "ION share failed: " + std::string(strerror(errno)));
    }

    // 4. mmap 到用户空间（可选，若需要 CPU 访问）
    void* cpu_ptr = mmap(nullptr, size, PROT_READ | PROT_WRITE,
                          MAP_SHARED, share_fd, 0);
    if (cpu_ptr == MAP_FAILED) {
        close(share_fd);
        close(ion_fd);
        return Error(ErrorCode::ION_ALLOC_FAILED,
                     "ION mmap failed: " + std::string(strerror(errno)));
    }

    IonBuffer buffer;
    buffer.fd       = share_fd;
    buffer.cpu_ptr  = cpu_ptr;
    buffer.size     = size;
    buffer.ion_fd  = ion_fd;

    spdlog::debug("ION alloc: size={} bytes, fd={}", size, share_fd);
    return buffer;
}

void IonAllocator::free(IonBuffer& buffer) {
    if (buffer.cpu_ptr && buffer.cpu_ptr != MAP_FAILED) {
        munmap(buffer.cpu_ptr, buffer.size);
        buffer.cpu_ptr = nullptr;
    }
    if (buffer.fd >= 0) {
        close(buffer.fd);
        buffer.fd = -1;
    }
    if (buffer.ion_fd >= 0) {
        close(buffer.ion_fd);
        buffer.ion_fd = -1;
    }
    buffer.size = 0;
}

Result<int> IonAllocator::share_fd(const IonBuffer& buffer) {
    if (buffer.fd < 0) {
        return Error(ErrorCode::INVALID_ARGUMENT, "Invalid IonBuffer (fd < 0)");
    }
    // 文件描述符可通过 Unix domain socket 发送给其他进程
    // 此处返回文件描述符的副本（用于跨进程共享）
    return dup(buffer.fd);
}

}  // namespace memory
}  // namespace qoocore

#else  // !QOOCORE_ENABLE_ION

// 未启用 ION 支持时，提供空实现
namespace qoocore {
namespace memory {

Result<IonBuffer> IonAllocator::alloc(std::size_t size,
                                        std::size_t align,
                                        IonFlags flags) {
    (void)size; (void)align; (void)flags;
    return Error(ErrorCode::NOT_IMPLEMENTED,
                 "ION/DMA-BUF support not enabled. "
                 "Compile with -DQOOCORE_ENABLE_ION=ON");
}

void IonAllocator::free(IonBuffer& buffer) {
    (void)buffer;
}

Result<int> IonAllocator::share_fd(const IonBuffer& buffer) {
    (void)buffer;
    return Error(ErrorCode::NOT_IMPLEMENTED);
}

}  // namespace memory
}  // namespace qoocore

#endif  // QOOCORE_ENABLE_ION
