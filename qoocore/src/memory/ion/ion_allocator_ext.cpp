/**
 * @file ion_allocator_ext.cpp
 * @brief ION/DMA-BUF 零拷贝扩展 — 跨硬件数据流 + 内存池 + DMA-BUF Heap
 *
 * 在 ion_allocator.cpp 基础上，提供完整的零拷贝跨硬件内存共享方案：
 *
 *   1. Camera ISP → NPU：相机原始帧直接喂入 NPU（跳过 CPU 拷贝）
 *   2. NPU → GPU：NPU 输出直接作为 GPU 后续处理的输入
 *   3. DMA-BUF Heap Allocator（Linux 5.10+）：统一跨设备内存分配
 *   4. 引用计数内存管理：跨进程安全共享
 *   5. 零拷贝环形缓冲：多帧流水线不产生额外拷贝
 *
 * 数据流示例：
 *   Camera Sensor → ISP → ION buffer → NPU (推理) → ION buffer → GPU (后处理) → Display
 *
 * @copyright QooBot Project
 * @version 0.3.0
 */

#include "qoocore/memory/ion_allocator.h"
#include "qoocore/core.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <map>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#ifdef __linux__
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

// DMA-BUF Heap ioctl (Linux 5.10+)
#ifndef DMA_HEAP_IOC_ALLOC
#define DMA_HEAP_IOC_MAGIC 'H'
#define DMA_HEAP_IOC_ALLOC _IOWR(DMA_HEAP_IOC_MAGIC, 0, struct dma_heap_allocation_data)

struct dma_heap_allocation_data {
    uint64_t len;
    uint32_t fd;
    uint32_t fd_flags;
    uint64_t heap_flags;
};
#endif

#endif // __linux__

namespace qoocore {
namespace memory {

// ═══════════════════════════════════════════════════════════════════════════════
// 1. DMA-BUF Heap 分配器（Linux 5.10+）
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief DMA-BUF Heap 类型
 *
 * Linux 5.10+ 将传统 ION 重构为 DMA-BUF Heap 子系统。
 * 每个 heap 有特定的分配特性。
 */
enum class DmaHeapType : uint8_t {
    SYSTEM,              ///< 普通系统内存（默认，所有设备可访问）
    SYSTEM_UNCACHED,     ///< 非缓存系统内存（更快但需显式同步）
    CMA,                 ///< Contiguous Memory Allocator（相机/显示需要）
    CARVEOUT,            ///< 专用预留内存（NPU/GPU 专用）
};

/**
 * @brief DMA-BUF Heap 分配器
 *
 * 替代传统 /dev/ion，使用 /dev/dma_heap/* 接口。
 */
class DmaHeapAllocator {
public:
    explicit DmaHeapAllocator(DmaHeapType heap_type = DmaHeapType::SYSTEM)
        : heap_type_(heap_type) {
        init();
    }

    ~DmaHeapAllocator() {
        if (heap_fd_ >= 0) {
            ::close(heap_fd_);
            heap_fd_ = -1;
        }
    }

    /**
     * @brief 分配 DMA-BUF 缓冲区。
     *
     * @param size  分配大小（字节）
     * @param align 对齐要求（0 = 页对齐）
     * @return 成功返回 IonBuffer（fd 已设置，cpu_ptr 需通过 map() 获取）
     */
    Result<IonBuffer> alloc(size_t size, size_t align = 0) {
        if (!available_) {
            return Error<IonBuffer>(ErrorCode::ION_ALLOC_FAILED,
                "DMA-BUF Heap not available on this system");
        }

        size_t aligned_size = align_up(size, std::max(align, page_size_));

#ifdef __linux__
        dma_heap_allocation_data alloc_data = {};
        alloc_data.len = aligned_size;
        alloc_data.fd_flags = O_RDWR | O_CLOEXEC;
        alloc_data.heap_flags = 0;

        if (::ioctl(heap_fd_, DMA_HEAP_IOC_ALLOC, &alloc_data) < 0) {
            return Error<IonBuffer>(ErrorCode::ION_ALLOC_FAILED,
                "DMA-BUF Heap allocation failed: " +
                std::string(strerror(errno)));
        }

        IonBuffer buf;
        buf.fd = static_cast<int>(alloc_data.fd);
        buf.size = aligned_size;
        buf.cpu_ptr = nullptr;  // 延迟 mmap
        buf.ion_fd = heap_fd_;

        return Ok(std::move(buf));
#else
        return Error<IonBuffer>(ErrorCode::NOT_IMPLEMENTED, "Not on Linux");
#endif
    }

    /**
     * @brief 检查 DMA-BUF Heap 是否可用。
     */
    [[nodiscard]] bool available() const { return available_; }

    /**
     * @brief 获取页大小。
     */
    [[nodiscard]] size_t page_size() const { return page_size_; }

private:
    DmaHeapType heap_type_;
    int heap_fd_{-1};
    bool available_{false};
    size_t page_size_{4096};

    void init() {
#ifdef __linux__
        page_size_ = static_cast<size_t>(::sysconf(_SC_PAGESIZE));

        const char* heap_path = nullptr;
        switch (heap_type_) {
            case DmaHeapType::SYSTEM:
                heap_path = "/dev/dma_heap/system";
                break;
            case DmaHeapType::SYSTEM_UNCACHED:
                heap_path = "/dev/dma_heap/system-uncached";
                break;
            case DmaHeapType::CMA:
                heap_path = "/dev/dma_heap/linux,cma";
                break;
            case DmaHeapType::CARVEOUT:
                heap_path = "/dev/dma_heap/reserved";
                break;
        }

        heap_fd_ = ::open(heap_path, O_RDWR | O_CLOEXEC);
        available_ = (heap_fd_ >= 0);
#endif
    }

    static size_t align_up(size_t size, size_t align) {
        if (align == 0) align = 4096;
        return (size + align - 1) & ~(align - 1);
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 2. 零拷贝跨硬件数据流管理
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 硬件数据流节点类型
 */
enum class DataFlowNode : uint8_t {
    CAMERA_ISP,     ///< 相机图像信号处理器
    LIDAR_SENSOR,   ///< LiDAR 传感器
    NPU,            ///< NPU 推理引擎
    GPU,            ///< GPU 渲染/计算
    DSP,            ///< DSP 信号处理
    CPU,            ///< CPU（非零拷贝回退）
    DISPLAY,        ///< 显示输出
    ENCODER,        ///< 视频编码器
};

/**
 * @brief 数据流缓冲区引用
 *
 * 使用引用计数管理 DMA-BUF 的生命周期。
 * 多个硬件节点可以同时引用同一个 DMA-BUF fd。
 */
class DmaBufRef {
public:
    DmaBufRef() = default;

    explicit DmaBufRef(IonBuffer buf, DataFlowNode producer)
        : buf_(std::move(buf)), producer_(producer) {
        ref_count_.store(1, std::memory_order_release);
    }

    // 禁止拷贝（DMA-BUF 所有权唯一）
    DmaBufRef(const DmaBufRef&) = delete;
    DmaBufRef& operator=(const DmaBufRef&) = delete;

    // 移动语义
    DmaBufRef(DmaBufRef&& other) noexcept
        : buf_(std::move(other.buf_)), producer_(other.producer_) {
        ref_count_.store(other.ref_count_.load(std::memory_order_acquire),
                         std::memory_order_release);
        other.ref_count_.store(0, std::memory_order_release);
    }

    ~DmaBufRef() { release(); }

    /**
     * @brief 增加引用计数（新消费者获取）。
     */
    void acquire() {
        ref_count_.fetch_add(1, std::memory_order_acq_rel);
    }

    /**
     * @brief 释放一个引用。
     *
     * 当引用计数归零时，自动释放 DMA-BUF。
     */
    void release() {
        if (ref_count_.fetch_sub(1, std::memory_order_acq_rel) == 1) {
            IonAllocator::free(buf_);
        }
    }

    [[nodiscard]] int fd() const { return buf_.fd; }
    [[nodiscard]] void* cpu_ptr() const { return buf_.cpu_ptr; }
    [[nodiscard]] size_t size() const { return buf_.size; }
    [[nodiscard]] DataFlowNode producer() const { return producer_; }
    [[nodiscard]] int32_t ref_count() const {
        return ref_count_.load(std::memory_order_acquire);
    }

    /**
     * @brief 导出 DMA-BUF fd（用于跨进程传递）。
     *
     * 注意：调用者需自行管理 fd 生命周期。
     */
    [[nodiscard]] int export_fd() const {
        if (buf_.fd < 0) return -1;
        return ::dup(buf_.fd);
    }

private:
    IonBuffer buf_;
    DataFlowNode producer_{DataFlowNode::CPU};
    std::atomic<int32_t> ref_count_{0};
};

/**
 * @brief 跨硬件零拷贝数据流管道
 *
 * 管理从传感器到 NPU 再到 GPU 的完整数据流。
 * 所有节点共享同一块 DMA-BUF 内存，避免 CPU 拷贝。
 */
class ZeroCopyPipeline {
public:
    /**
     * @brief 管道阶段描述
     */
    struct Stage {
        DataFlowNode node;
        std::string name;
        size_t buffer_count{3};  ///< 该阶段的缓冲数量（流水线深度）
    };

    /**
     * @brief 创建零拷贝管道
     *
     * @param stages  数据流阶段（按顺序）
     * @param buffer_size 每个缓冲区大小
     *
     * 示例：
     *   ZeroCopyPipeline pipeline({
     *       {CAMERA_ISP, "camera", 4},
     *       {NPU, "detection", 3},
     *       {GPU, "render", 2},
     *   }, 1920 * 1080 * 3);
     */
    ZeroCopyPipeline(const std::vector<Stage>& stages, size_t buffer_size)
        : stages_(stages), buffer_size_(buffer_size) {
        // 预分配缓冲池
        DmaHeapAllocator allocator(DmaHeapType::CMA);

        for (size_t i = 0; i < stages.size(); ++i) {
            auto& stage = stages_[i];

            for (size_t b = 0; b < stage.buffer_count; ++b) {
                auto result = allocator.alloc(buffer_size, 0);
                if (result.ok()) {
                    auto ref = std::make_shared<DmaBufRef>(
                        std::move(result).value(), stage.node);
                    free_buffers_[i].push_back(ref);
                }
            }
        }
    }

    /**
     * @brief 获取一个可用的缓冲区（用于生产者写入）。
     *
     * @param stage_idx 阶段索引
     * @return 缓冲区引用（使用完毕自动归还）
     */
    std::shared_ptr<DmaBufRef> acquire_buffer(size_t stage_idx) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto& free_list = free_buffers_[stage_idx];
        if (free_list.empty()) {
            // 所有缓冲都在使用中——需要等待或分配新缓冲
            return nullptr;
        }

        auto buf = free_list.front();
        free_list.pop_front();
        buf->acquire();
        return buf;
    }

    /**
     * @brief 将一个缓冲区从阶段 A 传递到阶段 B（零拷贝！）
     *
     * 这是整个零拷贝管道的核心——仅传递 fd 引用，不拷贝数据。
     */
    Result<void> forward_buffer(
        std::shared_ptr<DmaBufRef> buffer,
        size_t from_stage, size_t to_stage) {

        if (!buffer || from_stage >= stages_.size() || to_stage >= stages_.size()) {
            return Error(ErrorCode::INVALID_ARGUMENT, "Invalid stage indices");
        }

        // 跨进程传递：导出 fd → 目标进程通过 fd 导入
        int exported_fd = buffer->export_fd();
        if (exported_fd < 0) {
            return Error(ErrorCode::DMA_BUF_ERROR, "Failed to export DMA-BUF fd");
        }

        // TODO: 通过 Unix Domain Socket 将 fd 发送给目标进程
        // sendmsg() + SCM_RIGHTS

        {
            std::lock_guard<std::mutex> lock(mutex_);
            in_flight_buffers_[to_stage].push_back(buffer);
        }

        return Ok();
    }

    /**
     * @brief 释放已处理完的缓冲区（归还到空闲池）。
     */
    void release_buffer(std::shared_ptr<DmaBufRef> buffer, size_t stage_idx) {
        buffer->release();

        std::lock_guard<std::mutex> lock(mutex_);
        // 从 in_flight 移除
        auto& inflight = in_flight_buffers_[stage_idx];
        auto it = std::find(inflight.begin(), inflight.end(), buffer);
        if (it != inflight.end()) {
            inflight.erase(it);
        }

        // 归还到空闲池
        free_buffers_[stage_idx].push_back(buffer);
    }

    /**
     * @brief 获取管道统计。
     */
    struct PipelineStats {
        size_t total_buffers;
        size_t free_buffers;
        size_t in_flight;
    };

    PipelineStats stats(size_t stage_idx) const {
        std::lock_guard<std::mutex> lock(mutex_);
        PipelineStats s;
        s.total_buffers = stages_[stage_idx].buffer_count;
        s.free_buffers = free_buffers_[stage_idx].size();
        s.in_flight = in_flight_buffers_[stage_idx].size();
        return s;
    }

private:
    std::vector<Stage> stages_;
    size_t buffer_size_;
    mutable std::mutex mutex_;
    std::map<size_t, std::deque<std::shared_ptr<DmaBufRef>>> free_buffers_;
    std::map<size_t, std::deque<std::shared_ptr<DmaBufRef>>> in_flight_buffers_;
};

// ═══════════════════════════════════════════════════════════════════════════════
// 3. 零拷贝环形缓冲（多帧流水线）
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief DMA-BUF 环形缓冲
 *
 * 用于多帧推理流水线中的零拷贝帧传递。
 * 生产者（相机）写入帧 → 消费者（NPU）读取帧，无需拷贝。
 *
 * 帧序列：Frame N → Frame N+1 → Frame N+2 → ...
 *            ↓          ↓          ↓
 *          Buffer 0   Buffer 1   Buffer 2  (环形复用)
 */
template <size_t NumBuffers = 4>
class DmaRingBuffer {
public:
    DmaRingBuffer() = default;

    /**
     * @brief 初始化环形缓冲（预分配所有 DMA-BUF）。
     */
    Result<void> init(size_t buffer_size) {
        DmaHeapAllocator allocator(DmaHeapType::CMA);

        for (size_t i = 0; i < NumBuffers; ++i) {
            auto result = allocator.alloc(buffer_size, 0);
            if (!result.ok()) {
                return Error(ErrorCode::ION_ALLOC_FAILED,
                    "Failed to allocate ring buffer " + std::to_string(i));
            }
            buffers_[i] = std::make_shared<DmaBufRef>(
                std::move(result).value(), DataFlowNode::CPU);
        }

        initialized_ = true;
        return Ok();
    }

    /**
     * @brief 获取下一个可写缓冲区（生产者调用）。
     *
     * @return 缓冲区引用；若环形缓冲已满则返回 nullptr
     */
    std::shared_ptr<DmaBufRef> acquire_write() {
        if (!initialized_) return nullptr;

        size_t next = write_idx_.load(std::memory_order_acquire);
        size_t read = read_idx_.load(std::memory_order_acquire);

        // 检查是否已满
        if ((next + 1) % NumBuffers == read) {
            return nullptr;  // 缓冲区已满
        }

        auto buf = buffers_[next];
        buf->acquire();
        write_idx_.store((next + 1) % NumBuffers, std::memory_order_release);
        return buf;
    }

    /**
     * @brief 获取下一个可读缓冲区（消费者调用）。
     *
     * @return 缓冲区引用；若无新数据则返回 nullptr
     */
    std::shared_ptr<DmaBufRef> acquire_read() {
        if (!initialized_) return nullptr;

        size_t read = read_idx_.load(std::memory_order_acquire);
        size_t write = write_idx_.load(std::memory_order_acquire);

        // 检查是否为空
        if (read == write) {
            return nullptr;  // 无新数据
        }

        auto buf = buffers_[read];
        buf->acquire();
        read_idx_.store((read + 1) % NumBuffers, std::memory_order_release);
        return buf;
    }

    /**
     * @brief 获取可用读缓冲数量。
     */
    [[nodiscard]] size_t available_read() const {
        size_t write = write_idx_.load(std::memory_order_acquire);
        size_t read = read_idx_.load(std::memory_order_acquire);
        if (write >= read) return write - read;
        return NumBuffers - read + write;
    }

    /**
     * @brief 获取可用写缓冲数量。
     */
    [[nodiscard]] size_t available_write() const {
        return NumBuffers - 1 - available_read();
    }

private:
    std::array<std::shared_ptr<DmaBufRef>, NumBuffers> buffers_;
    std::atomic<size_t> write_idx_{0};
    std::atomic<size_t> read_idx_{0};
    bool initialized_{false};
};

// ═══════════════════════════════════════════════════════════════════════════════
// 4. DMA-BUF 同步原语
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief DMA-BUF 同步操作
 *
 * 在多硬件共享 DMA-BUF 时，需要显式同步确保缓存一致性。
 *
 * DMA_BUF_IOCTL_SYNC 用于在 CPU 访问前后 flush/invalidate 缓存。
 */
class DmaBufSync {
public:
    enum class Direction {
        BEGIN_CPU_ACCESS,    ///< CPU 开始访问（需要 invalidate 缓存）
        END_CPU_ACCESS,      ///< CPU 结束访问（需要 flush 缓存）
        BEGIN_DEVICE_ACCESS, ///< 设备开始访问
        END_DEVICE_ACCESS,   ///< 设备结束访问
    };

    /**
     * @brief 同步 DMA-BUF
     *
     * @param fd    DMA-BUF 文件描述符
     * @param dir   同步方向
     * @param offset 起始偏移
     * @param length 同步长度
     */
    static Result<void> sync(int fd, Direction dir,
                              size_t offset = 0, size_t length = 0) {
#ifdef __linux__
        // DMA_BUF_IOCTL_SYNC
        struct dma_buf_sync {
            uint64_t flags;
        };

        constexpr uint64_t DMA_BUF_SYNC_READ  = 1ull << 0;
        constexpr uint64_t DMA_BUF_SYNC_WRITE = 1ull << 1;
        constexpr uint64_t DMA_BUF_SYNC_START = 1ull << 2;
        constexpr uint64_t DMA_BUF_SYNC_END   = 1ull << 3;

        dma_buf_sync sync_data = {};

        switch (dir) {
            case Direction::BEGIN_CPU_ACCESS:
                sync_data.flags = DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ | DMA_BUF_SYNC_WRITE;
                break;
            case Direction::END_CPU_ACCESS:
                sync_data.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ | DMA_BUF_SYNC_WRITE;
                break;
            case Direction::BEGIN_DEVICE_ACCESS:
                sync_data.flags = DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ | DMA_BUF_SYNC_WRITE;
                break;
            case Direction::END_DEVICE_ACCESS:
                sync_data.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ | DMA_BUF_SYNC_WRITE;
                break;
        }

        constexpr uint32_t DMA_BUF_IOCTL_SYNC = 0x40086200;
        if (::ioctl(fd, DMA_BUF_IOCTL_SYNC, &sync_data) < 0) {
            // 某些内核不支持此 ioctl，非致命
            return Ok();
        }
#endif
        return Ok();
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 5. 跨进程 DMA-BUF 传递
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief 通过 Unix Domain Socket 传递 DMA-BUF fd
 *
 * 使用 SCM_RIGHTS 在进程间共享 DMA-BUF 文件描述符。
 * 这是 Android/Linux 上标准的零拷贝跨进程通信方式。
 */
class DmaBufIPC {
public:
    /**
     * @brief 发送 DMA-BUF fd 到另一个进程。
     *
     * @param socket_fd  Unix Domain Socket 文件描述符
     * @param dma_buf_fd 要发送的 DMA-BUF fd
     * @param metadata   附加元数据（缓冲区大小、格式等）
     */
    static Result<void> send_fd(int socket_fd, int dma_buf_fd,
                                 const std::string& metadata) {
#ifdef __linux__
        struct msghdr msg = {};
        struct iovec iov;
        char cmsg_buf[CMSG_SPACE(sizeof(int))];

        // 发送元数据
        iov.iov_base = const_cast<char*>(metadata.data());
        iov.iov_len = metadata.size();

        msg.msg_iov = &iov;
        msg.msg_iovlen = 1;

        // 附加文件描述符
        msg.msg_control = cmsg_buf;
        msg.msg_controllen = sizeof(cmsg_buf);

        struct cmsghdr* cmsg = CMSG_FIRSTHDR(&msg);
        cmsg->cmsg_level = SOL_SOCKET;
        cmsg->cmsg_type = SCM_RIGHTS;
        cmsg->cmsg_len = CMSG_LEN(sizeof(int));
        *reinterpret_cast<int*>(CMSG_DATA(cmsg)) = dma_buf_fd;

        if (::sendmsg(socket_fd, &msg, 0) < 0) {
            return Error(ErrorCode::DMA_BUF_ERROR,
                "Failed to send DMA-BUF fd via socket: " +
                std::string(strerror(errno)));
        }
#endif
        return Ok();
    }

    /**
     * @brief 接收 DMA-BUF fd 从另一个进程。
     *
     * @param socket_fd  Unix Domain Socket 文件描述符
     * @param metadata   输出：接收到的元数据
     * @return 接收到的 DMA-BUF fd（-1 表示失败）
     */
    static Result<int> recv_fd(int socket_fd, std::string& metadata) {
#ifdef __linux__
        char buf[256];
        struct msghdr msg = {};
        struct iovec iov;
        char cmsg_buf[CMSG_SPACE(sizeof(int))];

        iov.iov_base = buf;
        iov.iov_len = sizeof(buf);

        msg.msg_iov = &iov;
        msg.msg_iovlen = 1;
        msg.msg_control = cmsg_buf;
        msg.msg_controllen = sizeof(cmsg_buf);

        ssize_t n = ::recvmsg(socket_fd, &msg, 0);
        if (n < 0) {
            return Error<int>(ErrorCode::DMA_BUF_ERROR,
                "Failed to receive DMA-BUF fd: " +
                std::string(strerror(errno)));
        }

        metadata.assign(buf, static_cast<size_t>(n));

        struct cmsghdr* cmsg = CMSG_FIRSTHDR(&msg);
        if (cmsg && cmsg->cmsg_level == SOL_SOCKET &&
            cmsg->cmsg_type == SCM_RIGHTS) {
            return *reinterpret_cast<int*>(CMSG_DATA(cmsg));
        }
#endif
        return Error<int>(ErrorCode::DMA_BUF_ERROR, "No fd received");
    }
};

// ═══════════════════════════════════════════════════════════════════════════════
// 6. 诊断工具
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @brief DMA-BUF 诊断信息
 */
struct DmaBufDiagnostics {
    size_t total_allocated_bytes{0};
    size_t total_free_bytes{0};
    size_t active_buffers{0};
    size_t peak_usage_bytes{0};
    std::map<std::string, size_t> per_heap_usage;
};

/**
 * @brief 收集 DMA-BUF 诊断信息
 */
DmaBufDiagnostics collect_dma_diagnostics() {
    DmaBufDiagnostics diag;

#ifdef __linux__
    // 读取 /sys/kernel/debug/dma_buf/bufinfo
    // 注意：需要 root 权限或 debugfs 已挂载
    int fd = ::open("/sys/kernel/debug/dma_buf/bufinfo", O_RDONLY);
    if (fd >= 0) {
        char buf[4096];
        ssize_t n = ::read(fd, buf, sizeof(buf) - 1);
        if (n > 0) {
            buf[n] = '\0';
            // 解析 bufinfo 输出（简化：仅计数行数）
            std::string content(buf);
            size_t line_count = std::count(content.begin(), content.end(), '\n');
            diag.active_buffers = line_count;
        }
        ::close(fd);
    }
#endif

    return diag;
}

}  // namespace memory
}  // namespace qoocore
