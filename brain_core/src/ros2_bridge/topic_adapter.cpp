// topic_adapter.cpp — Implementation
#include "brain_core/ros2_bridge/topic_adapter.h"
#include <iostream>
#include <algorithm>

namespace brain_core {

TopicAdapter::TopicAdapter()  = default;
TopicAdapter::~TopicAdapter() = default;

bool TopicAdapter::initialize(void* node_handle) {
    if (!node_handle) return false;
    node_handle_  = node_handle;
    initialized_  = true;
    std::cout << "[TopicAdapter] Initialized." << std::endl;
    return true;
}

bool TopicAdapter::createPublisher(const std::string& topic, const std::string& msg_type) {
    if (!initialized_) return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if (publishers_.count(topic)) return false;

    PubEntry entry;
    entry.topic    = topic;
    entry.msg_type = msg_type;
    entry.raw_pub  = reinterpret_cast<void*>(1); // stub
    publishers_[topic] = entry;
    std::cout << "[TopicAdapter] Created publisher: " << topic << " (" << msg_type << ")" << std::endl;
    return true;
}

bool TopicAdapter::publish(const std::string& topic, const std::string& serialized_data) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = publishers_.find(topic);
    if (it == publishers_.end()) return false;

    // Stub: real impl would deserialize + publish
    (void)serialized_data;
    if (global_callback_) {
        global_callback_(topic, serialized_data);
    }
    return true;
}

void TopicAdapter::removePublisher(const std::string& topic) {
    std::lock_guard<std::mutex> lock(mutex_);
    publishers_.erase(topic);
}

bool TopicAdapter::createSubscription(const std::string& topic, const std::string& msg_type,
                                       MessageCallback callback) {
    if (!initialized_) return false;
    std::lock_guard<std::mutex> lock(mutex_);
    if (subscribers_.count(topic)) return false;

    SubEntry entry;
    entry.topic     = topic;
    entry.msg_type  = msg_type;
    entry.raw_sub   = reinterpret_cast<void*>(1); // stub
    entry.callback  = std::move(callback);
    subscribers_[topic] = entry;
    std::cout << "[TopicAdapter] Subscribed to: " << topic << " (" << msg_type << ")" << std::endl;
    return true;
}

void TopicAdapter::removeSubscription(const std::string& topic) {
    std::lock_guard<std::mutex> lock(mutex_);
    subscribers_.erase(topic);
}

std::vector<std::string> TopicAdapter::listTopics() const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<std::string> topics;
    for (const auto& [k, _] : publishers_)  topics.push_back(k + " [pub]");
    for (const auto& [k, _] : subscribers_) topics.push_back(k + " [sub]");
    return topics;
}

size_t TopicAdapter::publisherCount() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return publishers_.size();
}

size_t TopicAdapter::subscriberCount() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return subscribers_.size();
}

void TopicAdapter::setGlobalCallback(MessageCallback cb) {
    std::lock_guard<std::mutex> lock(mutex_);
    global_callback_ = std::move(cb);
}

} // namespace brain_core
