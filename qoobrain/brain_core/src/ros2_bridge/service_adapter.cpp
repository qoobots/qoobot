// service_adapter.cpp — Implementation
#include "brain_core/ros2_bridge/service_adapter.h"
#include <iostream>

namespace brain_core {

ServiceAdapter::ServiceAdapter()  = default;
ServiceAdapter::~ServiceAdapter() = default;

bool ServiceAdapter::initialize(void* node_handle) {
    if (!node_handle) return false;
    node_handle_ = node_handle;
    initialized_ = true;
    std::cout << "[ServiceAdapter] Initialized." << std::endl;
    return true;
}

bool ServiceAdapter::createService(const std::string& service_name, const std::string& srv_type,
                                    ServiceCallback handler) {
    if (!initialized_) return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if (servers_.count(service_name)) return false;

    SrvEntry entry;
    entry.name        = service_name;
    entry.srv_type    = srv_type;
    entry.raw_service = reinterpret_cast<void*>(1); // stub
    entry.handler     = std::move(handler);
    servers_[service_name] = entry;
    std::cout << "[ServiceAdapter] Created service: " << service_name << std::endl;
    return true;
}

void ServiceAdapter::removeService(const std::string& service_name) {
    std::lock_guard<std::mutex> lock(mutex_);
    servers_.erase(service_name);
}

bool ServiceAdapter::createClient(const std::string& service_name, const std::string& srv_type) {
    if (!initialized_) return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if (clients_.count(service_name)) return false;

    CliEntry entry;
    entry.name       = service_name;
    entry.srv_type   = srv_type;
    entry.raw_client = reinterpret_cast<void*>(1); // stub
    clients_[service_name] = entry;
    std::cout << "[ServiceAdapter] Created client: " << service_name << std::endl;
    return true;
}

std::string ServiceAdapter::call(const std::string& service_name, const std::string& request_data, int timeout_ms) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = clients_.find(service_name);
    if (it == clients_.end()) return "";

    // Stub: forward to service server if local, else return empty
    auto srv = servers_.find(service_name);
    if (srv != servers_.end() && srv->second.handler) {
        return srv->second.handler(request_data);
    }
    (void)timeout_ms;
    return "{}";
}

bool ServiceAdapter::isServiceAvailable(const std::string& service_name, int timeout_ms) {
    std::lock_guard<std::mutex> lock(mutex_);
    (void)timeout_ms;
    return servers_.count(service_name) > 0;
}

void ServiceAdapter::removeClient(const std::string& service_name) {
    std::lock_guard<std::mutex> lock(mutex_);
    clients_.erase(service_name);
}

std::vector<std::string> ServiceAdapter::listServices() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<std::string> result;
    for (const auto& [k, _] : servers_) result.push_back(k);
    return result;
}

std::vector<std::string> ServiceAdapter::listClients() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<std::string> result;
    for (const auto& [k, _] : clients_) result.push_back(k);
    return result;
}

} // namespace brain_core
