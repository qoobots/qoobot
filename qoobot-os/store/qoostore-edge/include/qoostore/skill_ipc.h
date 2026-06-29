#pragma once

#include <string>
#include <vector>
#include <functional>
#include <cstdint>

namespace qoostore {
namespace edge {

/**
 * SkillIPC — 技能间通信
 * 对标 Android Intent + ContentProvider + Binder
 */
class SkillIPC {
public:
    virtual ~SkillIPC() = default;

    // Intent 广播
    virtual void broadcast(const std::string& action,
                            const std::string& data_json) = 0;
    virtual void sendToSkill(const std::string& target_skill_id,
                              const std::string& action,
                              const std::string& data_json) = 0;

    // 事件订阅
    using IntentHandler = std::function<void(const std::string& action,
                                              const std::string& data_json,
                                              const std::string& source_skill_id)>;
    virtual void subscribe(const std::string& skill_id, const std::string& action,
                            IntentHandler handler) = 0;
    virtual void unsubscribe(const std::string& skill_id, const std::string& action) = 0;

    // 数据共享 (ContentProvider 对标)
    virtual bool registerDataProvider(const std::string& skill_id,
                                       const std::string& uri,
                                       const std::string& data_json) = 0;
    virtual std::string queryData(const std::string& skill_id,
                                   const std::string& uri) = 0;

    // 安全通信 (Binder 对标)
    virtual bool sendSecure(const std::string& target_skill_id,
                             const std::vector<uint8_t>& payload) = 0;
    virtual std::vector<uint8_t> receiveSecure(const std::string& skill_id,
                                                uint32_t timeout_ms) = 0;
};

} // namespace edge
} // namespace qoostore
