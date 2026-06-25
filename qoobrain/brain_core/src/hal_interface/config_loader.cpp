// hal_interface/config_loader.cpp — YAML/JSON config loader
#include "brain_core/hal_interface/config_loader.h"
#include <iostream>
#include <sstream>
#include <fstream>
#include <algorithm>

namespace brain_core {

ConfigLoader::ConfigLoader()
{
    std::cout << "[ConfigLoader] Initialized." << std::endl;
}

bool ConfigLoader::loadYAML(const std::string& path)
{
    // Stub: simulate loading key-value pairs
    // Full build would use yaml-cpp library
    _last_file = path;

    // Mock Brain OS default config
    _values = {
        {"robot.arm.joints", "6"},
        {"robot.arm.max_velocity", "1.5"},
        {"robot.arm.max_acceleration", "3.0"},
        {"robot.gripper.max_force", "20.0"},
        {"safety.emergency_timeout_sec", "0.1"},
        {"safety.workspace.radius", "0.8"},
        {"llm.model", "qwen2.5-7b"},
        {"llm.backend", "tensorrt"},
        {"planner.default_strategy", "optimal"},
        {"perception.detector_model", "yolov11n"},
        {"perception.confidence_threshold", "0.6"},
        {"ros2.domain_id", "0"},
        {"ros2.node_name", "brain_core"},
    };

    _loaded = true;
    std::cout << "[ConfigLoader] Loaded " << _values.size()
              << " config keys from " << path << std::endl;
    return true;
}

bool ConfigLoader::loadJSON(const std::string& path)
{
    // Stub: converts to same key-value store
    return loadYAML(path);
}

std::string ConfigLoader::getString(const std::string& key,
                                     const std::string& default_val) const
{
    auto it = _values.find(key);
    return (it != _values.end()) ? it->second : default_val;
}

int ConfigLoader::getInt(const std::string& key, int default_val) const
{
    auto it = _values.find(key);
    if (it != _values.end()) {
        try { return std::stoi(it->second); }
        catch (...) {}
    }
    return default_val;
}

double ConfigLoader::getDouble(const std::string& key, double default_val) const
{
    auto it = _values.find(key);
    if (it != _values.end()) {
        try { return std::stod(it->second); }
        catch (...) {}
    }
    return default_val;
}

bool ConfigLoader::getBool(const std::string& key, bool default_val) const
{
    auto it = _values.find(key);
    if (it != _values.end()) {
        std::string v = it->second;
        std::transform(v.begin(), v.end(), v.begin(), ::tolower);
        return v == "true" || v == "1" || v == "yes";
    }
    return default_val;
}

std::vector<std::string> ConfigLoader::getStringArray(const std::string& key) const
{
    auto it = _values.find(key);
    if (it == _values.end()) return {};

    std::vector<std::string> result;
    std::stringstream ss(it->second);
    std::string item;
    while (std::getline(ss, item, ',')) {
        // Trim whitespace
        auto start = item.find_first_not_of(" \t");
        auto end   = item.find_last_not_of(" \t");
        if (start != std::string::npos) {
            result.push_back(item.substr(start, end - start + 1));
        }
    }
    return result;
}

bool ConfigLoader::hasKey(const std::string& key) const
{
    return _values.find(key) != _values.end();
}

std::vector<std::string> ConfigLoader::topLevelKeys() const
{
    std::vector<std::string> keys;
    for (const auto& [k, _] : _values) {
        auto dot = k.find('.');
        std::string top = (dot != std::string::npos) ? k.substr(0, dot) : k;
        if (std::find(keys.begin(), keys.end(), top) == keys.end()) {
            keys.push_back(top);
        }
    }
    std::sort(keys.begin(), keys.end());
    return keys;
}

void ConfigLoader::setValue(const std::string& key, const std::string& value)
{
    _values[key] = value;
}

bool ConfigLoader::reload()
{
    if (_last_file.empty()) return false;
    return loadYAML(_last_file);
}

} // namespace brain_core
