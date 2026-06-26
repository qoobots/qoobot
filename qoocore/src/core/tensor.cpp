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
#include <algorithm>
#include <spdlog/spdlog.h>

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
        return Error(ErrorCode::INVALID_ARGUMENT, "Shape cannot be empty");
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
        return Error(ErrorCode::OUT_OF_MEMORY,
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
    (void)ion_fd; (void)shape; (void)dtype; (void)size;
    return Error(ErrorCode::NOT_IMPLEMENTED,
                 "Tensor::from_ion_fd() not yet implemented");
}

// ── 移动构造 / 移动赋值 ─────────────────────────────────────────
Tensor::Tensor(Tensor&& other) noexcept
    : meta_(std::move(other.meta_))
    , data_(other.data_)
    , nbytes_(other.nbytes_)
    , strides_(std::move(other.strides_))
    , ion_fd_(other.ion_fd_)
    , deleter_(other.deleter_)
    , deleter_ctx_(other.deleter_ctx_) {
    other.data_     = nullptr;
    other.nbytes_   = 0;
    other.ion_fd_   = -1;
    other.deleter_   = nullptr;
    other.deleter_ctx_ = nullptr;
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
        deleter_ctx_   = other.deleter_ctx_;

        other.data_     = nullptr;
        other.nbytes_   = 0;
        other.ion_fd_   = -1;
        other.deleter_   = nullptr;
        other.deleter_ctx_ = nullptr;
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
        deleter_(deleter_ctx_, data_);
    } else if (data_ && owns_data()) {
        aligned_free(data_);
    }
    data_     = nullptr;
    nbytes_   = 0;
    ion_fd_   = -1;
    deleter_   = nullptr;
    deleter_ctx_ = nullptr;
}

// ── Tensor::quantize() ──────────────────────────────────────────
Result<void> Tensor::quantize(const QuantParams& params) {
    if (meta_.dtype == DType::FLOAT32 && params.target_dtype == DType::QINT8) {
        // FP32 → INT8 量化（逐张量）
        // 公式：q = round(f / scale) + zero_point
        // TODO: 完整实现
        return Error(ErrorCode::NOT_IMPLEMENTED,
                     "Tensor::quantize() not yet implemented");
    }
    return Error(ErrorCode::INVALID_ARGUMENT, "Unsupported quantization");
}

// ── Tensor::dequantize() ───────────────────────────────────────
Result<Tensor> Tensor::dequantize() const {
    if (!meta_.quant.has_value()) {
        return Error(ErrorCode::INVALID_ARGUMENT, "Tensor is not quantized");
    }
    // TODO: 完整实现
    return Error(ErrorCode::NOT_IMPLEMENTED,
                 "Tensor::dequantize() not yet implemented");
}

// ── Tensor::to_layout() ───────────────────────────────────────
Result<Tensor> Tensor::to_layout(TensorLayout target) const {
    if (meta_.layout == target) {
        return Tensor(*this);  // 返回副本
    }
    // NCHW → NHWC 转换
    // TODO: 完整实现
    return Error(ErrorCode::NOT_IMPLEMENTED,
                 "Tensor::to_layout() not yet implemented");
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
