// topic_adapter.h — ROS 2 Topic publisher/subscriber abstraction
#pragma once

#include <string>
#include <memory>
#include <functional>
#include <mutex>
#include <unordered_map>

namespace brain_core {

/**
 * @brief Generic topic adapter that wraps rclcpp publisher/subscriber.
 *
 * Supports dynamic topic creation, typed message forwarding,
 * and subscription callbacks dispatched to internal event bus.
 */
class TopicAdapter {
public:
    using MessageCallback = std::function<void(const std::string& topic, const std::string& msg_data)>;

    TopicAdapter();
    ~TopicAdapter();

    // ── Initialization ────────────────────────────────────
    bool initialize(void* node_handle);

    // ── Publisher API ─────────────────────────────────────
    bool createPublisher(const std::string& topic, const std::string& msg_type);
    bool publish(const std::string& topic, const std::string& serialized_data);
    void removePublisher(const std::string& topic);

    // ── Subscriber API ────────────────────────────────────
    bool createSubscription(const std::string& topic, const std::string& msg_type,
                            MessageCallback callback);
    void removeSubscription(const std::string& topic);

    // ── Query ─────────────────────────────────────────────
    std::vector<std::string> listTopics() const;
    size_t publisherCount() const;
    size_t subscriberCount() const;

    // ── Callback registration ─────────────────────────────
    void setGlobalCallback(MessageCallback cb);

private:
    void* node_handle_{nullptr};
    bool  initialized_{false};

    struct PubEntry {
        std::string topic;
        std::string msg_type;
        void*       raw_pub{nullptr};
    };
    struct SubEntry {
        std::string     topic;
        std::string     msg_type;
        void*           raw_sub{nullptr};
        MessageCallback callback;
    };

    std::unordered_map<std::string, PubEntry> publishers_;
    std::unordered_map<std::string, SubEntry> subscribers_;
    mutable std::mutex mutex_;
    MessageCallback    global_callback_;
};

} // namespace brain_core
