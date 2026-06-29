#pragma once

#include <cstddef>
#include <cstdint>

namespace qoosvc::manager {

/**
 * IPC message types for DDS bridge communication.
 */
enum class IpcMessageType : uint32_t {
    // Lifecycle commands
    CMD_START_SERVICE = 0x0100,
    CMD_STOP_SERVICE = 0x0101,
    CMD_PAUSE_SERVICE = 0x0102,
    CMD_RESUME_SERVICE = 0x0103,
    CMD_RESTART_SERVICE = 0x0104,

    // Status reports
    STATUS_SERVICE_STATE = 0x0200,
    STATUS_HEALTH_REPORT = 0x0201,
    STATUS_RESOURCE_USAGE = 0x0202,

    // Heartbeat
    HEARTBEAT = 0x0300,
    HEARTBEAT_ACK = 0x0301,
};

/**
 * DDS bridge configuration.
 */
struct DdsBridgeConfig {
    std::string domain_id = "0";
    std::string qos_profile = "qoosvc_default";
    std::chrono::milliseconds heartbeat_interval{1000};
    int32_t max_missed_heartbeats = 5;
};

} // namespace qoosvc::manager
