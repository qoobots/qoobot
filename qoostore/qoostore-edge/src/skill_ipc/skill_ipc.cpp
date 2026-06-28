#include "qoostore/skill_ipc.h"
#include <iostream>
#include <map>
#include <mutex>

namespace qoostore {
namespace edge {

class SkillIPCImpl : public SkillIPC {
public:
    SkillIPCImpl() {
        std::cout << "[SkillIPC] Initialized" << std::endl;
    }

    void broadcast(const std::string& action, const std::string& data_json) override {
        std::lock_guard<std::mutex> lock(mutex_);
        std::cout << "[SkillIPC] Broadcasting action=" << action << " data=" << data_json << std::endl;

        // 发送给所有订阅者
        for (const auto& [skill_id, handlers] : subscriptions_) {
            auto it = handlers.find(action);
            if (it != handlers.end()) {
                it->second(action, data_json, "system");
            }
        }
    }

    void sendToSkill(const std::string& target_skill_id,
                      const std::string& action,
                      const std::string& data_json) override {
        std::lock_guard<std::mutex> lock(mutex_);
        std::cout << "[SkillIPC] Sending to " << target_skill_id << " action=" << action << std::endl;

        auto it = subscriptions_.find(target_skill_id);
        if (it != subscriptions_.end()) {
            auto handler_it = it->second.find(action);
            if (handler_it != it->second.end()) {
                handler_it->second(action, data_json, "system");
            }
        }
    }

    void subscribe(const std::string& skill_id, const std::string& action,
                    IntentHandler handler) override {
        std::lock_guard<std::mutex> lock(mutex_);
        subscriptions_[skill_id][action] = std::move(handler);
        std::cout << "[SkillIPC] " << skill_id << " subscribed to " << action << std::endl;
    }

    void unsubscribe(const std::string& skill_id, const std::string& action) override {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = subscriptions_.find(skill_id);
        if (it != subscriptions_.end()) {
            it->second.erase(action);
        }
    }

    bool registerDataProvider(const std::string& skill_id,
                               const std::string& uri,
                               const std::string& data_json) override {
        std::lock_guard<std::mutex> lock(mutex_);
        data_providers_[skill_id + ":" + uri] = data_json;
        std::cout << "[SkillIPC] Data provider registered: " << skill_id << " uri=" << uri << std::endl;
        return true;
    }

    std::string queryData(const std::string& skill_id,
                           const std::string& uri) override {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = data_providers_.find(skill_id + ":" + uri);
        return it != data_providers_.end() ? it->second : "{}";
    }

    bool sendSecure(const std::string& target_skill_id,
                     const std::vector<uint8_t>& payload) override {
        std::lock_guard<std::mutex> lock(mutex_);
        secure_messages_[target_skill_id].push_back(payload);
        std::cout << "[SkillIPC] Secure message sent to " << target_skill_id
                  << " size=" << payload.size() << std::endl;
        return true;
    }

    std::vector<uint8_t> receiveSecure(const std::string& skill_id,
                                        uint32_t timeout_ms) override {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = secure_messages_.find(skill_id);
        if (it != secure_messages_.end() && !it->second.empty()) {
            auto msg = it->second.front();
            it->second.erase(it->second.begin());
            return msg;
        }
        return {};
    }

private:
    std::mutex mutex_;
    std::map<std::string, std::map<std::string, IntentHandler>> subscriptions_;
    std::map<std::string, std::string> data_providers_;
    std::map<std::string, std::vector<std::vector<uint8_t>>> secure_messages_;
};

std::unique_ptr<SkillIPC> createSkillIPC() {
    return std::make_unique<SkillIPCImpl>();
}

} // namespace edge
} // namespace qoostore
