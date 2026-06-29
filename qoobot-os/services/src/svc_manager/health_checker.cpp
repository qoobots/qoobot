#include "qoosvc/common/result.h"
#include <chrono>
#include <string>
#include <unordered_map>

namespace qoosvc::manager {

/**
 * HealthChecker — performs periodic health checks on registered services.
 *
 * Tracks health history for trend analysis and predictive failure detection.
 */
class HealthChecker {
public:
    struct HealthRecord {
        bool healthy;
        std::chrono::system_clock::time_point timestamp;
    };

    static constexpr int kMaxHistory = 100;

    /**
     * Record a health check result for a service.
     */
    void record(const std::string& service_name, bool healthy) {
        auto& history = history_[service_name];
        history.push_back({healthy, std::chrono::system_clock::now()});
        if (history.size() > kMaxHistory) {
            history.erase(history.begin());
        }
    }

    /**
     * Check if a service has been consistently unhealthy.
     * Returns true if the last N checks were all unhealthy.
     */
    bool is_degraded(const std::string& service_name, int window = 5) const {
        auto it = history_.find(service_name);
        if (it == history_.end()) return false;

        const auto& history = it->second;
        if (history.size() < static_cast<size_t>(window)) return false;

        for (size_t i = history.size() - window; i < history.size(); ++i) {
            if (history[i].healthy) return false;
        }
        return true;
    }

    /**
     * Get the health trend (ratio of healthy checks in recent window).
     */
    double health_ratio(const std::string& service_name, int window = 20) const {
        auto it = history_.find(service_name);
        if (it == history_.end() || it->second.empty()) return 1.0;

        const auto& history = it->second;
        int count = std::min(window, static_cast<int>(history.size()));
        int healthy_count = 0;

        for (size_t i = history.size() - count; i < history.size(); ++i) {
            if (history[i].healthy) healthy_count++;
        }

        return static_cast<double>(healthy_count) / count;
    }

    /**
     * Clear history for a service.
     */
    void clear(const std::string& service_name) {
        history_.erase(service_name);
    }

private:
    std::unordered_map<std::string, std::vector<HealthRecord>> history_;
};

} // namespace qoosvc::manager
