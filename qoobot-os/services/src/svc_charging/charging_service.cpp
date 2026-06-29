#include "qoosvc/charging/charging_service.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <mutex>

namespace qoosvc::charging {

struct ChargingService::Impl {
    std::vector<ChargingDock> docks;
    ChargingStatus status;
    WirelessChargingConfig wireless_config;
    std::function<void(const ChargingStatus&)> status_callback;
    mutable std::mutex mutex;
};

ChargingService::ChargingService()
    : ServiceBase("charging_service"), impl_(std::make_unique<Impl>()) {
    strategy_.mode = ChargingMode::THRESHOLD;
    strategy_.low_battery_threshold = 0.20;
    strategy_.full_battery_threshold = 0.95;
}

ChargingService::~ChargingService() { stop(); }

Result<void> ChargingService::configure(const ChargingStrategy& strategy) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    strategy_ = strategy;
    return Result<void>::ok();
}

// ========================================================================
// Autonomous Return-to-Dock
// ========================================================================

Result<void> ChargingService::return_to_dock() {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->docks.empty()) {
        return Result<void>::err(ErrorCode::CHARGE_DOCK_NOT_FOUND, "No docks registered");
    }

    // Find nearest available dock
    double min_dist = std::numeric_limits<double>::max();
    const ChargingDock* nearest = nullptr;

    for (const auto& dock : impl_->docks) {
        if (!dock.is_available) continue;
        // In production, get current pose from SLAM
        double dist = dock.pose.distance_to({0, 0, 0, 0, 0, 0, "map"});
        if (dist < min_dist) {
            min_dist = dist;
            nearest = &dock;
        }
    }

    if (!nearest) {
        return Result<void>::err(ErrorCode::CHARGE_DOCK_NOT_FOUND, "No available dock");
    }

    return return_to_dock(nearest->dock_id);
}

Result<void> ChargingService::return_to_dock(const std::string& dock_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->docks.begin(), impl_->docks.end(),
        [&](const ChargingDock& d) { return d.dock_id == dock_id; });

    if (it == impl_->docks.end()) {
        return Result<void>::err(ErrorCode::CHARGE_DOCK_NOT_FOUND, "Dock not found: " + dock_id);
    }

    current_state_ = ChargingState::SEARCHING_DOCK;
    impl_->status.state = ChargingState::SEARCHING_DOCK;
    impl_->status.dock_id = dock_id;

    // Phase 1: Navigate to approach point
    current_state_ = ChargingState::APPROACHING;
    impl_->status.state = ChargingState::APPROACHING;

    // Phase 2: Detect dock precisely
    auto detection = detect_dock();
    if (detection.is_err()) {
        current_state_ = ChargingState::ERROR;
        return Result<void>::err(detection.error_code(), detection.error_message());
    }

    // Phase 3: Fine alignment
    current_state_ = ChargingState::ALIGNING;
    impl_->status.state = ChargingState::ALIGNING;

    // Phase 4: Dock connection
    current_state_ = ChargingState::DOCKED;
    impl_->status.state = ChargingState::DOCKED;
    impl_->status.dock_connected = true;
    it->last_docked_us = std::chrono::duration_cast<std::chrono::microseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    // Phase 5: Start charging
    current_state_ = ChargingState::CHARGING;
    impl_->status.state = ChargingState::CHARGING;
    impl_->status.charging_power_w = 60.0;  // Standard charging power
    impl_->status.voltage_v = 24.0;
    impl_->status.current_a = 2.5;

    if (impl_->status_callback) {
        impl_->status_callback(impl_->status);
    }

    return Result<void>::ok();
}

Result<void> ChargingService::cancel_return() {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    current_state_ = ChargingState::IDLE;
    impl_->status.state = ChargingState::IDLE;
    return Result<void>::ok();
}

// ========================================================================
// Dock Detection
// ========================================================================

Result<DockDetectionResult> ChargingService::detect_dock() {
    DockDetectionResult result;

    // In production, this would:
    // 1. Use camera to detect ArUco/QR marker on dock
    // 2. Use IR sensor for beacon detection
    // 3. Use LiDAR for geometric feature matching

    // Simplified: check registered docks
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (impl_->docks.empty()) {
        return Result<DockDetectionResult>::err(ErrorCode::CHARGE_DOCK_NOT_FOUND,
                                                 "No docks registered");
    }

    // Assume first dock is detected (in production: sensor-based detection)
    result.detected = true;
    result.dock_pose = impl_->docks[0].pose;
    result.confidence = 0.9;
    result.distance_m = 1.5;  // placeholder
    result.method = DockDetectionMethod::VISUAL_MARKER;

    return result;
}

Result<void> ChargingService::register_dock(const ChargingDock& dock) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->docks.begin(), impl_->docks.end(),
        [&](const ChargingDock& d) { return d.dock_id == dock.dock_id; });

    if (it != impl_->docks.end()) {
        *it = dock;  // Update existing
    } else {
        impl_->docks.push_back(dock);
    }
    return Result<void>::ok();
}

Result<void> ChargingService::remove_dock(const std::string& dock_id) {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    auto it = std::find_if(impl_->docks.begin(), impl_->docks.end(),
        [&](const ChargingDock& d) { return d.dock_id == dock_id; });

    if (it == impl_->docks.end()) {
        return Result<void>::err(ErrorCode::CHARGE_DOCK_NOT_FOUND, "Dock not found");
    }

    impl_->docks.erase(it);
    return Result<void>::ok();
}

std::vector<ChargingDock> ChargingService::get_docks() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->docks;
}

// ========================================================================
// Charging Strategy
// ========================================================================

Result<void> ChargingService::set_charging_mode(ChargingMode mode) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    strategy_.mode = mode;
    return Result<void>::ok();
}

Result<void> ChargingService::add_schedule(const ChargingSchedule& schedule) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    strategy_.schedules.push_back(schedule);
    return Result<void>::ok();
}

Result<void> ChargingService::remove_schedule(size_t index) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    if (index >= strategy_.schedules.size()) {
        return Result<void>::err(ErrorCode::INVALID_ARGUMENT, "Invalid schedule index");
    }
    strategy_.schedules.erase(strategy_.schedules.begin() + index);
    return Result<void>::ok();
}

bool ChargingService::should_charge(double battery_level) const {
    std::lock_guard<std::mutex> lock(impl_->mutex);

    if (battery_level <= strategy_.low_battery_threshold) return true;

    if (strategy_.mode == ChargingMode::SCHEDULED) {
        // Check if current time is within a schedule
        // In production: compare system time against schedules
        return false;
    }

    return battery_level < strategy_.full_battery_threshold;
}

// ========================================================================
// Wireless Charging
// ========================================================================

Result<void> ChargingService::enable_wireless_charging(bool enable) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->wireless_config.enabled = enable;
    return Result<void>::ok();
}

Result<void> ChargingService::configure_wireless(const WirelessChargingConfig& config) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->wireless_config = config;
    return Result<void>::ok();
}

// ========================================================================
// Status
// ========================================================================

ChargingStatus ChargingService::get_status() const {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    return impl_->status;
}

void ChargingService::on_status_change(std::function<void(const ChargingStatus&)> callback) {
    std::lock_guard<std::mutex> lock(impl_->mutex);
    impl_->status_callback = std::move(callback);
}

// ========================================================================
// Service Lifecycle
// ========================================================================

Result<void> ChargingService::on_initialize() {
    current_state_ = ChargingState::IDLE;
    impl_->status.state = ChargingState::IDLE;
    return Result<void>::ok();
}

Result<void> ChargingService::on_stop() {
    if (is_charging()) {
        current_state_ = ChargingState::UNDOCKING;
    }
    current_state_ = ChargingState::IDLE;
    return Result<void>::ok();
}

} // namespace qoosvc::charging
