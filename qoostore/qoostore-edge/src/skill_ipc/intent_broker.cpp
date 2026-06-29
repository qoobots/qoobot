/**
 * intent_broker.cpp — Intent 广播代理
 * 职责：技能间事件广播、Intent 路由、事件订阅管理
 * 对标 Android Intent + BroadcastReceiver 机制
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <mutex>
#include <shared_mutex>

namespace qoostore::edge {

/**
 * Intent 消息
 */
struct Intent {
    std::string action;                 // 动作名称 (e.g., "qoobot.intent.ROOM_CLEANED")
    std::string from_skill_id;          // 发送者技能 ID
    std::string to_skill_id;            // 目标技能 ID (空 = 广播)
    std::map<std::string, std::string> extras;  // 附加数据
    std::vector<uint8_t> binary_data;   // 二进制载荷
    int priority = 0;                   // 优先级 (越高越先处理)
};

/**
 * Intent 订阅信息
 */
struct Subscription {
    std::string skill_id;
    std::string action;
    int priority = 0;
    bool enabled = true;
};

/**
 * Intent 广播代理
 */
class IntentBroker {
public:
    IntentBroker() = default;

    /**
     * 订阅 Intent
     */
    void subscribe(const std::string& skill_id, const std::string& action, int priority = 0) {
        std::unique_lock<std::shared_mutex> lock(mutex_);

        Subscription sub{skill_id, action, priority, true};
        subscriptions_[action].push_back(sub);

        // 按优先级排序
        auto& subs = subscriptions_[action];
        std::sort(subs.begin(), subs.end(),
                  [](const Subscription& a, const Subscription& b) {
                      return a.priority > b.priority;
                  });

        std::cout << "[IntentBroker] Subscribed: skill=" << skill_id
                  << " action=" << action << " priority=" << priority << std::endl;
    }

    /**
     * 取消订阅
     */
    void unsubscribe(const std::string& skill_id, const std::string& action) {
        std::unique_lock<std::shared_mutex> lock(mutex_);

        auto it = subscriptions_.find(action);
        if (it != subscriptions_.end()) {
            auto& subs = it->second;
            subs.erase(std::remove_if(subs.begin(), subs.end(),
                [&](const Subscription& s) { return s.skill_id == skill_id; }),
                subs.end());

            if (subs.empty()) {
                subscriptions_.erase(it);
            }
        }
    }

    /**
     * 广播 Intent 给所有订阅者
     */
    std::vector<std::string> broadcast(const Intent& intent) {
        std::shared_lock<std::shared_mutex> lock(mutex_);

        std::vector<std::string> recipients;

        auto it = subscriptions_.find(intent.action);
        if (it == subscriptions_.end()) {
            std::cout << "[IntentBroker] No subscribers for action: " << intent.action << std::endl;
            return recipients;
        }

        for (const auto& sub : it->second) {
            if (!sub.enabled) continue;

            // 不发送给自己
            if (sub.skill_id == intent.from_skill_id) continue;

            // 如果有指定目标，只发送给目标
            if (!intent.to_skill_id.empty() && sub.skill_id != intent.to_skill_id) continue;

            deliverIntent(sub.skill_id, intent);
            recipients.push_back(sub.skill_id);
        }

        std::cout << "[IntentBroker] Broadcast action=" << intent.action
                  << " recipients=" << recipients.size() << std::endl;

        return recipients;
    }

    /**
     * 点对点发送 Intent
     */
    bool sendToSkill(const std::string& target_skill_id, const Intent& intent) {
        std::shared_lock<std::shared_mutex> lock(mutex_);

        // 检查目标是否订阅了该 action
        auto it = subscriptions_.find(intent.action);
        if (it != subscriptions_.end()) {
            for (const auto& sub : it->second) {
                if (sub.skill_id == target_skill_id && sub.enabled) {
                    deliverIntent(target_skill_id, intent);
                    return true;
                }
            }
        }

        std::cerr << "[IntentBroker] Target skill not subscribed: "
                  << target_skill_id << " action=" << intent.action << std::endl;
        return false;
    }

    /**
     * 获取某个 action 的订阅者列表
     */
    std::vector<std::string> getSubscribers(const std::string& action) const {
        std::shared_lock<std::shared_mutex> lock(mutex_);

        std::vector<std::string> subscribers;
        auto it = subscriptions_.find(action);
        if (it != subscriptions_.end()) {
            for (const auto& sub : it->second) {
                if (sub.enabled) {
                    subscribers.push_back(sub.skill_id);
                }
            }
        }
        return subscribers;
    }

    /**
     * 获取技能的所有订阅
     */
    std::vector<Subscription> getSkillSubscriptions(const std::string& skill_id) const {
        std::shared_lock<std::shared_mutex> lock(mutex_);

        std::vector<Subscription> result;
        for (const auto& [action, subs] : subscriptions_) {
            for (const auto& sub : subs) {
                if (sub.skill_id == skill_id) {
                    result.push_back(sub);
                }
            }
        }
        return result;
    }

    /**
     * 启用/禁用订阅
     */
    void setSubscriptionEnabled(const std::string& skill_id, const std::string& action, bool enabled) {
        std::unique_lock<std::shared_mutex> lock(mutex_);

        auto it = subscriptions_.find(action);
        if (it != subscriptions_.end()) {
            for (auto& sub : it->second) {
                if (sub.skill_id == skill_id) {
                    sub.enabled = enabled;
                    break;
                }
            }
        }
    }

    /**
     * 移除技能的所有订阅（技能卸载时调用）
     */
    void removeSkill(const std::string& skill_id) {
        std::unique_lock<std::shared_mutex> lock(mutex_);

        for (auto it = subscriptions_.begin(); it != subscriptions_.end(); ) {
            auto& subs = it->second;
            subs.erase(std::remove_if(subs.begin(), subs.end(),
                [&](const Subscription& s) { return s.skill_id == skill_id; }),
                subs.end());

            if (subs.empty()) {
                it = subscriptions_.erase(it);
            } else {
                ++it;
            }
        }

        std::cout << "[IntentBroker] Removed all subscriptions for: " << skill_id << std::endl;
    }

    /**
     * 获取统计信息
     */
    std::map<std::string, size_t> getStats() const {
        std::shared_lock<std::shared_mutex> lock(mutex_);

        std::map<std::string, size_t> stats;
        stats["total_actions"] = subscriptions_.size();
        size_t total_subs = 0;
        for (const auto& [action, subs] : subscriptions_) {
            total_subs += subs.size();
        }
        stats["total_subscriptions"] = total_subs;
        return stats;
    }

private:
    mutable std::shared_mutex mutex_;
    std::map<std::string, std::vector<Subscription>> subscriptions_;

    // 待投递队列（按技能ID）
    std::map<std::string, std::vector<Intent>> delivery_queues_;
    std::mutex delivery_mutex_;

    /**
     * 投递 Intent 到目标技能
     * 生产环境通过 Unix Domain Socket 或共享内存传递
     */
    void deliverIntent(const std::string& target_skill_id, const Intent& intent) {
        std::lock_guard<std::mutex> lock(delivery_mutex_);
        delivery_queues_[target_skill_id].push_back(intent);

        // 如果队列过长，丢弃最旧的
        auto& queue = delivery_queues_[target_skill_id];
        if (queue.size() > 100) {
            queue.erase(queue.begin());
        }

        std::cout << "[IntentBroker] Intent delivered: " << intent.from_skill_id
                  << " -> " << target_skill_id
                  << " action=" << intent.action << std::endl;
    }
};

std::unique_ptr<IntentBroker> createIntentBroker() {
    return std::make_unique<IntentBroker>();
}

} // namespace qoostore::edge
