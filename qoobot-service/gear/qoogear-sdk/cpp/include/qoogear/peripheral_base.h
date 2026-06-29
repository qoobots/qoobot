#pragma once

/**
 * @file peripheral_base.h
 * @brief 配件抽象基类 — C++17
 *
 * 所有第三方配件驱动都应继承此类。
 * 提供完整的生命周期管理、事件回调、状态追踪和健康监控。
 */

#include "peripheral_types.h"

#include <atomic>
#include <chrono>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace qoogear {

class AccessoryBase {
public:
    using EventCallback = std::function<void(const std::string& event, const std::string& data)>;

    explicit AccessoryBase(const AccessoryInfo& info = AccessoryInfo{});
    virtual ~AccessoryBase() = default;

    // ---- 属性 ----

    const AccessoryInfo& info() const { return info_; }
    AccessoryState state() const { return state_; }
    bool is_connected() const {
        auto s = state_.load();
        return s == AccessoryState::CONNECTED || s == AccessoryState::READY || s == AccessoryState::ACTIVE;
    }
    bool is_active() const { return state_.load() == AccessoryState::ACTIVE; }
    uint32_t uptime_seconds() const;

    // ---- 生命周期 ----

    bool connect();
    bool activate();
    bool deactivate();
    bool disconnect();
    bool emergency_stop();

    // ---- 能力管理 ----

    void register_capability(const Capability& cap);
    const Capability* get_capability(const std::string& cap_id) const;
    float get_capability_value(const std::string& cap_id) const;
    bool set_capability_value(const std::string& cap_id, float value);

    // ---- 状态 ----

    AccessoryStatus get_status() const;
    std::string get_health() const;
    void clear_errors();

    // ---- 事件 ----

    void on(const std::string& event, EventCallback callback);
    void off(const std::string& event);

    // ---- 抽象方法 ----

    virtual bool initialize() = 0;
    virtual void shutdown() = 0;
    virtual float read_capability(const std::string& cap_id) = 0;
    virtual bool write_capability(const std::string& cap_id, float value) = 0;

protected:
    void set_state(AccessoryState new_state);
    void add_error(const std::string& message);
    void update_metric(const std::string& name, float value);
    void fire_event(const std::string& event, const std::string& data = "");

    AccessoryInfo info_;
    std::atomic<AccessoryState> state_{AccessoryState::DISCONNECTED};

private:
    std::unordered_map<std::string, Capability> capabilities_;
    std::unordered_map<std::string, float> metrics_;
    std::vector<std::string> errors_;
    std::chrono::steady_clock::time_point start_time_;
    bool initialized_ = false;
    mutable std::mutex mutex_;
    std::unordered_map<std::string, std::vector<EventCallback>> event_handlers_;
};

// ============================================================================
// 末端执行器基类
// ============================================================================

class GripperAccessory : public AccessoryBase {
public:
    explicit GripperAccessory(const AccessoryInfo& info = AccessoryInfo{});

    bool grasp(float force_n = 50.0f, float speed_percent = 50.0f, float position_mm = 0.0f);
    bool release(float speed_percent = 50.0f, float open_position_mm = 100.0f);
    bool move_to(float position_mm, float speed_percent = 50.0f);
    bool stop(bool emergency = false);

    float grip_force() const { return get_capability_value("grip_force"); }
    float grip_position() const { return get_capability_value("grip_position"); }

    // 抽象方法桩实现
    bool initialize() override { return true; }
    void shutdown() override {}
    float read_capability(const std::string&) override { return 0.0f; }
    bool write_capability(const std::string&, float) override { return true; }
};

} // namespace qoogear
