#include "qoosvc/common/result.h"
#include <fstream>
#include <string>
#include <unordered_map>
#include <vector>

// Simulate yaml-cpp usage — in production, link against yaml-cpp library.
// For now, provide a lightweight YAML config loader.
namespace qoosvc::manager {

/**
 * ConfigLoader — loads YAML configuration files for qoosvc services.
 *
 * Supports:
 *  - voice_config.yaml
 *  - nav_config.yaml
 *  - light_profiles.yaml
 *  - zones.yaml
 */
class ConfigLoader {
public:
    using ConfigMap = std::unordered_map<std::string, std::string>;

    /**
     * Load a YAML config file and return flattened key-value pairs.
     */
    Result<ConfigMap> load(const std::string& filepath) {
        std::ifstream file(filepath);
        if (!file.is_open()) {
            return Result<ConfigMap>::err(ErrorCode::INVALID_ARGUMENT,
                                           "Cannot open config file: " + filepath);
        }
        ConfigMap config;
        std::string line;
        std::string current_section;
        int line_num = 0;

        while (std::getline(file, line)) {
            line_num++;
            // Skip comments and empty lines
            if (line.empty() || line[0] == '#') continue;

            // Section header
            if (line.back() == ':' && line.find(':') == line.size() - 1) {
                current_section = line.substr(0, line.size() - 1);
                // Trim leading spaces
                size_t pos = current_section.find_first_not_of(" \t");
                if (pos != std::string::npos) {
                    current_section = current_section.substr(pos);
                }
                continue;
            }

            // Key-value pair
            auto colon_pos = line.find(':');
            if (colon_pos != std::string::npos) {
                auto key = line.substr(0, colon_pos);
                auto value = line.substr(colon_pos + 1);

                // Trim
                key.erase(0, key.find_first_not_of(" \t"));
                key.erase(key.find_last_not_of(" \t") + 1);
                value.erase(0, value.find_first_not_of(" \t"));
                value.erase(value.find_last_not_of(" \t") + 1);

                // Remove quotes
                if (value.size() >= 2 && value.front() == '"' && value.back() == '"') {
                    value = value.substr(1, value.size() - 2);
                }
                if (value.size() >= 2 && value.front() == '\'' && value.back() == '\'') {
                    value = value.substr(1, value.size() - 2);
                }

                std::string full_key = current_section.empty() ? key : current_section + "." + key;
                config[full_key] = value;
            }
        }

        return Result<ConfigMap>::ok(std::move(config));
    }

    /**
     * Load all default config files from a directory.
     */
    Result<std::vector<ConfigMap>> load_all(const std::string& config_dir) {
        std::vector<ConfigMap> results;
        std::vector<std::string> files = {
            "voice_config.yaml",
            "nav_config.yaml",
            "light_profiles.yaml",
            "zones.yaml"
        };

        for (const auto& file : files) {
            auto result = load(config_dir + "/" + file);
            if (result.is_ok()) {
                results.push_back(std::move(result.value()));
            }
        }

        if (results.empty()) {
            return Result<std::vector<ConfigMap>>::err(
                ErrorCode::INVALID_ARGUMENT, "No config files found in " + config_dir);
        }

        return Result<std::vector<ConfigMap>>::ok(std::move(results));
    }

    /**
     * Get a string value from config, with default fallback.
     */
    static std::string get_string(const ConfigMap& config, const std::string& key,
                                   const std::string& default_val = {}) {
        auto it = config.find(key);
        return it != config.end() ? it->second : default_val;
    }

    /**
     * Get a double value from config, with default fallback.
     */
    static double get_double(const ConfigMap& config, const std::string& key,
                              double default_val = 0.0) {
        auto it = config.find(key);
        if (it != config.end()) {
            try { return std::stod(it->second); } catch (...) {}
        }
        return default_val;
    }

    /**
     * Get an int value from config, with default fallback.
     */
    static int get_int(const ConfigMap& config, const std::string& key,
                        int default_val = 0) {
        auto it = config.find(key);
        if (it != config.end()) {
            try { return std::stoi(it->second); } catch (...) {}
        }
        return default_val;
    }

    /**
     * Get a bool value from config, with default fallback.
     */
    static bool get_bool(const ConfigMap& config, const std::string& key,
                          bool default_val = false) {
        auto it = config.find(key);
        if (it != config.end()) {
            auto v = it->second;
            return v == "true" || v == "True" || v == "1" || v == "yes";
        }
        return default_val;
    }
};

} // namespace qoosvc::manager
