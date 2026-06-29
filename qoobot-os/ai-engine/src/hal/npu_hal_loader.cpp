/**
 * @file npu_hal_loader.cpp
 * @brief NPU HAL 动态加载器实现 — 插件化架构核心
 *
 * 负责运行时发现、加载、管理 NPU HAL 共享库（.so/.dll）。
 * 支持自动探测（/usr/lib/libqoocore_hal_*.so）和手动指定路径。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/hal/npu_hal.h"

#include <spdlog/spdlog.h>
#include <algorithm>
#include <filesystem>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#define DL_HANDLE HMODULE
#define DL_OPEN(path) LoadLibraryA(path)
#define DL_SYM(handle, name) GetProcAddress(handle, name)
#define DL_CLOSE(handle) FreeLibrary(handle)
#define DL_ERR() std::to_string(GetLastError())
#else
#include <dlfcn.h>
#define DL_HANDLE void*
#define DL_OPEN(path) dlopen(path, RTLD_NOW | RTLD_LOCAL)
#define DL_SYM(handle, name) dlsym(handle, name)
#define DL_CLOSE(handle) dlclose(handle)
#define DL_ERR() std::string(dlerror())
#endif

namespace qoocore {

// ── 共享库导出符号名（厂商必须实现）─────────────────────────────────
static constexpr const char* SYM_CREATE = "create_qoocore_npu_hal";
static constexpr const char* SYM_DESTROY = "destroy_qoocore_npu_hal";

// ── 函数指针类型 ─────────────────────────────────────────────────────
using CreateFn = NpuHal* (*)();
using DestroyFn = void (*)(NpuHal*);

// ── NpuHalLoader::Impl ────────────────────────────────────────────────
struct NpuHalLoader::Impl {
    struct LoadedHal {
        std::string name;
        std::string library_path;
        DL_HANDLE   dl_handle{nullptr};
        CreateFn    create_fn{nullptr};
        DestroyFn   destroy_fn{nullptr};
        NpuHal*     instance{nullptr};
    };

    std::unordered_map<std::string, LoadedHal> hal_map;
    std::mutex mutex;
};

// ── 单例 ──────────────────────────────────────────────────────────────
NpuHalLoader& NpuHalLoader::instance() {
    static NpuHalLoader inst;
    return inst;
}

NpuHalLoader::NpuHalLoader() : impl_(std::make_unique<Impl>()) {}
NpuHalLoader::~NpuHalLoader() {
    // 卸载所有已加载的 HAL
    std::lock_guard<std::mutex> lock(impl_->mutex);
    for (auto& [name, hal] : impl_->hal_map) {
        if (hal.instance && hal.destroy_fn) {
            hal.instance->deinit();
            hal.destroy_fn(hal.instance);
        }
        if (hal.dl_handle) {
            DL_CLOSE(hal.dl_handle);
        }
    }
    impl_->hal_map.clear();
}

// ── load — 加载 HAL 共享库 ───────────────────────────────────────────
Result<void> NpuHalLoader::load(const std::string& name,
                                 const std::string& library_path) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    // 检查是否已加载
    if (impl_->hal_map.find(name) != impl_->hal_map.end()) {
        return Error(ErrorCode::INVALID_ARGUMENT,
                     "HAL '" + name + "' is already loaded");
    }

    // 检查文件是否存在
    if (!std::filesystem::exists(library_path)) {
        return Error(ErrorCode::FILE_NOT_FOUND,
                     "HAL library not found: " + library_path);
    }

    // 打开共享库
    DL_HANDLE handle = DL_OPEN(library_path.c_str());
    if (!handle) {
        return Error(ErrorCode::HAL_INIT_FAILED,
                     "Failed to load HAL library '" + library_path +
                     "': " + DL_ERR());
    }

    // 解析导出符号
    auto create_fn = reinterpret_cast<CreateFn>(
        DL_SYM(handle, SYM_CREATE));
    auto destroy_fn = reinterpret_cast<DestroyFn>(
        DL_SYM(handle, SYM_DESTROY));

    if (!create_fn || !destroy_fn) {
        DL_CLOSE(handle);
        return Error(ErrorCode::HAL_INIT_FAILED,
                     "HAL library '" + library_path +
                     "' does not export required symbols (" +
                     SYM_CREATE + " / " + SYM_DESTROY + "): " +
                     DL_ERR());
    }

    // 创建 HAL 实例
    NpuHal* hal_instance = create_fn();
    if (!hal_instance) {
        DL_CLOSE(handle);
        return Error(ErrorCode::HAL_INIT_FAILED,
                     "HAL factory returned nullptr for '" + name + "'");
    }

    // 注册到表
    Impl::LoadedHal entry;
    entry.name = name;
    entry.library_path = library_path;
    entry.dl_handle = handle;
    entry.create_fn = create_fn;
    entry.destroy_fn = destroy_fn;
    entry.instance = hal_instance;

    impl_->hal_map[name] = std::move(entry);

    spdlog::info("NpuHal '{}' loaded from {}", name, library_path);
    return Ok();
}

// ── unload — 卸载 HAL ────────────────────────────────────────────────
Result<void> NpuHalLoader::unload(const std::string& name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = impl_->hal_map.find(name);
    if (it == impl_->hal_map.end()) {
        return Error(ErrorCode::INVALID_ARGUMENT,
                     "HAL '" + name + "' is not loaded");
    }

    auto& hal = it->second;

    // 销毁实例
    if (hal.instance) {
        hal.instance->deinit();
        hal.destroy_fn(hal.instance);
        hal.instance = nullptr;
    }

    // 卸载共享库
    if (hal.dl_handle) {
        DL_CLOSE(hal.dl_handle);
        hal.dl_handle = nullptr;
    }

    impl_->hal_map.erase(it);

    spdlog::info("NpuHal '{}' unloaded", name);
    return Ok();
}

// ── get — 获取已加载的 HAL ───────────────────────────────────────────
Result<NpuHal*> NpuHalLoader::get(const std::string& name) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = impl_->hal_map.find(name);
    if (it == impl_->hal_map.end()) {
        return Error<NpuHal*>(ErrorCode::INVALID_ARGUMENT,
                               "HAL '" + name + "' is not loaded");
    }

    return it->second.instance;
}

// ── list — 列出已加载的 HAL ──────────────────────────────────────────
std::vector<std::string> NpuHalLoader::list() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    std::vector<std::string> result;
    for (const auto& [name, _] : impl_->hal_map) {
        result.push_back(name);
    }
    return result;
}

// ── auto_probe — 自动探测可用 NPU HAL ────────────────────────────────
Result<std::vector<std::string>> NpuHalLoader::auto_probe() {
    std::vector<std::string> loaded;
    std::vector<std::string> probe_paths = {
#ifdef _WIN32
        "C:\\Program Files\\QooBot\\hal\\",
#else
        "/usr/lib/qoocore/hal/",
        "/usr/local/lib/qoocore/hal/",
#endif
    };

    // 也尝试 HOME 目录
    const char* home = std::getenv("HOME");
    if (home) {
        std::string home_path = std::string(home) + "/.local/lib/qoocore/hal/";
        probe_paths.push_back(home_path);
    }

    // 探测文件模式：libqoocore_hal_*.so / qoocore_hal_*.dll
    for (const auto& dir : probe_paths) {
        if (!std::filesystem::exists(dir)) continue;

        for (const auto& entry : std::filesystem::directory_iterator(dir)) {
            if (!entry.is_regular_file()) continue;

            std::string filename = entry.path().filename().string();
            std::string hal_name;

#ifdef _WIN32
            // qoocore_hal_qnn.dll → "qnn"
            const std::string prefix = "qoocore_hal_";
            const std::string suffix = ".dll";
#else
            // libqoocore_hal_qnn.so → "qnn"
            const std::string prefix = "libqoocore_hal_";
            const std::string suffix = ".so";
#endif

            if (filename.find(prefix) == 0 && 
                filename.find(suffix) != std::string::npos) {
                hal_name = filename.substr(
                    prefix.size(),
                    filename.size() - prefix.size() - suffix.size());
            }

            if (hal_name.empty()) continue;

            auto result = load(hal_name, entry.path().string());
            if (result.ok()) {
                loaded.push_back(hal_name);
            } else {
                spdlog::warn("Failed to auto-load HAL '{}' from {}: {}",
                              hal_name, entry.path().string(),
                              result.error().message);
            }
        }
    }

    spdlog::info("Auto-probe loaded {} HAL(s): [{}]",
                  loaded.size(),
                  [&]() {
                      std::string s;
                      for (const auto& n : loaded) {
                          if (!s.empty()) s += ", ";
                          s += n;
                      }
                      return s;
                  }());
    return loaded;
}

}  // namespace qoocore
