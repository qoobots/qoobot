// hal_interface/sensor_reader.h — Sensor data acquisition interface
#pragma once

#include "brain_core/core_types.h"
#include <string>
#include <vector>
#include <functional>
#include <atomic>

namespace brain_core {

/// Sensor types supported by the HAL.
enum class SensorType {
    RGB_CAMERA,
    DEPTH_CAMERA,
    RGBD_CAMERA,
    LIDAR,
    FORCE_TORQUE,
    JOINT_ENCODER,
    IMU,
};

/// Sensor configuration.
struct SensorConfig {
    std::string name;
    SensorType  type;
    int         update_rate_hz{30};
    bool        enabled{true};
};

class SensorReader {
public:
    using FrameCallback = std::function<void(const SensorFrame&)>;

    SensorReader();

    /// Register a sensor.
    void registerSensor(const SensorConfig& config);

    /// Start reading from a sensor (background thread).
    bool startSensor(const std::string& name);

    /// Stop reading from a sensor.
    void stopSensor(const std::string& name);

    /// Stop all sensors.
    void stopAll();

    /// Get latest frame from a sensor.
    SensorFrame getLatestFrame(const std::string& name) const;

    /// Register callback for new frames.
    void onFrame(const std::string& sensor_name, FrameCallback cb);

    /// List registered sensors.
    std::vector<std::string> listSensors() const;

private:
    std::vector<SensorConfig> _sensors;
    std::unordered_map<std::string, SensorFrame> _latest_frames;
    std::unordered_map<std::string, FrameCallback> _callbacks;
    mutable std::mutex _mutex;
};

} // namespace brain_core
