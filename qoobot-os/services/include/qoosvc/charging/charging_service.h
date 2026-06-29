#pragma once

#include "charge_types.h"
#include "../common/result.h"
#include "../common/service_base.h"
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace qoosvc::charging {

class ChargingService : public ServiceBase {
public:
    ChargingService();
    ~ChargingService() override;

    Result<void> configure(const ChargingStrategy& strategy);
    const ChargingStrategy& strategy() const { return strategy_; }

    // ========================================================================
    // Autonomous Return-to-Dock
    // ========================================================================
    Result<void> return_to_dock();
    Result<void> return_to_dock(const std::string& dock_id);
    Result<void> cancel_return();

    // ========================================================================
    // Dock Detection
    // ========================================================================
    Result<DockDetectionResult> detect_dock();
    Result<void> register_dock(const ChargingDock& dock);
    Result<void> remove_dock(const std::string& dock_id);
    std::vector<ChargingDock> get_docks() const;

    // ========================================================================
    // Charging Strategy
    // ========================================================================
    Result<void> set_charging_mode(ChargingMode mode);
    Result<void> add_schedule(const ChargingSchedule& schedule);
    Result<void> remove_schedule(size_t index);
    bool should_charge(double battery_level) const;

    // ========================================================================
    // Wireless Charging
    // ========================================================================
    Result<void> enable_wireless_charging(bool enable);
    Result<void> configure_wireless(const WirelessChargingConfig& config);

    // ========================================================================
    // Status
    // ========================================================================
    ChargingStatus get_status() const;
    ChargingState state() const { return current_state_; }
    void on_status_change(std::function<void(const ChargingStatus&)> callback);

    // ========================================================================
    // Service Lifecycle
    // ========================================================================
    bool is_charging() const { return current_state_ == ChargingState::CHARGING; }
    bool is_docked() const { return current_state_ == ChargingState::DOCKED || is_charging(); }

protected:
    Result<void> on_initialize() override;
    Result<void> on_stop() override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
    ChargingStrategy strategy_;
    ChargingState current_state_ = ChargingState::IDLE;
};

} // namespace qoosvc::charging
