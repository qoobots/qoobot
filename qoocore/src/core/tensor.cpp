/**
 * @file tensor.cpp
 * @brief Tensor 张量实现 — qoocore 核心数据结构
 *
 * 实现 CPU 内存分配/释放、ION/DMA-BUF 支持、量化/反量化。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/tensor.h"

#include <cstring>
#include <cstdlib>
#include <cmath>
#include <algorithm>
#include <cerrno>
#include <spdlog/spdlog.h>

#ifdef QOOCORE_ENABLE_ION
#if defined(__linux__) || defined(__ANDROID__)
#include <sys/mman.h>
#include <unistd.h>
#endif
#endif

namespace qoocore {

// ── 辅助：对齐分配 ────────────────────────────────────────────────
static void* aligned_alloc(std::size_t alignment, std::size_t size) {
#if defined(_WIN32)
    return _aligned_malloc(size, alignment);
#else
    void* ptr = nullptr;
    if (posix_memalign(&ptr, alignment, size) != 0) {
        return nullptr;
    }
    return ptr;
#endif
}

static void aligned_free(void* ptr) {
#if defined(_WIN32)
    _aligned_free(ptr);
#else
    free(ptr);
#endif
}

// ── Tensor::create() ─────────────────────────────────────────────────
Result<Tensor> Tensor::create(const std::vector<std::int64_t>& shape,
                                 DType dtype,
                                 TensorLayout layout) {
    if (shape.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Shape cannot be empty");
    }

    Tensor t;
    t.meta_.shape   = shape;
    t.meta_.dtype  = dtype;
    t.meta_.layout = layout;

    // 计算字节数
    std::size_t element_bytes = dtype_bytes(dtype);
    if (element_bytes == 0 && dtype == DType::QINT4) {
        // INT4：每 2 个元素占 1 字节
        std::int64_t num_el = 1;
        for (auto d : shape) num_el *= d;
        t.nbytes_ = static_cast<std::size_t>((num_el + 1) / 2);
    } else {
        std::int64_t num_el = 1;
        for (auto d : shape) num_el *= d;
        t.nbytes_ = static_cast<std::size_t>(num_el) * element_bytes;
    }

    // 分配对齐内存（64 字节对齐，适配 SIMD）
    t.data_ = static_cast<std::uint8_t*>(aligned_alloc(64, t.nbytes_));
    if (!t.data_) {
        return Error<Tensor>(ErrorCode::OUT_OF_MEMORY,
                     "Failed to allocate " + std::to_string(t.nbytes_) + " bytes");
    }

    // 设置默认 strides（连续张量）
    t.strides_ = Strides::from_shape(shape);

    spdlog::debug("Tensor created: shape=[{}], dtype={}, {} bytes",
                   shape.size(), dtype_to_string(dtype), t.nbytes_);

    return std::move(t);
}

// ── Tensor::from_cpu_view() ────────────────────────────────────────
Tensor Tensor::from_cpu_view(std::uint8_t* data,
                               const std::vector<std::int64_t>& shape,
                               DType dtype,
                               TensorLayout layout) {
    Tensor t;
    t.meta_.shape   = shape;
    t.meta_.dtype  = dtype;
    t.meta_.layout = layout;
    t.data_          = data;
    t.deleter_      = nullptr;  // 不释放
    t.strides_       = Strides::from_shape(shape);

    std::int64_t num_el = 1;
    for (auto d : shape) num_el *= d;
    t.nbytes_ = static_cast<std::size_t>(num_el) * dtype_bytes(dtype);

    return t;
}

// ── Tensor::from_ion_fd() ────────────────────────────────────────
Result<Tensor> Tensor::from_ion_fd(int ion_fd,
                                      const std::vector<std::int64_t>& shape,
                                      DType dtype,
                                      std::size_t size) {
    if (ion_fd < 0) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
                     "Invalid ION fd: " + std::to_string(ion_fd));
    }
    if (shape.empty()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
                     "Shape cannot be empty for ION tensor");
    }
    if (size == 0) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
                     "ION buffer size cannot be zero");
    }

#ifdef QOOCORE_ENABLE_ION
    // 平台相关：将 ION/DMA-BUF fd 映射到用户空间
    // Linux: mmap(ion_fd, size, PROT_READ|PROT_WRITE, MAP_SHARED, ...)
    // Android: ION_IOC_MAP 或 AHardwareBuffer
#if defined(__linux__) || defined(__ANDROID__)
    #include <sys/mman.h>
    #include <unistd.h>

    // 获取 fd 对应的实际大小
    off_t fd_size = lseek(ion_fd, 0, SEEK_END);
    if (fd_size < 0) {
        return Error<Tensor>(ErrorCode::ION_ALLOC_FAILED,
                     "Cannot seek ION fd " + std::to_string(ion_fd) + ": " + strerror(errno));
    }
    lseek(ion_fd, 0, SEEK_SET);

    std::size_t map_size = static_cast<std::size_t>(fd_size);
    if (map_size < size) {
        spdlog::warn("ION fd size ({}) < requested size ({}), using fd size", map_size, size);
    } else {
        map_size = size;
    }

    void* mapped = mmap(nullptr, map_size, PROT_READ | PROT_WRITE, MAP_SHARED, ion_fd, 0);
    if (mapped == MAP_FAILED) {
        return Error<Tensor>(ErrorCode::ION_ALLOC_FAILED,
                     "mmap failed for ION fd " + std::to_string(ion_fd) + ": " + strerror(errno));
    }

    Tensor t;
    t.meta_.shape   = shape;
    t.meta_.dtype   = dtype;
    t.meta_.layout  = TensorLayout::NCHW;
    t.data_         = static_cast<std::uint8_t*>(mapped);
    t.nbytes_       = map_size;
    t.strides_      = Strides::from_shape(shape);
    t.ion_fd_       = ion_fd;

    // ION 内存使用自定义 deleter：munmap
    t.deleter_ = [](void* ctx, std::uint8_t* data) {
        auto* info = static_cast<std::pair<std::size_t, int>*>(ctx);
        munmap(data, info->first);
        delete info;
    };
    t.deleter_context_ = new std::pair<std::size_t, int>(map_size, ion_fd);

    spdlog::debug("Tensor created from ION fd={}, size={} bytes, shape=[{}]",
                   ion_fd, map_size, shape.size());
    return std::move(t);
#else
    return Error<Tensor>(ErrorCode::NOT_IMPLEMENTED,
                 "ION/DMA-BUF not supported on this platform");
#endif

#else
    // ION 未启用：回退到 CPU 内存拷贝
    spdlog::warn("ION support disabled. Tensor::from_ion_fd() "
                 "will fallback to CPU memory (zero-copy unavailable). "
                 "Enable with -DQOOCORE_ENABLE_ION=ON");

    Tensor t;
    t.meta_.shape   = shape;
    t.meta_.dtype   = dtype;
    t.meta_.layout  = TensorLayout::NCHW;

    std::int64_t num_el = 1;
    for (auto d : shape) num_el *= d;
    std::size_t element_bytes = dtype_bytes(dtype);
    if (element_bytes == 0 && dtype == DType::QINT4) {
        t.nbytes_ = static_cast<std::size_t>((num_el + 1) / 2);
    } else {
        t.nbytes_ = static_cast<std::size_t>(num_el) * element_bytes;
    }

    // 使用较小的大小
    std::size_t alloc_size = (size > 0 && size < t.nbytes_) ? size : t.nbytes_;
    t.data_ = static_cast<std::uint8_t*>(aligned_alloc(64, alloc_size));
    if (!t.data_) {
        return Error<Tensor>(ErrorCode::OUT_OF_MEMORY,
                     "Failed to allocate " + std::to_string(alloc_size) + " bytes");
    }
    t.nbytes_ = alloc_size;
    t.strides_ = Strides::from_shape(shape);

    spdlog::debug("Tensor created (ION fallback CPU) fd={}, {} bytes", ion_fd, alloc_size);
    return std::move(t);
#endif
}

// ── 移动构造 / 移动赋值 ─────────────────────────────────────────
Tensor::Tensor(Tensor&& other) noexcept
    : meta_(std::move(other.meta_))
    , data_(other.data_)
    , nbytes_(other.nbytes_)
    , strides_(std::move(other.strides_))
    , ion_fd_(other.ion_fd_)
    , deleter_(other.deleter_)
    , deleter_context_(other.deleter_context_) {
    other.data_     = nullptr;
    other.nbytes_   = 0;
    other.ion_fd_   = -1;
    other.deleter_   = nullptr;
    other.deleter_context_ = nullptr;
}

Tensor& Tensor::operator=(Tensor&& other) noexcept {
    if (this != &other) {
        release();
        meta_         = std::move(other.meta_);
        data_         = other.data_;
        nbytes_       = other.nbytes_;
        strides_       = std::move(other.strides_);
        ion_fd_       = other.ion_fd_;
        deleter_       = other.deleter_;
        deleter_context_   = other.deleter_context_;

        other.data_     = nullptr;
        other.nbytes_   = 0;
        other.ion_fd_   = -1;
        other.deleter_   = nullptr;
        other.deleter_context_ = nullptr;
    }
    return *this;
}

// ── Tensor::~Tensor() ─────────────────────────────────────────────
Tensor::~Tensor() {
    release();
}

// ── Tensor::release() ────────────────────────────────────────────
void Tensor::release() {
    if (data_ && deleter_) {
        deleter_(deleter_context_, data_);
    } else if (data_ && owns_data()) {
        aligned_free(data_);
    }
    data_     = nullptr;
    nbytes_   = 0;
    ion_fd_   = -1;
    deleter_   = nullptr;
    deleter_context_ = nullptr;
}

// ── Tensor::quantize() ──────────────────────────────────────────
Result<void> Tensor::quantize(const QuantParams& params) {
    if (data_ == nullptr) {
        return Error<void>(ErrorCode::INVALID_ARGUMENT, "Cannot quantize empty tensor");
    }

    if (meta_.dtype != DType::FLOAT32) {
        return Error<void>(ErrorCode::INVALID_ARGUMENT,
                     "Only FP32 tensor can be quantized, got " +
                     std::string(dtype_to_string(meta_.dtype)));
    }

    std::int64_t num_el = 1;
    for (auto d : meta_.shape) num_el *= d;

    // ── FP32 → INT8 量化（逐张量或逐通道） ────────────────
    if (params.target_dtype == DType::QINT8 || params.target_dtype == DType::INT8) {
        if (params.scales.empty()) {
            return Error<void>(ErrorCode::INVALID_ARGUMENT,
                         "QuantParams.scales must not be empty for INT8 quantization");
        }

        float* fp32_data = reinterpret_cast<float*>(data_);

        if (params.per_channel && !meta_.shape.empty()) {
            // 逐通道量化：每个输出通道独立 scale/zero_point
            // shape = [N, C, H, W] 或 [C, H, W]
            std::int64_t channels = meta_.shape.size() >= 2 ? meta_.shape[1] : meta_.shape[0];
            std::int64_t per_channel_el = num_el / channels;

            // 分配新的量化数据缓冲区
            std::size_t quant_bytes = static_cast<std::size_t>(num_el); // INT8 = 1 byte/elem
            std::uint8_t* quant_data = static_cast<std::uint8_t*>(aligned_alloc(64, quant_bytes));
            if (!quant_data) {
                return Error<void>(ErrorCode::OUT_OF_MEMORY,
                             "Failed to allocate quantized buffer: " + std::to_string(quant_bytes));
            }

            for (std::int64_t c = 0; c < channels; ++c) {
                float scale = (c < static_cast<std::int64_t>(params.scales.size()))
                              ? params.scales[static_cast<std::size_t>(c)]
                              : params.scales[0];
                std::int32_t zp = params.zero_points.empty() ? 0 :
                    (c < static_cast<std::int64_t>(params.zero_points.size()))
                        ? params.zero_points[static_cast<std::size_t>(c)]
                        : params.zero_points[0];

                for (std::int64_t i = 0; i < per_channel_el; ++i) {
                    std::int64_t idx = c * per_channel_el + i;
                    float val = fp32_data[idx] / scale + static_cast<float>(zp);
                    // 饱和截断到 [-128, 127]
                    val = std::max(-128.0f, std::min(127.0f, std::round(val)));
                    quant_data[idx] = static_cast<std::uint8_t>(static_cast<std::int8_t>(val));
                }
            }

            // 替换数据指针
            if (owns_data() || is_ion_memory()) {
                release();
            }
            data_ = quant_data;
            nbytes_ = quant_bytes;
            deleter_ = nullptr; // 使用 aligned_free
        } else {
            // 逐张量量化
            float scale = params.scales[0];
            std::int32_t zp = params.zero_points.empty() ? 0 : params.zero_points[0];

            // 对称量化：zp = 0
            if (params.symmetric) {
                zp = 0;
                // 对称 INT8：范围 [-127, 127]
                float max_abs = 0.0f;
                for (std::int64_t i = 0; i < num_el; ++i) {
                    max_abs = std::max(max_abs, std::abs(fp32_data[i]));
                }
                if (max_abs > 0.0f) {
                    scale = max_abs / 127.0f;
                }
            }

            std::size_t quant_bytes = static_cast<std::size_t>(num_el);
            std::uint8_t* quant_data = static_cast<std::uint8_t*>(aligned_alloc(64, quant_bytes));
            if (!quant_data) {
                return Error<void>(ErrorCode::OUT_OF_MEMORY,
                             "Failed to allocate quantized buffer: " + std::to_string(quant_bytes));
            }

            for (std::int64_t i = 0; i < num_el; ++i) {
                float val = fp32_data[i] / scale + static_cast<float>(zp);
                val = std::max(-128.0f, std::min(127.0f, std::round(val)));
                quant_data[i] = static_cast<std::uint8_t>(static_cast<std::int8_t>(val));
            }

            if (owns_data() || is_ion_memory()) {
                release();
            }
            data_ = quant_data;
            nbytes_ = quant_bytes;
            deleter_ = nullptr;
        }

        meta_.dtype = DType::QINT8;
        meta_.quant = params;
        spdlog::debug("Tensor quantized: FP32→INT8, {} elements, scale={}", num_el,
                       params.scales[0]);
        return Ok();
    }

    // ── FP32 → FP16 量化 ──────────────────────────────────
    if (params.target_dtype == DType::FLOAT16) {
        std::size_t quant_bytes = static_cast<std::size_t>(num_el) * 2;
        std::uint8_t* quant_data = static_cast<std::uint8_t*>(aligned_alloc(64, quant_bytes));
        if (!quant_data) {
            return Error<void>(ErrorCode::OUT_OF_MEMORY,
                         "Failed to allocate FP16 buffer: " + std::to_string(quant_bytes));
        }

        float* fp32_data = reinterpret_cast<float*>(data_);
        std::uint16_t* fp16_data = reinterpret_cast<std::uint16_t*>(quant_data);

        for (std::int64_t i = 0; i < num_el; ++i) {
            // IEEE 754 FP32 → FP16 转换
            std::uint32_t bits = *reinterpret_cast<std::uint32_t*>(&fp32_data[i]);
            std::uint32_t sign = (bits >> 16) & 0x8000;
            std::int32_t exp = static_cast<std::int32_t>((bits >> 23) & 0xFF) - 127 + 15;
            std::uint32_t mant = (bits >> 13) & 0x3FF;

            if (exp <= 0) {
                fp16_data[i] = static_cast<std::uint16_t>(sign); // 下溢为 0
            } else if (exp >= 31) {
                fp16_data[i] = static_cast<std::uint16_t>(sign | 0x7C00); // 上溢为 Inf
            } else {
                fp16_data[i] = static_cast<std::uint16_t>(sign | (static_cast<std::uint32_t>(exp) << 10) | mant);
            }
        }

        if (owns_data() || is_ion_memory()) {
            release();
        }
        data_ = quant_data;
        nbytes_ = quant_bytes;
        deleter_ = nullptr;
        meta_.dtype = DType::FLOAT16;
        meta_.quant = params;
        spdlog::debug("Tensor quantized: FP32→FP16, {} elements, {} bytes", num_el, quant_bytes);
        return Ok();
    }

    return Error<void>(ErrorCode::INVALID_ARGUMENT,
                 "Unsupported quantization: " + std::string(dtype_to_string(meta_.dtype)) +
                 " → " + std::string(dtype_to_string(params.target_dtype)));
}

// ── Tensor::dequantize() ───────────────────────────────────────
Result<Tensor> Tensor::dequantize() const {
    if (!meta_.quant.has_value()) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Tensor is not quantized");
    }
    if (data_ == nullptr) {
        return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Cannot dequantize empty tensor");
    }

    const QuantParams& qp = meta_.quant.value();
    std::int64_t num_el = 1;
    for (auto d : meta_.shape) num_el *= d;

    // ── INT8 → FP32 反量化 ──────────────────────────────────
    if (meta_.dtype == DType::QINT8 || meta_.dtype == DType::INT8) {
        if (qp.scales.empty()) {
            return Error<Tensor>(ErrorCode::INVALID_ARGUMENT, "Missing scale for INT8 dequantization");
        }

        auto fp32 = Tensor::create(meta_.shape, DType::FLOAT32, meta_.layout);
        if (!fp32.ok()) {
            return fp32;
        }
        Tensor result = std::move(fp32).value();
        float* fp32_data = reinterpret_cast<float*>(result.data_);
        std::int8_t* int8_data = reinterpret_cast<std::int8_t*>(data_);

        if (qp.per_channel && !meta_.shape.empty()) {
            std::int64_t channels = meta_.shape.size() >= 2 ? meta_.shape[1] : meta_.shape[0];
            std::int64_t per_channel_el = num_el / channels;

            for (std::int64_t c = 0; c < channels; ++c) {
                float scale = (c < static_cast<std::int64_t>(qp.scales.size()))
                              ? qp.scales[static_cast<std::size_t>(c)]
                              : qp.scales[0];
                std::int32_t zp = qp.zero_points.empty() ? 0 :
                    (c < static_cast<std::int64_t>(qp.zero_points.size()))
                        ? qp.zero_points[static_cast<std::size_t>(c)]
                        : qp.zero_points[0];

                for (std::int64_t i = 0; i < per_channel_el; ++i) {
                    std::int64_t idx = c * per_channel_el + i;
                    fp32_data[idx] = (static_cast<float>(int8_data[idx]) - static_cast<float>(zp)) * scale;
                }
            }
        } else {
            float scale = qp.scales[0];
            std::int32_t zp = qp.zero_points.empty() ? 0 : qp.zero_points[0];

            for (std::int64_t i = 0; i < num_el; ++i) {
                fp32_data[i] = (static_cast<float>(int8_data[i]) - static_cast<float>(zp)) * scale;
            }
        }

        result.meta_.quant = qp;
        spdlog::debug("Tensor dequantized: INT8→FP32, {} elements, scale={}", num_el, qp.scales[0]);
        return std::move(result);
    }

    // ── FP16 → FP32 反量化 ──────────────────────────────────
    if (meta_.dtype == DType::FLOAT16) {
        auto fp32 = Tensor::create(meta_.shape, DType::FLOAT32, meta_.layout);
        if (!fp32.ok()) {
            return fp32;
        }
        Tensor result = std::move(fp32).value();
        float* fp32_data = reinterpret_cast<float*>(result.data_);
        std::uint16_t* fp16_data = reinterpret_cast<std::uint16_t*>(data_);

        for (std::int64_t i = 0; i < num_el; ++i) {
            // IEEE 754 FP16 → FP32 转换
            std::uint32_t sign = (fp16_data[i] & 0x8000) << 16;
            std::uint32_t exp  = (fp16_data[i] & 0x7C00) >> 10;
            std::uint32_t mant = (fp16_data[i] & 0x03FF) << 13;

            if (exp == 0) {
                // 零或非规格化数：视为零
                std::uint32_t bits = sign;
                fp32_data[i] = *reinterpret_cast<float*>(&bits);
            } else if (exp == 31) {
                // Inf 或 NaN
                std::uint32_t bits = sign | 0x7F800000 | mant;
                fp32_data[i] = *reinterpret_cast<float*>(&bits);
            } else {
                exp = exp - 15 + 127;
                std::uint32_t bits = sign | (exp << 23) | mant;
                fp32_data[i] = *reinterpret_cast<float*>(&bits);
            }
        }

        result.meta_.quant = qp;
        spdlog::debug("Tensor dequantized: FP16→FP32, {} elements", num_el);
        return std::move(result);
    }

    return Error<Tensor>(ErrorCode::INVALID_ARGUMENT,
                 "Unsupported dequantization for dtype: " +
                 std::string(dtype_to_string(meta_.dtype)));
}

// ── Tensor::to_layout() ───────────────────────────────────────
Result<Tensor> Tensor::to_layout(TensorLayout target) const {
    if (meta_.layout == target) {
        // 布局已匹配，创建副本
        auto copy = Tensor::create(meta_.shape, meta_.dtype, target);
        if (!copy.ok()) {
            return copy;
        }
        Tensor result = std::move(copy).value();
        if (data_ && result.data_) {
            std::memcpy(result.data_, data_, nbytes_);
        }
        result.meta_.quant = meta_.quant;
        return std::move(result);
    }

    // ── NCHW ↔ NHWC 转换 ────────────────────────────────────
    if (meta_.shape.size() == 4) {
        std::int64_t N = meta_.shape[0];
        std::int64_t C = meta_.shape[1];
        std::int64_t H = meta_.shape[2];
        std::int64_t W = meta_.shape[3];
        std::size_t elem_size = dtype_bytes(meta_.dtype);

        std::vector<std::int64_t> new_shape;
        if (target == TensorLayout::NHWC) {
            new_shape = {N, H, W, C};  // NCHW → NHWC
        } else {
            new_shape = {N, C, H, W};  // NHWC → NCHW
        }

        auto new_tensor = Tensor::create(new_shape, meta_.dtype, target);
        if (!new_tensor.ok()) {
            return new_tensor;
        }
        Tensor result = std::move(new_tensor).value();

        if (!data_ || !result.data_ || elem_size == 0) {
            return std::move(result);
        }

        // 执行布局转换
        for (std::int64_t n = 0; n < N; ++n) {
            for (std::int64_t c = 0; c < C; ++c) {
                for (std::int64_t h = 0; h < H; ++h) {
                    for (std::int64_t w = 0; w < W; ++w) {
                        std::int64_t src_idx, dst_idx;

                        if (meta_.layout == TensorLayout::NCHW && target == TensorLayout::NHWC) {
                            // NCHW → NHWC: [n,c,h,w] → [n,h,w,c]
                            src_idx = ((n * C + c) * H + h) * W + w;
                            dst_idx = ((n * H + h) * W + w) * C + c;
                        } else {
                            // NHWC → NCHW: [n,h,w,c] → [n,c,h,w]
                            src_idx = ((n * H + h) * W + w) * C + c;
                            dst_idx = ((n * C + c) * H + h) * W + w;
                        }

                        std::memcpy(result.data_ + dst_idx * elem_size,
                                   data_ + src_idx * elem_size,
                                   elem_size);
                    }
                }
            }
        }

        result.meta_.quant = meta_.quant;
        spdlog::debug("Tensor layout converted: {} → {}, shape=[{}]",
                       layout_to_string(meta_.layout),
                       layout_to_string(target),
                       new_shape.size());
        return std::move(result);
    }

    // ── 2D 张量 (NC) 布局转换 ──────────────────────────────
    if (meta_.shape.size() == 2) {
        // NC 布局对于 2D 张量无变化，直接复制
        auto copy = Tensor::create(meta_.shape, meta_.dtype, target);
        if (!copy.ok()) {
            return copy;
        }
        Tensor result = std::move(copy).value();
        if (data_ && result.data_) {
            std::memcpy(result.data_, data_, nbytes_);
        }
        result.meta_.quant = meta_.quant;
        return std::move(result);
    }

    // ── 5D 张量 (NCDHW) 转换 ───────────────────────────────
    if (meta_.shape.size() == 5 && target == TensorLayout::NCDHW) {
        // NCDHW 对于 5D 张量视为标准布局，直接复制
        auto copy = Tensor::create(meta_.shape, meta_.dtype, target);
        if (!copy.ok()) {
            return copy;
        }
        Tensor result = std::move(copy).value();
        if (data_ && result.data_) {
            std::memcpy(result.data_, data_, nbytes_);
        }
        result.meta_.quant = meta_.quant;
        return std::move(result);
    }

    return Error<Tensor>(ErrorCode::NOT_IMPLEMENTED,
                 "Layout conversion not supported for shape rank " +
                 std::to_string(meta_.shape.size()) + ": " +
                 std::string(layout_to_string(meta_.layout)) + " → " +
                 std::string(layout_to_string(target)));
}

// ── Tensor::summary() ──────────────────────────────────────────
std::string Tensor::summary() const {
    std::string s = "Tensor{shape=[";
    for (std::size_t i = 0; i < meta_.shape.size(); ++i) {
        if (i > 0) s += ", ";
        s += std::to_string(meta_.shape[i]);
    }
    s += "], dtype=" + std::string(dtype_to_string(meta_.dtype));
    s += ", layout=" + std::string(layout_to_string(meta_.layout));
    s += ", nbytes=" + std::to_string(nbytes_);
    if (is_ion_memory()) s += ", ion_fd=" + std::to_string(ion_fd_);
    s += "}";
    return s;
}

}  // namespace qoocore
