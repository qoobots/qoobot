// src/engine/backend_manager.cpp
// QooCore — 后端管理器实现

#include "qoocore/backend.h"
#include "qoocore/hal/npu_hal.h"
#include <mutex>
#include <vector>
#include <algorithm>

namespace qoocore {

struct BackendInfo {
    BackendType        type;
    std::string       name;
    int               priority;  // 数值越小优先级越高
    bool              available = false;
    std::shared_ptr<Backend> backend;
};

class BackendManager {
public:
    static BackendManager& instance() {
        static BackendManager inst;
        return inst;
    }

    void register_backend(std::shared_ptr<Backend> be, int priority = 100) {
        std::lock_guard<std::mutex> lock(mu_);
        BackendInfo info;
        info.type     = be->type();
        info.name     = backend_to_string(be->type());
        info.priority = priority;
        info.available = be->available();
        info.backend  = be;
        backends_.push_back(std::move(info));
        // 按优先级排序
        std::sort(backends_.begin(), backends_.end(),
                  [](const BackendInfo& a, const BackendInfo& b) {
                      return a.priority < b.priority;
                  });
    }

    Result<std::shared_ptr<Backend>> select_backend(const std::string& model_path) {
        std::lock_guard<std::mutex> lock(mu_);
        // TODO: 读取模型元数据，匹配合适后端
        (void)model_path;
        for (const auto& info : backends_) {
            if (info.available && info.backend) {
                return info.backend;
            }
        }
        return Result<std::shared_ptr<Backend>>::error(
            ErrorCode::BACKEND_UNAVAILABLE, "无可用后端");
    }

    Result<std::shared_ptr<Backend>> get_backend(BackendType type) {
        std::lock_guard<std::mutex> lock(mu_);
        for (const auto& info : backends_) {
            if (info.type == type && info.backend) {
                return info.backend;
            }
        }
        return Result<std::shared_ptr<Backend>>::error(
            ErrorCode::BACKEND_UNAVAILABLE, backend_to_string(type));
    }

    std::vector<BackendType> available_backends() const {
        std::lock_guard<std::mutex> lock(mu_);
        std::vector<BackendType> result;
        for (const auto& info : backends_) {
            if (info.available && info.backend) {
                result.push_back(info.type);
            }
        }
        return result;
    }

    std::string status_json() const {
        std::lock_guard<std::mutex> lock(mu_);
        std::string s = "{ \"backends\": [";
        bool first = true;
        for (const auto& info : backends_) {
            if (!first) s += ", ";
            first = false;
            s += "{ \"type\": \"" + backend_to_string(info.type) + "\""
                  ", \"available\": " + std::string(info.available ? "true" : "false") +
                  ", \"priority\": " + std::to_string(info.priority) + " }";
        }
        s += "] }";
        return s;
    }

private:
    BackendManager() = default;
    mutable std::mutex mu_;
    std::vector<BackendInfo> backends_;
};

}  // namespace qoocore
