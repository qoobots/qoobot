#include "qoosvc/manager/service_manager.h"
#include "qoosvc/common/result.h"

namespace qoosvc::manager {

// Lifecycle policy per service type
enum class LifecyclePolicy {
    ALWAYS_ON,       // Must always be running
    ON_DEMAND,       // Started when needed, stopped when idle
    SCHEDULED,       // Started/stopped on a schedule
    MANUAL,          // Manually controlled
};

struct LifecycleConfig {
    LifecyclePolicy policy = LifecyclePolicy::ALWAYS_ON;
    int idle_timeout_sec = 300;
    std::string schedule_cron;  // For SCHEDULED policy
};

/**
 * LifecycleManager — enforces lifecycle policies for services.
 *
 * This is a helper used by ServiceManager to determine when to
 * automatically start/stop services based on their configured policy.
 */
class LifecycleManager {
public:
    explicit LifecycleManager(ServiceManager& manager) : manager_(manager) {}

    /**
     * Set the lifecycle policy for a service.
     */
    void set_policy(const std::string& name, LifecyclePolicy policy, int idle_timeout = 300) {
        LifecycleConfig config;
        config.policy = policy;
        config.idle_timeout_sec = idle_timeout;
        policies_[name] = config;
    }

    /**
     * Apply policies: start ALWAYS_ON services, stop idle ON_DEMAND services.
     */
    void apply() {
        for (const auto& [name, config] : policies_) {
            auto info = manager_.get_service_info(name);
            if (info.is_err()) continue;

            switch (config.policy) {
            case LifecyclePolicy::ALWAYS_ON:
                if (info->state != ServiceState::RUNNING) {
                    manager_.start_service(name);
                }
                break;
            case LifecyclePolicy::ON_DEMAND:
                // If idle too long, stop
                if (info->state == ServiceState::RUNNING) {
                    auto now = std::chrono::steady_clock::now();
                    auto it = last_active_.find(name);
                    if (it != last_active_.end()) {
                        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                            now - it->second).count();
                        if (elapsed > config.idle_timeout_sec) {
                            manager_.stop_service(name);
                        }
                    }
                }
                break;
            default:
                break;
            }
        }
    }

    /**
     * Mark a service as active (reset idle timer).
     */
    void mark_active(const std::string& name) {
        last_active_[name] = std::chrono::steady_clock::now();
    }

private:
    ServiceManager& manager_;
    std::unordered_map<std::string, LifecycleConfig> policies_;
    std::unordered_map<std::string, std::chrono::steady_clock::time_point> last_active_;
};

} // namespace qoosvc::manager
