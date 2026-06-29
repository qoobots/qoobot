#pragma once

#include <string>
#include <string_view>

namespace qoosvc {

/**
 * Unified error codes for all qoosvc services.
 */
enum class ErrorCode : int32_t {
    // Success
    OK = 0,

    // General (100-199)
    UNKNOWN = 100,
    NOT_IMPLEMENTED = 101,
    INVALID_ARGUMENT = 102,
    TIMEOUT = 103,
    RESOURCE_EXHAUSTED = 104,
    INTERNAL = 105,

    // Voice (200-299)
    VOICE_WAKE_WORD_NOT_FOUND = 200,
    VOICE_ASR_FAILED = 201,
    VOICE_NLU_NO_INTENT = 202,
    VOICE_TTS_FAILED = 203,
    VOICE_SPEAKER_UNKNOWN = 204,

    // Navigation (300-399)
    NAV_NO_PATH = 300,
    NAV_GOAL_UNREACHABLE = 301,
    NAV_COLLISION_IMMINENT = 302,
    NAV_LOCALIZATION_LOST = 303,
    NAV_ZONE_RESTRICTED = 304,

    // Spatial (400-499)
    SPATIAL_MAP_NOT_LOADED = 400,
    SPATIAL_SLAM_FAILED = 401,
    SPATIAL_OBJECT_NOT_FOUND = 402,

    // Diagnostics (500-599)
    DIAG_POST_FAILED = 500,
    DIAG_SENSOR_FAULT = 501,
    DIAG_MOTOR_FAULT = 502,
    DIAG_BATTERY_CRITICAL = 503,
    DIAG_TEMPERATURE_HIGH = 504,

    // HMI (600-699)
    HMI_LED_FAULT = 600,
    HMI_DISPLAY_FAULT = 601,

    // Charging (700-799)
    CHARGE_DOCK_NOT_FOUND = 700,
    CHARGE_DOCK_FAILED = 701,
    CHARGE_BATTERY_FULL = 702,

    // People (800-899)
    PEOPLE_FACE_NOT_RECOGNIZED = 800,
    PEOPLE_TRACKING_LOST = 801,

    // Multi-robot (900-999)
    MR_DISCOVERY_FAILED = 900,
    MR_TASK_REJECTED = 901,
};

/**
 * Get a human-readable description for an error code.
 */
inline std::string_view error_code_message(ErrorCode code) {
    switch (code) {
    case ErrorCode::OK: return "Success";
    case ErrorCode::UNKNOWN: return "Unknown error";
    case ErrorCode::NOT_IMPLEMENTED: return "Not implemented";
    case ErrorCode::INVALID_ARGUMENT: return "Invalid argument";
    case ErrorCode::TIMEOUT: return "Operation timed out";
    case ErrorCode::VOICE_WAKE_WORD_NOT_FOUND: return "Wake word not found";
    case ErrorCode::VOICE_ASR_FAILED: return "ASR failed";
    case ErrorCode::NAV_NO_PATH: return "No path found";
    case ErrorCode::NAV_GOAL_UNREACHABLE: return "Goal unreachable";
    case ErrorCode::NAV_COLLISION_IMMINENT: return "Collision imminent";
    case ErrorCode::DIAG_POST_FAILED: return "POST self-test failed";
    case ErrorCode::DIAG_SENSOR_FAULT: return "Sensor fault detected";
    case ErrorCode::DIAG_MOTOR_FAULT: return "Motor fault detected";
    case ErrorCode::DIAG_BATTERY_CRITICAL: return "Battery level critical";
    default: return "Unknown error code";
    }
}

} // namespace qoosvc
