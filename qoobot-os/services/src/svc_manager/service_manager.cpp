#include "qoosvc/manager/service_manager.h"
#include "qoosvc/manager/manager_types.h"
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <queue>
#include <thread>

namespace qoosvc::manager {

struct ServiceEntry {
    std::unique_ptr<ServiceBase> service;
    ServiceInfo info;
    ResourceQuota quota;
    std::vector<std::string> dependencies;
    std::vector<std::string> dependents;
};

struct ServiceManager::Impl {
    std::mutex mtx;
    std::unordered_map<std::string, ServiceEntry> services;
    std::vector<std::string> init_order;
    std::vector<std::string> shutdown_order;

    // Health monitor
    std::unique_ptr<std::thread> health_thread;
    std::condition_variable health_cv;
    std::atomic<bool> health_running{false};
    std::chrono::milliseconds health_interval{5000};
    std::function<void(std::string_view)> on_unhealthy;

    // --- Topological sort helpers ---
    void compute_init_order() {
        init_order.clear();
        shutdown_order.clear();
        std::unordered_map<std::string, int> indegree;
        std::unordered_map<std::string, std::vector<std::string>> adj;

        for (const auto& [name, entry] : services) {
            indegree[name] = 0;
        }
        for (const auto& [name, entry] : services) {
            for (const auto& dep : entry.dependencies) {
                if (services.find(dep) != services.end()) {
                    adj[dep].push_back(name);
                    indegree[name]++;
                }
            }
        }

        std::queue<std::string> q;
        for (const auto& [name, deg] : indegree) {
            if (deg == 0) q.push(name);
        }

        while (!q.empty()) {
            auto name = q.front(); q.pop();
            init_order.push_back(name);
            for (const auto& next : adj[name]) {
                if (--indegree[next] == 0) q.push(next);
            }
        }

        shutdown_order = init_order;
        std::reverse(shutdown_order.begin(), shutdown_order.end());
    }

    ServiceEntry* find_entry(std::string_view name) {
        auto it = services.find(std::string(name));
        return it != services.end() ? &it->second : nullptr;
    }
};

ServiceManager::ServiceManager() : impl_(std::make_unique<Impl>()) {}

ServiceManager::~ServiceManager() {
    stop_health_monitor();
    stop_all();
}

Result<void> ServiceManager::register_service(std::unique_ptr<ServiceBase> service,
                                               const ServiceInfo& info) {
    return register_service(std::move(service), info, ResourceQuota{});
}

Result<void> ServiceManager::register_service(std::unique_ptr<ServiceBase> service,
                                               const ServiceInfo& info,
                                               const ResourceQuota& quota) {
    if (!service) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "Service is null");
    }

    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto name = std::string(service->name());

    if (impl_->services.find(name) != impl_->services.end()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                  "Service '" + name + "' already registered");
    }

    ServiceEntry entry;
    entry.service = std::move(service);
    entry.info = info;
    entry.info.name = name;
    entry.info.state = ServiceState::UNINITIALIZED;
    entry.quota = quota;

    impl_->services[name] = std::move(entry);
    impl_->compute_init_order();

    return Result<void>::ok();
}

Result<void> ServiceManager::unregister_service(std::string_view name) {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto it = impl_->services.find(std::string(name));
    if (it == impl_->services.end()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                  "Service not found: " + std::string(name));
    }

    // Check if any other service depends on this one
    for (const auto& [n, entry] : impl_->services) {
        for (const auto& dep : entry.dependencies) {
            if (dep == name) {
                return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                          "Service '" + std::string(name) +
                                          "' is a dependency of '" + n + "'");
            }
        }
    }

    // Stop the service first
    if (it->second.info.state == ServiceState::RUNNING ||
        it->second.info.state == ServiceState::PAUSED) {
        it->second.service->stop();
    }

    impl_->services.erase(it);
    impl_->compute_init_order();

    return Result<void>::ok();
}

Result<void> ServiceManager::initialize_all() {
    std::lock_guard<std::mutex> lock(impl_->mtx);

    for (const auto& name : impl_->init_order) {
        auto& entry = impl_->services[name];
        if (entry.info.state == ServiceState::RUNNING ||
            entry.info.state == ServiceState::INITIALIZING) {
            continue;
        }
        auto result = entry.service->initialize();
        if (result.is_err()) {
            return result;
        }
        entry.info.state = ServiceState::RUNNING;
    }

    return Result<void>::ok();
}

Result<void> ServiceManager::start_all() {
    auto init_result = initialize_all();
    if (init_result.is_err()) return init_result;

    std::lock_guard<std::mutex> lock(impl_->mtx);
    for (const auto& name : impl_->init_order) {
        auto& entry = impl_->services[name];
        auto result = entry.service->start();
        if (result.is_err()) return result;
    }
    return Result<void>::ok();
}

Result<void> ServiceManager::start_service(std::string_view name) {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto* entry = impl_->find_entry(name);
    if (!entry) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                  "Service not found: " + std::string(name));
    }
    if (entry->info.state == ServiceState::RUNNING) {
        return Result<void>::ok();
    }
    if (entry->info.state == ServiceState::UNINITIALIZED) {
        auto init_result = entry->service->initialize();
        if (init_result.is_err()) return init_result;
        entry->info.state = ServiceState::RUNNING;
    }
    return entry->service->start();
}

Result<void> ServiceManager::stop_all() {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    for (const auto& name : impl_->shutdown_order) {
        auto& entry = impl_->services[name];
        if (entry.info.state == ServiceState::RUNNING ||
            entry.info.state == ServiceState::PAUSED) {
            entry.service->stop();
            entry.info.state = ServiceState::STOPPED;
        }
    }
    return Result<void>::ok();
}

Result<void> ServiceManager::stop_service(std::string_view name) {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto* entry = impl_->find_entry(name);
    if (!entry) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                  "Service not found: " + std::string(name));
    }
    auto result = entry->service->stop();
    if (result.is_ok()) {
        entry->info.state = ServiceState::STOPPED;
    }
    return result;
}

Result<void> ServiceManager::pause_service(std::string_view name) {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto* entry = impl_->find_entry(name);
    if (!entry) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                  "Service not found: " + std::string(name));
    }
    auto result = entry->service->pause();
    if (result.is_ok()) {
        entry->info.state = ServiceState::PAUSED;
    }
    return result;
}

Result<void> ServiceManager::resume_service(std::string_view name) {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto* entry = impl_->find_entry(name);
    if (!entry) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                  "Service not found: " + std::string(name));
    }
    auto result = entry->service->resume();
    if (result.is_ok()) {
        entry->info.state = ServiceState::RUNNING;
    }
    return result;
}

Result<void> ServiceManager::restart_service(std::string_view name) {
    auto stop_result = stop_service(name);
    if (stop_result.is_err()) return stop_result;
    return start_service(name);
}

std::unordered_map<std::string, bool> ServiceManager::check_all_health() {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    std::unordered_map<std::string, bool> results;
    for (const auto& [name, entry] : impl_->services) {
        results[name] = entry.service->health_check();
    }
    return results;
}

void ServiceManager::start_health_monitor(std::chrono::milliseconds interval_ms,
                                           std::function<void(std::string_view)> on_unhealthy) {
    stop_health_monitor();

    impl_->health_interval = interval_ms;
    impl_->on_unhealthy = std::move(on_unhealthy);
    impl_->health_running = true;

    impl_->health_thread = std::make_unique<std::thread>([this]() {
        while (impl_->health_running) {
            {
                std::lock_guard<std::mutex> lock(impl_->mtx);
                for (auto& [name, entry] : impl_->services) {
                    if (!entry.service->health_check()) {
                        if (impl_->on_unhealthy) {
                            impl_->on_unhealthy(name);
                        }
                        // Auto-restart if configured
                        if (entry.info.auto_restart &&
                            entry.info.restart_count < entry.info.max_restarts) {
                            entry.service->stop();
                            auto init_result = entry.service->initialize();
                            if (init_result.is_ok()) {
                                entry.service->start();
                                entry.info.restart_count++;
                                entry.info.state = ServiceState::RUNNING;
                            }
                        }
                    }
                }
            }
            std::unique_lock<std::mutex> cv_lock(impl_->mtx);
            impl_->health_cv.wait_for(cv_lock, impl_->health_interval);
        }
    });
}

void ServiceManager::stop_health_monitor() {
    impl_->health_running = false;
    impl_->health_cv.notify_all();
    if (impl_->health_thread && impl_->health_thread->joinable()) {
        impl_->health_thread->join();
    }
    impl_->health_thread.reset();
}

std::vector<ServiceInfo> ServiceManager::list_services() const {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    std::vector<ServiceInfo> result;
    for (const auto& [name, entry] : impl_->services) {
        result.push_back(entry.info);
    }
    return result;
}

Result<ServiceInfo> ServiceManager::get_service_info(std::string_view name) const {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto* entry = impl_->find_entry(name);
    if (!entry) {
        return Result<ServiceInfo>::err(ErrorCode::INVALID_ARGUMENT,
                                         "Service not found: " + std::string(name));
    }
    return Result<ServiceInfo>::ok(entry->info);
}

ServiceBase* ServiceManager::get_service(std::string_view name) const {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto* entry = impl_->find_entry(name);
    return entry ? entry->service.get() : nullptr;
}

Result<void> ServiceManager::set_resource_quota(std::string_view name,
                                                  const ResourceQuota& quota) {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto* entry = impl_->find_entry(name);
    if (!entry) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                  "Service not found: " + std::string(name));
    }
    entry->quota = quota;
    return Result<void>::ok();
}

std::vector<ServiceManager::ResourceUsage> ServiceManager::get_resource_usage() const {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    std::vector<ResourceUsage> result;
    for (const auto& [name, entry] : impl_->services) {
        result.push_back({name, entry.info.cpu_percent, entry.info.memory_mb});
    }
    return result;
}

Result<void> ServiceManager::add_dependency(std::string_view service,
                                              std::string_view dependency) {
    std::lock_guard<std::mutex> lock(impl_->mtx);
    auto* svc_entry = impl_->find_entry(service);
    auto* dep_entry = impl_->find_entry(dependency);
    if (!svc_entry || !dep_entry) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                  "Service or dependency not found");
    }

    // Detect circular dependency
    std::function<bool(const std::string&, const std::string&)> has_path =
        [&](const std::string& from, const std::string& to) -> bool {
        for (const auto& d : impl_->services[from].dependencies) {
            if (d == to) return true;
            if (has_path(d, to)) return true;
        }
        return false;
    };

    if (has_path(std::string(dependency), std::string(service))) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "Circular dependency detected");
    }

    svc_entry->dependencies.push_back(std::string(dependency));
    dep_entry->dependents.push_back(std::string(service));
    impl_->compute_init_order();

    return Result<void>::ok();
}

} // namespace qoosvc::manager
