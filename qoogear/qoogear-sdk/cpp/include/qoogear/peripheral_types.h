#pragma once

/**
 * @file peripheral_types.h
 * @brief QooBot 配件类型定义 — C++17
 *
 * Made for QooBot (MFQ) 认证体系的配件基础类型定义。
 * 包含配件标识、类型枚举、能力描述、状态等核心数据结构。
 */

#include <cstdint>
#include <map>
#include <string>
#include <vector>

namespace qoogear {

// ============================================================================
// 枚举
// ============================================================================

/** 配件类型 */
enum class AccessoryType : uint8_t {
    END_EFFECTOR = 1,    // 末端执行器
    SENSOR = 2,          // 传感器模组
    WEARABLE = 3,        // 可穿戴设备
    POWER = 4,           // 电源配件
    MOBILITY = 5,        // 移动平台配件
    COMMUNICATION = 6,   // 通信配件
    TOOL = 7,            // 工具配件
};

/** 配件状态 */
enum class AccessoryState : uint8_t {
    DISCONNECTED = 0,
    CONNECTING = 1,
    CONNECTED = 2,
    READY = 3,
    ACTIVE = 4,
    ERROR = 5,
    EMERGENCY_STOP = 6,
    FIRMWARE_UPDATE = 7,
};

/** 物理接口 */
enum class PhysicalInterface : uint8_t {
    CAN_FD = 1,
    RS485 = 2,
    ETHERNET = 3,
    USB_3 = 4,
    I2C = 5,
    SPI = 6,
    BLUETOOTH_LE = 7,
    WIFI_DIRECT = 8,
    MAGSAFE = 9,
};

/** MFQ 认证等级 */
enum class MfqCertLevel : uint8_t {
    BASIC = 1,
    PREMIUM = 2,
    PRO = 3,
};

// ============================================================================
// 数据结构
// ============================================================================

/** 配件标识 */
struct AccessoryId {
    uint32_t vendor_id = 0;
    uint32_t product_id = 0;
    uint32_t serial_number = 0;
    uint32_t hardware_version = 1;

    std::string to_string() const;
};

/** 配件信息 */
struct AccessoryInfo {
    AccessoryId id;
    std::string name;
    std::string vendor_name;
    std::string model;
    std::string firmware_version{"0.0.1"};
    AccessoryType type{AccessoryType::END_EFFECTOR};
    PhysicalInterface phy_interface{PhysicalInterface::CAN_FD};
    std::string mfq_cert_hash;
    MfqCertLevel mfq_level{MfqCertLevel::BASIC};
};

/** 能力定义 */
struct Capability {
    std::string capability_id;
    std::string name;
    std::string description;
    std::string unit;
    float min_value = 0.0f;
    float max_value = 100.0f;
    float default_value = 0.0f;
    bool is_readonly = false;
    std::map<std::string, std::string> parameters;
};

/** 配件状态快照 */
struct AccessoryStatus {
    AccessoryState state{AccessoryState::DISCONNECTED};
    uint32_t uptime_seconds = 0;
    std::map<std::string, float> metrics;
    std::vector<std::string> active_errors;
    float cpu_usage_percent = 0.0f;
    float memory_usage_kb = 0.0f;
};

/** 电气规格 */
struct ElectricalSpec {
    float nominal_voltage_v = 48.0f;
    float max_current_a = 10.0f;
    float peak_power_w = 480.0f;
    float standby_power_w = 5.0f;
    bool supports_hotplug = true;
    std::string connector_type;
};

/** 机械规格 */
struct MechanicalSpec {
    float weight_kg = 1.0f;
    float width_mm = 100.0f;
    float height_mm = 100.0f;
    float depth_mm = 100.0f;
    std::string flange_type;
    float max_payload_kg = 5.0f;
    std::string material;
    std::string ip_rating{"IP54"};
};

// ============================================================================
// 工具函数
// ============================================================================

/** 状态名称转换 */
constexpr const char* to_string(AccessoryState state) {
    switch (state) {
        case AccessoryState::DISCONNECTED:  return "disconnected";
        case AccessoryState::CONNECTING:    return "connecting";
        case AccessoryState::CONNECTED:     return "connected";
        case AccessoryState::READY:         return "ready";
        case AccessoryState::ACTIVE:        return "active";
        case AccessoryState::ERROR:         return "error";
        case AccessoryState::EMERGENCY_STOP:return "emergency_stop";
        case AccessoryState::FIRMWARE_UPDATE:return "firmware_update";
        default:                            return "unknown";
    }
}

} // namespace qoogear
