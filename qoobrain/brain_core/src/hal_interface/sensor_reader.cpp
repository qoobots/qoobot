// hal_interface/sensor_reader.cpp — Sensor data acquisition
#include "brain_core/hal_interface/sensor_reader.h"
#include <iostream>
#include <algorithm>

namespace brain_core {

SensorReader::SensorReader()
{
    std::cout << "[SensorReader] Initialized." << std::endl;
}

void SensorReader::registerSensor(const SensorConfig& config)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _sensors.push_back(config);
    std::cout << "[SensorReader] Registered sensor: " << config.name
              << " (type=" << static_cast<int>(config.type) << ")" << std::endl;
}

bool SensorReader::startSensor(const std::string& name)
{
    std::lock_guard<std::mutex> lock(_mutex);
    for (auto& s : _sensors) {
        if (s.name == name) {
            s.enabled = true;
            std::cout << "[SensorReader] Started: " << name
                      << " at " << s.update_rate_hz << " Hz" << std::endl;
            return true;
        }
    }
    return false;
}

void SensorReader::stopSensor(const std::string& name)
{
    std::lock_guard<std::mutex> lock(_mutex);
    for (auto& s : _sensors) {
        if (s.name == name) {
            s.enabled = false;
            return;
        }
    }
}

void SensorReader::stopAll()
{
    std::lock_guard<std::mutex> lock(_mutex);
    for (auto& s : _sensors) s.enabled = false;
    std::cout << "[SensorReader] All sensors stopped." << std::endl;
}

SensorFrame SensorReader::getLatestFrame(const std::string& name) const
{
    std::lock_guard<std::mutex> lock(_mutex);
    auto it = _latest_frames.find(name);
    if (it != _latest_frames.end()) return it->second;

    // Return mock frame
    SensorFrame frame;
    frame.source_id = name;
    frame.width  = 640;
    frame.height = 480;
    frame.stamp  = std::chrono::system_clock::now();
    return frame;
}

void SensorReader::onFrame(const std::string& sensor_name, FrameCallback cb)
{
    std::lock_guard<std::mutex> lock(_mutex);
    _callbacks[sensor_name] = std::move(cb);
}

std::vector<std::string> SensorReader::listSensors() const
{
    std::lock_guard<std::mutex> lock(_mutex);
    std::vector<std::string> names;
    for (const auto& s : _sensors) names.push_back(s.name);
    std::sort(names.begin(), names.end());
    return names;
}

} // namespace brain_core
