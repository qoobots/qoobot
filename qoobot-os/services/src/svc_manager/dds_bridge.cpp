#include "qoosvc/manager/manager_types.h"
#include <atomic>
#include <chrono>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>

namespace qoosvc::manager {

/**
 * DdsBridge — bridges ServiceManager to DDS/ROS2 communication layer.
 *
 * Provides publish/subscribe to DDS topics for service lifecycle commands
 * and status reporting. Currently a stub that simulates DDS communication;
 * will integrate with Fast DDS / Cyclone DDS when the qoobrain IPC layer
 * is available.
 */
class DdsBridge {
public:
    using MessageHandler = std::function<void(IpcMessageType, const std::string& payload)>;

    DdsBridge() = default;
    ~DdsBridge() { stop(); }

    /**
     * Initialize the DDS bridge.
     */
    bool init(const DdsBridgeConfig& config) {
        config_ = config;
        initialized_ = true;
        return true;
    }

    /**
     * Start publishing heartbeats and listening for commands.
     */
    void start() {
        if (!initialized_ || running_) return;
        running_ = true;

        heartbeat_thread_ = std::thread([this]() {
            while (running_) {
                publish_heartbeat();
                std::this_thread::sleep_for(config_.heartbeat_interval);
            }
        });
    }

    /**
     * Stop the bridge.
     */
    void stop() {
        running_ = false;
        if (heartbeat_thread_.joinable()) {
            heartbeat_thread_.join();
        }
    }

    /**
     * Publish a service state change.
     */
    void publish_state(const std::string& service_name, ServiceState state) {
        pending_messages_.push_back({
            IpcMessageType::STATUS_SERVICE_STATE,
            service_name + ":" + std::to_string(static_cast<int>(state))
        });
    }

    /**
     * Publish a health report.
     */
    void publish_health_report(const std::string& report_json) {
        pending_messages_.push_back({
            IpcMessageType::STATUS_HEALTH_REPORT,
            report_json
        });
    }

    /**
     * Register a handler for incoming commands.
     */
    void set_command_handler(MessageHandler handler) {
        std::lock_guard<std::mutex> lock(mutex_);
        command_handler_ = std::move(handler);
    }

    /**
     * Process incoming messages (call periodically).
     */
    void poll() {
        std::lock_guard<std::mutex> lock(mutex_);
        // In production: read from DDS subscriber queue
        // For now, process simulated commands
        for (auto& msg : pending_commands_) {
            if (command_handler_) {
                command_handler_(msg.first, msg.second);
            }
        }
        pending_commands_.clear();
    }

    /**
     * Simulate receiving a command (for testing).
     */
    void simulate_command(IpcMessageType type, const std::string& payload) {
        std::lock_guard<std::mutex> lock(mutex_);
        pending_commands_.push_back({type, payload});
    }

private:
    void publish_heartbeat() {
        // In production: publish to DDS heartbeat topic
        // /qoosvc/manager/heartbeat with QoS RELIABLE
        heartbeat_seq_++;
    }

    DdsBridgeConfig config_;
    bool initialized_ = false;
    std::atomic<bool> running_{false};
    std::thread heartbeat_thread_;
    uint64_t heartbeat_seq_ = 0;

    std::mutex mutex_;
    MessageHandler command_handler_;
    std::vector<std::pair<IpcMessageType, std::string>> pending_commands_;
    std::vector<std::pair<IpcMessageType, std::string>> pending_messages_;
};

} // namespace qoosvc::manager
