/**
 * @file dtype.cpp
 * @brief DType / TensorLayout 工具函数实现
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/core.h"
#include "qoocore/tensor.h"

namespace qoocore {

// ── dtype_bytes 实现 ───────────────────────────────────────────────────────
std::size_t dtype_bytes(DType dt) noexcept {
    switch (dt) {
        case DType::FLOAT64:  return 8;
        case DType::FLOAT32:  return 4;
        case DType::FLOAT16:
        case DType::BFLOAT16: return 2;
        case DType::INT32:
        case DType::UINT32:  return 4;
        case DType::INT16:
        case DType::UINT16:  return 2;
        case DType::INT8:
        case DType::UINT8:
        case DType::QINT8:   return 1;
        case DType::INT4:
        case DType::QINT4:   return 0;  // 特殊处理：需除 2
        case DType::BOOL:     return 1;
        default:              return 0;
    }
}

// ── dtype_to_string 实现 ──────────────────────────────────────────────────
const char* dtype_to_string(DType dt) noexcept {
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

// ── is_floating / is_integer / is_quantized 实现 ───────────────────────
bool is_floating(DType dt) noexcept {
    return dt == DType::FLOAT32 || dt == DType::FLOAT16 ||
           dt == DType::FLOAT64 || dt == DType::BFLOAT16;
}

bool is_integer(DType dt) noexcept {
    return dt == DType::INT32 || dt == DType::INT16 || dt == DType::INT8 ||
           dt == DType::UINT32 || dt == DType::UINT16 || dt == DType::UINT8;
}

bool is_quantized(DType dt) noexcept {
    return dt == DType::QINT8 || dt == DType::QINT4 || dt == DType::QFP16;
}

// ── layout_to_string 实现 ─────────────────────────────────────────────────
const char* layout_to_string(TensorLayout lo) noexcept {
    switch (lo) {
        case TensorLayout::NCHW:  return "NCHW";
        case TensorLayout::NHWC:  return "NHWC";
        case TensorLayout::NC:    return "NC";
        case TensorLayout::NCDHW: return "NCDHW";
        case TensorLayout::NDCHW: return "NDCHW";
        default:                   return "unknown";
    }
}

// ── backend_to_string 实现 ────────────────────────────────────────────────
const char* backend_to_string(BackendType bt) noexcept {
    switch (bt) {
        case BackendType::NPU:  return "npu";
        case BackendType::GPU:  return "gpu";
        case BackendType::DSP:  return "dsp";
        case BackendType::CPU:  return "cpu";
        case BackendType::AUTO: return "auto";
        default:                 return "unknown";
    }
}

}  // namespace qoocore
