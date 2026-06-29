#include "qoogear/peripheral_base.h"
#include <sstream>
#include <iomanip>

namespace qoogear {

// ---- AccessoryId ----

std::string AccessoryId::to_string() const {
    std::ostringstream oss;
    oss << std::hex << std::uppercase << std::setfill('0')
        << std::setw(4) << vendor_id << ":"
        << std::setw(4) << product_id << ":"
        << std::setw(8) << serial_number;
    return oss.str();
}

// ---- AccessoryBase ----

AccessoryBase::AccessoryBase(const AccessoryInfo& info) : info_(info) {}

uint32_t AccessoryBase::uptime_seconds() const {
    if (state_.load() == AccessoryState::DISCONNECTED) return 0;
    auto now = std::chrono::steady_clock::now();
    return static_cast<uint32_t>(
        std::chrono::duration_cast<std::chrono::seconds>(now - start_time_).count());
}

bool AccessoryBase::connect() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (state_.load() != AccessoryState::DISCONNECTED) return false;

    set_state(AccessoryState::CONNECTING);
    try {
        if (!initialize()) {
            add_error("Initialize failed");
            set_state(AccessoryState::ERROR);
            return false;
        }
        initialized_ = true;
        start_time_ = std::chrono::steady_clock::now();
        set_state(AccessoryState::CONNECTED);
        set_state(AccessoryState::READY);
        fire_event("connected");
        return true;
    } catch (const std::exception& e) {
        add_error(std::string("Connection failed: ") + e.what());
        set_state(AccessoryState::ERROR);
        return false;
    }
}

bool AccessoryBase::activate() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (state_.load() != AccessoryState::READY) return false;
    set_state(AccessoryState::ACTIVE);
    return true;
}

bool AccessoryBase::deactivate() {
    std::lock_guard<std::mutex> lock(mutex_);
    if (state_.load() != AccessoryState::ACTIVE) return false;
    set_state(AccessoryState::READY);
    return true;
}

bool AccessoryBase::disconnect() {
    std::lock_guard<std::mutex> lock(mutex_);
    try {
        if (state_.load() == AccessoryState::ACTIVE) {
            set_state(AccessoryState::READY);
        }
        shutdown();
        initialized_ = false;
        set_state(AccessoryState::DISCONNECTED);
        fire_event("disconnected");
        return true;
    } catch (const std::exception& e) {
        add_error(std::string("Disconnection failed: ") + e.what());
        return false;
    }
}

bool AccessoryBase::emergency_stop() {
    std::lock_guard<std::mutex> lock(mutex_);
    set_state(AccessoryState::EMERGENCY_STOP);
    return true;
}

void AccessoryBase::register_capability(const Capability& cap) {
    std::lock_guard<std::mutex> lock(mutex_);
    capabilities_[cap.capability_id] = cap;
}

const Capability* AccessoryBase::get_capability(const std::string& cap_id) const {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = capabilities_.find(cap_id);
    return (it != capabilities_.end()) ? &it->second : nullptr;
}

float AccessoryBase::get_capability_value(const std::string& cap_id) const {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = capabilities_.find(cap_id);
    if (it == capabilities_.end()) return 0.0f;
    return read_capability(cap_id);
}

bool AccessoryBase::set_capability_value(const std::string& cap_id, float value) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = capabilities_.find(cap_id);
    if (it == capabilities_.end()) {
        add_error("Unknown capability: " + cap_id);
        return false;
    }
    if (it->second.is_readonly) {
        add_error("Capability " + cap_id + " is read-only");
        return false;
    }
    if (value < it->second.min_value || value > it->second.max_value) {
        add_error("Value out of range for " + cap_id);
        return false;
    }
    return write_capability(cap_id, value);
}

AccessoryStatus AccessoryBase::get_status() const {
    std::lock_guard<std::mutex> lock(mutex_);
    AccessoryStatus status;
    status.state = state_.load();
    status.uptime_seconds = uptime_seconds();
    status.metrics = metrics_;
    status.active_errors = errors_;
    return status;
}

std::string AccessoryBase::get_health() const {
    return std::string("{\"state\":\"") + to_string(state_.load()) +
           "\",\"is_healthy\":" + (state_.load() < AccessoryState::ERROR ? "true" : "false") + "}";
}

void AccessoryBase::clear_errors() {
    std::lock_guard<std::mutex> lock(mutex_);
    errors_.clear();
}

void AccessoryBase::on(const std::string& event, EventCallback callback) {
    std::lock_guard<std::mutex> lock(mutex_);
    event_handlers_[event].push_back(std::move(callback));
}

void AccessoryBase::off(const std::string& event) {
    std::lock_guard<std::mutex> lock(mutex_);
    event_handlers_.erase(event);
}

void AccessoryBase::set_state(AccessoryState new_state) {
    auto old = state_.exchange(new_state);
    if (old != new_state) {
        fire_event("state_change", to_string(new_state));
    }
}

void AccessoryBase::add_error(const std::string& message) {
    errors_.push_back(message);
    fire_event("error", message);
}

void AccessoryBase::update_metric(const std::string& name, float value) {
    metrics_[name] = value;
}

void AccessoryBase::fire_event(const std::string& event, const std::string& data) {
    auto it = event_handlers_.find(event);
    if (it != event_handlers_.end()) {
        for (auto& cb : it->second) {
            try { cb(event, data); } catch (...) {}
        }
    }
}

// ---- GripperAccessory ----

GripperAccessory::GripperAccessory(const AccessoryInfo& info) : AccessoryBase(info) {
    info_.type = AccessoryType::END_EFFECTOR;
    register_capability({"grip_force", "Grip Force", "N", 0.0f, 200.0f, 50.0f});
    register_capability({"grip_position", "Grip Position", "mm", 0.0f, 100.0f, 0.0f});
    register_capability({"grip_speed", "Grip Speed", "mm/s", 1.0f, 500.0f, 100.0f});
    register_capability({"temperature", "Temperature", "C", 0.0f, 150.0f, 0.0f, true});
    register_capability({"current", "Current", "A", 0.0f, 10.0f, 0.0f, true});
}

bool GripperAccessory::grasp(float force_n, float speed_percent, float position_mm) {
    if (!is_active()) return false;
    set_capability_value("grip_speed", speed_percent * 5.0f);
    if (position_mm > 0) set_capability_value("grip_position", position_mm);
    return set_capability_value("grip_force", force_n);
}

bool GripperAccessory::release(float speed_percent, float open_position_mm) {
    if (!is_active()) return false;
    set_capability_value("grip_force", 0.0f);
    set_capability_value("grip_speed", speed_percent * 5.0f);
    return set_capability_value("grip_position", open_position_mm);
}

bool GripperAccessory::move_to(float position_mm, float speed_percent) {
    if (!is_active()) return false;
    set_capability_value("grip_speed", speed_percent * 5.0f);
    return set_capability_value("grip_position", position_mm);
}

bool GripperAccessory::stop(bool emergency) {
    if (emergency) return emergency_stop();
    set_capability_value("grip_speed", 0.0f);
    return true;
}

} // namespace qoogear
