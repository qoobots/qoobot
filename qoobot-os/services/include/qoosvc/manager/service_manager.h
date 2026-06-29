#pragma once

#include "qoosvc/common/result.h"
#include "qoosvc/common/service_base.h"
#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace qoosvc::manager {

/**
 * ServiceInfo — metadata for a registered service.
 */
struct ServiceInfo {
    std::string name;
    ServiceState state = ServiceState::UNINITIALIZED;
    double cpu_percent = 0.0;
    size_t memory_mb = 0;
    std::string version;
    std::string description;
    bool auto_restart = true;
    int restart_count = 0;
    int max_restarts = 3;
};

/**
 * ResourceQuota — resource limits for a service.
 */
struct ResourceQuota {
    double max_cpu_percent = 100.0;
    size_t max_memory_mb = 0;
    size_t max_disk_mb = 0;
    int32_t priority = 0;  // lower = higher priority
};

/**
 * ServiceManager — manages lifecycle, health, and resources for all qoosvc services.
 *
 * Responsibilities:
 *  - Service registration and discovery
 *  - Lifecycle orchestration (start/stop/pause/resume all or individual)
 *  - Health monitoring with automatic restart
 *  - Resource quota enforcement
 *  - Dependency ordering
 */
class ServiceManager {
public:
    ServiceManager();
    ~ServiceManager();

    // --- Registration ---

    /**
     * Register a service with the manager.
     */
    Result<void> register_service(std::unique_ptr<ServiceBase> service,
                                   const ServiceInfo& info = {});

    /**
     * Register a service with resource quota.
     */
    Result<void> register_service(std::unique_ptr<ServiceBase> service,
                                   const ServiceInfo& info,
                                   const ResourceQuota& quota);

    /**
     * Unregister a service by name.
     */
    Result<void> unregister_service(std::string_view name);

    // --- Lifecycle ---

    /**
     * Initialize all registered services in dependency order.
     */
    Result<void> initialize_all();

    /**
     * Start all registered services.
     */
    Result<void> start_all();

    /**
     * Start a specific service by name.
     */
    Result<void> start_service(std::string_view name);

    /**
     * Stop all services (reverse dependency order).
     */
    Result<void> stop_all();

    /**
     * Stop a specific service by name.
     */
    Result<void> stop_service(std::string_view name);

    /**
     * Pause a specific service.
     */
    Result<void> pause_service(std::string_view name);

    /**
     * Resume a specific service.
     */
    Result<void> resume_service(std::string_view name);

    /**
     * Restart a specific service.
     */
    Result<void> restart_service(std::string_view name);

    // --- Health ---

    /**
     * Run a health check on all services.
     * @return map of service name to healthy/unhealthy.
     */
    std::unordered_map<std::string, bool> check_all_health();

    /**
     * Start continuous health monitoring on a background thread.
     * @param interval_ms check interval in milliseconds.
     * @param on_unhealthy callback invoked when a service becomes unhealthy.
     */
    void start_health_monitor(std::chrono::milliseconds interval_ms,
                               std::function<void(std::string_view)> on_unhealthy = {});

    /**
     * Stop continuous health monitoring.
     */
    void stop_health_monitor();

    // --- Query ---

    /**
     * List all registered services and their states.
     */
    std::vector<ServiceInfo> list_services() const;

    /**
     * Get detailed info for a specific service.
     */
    Result<ServiceInfo> get_service_info(std::string_view name) const;

    /**
     * Get the raw ServiceBase pointer (for advanced use).
     */
    ServiceBase* get_service(std::string_view name) const;

    // --- Resource ---

    /**
     * Set resource quota for a service.
     */
    Result<void> set_resource_quota(std::string_view name, const ResourceQuota& quota);

    /**
     * Get current resource usage for all services.
     */
    struct ResourceUsage {
        std::string name;
        double cpu_percent;
        size_t memory_mb;
    };
    std::vector<ResourceUsage> get_resource_usage() const;

    // --- Dependency ---

    /**
     * Declare that 'service' depends on 'dependency'.
     * The dependency will be started first and stopped last.
     */
    Result<void> add_dependency(std::string_view service, std::string_view dependency);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace qoosvc::manager
