/**
 * @file export.h
 * @brief QooCore 符号导出宏
 *
 * 用于动态库（SHARED）构建时正确导出/导入符号。
 * 基于 CMake 生成的 `qoocore_export.h`（使用 GenerateExportHeader）。
 *
 * 本文件为兼容手写头文件提供基础宏定义。
 * 完整构建时由 CMake GenerateExportHeader 自动生成。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

// ── 检测是否使用 CMake 生成的导出头 ─────────────────────────────
// 若 CMake 已运行 GenerateExportHeader，优先使用生成文件
#if defined(QOOCORE_EXPORT_H)
#include "qoocore/qoocore_export.h"

// ── 手动定义宏（未使用 CMake 生成时）─────────────────────────
#else

#if defined(_WIN32) || defined(_WIN64)
    // Windows：使用 __declspec
    #if defined(QOOCORE_EXPORTS)
        #define QOOCORE_EXPORT __declspec(dllexport)
    #elif defined(QOOCORE_IMPORTS)
        #define QOOCORE_EXPORT __declspec(dllimport)
    #else
        #define QOOCORE_EXPORT  // 静态库：空
    #endif
#elif defined(__GNUC__) || defined(__clang__)
    // GCC/Clang：使用 __attribute__((visibility("default")))
    #if defined(QOOCORE_EXPORTS)
        #define QOOCORE_EXPORT __attribute__((visibility("default")))
    #else
        #define QOOCORE_EXPORT
    #endif
#else
    #define QOOCORE_EXPORT
#endif

#endif  // QOOCORE_EXPORT_H
