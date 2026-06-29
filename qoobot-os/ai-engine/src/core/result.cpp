/**
 * @file result.cpp
 * @brief Result<T> 错误处理类型的实现
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/core.h"

namespace qoocore {

// ── ErrorCode → 可读性字符串 ──────────────────────────────────────
const char* error_code_to_string(ErrorCode code) noexcept {
    switch (code) {
        case ErrorCode::OK:                  return "OK";
        case ErrorCode::UNKNOWN_ERROR:        return "UNKNOWN_ERROR";
        case ErrorCode::NOT_IMPLEMENTED:     return "NOT_IMPLEMENTED";
        case ErrorCode::INVALID_ARGUMENT:    return "INVALID_ARGUMENT";
        case ErrorCode::OUT_OF_RANGE:        return "OUT_OF_RANGE";
        case ErrorCode::TIMEOUT:             return "TIMEOUT";
        case ErrorCode::CANCELLED:          return "CANCELLED";
        case ErrorCode::FILE_NOT_FOUND:      return "FILE_NOT_FOUND";
        case ErrorCode::FILE_CORRUPTED:     return "FILE_CORRUPTED";
        case ErrorCode::INVALID_MODEL:       return "INVALID_MODEL";
        case ErrorCode::UNSUPPORTED_FORMAT:  return "UNSUPPORTED_FORMAT";
        case ErrorCode::VERSION_MISMATCH:    return "VERSION_MISMATCH";
        case ErrorCode::CHECKSUM_MISMATCH:   return "CHECKSUM_MISMATCH";
        case ErrorCode::COMPILE_FAILED:      return "COMPILE_FAILED";
        case ErrorCode::GRAPH_INVALID:       return "GRAPH_INVALID";
        case ErrorCode::OP_NOT_SUPPORTED:    return "OP_NOT_SUPPORTED";
        case ErrorCode::QUANTIZATION_FAILED: return "QUANTIZATION_FAILED";
        case ErrorCode::CODEGEN_FAILED:      return "CODEGEN_FAILED";
        case ErrorCode::ENGINE_NOT_INIT:    return "ENGINE_NOT_INIT";
        case ErrorCode::MODEL_NOT_LOADED:   return "MODEL_NOT_LOADED";
        case ErrorCode::INFER_FAILED:        return "INFER_FAILED";
        case ErrorCode::BACKEND_UNAVAILABLE: return "BACKEND_UNAVAILABLE";
        case ErrorCode::DEVICE_BUSY:        return "DEVICE_BUSY";
        case ErrorCode::OUT_OF_MEMORY:       return "OUT_OF_MEMORY";
        case ErrorCode::MEMORY_ALIGN_FAILED: return "MEMORY_ALIGN_FAILED";
        case ErrorCode::ION_ALLOC_FAILED:    return "ION_ALLOC_FAILED";
        case ErrorCode::DMA_BUF_ERROR:       return "DMA_BUF_ERROR";
        case ErrorCode::HAL_INIT_FAILED:     return "HAL_INIT_FAILED";
        case ErrorCode::NPU_DEVICE_NOT_FOUND: return "NPU_DEVICE_NOT_FOUND";
        case ErrorCode::NPU_INFER_FAILED:    return "NPU_INFER_FAILED";
        case ErrorCode::GPU_CONTEXT_FAILED:   return "GPU_CONTEXT_FAILED";
        case ErrorCode::DSP_LOAD_FAILED:      return "DSP_LOAD_FAILED";
        case ErrorCode::CONFIG_NOT_FOUND:    return "CONFIG_NOT_FOUND";
        case ErrorCode::CONFIG_PARSE_ERROR:  return "CONFIG_PARSE_ERROR";
        case ErrorCode::INVALID_BACKEND:     return "INVALID_BACKEND";
        case ErrorCode::INVALID_DTYPE:       return "INVALID_DTYPE";
        default:                            return "UNKNOWN_ERROR_CODE";
    }
}

}  // namespace qoocore
