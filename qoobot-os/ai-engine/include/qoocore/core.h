/**
 * @file core.h
 * @brief QooCore 核心类型定义 — Result<T>、ErrorCode、DType、TensorLayout
 *
 * 本文件是 qoocore 的基础设施，被所有其他模块依赖。
 * 设计原则：零开销抽象、强类型、C++17 兼容。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include <cstdint>
#include <optional>
#include <ostream>
#include <string>
#include <utility>
#include <variant>
#include <vector>

// ─────────────────────────────────────────────────────────────────────────────
//  Namespace
// ─────────────────────────────────────────────────────────────────────────────
namespace qoocore {

// ─────────────────────────────────────────────────────────────────────────────
//  ErrorCode — 统一错误码枚举
// ─────────────────────────────────────────────────────────────────────────────
enum class ErrorCode : std::int32_t {
    // ── 成功 ─────────────────────────────────────────────────────
    OK = 0,

    // ── 通用错误 (1xxx) ────────────────────────────────────────
    UNKNOWN_ERROR       = 1000,
    NOT_IMPLEMENTED    = 1001,
    INVALID_ARGUMENT    = 1002,
    OUT_OF_RANGE       = 1003,
    TIMEOUT            = 1004,
    CANCELLED          = 1005,

    // ── 模型/文件错误 (2xxx) ──────────────────────────────────
    FILE_NOT_FOUND     = 2000,
    FILE_CORRUPTED     = 2001,
    INVALID_MODEL       = 2002,
    UNSUPPORTED_FORMAT  = 2003,
    VERSION_MISMATCH    = 2004,
    CHECKSUM_MISMATCH   = 2005,

    // ── 编译错误 (3xxx) ───────────────────────────────────────
    COMPILE_FAILED      = 3000,
    GRAPH_INVALID       = 3001,
    OP_NOT_SUPPORTED    = 3002,
    QUANTIZATION_FAILED = 3003,
    CODEGEN_FAILED      = 3004,

    // ── 运行时错误 (4xxx) ──────────────────────────────────────
    ENGINE_NOT_INIT    = 4000,
    MODEL_NOT_LOADED   = 4001,
    INFER_FAILED        = 4002,
    BACKEND_UNAVAILABLE = 4003,
    DEVICE_BUSY         = 4004,

    // ── 内存错误 (5xxx) ────────────────────────────────────────
    OUT_OF_MEMORY      = 5000,
    MEMORY_ALIGN_FAILED = 5001,
    ION_ALLOC_FAILED   = 5002,
    DMA_BUF_ERROR      = 5003,

    // ── 硬件/后端错误 (6xxx) ──────────────────────────────────
    HAL_INIT_FAILED     = 6000,
    NPU_DEVICE_NOT_FOUND = 6001,
    NPU_INFER_FAILED    = 6002,
    GPU_CONTEXT_FAILED   = 6003,
    DSP_LOAD_FAILED      = 6004,

    // ── 配置/参数错误 (7xxx) ──────────────────────────────────
    CONFIG_NOT_FOUND    = 7000,
    CONFIG_PARSE_ERROR  = 7001,
    INVALID_BACKEND     = 7002,
    INVALID_DTYPE       = 7003,
};

// ─────────────────────────────────────────────────────────────────────────────
//  ErrorInfo — 错误信息结构体（命名空间作用域）
// ─────────────────────────────────────────────────────────────────────────────
struct ErrorInfo {
    ErrorCode code{ErrorCode::UNKNOWN_ERROR};
    std::string message;
    std::optional<std::string> details;

    ErrorInfo() = default;
    ErrorInfo(ErrorCode c, std::string msg)
        : code(c), message(std::move(msg)) {}
    ErrorInfo(ErrorCode c, std::string msg, std::string dtl)
        : code(c), message(std::move(msg)), details(std::move(dtl)) {}

    friend std::ostream& operator<<(std::ostream& os, const ErrorInfo& e) {
        os << "Error{" << static_cast<int>(e.code) << ": " << e.message;
        if (e.details.has_value()) os << " (" << e.details.value() << ")";
        return os;
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  Result<T> — 类似 Rust Result<T, E> 的错误处理类型
// ─────────────────────────────────────────────────────────────────────────────
/**
 * @brief 类型安全的错误处理，避免异常开销。
 *
 * 用法：
 * ```cpp
 * Result<Tensor> load_tensor(const std::string& path) {
 *     if (!file_exists(path)) {
 *         return Error<Tensor>(ErrorCode::FILE_NOT_FOUND, "File not found: " + path);
 *     }
 *     // ...
 *     return std::move(tensor);  // 或 Ok(std::move(tensor))
 * }
 *
 * auto result = load_tensor("input.bin");
 * if (!result.ok()) {
 *     spdlog::error("Failed: {}", result.error().message);
 *     return;
 * }
 * Tensor t = std::move(result).value();
 * ```
 */
template <typename T>
class Result {
public:
    // ── 构造：成功值 ────────────────────────────────────────────────
    Result(T value) : storage_(std::in_place_index<0>, std::move(value)) {}

    // ── 构造：错误 ───────────────────────────────────────────────
    Result(ErrorInfo error) : storage_(std::in_place_index<1>, std::move(error)) {}
    Result(ErrorCode code, std::string message)
        : storage_(std::in_place_index<1>, code, std::move(message)) {}

    // ── 查询状态 ───────────────────────────────────────────────
    [[nodiscard]] bool ok() const noexcept {
        return storage_.index() == 0;
    }

    [[nodiscard]] bool is_error() const noexcept {
        return storage_.index() == 1;
    }

    // ── 获取错误 ───────────────────────────────────────────────
    [[nodiscard]] const ErrorInfo& error() const & {
        return std::get<1>(storage_);
    }

    [[nodiscard]] ErrorInfo error() && {
        return std::move(std::get<1>(storage_));
    }

    // ── 获取值（调用前必须检查 ok()）──────────────────────────
    [[nodiscard]] T& value() & {
        return std::get<0>(storage_);
    }

    [[nodiscard]] const T& value() const& {
        return std::get<0>(storage_);
    }

    [[nodiscard]] T value() && {
        return std::move(std::get<0>(storage_));
    }

    // ── 便捷方法：值或默认值 ─────────────────────────────────
    [[nodiscard]] T value_or(T&& default_value) const& {
        return ok() ? std::get<0>(storage_) : std::forward<T>(default_value);
    }

    // ── 移动构造 / 移动赋值 ───────────────────────────────────
    Result(Result&&) noexcept = default;
    Result& operator=(Result&&) noexcept = default;

    // 禁止拷贝（避免意外开销）
    Result(const Result&) = delete;
    Result& operator=(const Result&) = delete;

private:
    std::variant<T, ErrorInfo> storage_;
};

// ── 无值 Result 特化（用于返回 void 的函数）──────────────────────────
template <>
class Result<void> {
public:
    Result() : error_(std::nullopt) {}
    Result(ErrorInfo error) : error_(std::move(error)) {}
    Result(ErrorCode code, std::string message)
        : error_(ErrorInfo{code, std::move(message)}) {}

    [[nodiscard]] bool ok() const noexcept { return !error_.has_value(); }
    [[nodiscard]] const ErrorInfo& error() const { return *error_; }

private:
    std::optional<ErrorInfo> error_;
};

// ─────────────────────────────────────────────────────────────────────────────
//  Result 辅助函数（方便返回值构造）
// ─────────────────────────────────────────────────────────────────────────────

/// @brief 构造成功的 Result<T>
template<typename T>
[[nodiscard]] inline Result<T> Ok(T&& v) {
    return Result<T>(std::forward<T>(v));
}

/// @brief 构造成功的 Result<void>
[[nodiscard]] inline Result<void> Ok() {
    return Result<void>();
}

/// @brief 构造失败的 Result<T>
template<typename T>
[[nodiscard]] inline Result<T> Error(ErrorCode code, std::string msg) {
    return Result<T>(code, std::move(msg));
}

/// @brief 构造失败的 Result<void>
[[nodiscard]] inline Result<void> Error(ErrorCode code, std::string msg) {
    return Result<void>(code, std::move(msg));
}

// ─────────────────────────────────────────────────────────────────────────────
//  DType — 数据类型枚举
// ─────────────────────────────────────────────────────────────────────────────
enum class DType : std::uint32_t {
    // 浮点
    FLOAT32 = 0,
    FLOAT16 = 1,
    FLOAT64 = 2,
    BFLOAT16= 3,

    // 有符号整数
    INT32   = 1000,
    INT16   = 1001,
    INT8    = 1002,
    INT4    = 1003,   // 打包存储，每字节 2 个元素

    // 无符号整数
    UINT32  = 2000,
    UINT16  = 2001,
    UINT8   = 2002,

    // 量化类型（权重/激活）
    QINT8  = 3000,  // 逐张量 INT8 量化
    QINT4  = 3001,  // 逐通道 INT4 量化
    QFP16  = 3002,  // 浮点 16 量化

    // 布尔 / 特殊
    BOOL   = 4000,
    STRING = 4001,
    UNKNOWN = 0xFFFF,
};

// ── DType 工具函数 ──────────────────────────────────────────────────────────
[[nodiscard]] constexpr bool is_floating(DType dt) noexcept {
    return dt == DType::FLOAT32 || dt == DType::FLOAT16 ||
           dt == DType::FLOAT64 || dt == DType::BFLOAT16;
}

[[nodiscard]] constexpr bool is_integer(DType dt) noexcept {
    return dt == DType::INT32 || dt == DType::INT16 || dt == DType::INT8 ||
           dt == DType::UINT32 || dt == DType::UINT16 || dt == DType::UINT8;
}

[[nodiscard]] constexpr bool is_quantized(DType dt) noexcept {
    return dt == DType::QINT8 || dt == DType::QINT4 || dt == DType::QFP16;
}

[[nodiscard]] constexpr std::size_t dtype_bytes(DType dt) noexcept {
    switch (dt) {
        case DType::FLOAT64:  return 8;
        case DType::FLOAT32:  return 4;
        case DType::FLOAT16:
        case DType::BFLOAT16: return 2;
        case DType::INT32:
        case DType::UINT32: return 4;
        case DType::INT16:
        case DType::UINT16: return 2;
        case DType::INT8:
        case DType::UINT8:
        case DType::QINT8:   return 1;
        case DType::INT4:
        case DType::QINT4:   return 0; // 特殊处理：需除 2
        case DType::BOOL:     return 1;
        default:              return 0;
    }
}

[[nodiscard]] constexpr const char* dtype_to_string(DType dt) noexcept {
    switch (dt) {
        case DType::FLOAT32:  return "float32";
        case DType::FLOAT16:  return "float16";
        case DType::FLOAT64:  return "float64";
        case DType::BFLOAT16: return "bfloat16";
        case DType::INT32:    return "int32";
        case DType::INT16:    return "int16";
        case DType::INT8:     return "int8";
        case DType::UINT32:   return "uint32";
        case DType::UINT16:   return "uint16";
        case DType::UINT8:    return "uint8";
        case DType::QINT8:    return "qint8";
        case DType::QINT4:    return "qint4";
        case DType::BOOL:     return "bool";
        default:              return "unknown";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  TensorLayout — 张量内存布局
// ─────────────────────────────────────────────────────────────────────────────
enum class TensorLayout : std::uint8_t {
    NCHW  = 0,
    NHWC  = 1,
    NC    = 2,
    NCDHW = 3,
};

[[nodiscard]] constexpr const char* layout_to_string(TensorLayout lo) noexcept {
    switch (lo) {
        case TensorLayout::NCHW:  return "NCHW";
        case TensorLayout::NHWC:  return "NHWC";
        case TensorLayout::NC:    return "NC";
        case TensorLayout::NCDHW: return "NCDHW";
        default:                   return "unknown";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  BackendType — 硬件后端类型
// ─────────────────────────────────────────────────────────────────────────────
enum class BackendType : std::uint8_t {
    NPU       = 0,  ///< 神经网络加速芯片（Qualcomm/Horizon/Rockchip）
    GPU       = 1,  ///< 图形处理器（CUDA/OpenCL/Vulkan）
    DSP       = 2,  ///< 数字信号处理器（Hexagon/CEVA）
    CPU       = 3,  ///< 中央处理器（ARM Neon/x86 AVX512）
    AUTO      = 255, ///< 自动选择（根据硬件能力 + 模型需求）
};

[[nodiscard]] constexpr const char* backend_to_string(BackendType bt) noexcept {
    switch (bt) {
        case BackendType::NPU:  return "npu";
        case BackendType::GPU:  return "gpu";
        case BackendType::DSP:  return "dsp";
        case BackendType::CPU:  return "cpu";
        case BackendType::AUTO: return "auto";
        default:                 return "unknown";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  QuantParams — 量化参数
// ─────────────────────────────────────────────────────────────────────────────
struct QuantParams {
    DType target_dtype{DType::QINT8};
    std::vector<float> scales;
    std::vector<std::int32_t> zero_points;
    bool per_channel{false};
    bool symmetric{true};

    [[nodiscard]] bool empty() const noexcept {
        return scales.empty();
    }
};

// ─────────────────────────────────────────────────────────────────────────────
//  Version — 语义化版本工具
// ─────────────────────────────────────────────────────────────────────────────
struct Version {
    std::uint16_t major{0};
    std::uint16_t minor{0};
    std::uint16_t patch{0};

    [[nodiscard]] std::string to_string() const {
        return std::to_string(major) + "." + std::to_string(minor) + "." + std::to_string(patch);
    }

    constexpr bool operator>=(const Version& other) const noexcept {
        if (major != other.major) return major > other.major;
        if (minor != other.minor) return minor > other.minor;
        return patch >= other.patch;
    }
};

// ── QooCore 版本宏（编译时可用）───────────────────────────────────────
#define QOOCORE_VERSION_MAJOR 0
#define QOOCORE_VERSION_MINOR 1
#define QOOCORE_VERSION_PATCH 0
#define QOOCORE_VERSION_STRING "0.1.0"

} // namespace qoocore
