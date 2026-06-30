/**
 * @file tensor.h
 * @brief Tensor 张量定义 — qoocore 的核心数据结构
 *
 * Tensor 是对硬件内存的轻量级视图（zero-copy 设计）：
 *   - 支持 CPU 内存、ION/DMA-BUF 共享内存
 *   - 支持 strides（非连续张量，避免不必要的拷贝）
 *   - 支持量化参数（INT8/INT4）
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "core.h"

#include <cstdint>
#include <cstring>
#include <memory>
#include <ostream>
#include <string>
#include <unordered_map>
#include <vector>

namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  Strides — 张量步长（支持非连续张量）
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 张量每个维度的步长（以元素为单位，非字节）。
 *
 * 用途：支持非连续张量（如从 NCHW 到 NHWC 的零拷贝视图），
 * 避免不必要的内存拷贝。
 *
 * 示例（NCHW，shape=[1,3,640,640]）：
 *   strides = [3*640*640, 640*640, 640, 1]
 *   元素 [n,c,h,w] 的偏移量 = n*strides[0] + c*strides[1] + h*strides[2] + w*strides[3]
 */
struct Strides {
    std::vector<std::int64_t> values;

    Strides() = default;
    explicit Strides(std::vector<std::int64_t> s) : values(std::move(s)) {}

    /** @brief 从 shape 计算连续张量的默认 strides（行主序）。 */
    static Strides from_shape(const std::vector<std::int64_t>& shape) {
        std::vector<std::int64_t> s(shape.size(), 1);
        for (int i = static_cast<int>(shape.size()) - 2; i >= 0; --i) {
            s[i] = s[i + 1] * shape[i + 1];
        }
        return Strides{std::move(s)};
    }

    [[nodiscard]] bool empty() const noexcept { return values.empty(); }
    [[nodiscard]] std::size_t size() const noexcept { return values.size(); }
    [[nodiscard]] std::int64_t operator[](std::size_t i) const { return values[i]; }
};

// ─────────────────────────────────────────────────────────────────────────────
//  TensorMetadata — 张量元数据（无所有权）
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 张量元数据，不包含实际数据指针（用于模型 IO 信息）。
 *
 * 轻量级，可拷贝，用于描述模型的输入/输出规格。
 */
struct TensorMetadata {
    std::string name;
    DType dtype{DType::FLOAT32};
    TensorLayout layout{TensorLayout::NCHW};
    std::vector<std::int64_t> shape;
    Strides strides;
    std::optional<QuantParams> quant;

    /** @brief 计算总元素数。 */
    [[nodiscard]] std::int64_t num_elements() const {
        std::int64_t n = 1;
        for (auto d : shape) n *= d;
        return n;
    }

    /** @brief 计算 contiguous 时的字节大小。 */
    [[nodiscard]] std::size_t bytes_contiguous() const {
        const std::size_t element_bytes = dtype_bytes(dtype);
        if (element_bytes == 0 && dtype == DType::QINT4) {
            // INT4：每 2 个元素占 1 字节
            return static_cast<std::size_t>((num_elements() + 1) / 2);
        }
        return static_cast<std::size_t>(num_elements()) * element_bytes;
    }

    /** @brief 检查 shape 是否有效。 */
    [[nodiscard]] bool valid() const noexcept {
        return !shape.empty() && num_elements() > 0;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  Tensor — 张量（可能持有或引用数据）
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 张量对象，支持多种内存来源。
 *
 * 内存来源：
 *   1. CPU 堆内存（普通 new/delete）
 *   2. ION/DMA-BUF（共享内存，零拷贝）
 *   3. 引用外部数据（non-owning，不释放）
 *
 * 设计要点：
 *   - 默认移动语义，禁止意外拷贝
 *   - 支持自定义 deleter（用于 ION 内存等特殊释放逻辑）
 *   - 与 FlatBuffer TensorInfo 可互相转换
 */
class Tensor {
public:
    using Deleter = void(*)(void* context, std::uint8_t* data);

    // ── 构造 ─────────────────────────────────────────────────────────────

    /** @brief 创建空张量（未分配内存）。 */
    Tensor() = default;

    /**
     * @brief 分配 CPU 内存，创建张量。
     * @param shape       张量形状
     * @param dtype       数据类型
     * @param layout      内存布局（默认 NCHW）
     */
    static Result<Tensor> create(const std::vector<std::int64_t>& shape,
                                 DType dtype,
                                 TensorLayout layout = TensorLayout::NCHW);

    /**
     * @brief 从已有 CPU 内存创建张量视图（non-owning）。
     * @param data    外部数据指针（不释放）
     * @param shape   形状
     * @param dtype   类型
     * @param layout  布局
     */
    static Tensor from_cpu_view(std::uint8_t* data,
                               const std::vector<std::int64_t>& shape,
                               DType dtype,
                               TensorLayout layout = TensorLayout::NCHW);

    /**
     * @brief 从 ION/DMA-BUF 文件描述符创建张量（零拷贝）。
     * @param ion_fd  ION/DMA-BUF 文件描述符
     * @param shape   形状
     * @param dtype   类型
     * @param size    映射大小（字节）
     */
    static Result<Tensor> from_ion_fd(int ion_fd,
                                      const std::vector<std::int64_t>& shape,
                                      DType dtype,
                                      std::size_t size);

    // ── 移动语义 ─────────────────────────────────────────────────────────
    Tensor(Tensor&& other) noexcept;
    Tensor& operator=(Tensor&& other) noexcept;

    // 禁止拷贝
    Tensor(const Tensor&) = delete;
    Tensor& operator=(const Tensor&) = delete;

    // ── 析构 ─────────────────────────────────────────────────────────────
    ~Tensor();

    // ── 属性查询 ───────────────────────────────────────────────────────
    [[nodiscard]] const TensorMetadata& meta() const noexcept { return meta_; }
    [[nodiscard]] const std::vector<std::int64_t>& shape() const noexcept { return meta_.shape; }
    [[nodiscard]] DType dtype() const noexcept { return meta_.dtype; }
    [[nodiscard]] TensorLayout layout() const noexcept { return meta_.layout; }
    [[nodiscard]] const std::optional<QuantParams>& quant() const noexcept { return meta_.quant; }

    /** @brief 返回数据指针（可能为空）。 */
    [[nodiscard]] std::uint8_t* data() noexcept { return data_; }
    [[nodiscard]] const std::uint8_t* data() const noexcept { return data_; }

    /** @brief 返回总字节数。 */
    [[nodiscard]] std::size_t nbytes() const noexcept { return nbytes_; }

    /** @brief 是否为空（未分配内存）。 */
    [[nodiscard]] bool empty() const noexcept { return data_ == nullptr; }

    /** @brief 是否拥有数据（需要释放）。 */
    [[nodiscard]] bool owns_data() const noexcept { return deleter_ != nullptr; }

    /** @brief 是否为 ION 内存（零拷贝）。 */
    [[nodiscard]] bool is_ion_memory() const noexcept { return ion_fd_ >= 0; }

    /** @brief 返回 ION 文件描述符（-1 表示非 ION 内存）。 */
    [[nodiscard]] int ion_fd() const noexcept { return ion_fd_; }

    /**
     * @brief 深拷贝张量（分配新的 CPU 内存）。
     * @note 显式拷贝，避免隐式拷贝开销。
     */
    [[nodiscard]] Result<Tensor> clone() const;

    // ── 数据访问辅助 ───────────────────────────────────────────────────
    /**
     * @brief 类型安全地访问元素（仅 contiguous 张量）。
     * @tparam T  元素类型（float/int8_t 等）
     * @param indices  多维索引，长度必须等于 shape 维度
     */
    template <typename T>
    [[nodiscard]] Result<T*> element(const std::vector<std::int64_t>& indices) {
        if (indices.size() != meta_.shape.size()) {
            return Error(ErrorCode::INVALID_ARGUMENT,
                        "Index dimensions mismatch: expected " +
                        std::to_string(meta_.shape.size()) + ", got " +
                        std::to_string(indices.size()));
        }
        if (!strides_.empty()) {
            return Error(ErrorCode::NOT_IMPLEMENTED,
                        "Element access with custom strides not yet implemented");
        }
        std::size_t offset = 0;
        for (std::size_t i = 0; i < indices.size(); ++i) {
            if (indices[i] < 0 || indices[i] >= meta_.shape[i]) {
                return Error(ErrorCode::OUT_OF_RANGE, "Index out of range");
            }
            offset += static_cast<std::size_t>(indices[i]) * meta_.shape[i + 1]; // simplified
        }
        return reinterpret_cast<T*>(data_ + offset * dtype_bytes(meta_.dtype));
    }

    // ── 量化 ───────────────────────────────────────────────────────────
    /** @brief 设置量化参数。 */
    void set_quant(QuantParams q) { meta_.quant = std::move(q); }

    /**
     * @brief 量化张量（in-place，仅支持 CPU 内存）。
     * @param params  量化参数
     */
    Result<void> quantize(const QuantParams& params);

    /**
     * @brief 反量化张量（返回新张量，FP32）。
     */
    Result<Tensor> dequantize() const;

    // ── 布局转换 ───────────────────────────────────────────────────────
    /**
     * @brief 转换内存布局（如 NCHW → NHWC）。
     * @note 返回新张量，数据拷贝。
     */
    Result<Tensor> to_layout(TensorLayout target) const;

    // ── 调试 ─────────────────────────────────────────────────────────────
    /** @brief 生成张量摘要字符串（用于日志）。 */
    [[nodiscard]] std::string summary() const;

private:
    TensorMetadata meta_;
    std::uint8_t* data_{nullptr};
    std::size_t nbytes_{0};
    Strides strides_;

    // ION 内存支持
    int ion_fd_{-1};

    // 自定义释放逻辑
    Deleter deleter_{nullptr};
    void* deleter_context_{nullptr};

    // 释放数据
    void release();
};

// ─────────────────────────────────────────────────────────────────────────────
//  ModelInfo — 模型元信息
// ─────────────────────────────────────────────────────────────────────────────
struct ModelInfo {
    std::string name;
    std::string version;
    std::vector<TensorMetadata> inputs;
    std::vector<TensorMetadata> outputs;
    std::size_t weight_size_bytes{0};
    std::size_t activation_size_bytes{0};
    std::optional<BackendType> compiled_for; ///< 编译目标后端（若有）
    std::unordered_map<std::string, std::string> metadata; ///< 任意附加信息
};

// ─────────────────────────────────────────────────────────────────────────────
//  ProfilingInfo — 推理性能剖析结果
// ─────────────────────────────────────────────────────────────────────────────
struct ProfilingInfo {
    double total_latency_ms{0.0};
    double preprocess_ms{0.0};
    double infer_ms{0.0};
    double postprocess_ms{0.0};
    double d2h_copy_ms{0.0}; ///< device-to-host 拷贝时间
    std::size_t peak_memory_bytes{0};
    std::optional<double> power_watts;
};

// ─────────────────────────────────────────────────────────────────────────────
//  ostream 输出支持（用于日志）
// ─────────────────────────────────────────────────────────────────────────────
inline std::ostream& operator<<(std::ostream& os, DType dt) {
    return os << dtype_to_string(dt);
}

inline std::ostream& operator<<(std::ostream& os, TensorLayout lo) {
    return os << layout_to_string(lo);
}

inline std::ostream& operator<<(std::ostream& os, BackendType bt) {
    return os << backend_to_string(bt);
}

} // namespace qoocore
