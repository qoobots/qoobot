// hal_interface/config_loader.h — YAML/JSON config file loader
#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <any>

namespace brain_core {

/// Key-value configuration store loaded from YAML/JSON files.
class ConfigLoader {
public:
    ConfigLoader();

    /// Load configuration from a YAML file.
    bool loadYAML(const std::string& path);

    /// Load configuration from a JSON file.
    bool loadJSON(const std::string& path);

    /// Get a string value by dot-separated key (e.g., "robot.arm.joints").
    std::string getString(const std::string& key, const std::string& default_val = "") const;

    /// Get an integer value.
    int getInt(const std::string& key, int default_val = 0) const;

    /// Get a double value.
    double getDouble(const std::string& key, double default_val = 0.0) const;

    /// Get a boolean value.
    bool getBool(const std::string& key, bool default_val = false) const;

    /// Get a string array.
    std::vector<std::string> getStringArray(const std::string& key) const;

    /// Check if a key exists.
    bool hasKey(const std::string& key) const;

    /// Get all top-level keys.
    std::vector<std::string> topLevelKeys() const;

    /// Override a value programmatically.
    void setValue(const std::string& key, const std::string& value);

    /// Reload config from the last loaded file.
    bool reload();

private:
    std::unordered_map<std::string, std::string> _values;
    std::string _last_file;
    bool _loaded{false};
};

} // namespace brain_core
