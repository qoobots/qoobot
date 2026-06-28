#pragma once

#include "result.h"
#include <atomic>
#include <string>
#include <string_view>

namespace qoosvc {

/**
 * ServiceState — lifecycle states for qoosvc services.
 */
enum class ServiceState : uint8_t {
    UNINITIALIZED,
    INITIALIZING,
    RUNNING,
    PAUSED,
    STOPPING,
    STOPPED,
    ERROR
};

/**
 * ServiceBase — base class for all qoosvc services.
 * Provides lifecycle management, health checking, and configuration.
 */
class ServiceBase {
public:
    explicit ServiceBase(std::string_view name) : name_(name) {}
    virtual ~ServiceBase() = default;

    // --- Lifecycle ---

    virtual Result<void> initialize() {
        if (state_ != ServiceState::UNINITIALIZED) {
            return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                     "Service already initialized");
        }
        state_ = ServiceState::INITIALIZING;
        auto result = on_initialize();
        if (result.is_ok()) {
            state_ = ServiceState::RUNNING;
        } else {
            state_ = ServiceState::ERROR;
        }
        return result;
    }

    virtual Result<void> start() {
        if (state_ != ServiceState::RUNNING && state_ != ServiceState::PAUSED) {
            return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                     "Service not in runnable state");
        }
        return on_start();
    }

    virtual Result<void> pause() {
        if (state_ != ServiceState::RUNNING) {
            return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                     "Service not running");
        }
        state_ = ServiceState::PAUSED;
        return on_pause();
    }

    virtual Result<void> resume() {
        if (state_ != ServiceState::PAUSED) {
            return Result<void>::err(ErrorCode::INVALID_ARGUMENT,
                                     "Service not paused");
        }
        state_ = ServiceState::RUNNING;
        return on_resume();
    }

    virtual Result<void> stop() {
        state_ = ServiceState::STOPPING;
        auto result = on_stop();
        state_ = result.is_ok() ? ServiceState::STOPPED : ServiceState::ERROR;
        return result;
    }

    // --- Health ---

    /**
     * Perform a health check. Returns true if service is healthy.
     */
    virtual bool health_check() {
        return state_ == ServiceState::RUNNING || state_ == ServiceState::PAUSED;
    }

    // --- Accessors ---

    const std::string& name() const { return name_; }
    ServiceState state() const { return state_; }
    bool is_running() const { return state_ == ServiceState::RUNNING; }

protected:
    // Subclass hooks
    virtual Result<void> on_initialize() { return Result<void>::ok(); }
    virtual Result<void> on_start() { return Result<void>::ok(); }
    virtual Result<void> on_pause() { return Result<void>::ok(); }
    virtual Result<void> on_resume() { return Result<void>::ok(); }
    virtual Result<void> on_stop() { return Result<void>::ok(); }

    std::string name_;
    std::atomic<ServiceState> state_{ServiceState::UNINITIALIZED};
};

} // namespace qoosvc
