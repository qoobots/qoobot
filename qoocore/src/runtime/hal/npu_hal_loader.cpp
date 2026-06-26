/**
 * @file npu_hal_loader.cpp
 * @brief NPU HAL 动态加载器实现
 *
 * 使用 dlopen/LoadLibrary 动态加载 HAL 共享库，
 * 实现插件化 NPU 后端架构。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/hal/npu_hal.h"

#include <cstdio>
#include <cstring>
#include <unordered_map>
#include <spdlog/spdlog.h>

// ── 跨平台动态库加载 ────────────────────────────────────────────────
#if defined(_WIN32)
    #include <windows.h>
    using LibraryHandle = HMODULE;
    static LibraryHandle dl_open(const char* path) {
        return LoadLibraryA(path);
    }
    static void dl_close(LibraryHandle h) {
        FreeLibrary(h);
    }
    static void* dl_sym(LibraryHandle h, const char* sym) {
        return reinterpret_cast<void*>(GetProcAddress(h, sym));
    }
    static const char* dl_error() {
        static char buf[256];
        FormatMessageA(FORMAT_MESSAGE_FROM_SYSTEM, nullptr, GetLastError(),
                       0, buf, sizeof(buf), nullptr);
        return buf;
    }
#else
    #include <dlfcn.h>
    using LibraryHandle = void*;
    static LibraryHandle dl_open(const char* path) {
        return dlopen(path, RTLD_LAZY | RTLD_LOCAL);
    }
    static void dl_close(LibraryHandle h) {
        dlclose(h);
    }
    static void* dl_sym(LibraryHandle h, const char* sym) {
        return dlsym(h, sym);
    }
    static const char* dl_error() {
        return dlerror();
    }
#endif

namespace qoocore {

// ── HAL 库记录 ───────────────────────────────────────────────────────
struct HalLibrary {
    LibraryHandle   lib_handle{nullptr};
    NpuHal*        hal_instance{nullptr};
    void (*destroy_fn)(NpuHal*){nullptr};
};

// ── NpuHalLoader::Impl ───────────────────────────────────────────────
struct NpuHalLoader::Impl {
    std::unordered_map<std::string, HalLibrary> libs;
};

// ── 单例 ────────────────────────────────────────────────────────────
NpuHalLoader& NpuHalLoader::instance() {
    static NpuHalLoader inst;
    return inst;
}

// ── 构造 / 析构 ────────────────────────────────────────────────────
NpuHalLoader::NpuHalLoader() : impl_(std::make_unique<Impl>()) {}
NpuHalLoader::~NpuHalLoader() = default;

// ── load() ───────────────────────────────────────────────────────────
Result<void> NpuHalLoader::load(const std::string& name,
                                  const std::string& library_path) {
    if (impl_->libs.count(name)) {
        return Error(ErrorCode::ALREADY_EXISTS,
                     "HAL '" + name + "' already loaded");
    }

    // 1. 打开共享库
    LibraryHandle lib = dl_open(library_path.c_str());
    if (!lib) {
        return Error(ErrorCode::DLOPEN_FAILED,
                     std::string("Failed to load ") + library_path + ": " +
                     dl_error());
    }

    // 2. 查找 create 函数
    using CreateFn = NpuHal* (*)();
    auto* create_sym = reinterpret_cast<CreateFn>(
        dl_sym(lib, "create_qoocore_npu_hal"));
    if (!create_sym) {
        dl_close(lib);
        return Error(ErrorCode::SYMBOL_NOT_FOUND,
                     "Symbol 'create_qoocore_npu_hal' not found in " +
                     library_path);
    }

    // 3. 查找 destroy 函数
    using DestroyFn = void (*)(NpuHal*);
    auto* destroy_sym = reinterpret_cast<DestroyFn>(
        dl_sym(lib, "destroy_qoocore_npu_hal"));
    if (!destroy_sym) {
        dl_close(lib);
        return Error(ErrorCode::SYMBOL_NOT_FOUND,
                     "Symbol 'destroy_qoocore_npu_hal' not found in " +
                     library_path);
    }

    // 4. 创建 HAL 实例
    NpuHal* hal = create_sym();
    if (!hal) {
        dl_close(lib);
        return Error(ErrorCode::UNKNOWN,
                     "create_qoocore_npu_hal() returned nullptr");
    }

    // 5. 记录
    HalLibrary rec;
    rec.lib_handle  = lib;
    rec.hal_instance = hal;
    rec.destroy_fn   = destroy_sym;
    impl_->libs[name] = std::move(rec);

    spdlog::info("HAL '{}' loaded from {}", name, library_path);
    return Ok();
}

// ── unload() ───────────────────────────────────────────────────────
Result<void> NpuHalLoader::unload(const std::string& name) {
    auto it = impl_->libs.find(name);
    if (it == impl_->libs.end()) {
        return Error(ErrorCode::NOT_FOUND,
                     "HAL '" + name + "' not loaded");
    }

    HalLibrary& rec = it->second;

    // 销毁 HAL 实例
    if (rec.hal_instance && rec.destroy_fn) {
        rec.destroy_fn(rec.hal_instance);
    }

    // 关闭共享库
    if (rec.lib_handle) {
        dl_close(rec.lib_handle);
    }

    impl_->libs.erase(it);
    spdlog::info("HAL '{}' unloaded", name);
    return Ok();
}

// ── get() ───────────────────────────────────────────────────────────
Result<NpuHal*> NpuHalLoader::get(const std::string& name) {
    auto it = impl_->libs.find(name);
    if (it == impl_->libs.end()) {
        return Error(ErrorCode::NOT_FOUND,
                     "HAL '" + name + "' not loaded");
    }
    return it->second.hal_instance;
}

// ── list() ──────────────────────────────────────────────────────────
std::vector<std::string> NpuHalLoader::list() const {
    std::vector<std::string> names;
    names.reserve(impl_->libs.size());
    for (const auto& [name, _] : impl_->libs) {
        names.push_back(name);
    }
    return names;
}

// ── auto_probe() ───────────────────────────────────────────────────
Result<std::vector<std::string>> NpuHalLoader::auto_probe() {
    // TODO: 扫描文件系统查找 HAL 共享库
    // Linux: /usr/lib/libqoocore_hal_*.so
    // Windows: %ProgramFiles%\QooCore\hal\*.dll
    spdlog::warn("NpuHalLoader::auto_probe() not yet implemented");
    return std::vector<std::string>{};
}

}  // namespace qoocore
