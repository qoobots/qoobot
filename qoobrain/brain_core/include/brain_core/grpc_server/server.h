// grpc_server/server.h — C++ gRPC server for robot control services
#pragma once

#include <string>
#include <atomic>
#include <memory>

namespace brain_core {

/// gRPC server that hosts Control, Safety, and Perception services
/// for the brain_core C++ process.
/// Acts as the bridge between external clients (brain_viz, brain_sdk)
/// and the onboard real-time modules.
class GRPCServer {
public:
    GRPCServer();

    /// Start the server on the given address.
    /// Default: 0.0.0.0:50052 (different port from brain_ai at 50051).
    bool start(const std::string& address = "0.0.0.0:50052");

    /// Stop the server gracefully.
    void stop();

    /// Check if the server is running.
    bool isRunning() const { return _running; }

    /// Get the listening address.
    const std::string& address() const { return _address; }

    /// Register all service implementations.
    void registerServices();

private:
    std::string _address;
    std::atomic<bool> _running{false};
    void* _server_impl{nullptr};  // grpc::Server*
};

} // namespace brain_core
