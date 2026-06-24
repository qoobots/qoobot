// service_adapter.h — ROS 2 Service client/server abstraction
#pragma once

#include <string>
#include <memory>
#include <functional>
#include <mutex>
#include <unordered_map>

namespace brain_core {

/**
 * @brief Wraps ROS 2 service client and server creation/management.
 */
class ServiceAdapter {
public:
    using ServiceCallback = std::function<std::string(const std::string& request)>;

    ServiceAdapter();
    ~ServiceAdapter();

    bool initialize(void* node_handle);

    // ── Service Server ────────────────────────────────────
    bool createService(const std::string& service_name, const std::string& srv_type,
                       ServiceCallback handler);
    void removeService(const std::string& service_name);

    // ── Service Client ────────────────────────────────────
    bool createClient(const std::string& service_name, const std::string& srv_type);
    std::string call(const std::string& service_name, const std::string& request_data,
                     int timeout_ms = 1000);
    bool isServiceAvailable(const std::string& service_name, int timeout_ms = 5000);
    void removeClient(const std::string& service_name);

    // ── Query ─────────────────────────────────────────────
    std::vector<std::string> listServices() const;
    std::vector<std::string> listClients() const;

private:
    void* node_handle_{nullptr};
    bool  initialized_{false};

    struct SrvEntry {
        std::string     name;
        std::string     srv_type;
        void*           raw_service{nullptr};
        ServiceCallback handler;
    };
    struct CliEntry {
        std::string name;
        std::string srv_type;
        void*       raw_client{nullptr};
    };

    std::unordered_map<std::string, SrvEntry> servers_;
    std::unordered_map<std::string, CliEntry> clients_;
    mutable std::mutex mutex_;
};

} // namespace brain_core
