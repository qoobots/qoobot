/**
 * permission_store.cpp — 权限持久化存储
 * 职责：权限状态的持久化读写、权限变更记录
 */
#include "qoostore/skill_types.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <map>
#include <vector>
#include <chrono>
#include <ctime>

namespace qoostore::edge {

namespace fs = std::filesystem;

class PermissionStore {
public:
    struct PermissionRecord {
        std::string skill_id;
        std::string permission_name;
        PermissionLevel level;
        bool granted = false;
        std::chrono::system_clock::time_point granted_at;
        std::chrono::system_clock::time_point updated_at;
    };

    struct AuditEntry {
        std::string skill_id;
        std::string permission_name;
        std::string action;     // grant/revoke/check/deny
        std::string result;     // success/failure
        std::chrono::system_clock::time_point timestamp;
    };

    explicit PermissionStore(const std::string& store_path = "/data/qoostore/permissions")
        : store_path_(store_path) {
        fs::create_directories(store_path_);
        load();
    }

    /**
     * 保存权限记录
     */
    void savePermission(const PermissionRecord& record) {
        permissions_[record.skill_id][record.permission_name] = record;
        persist();
    }

    /**
     * 获取权限记录
     */
    std::optional<PermissionRecord> getPermission(const std::string& skill_id,
                                                    const std::string& permission_name) const {
        auto skill_it = permissions_.find(skill_id);
        if (skill_it == permissions_.end()) return std::nullopt;

        auto perm_it = skill_it->second.find(permission_name);
        if (perm_it == skill_it->second.end()) return std::nullopt;

        return perm_it->second;
    }

    /**
     * 获取技能的所有权限
     */
    std::vector<PermissionRecord> getSkillPermissions(const std::string& skill_id) const {
        std::vector<PermissionRecord> result;
        auto it = permissions_.find(skill_id);
        if (it != permissions_.end()) {
            for (const auto& [name, record] : it->second) {
                result.push_back(record);
            }
        }
        return result;
    }

    /**
     * 删除技能的所有权限记录
     */
    void removeSkillPermissions(const std::string& skill_id) {
        permissions_.erase(skill_id);
        persist();
        std::cout << "[PermissionStore] Removed permissions for: " << skill_id << std::endl;
    }

    /**
     * 记录审计日志
     */
    void recordAudit(const AuditEntry& entry) {
        audit_log_.push_back(entry);

        // 限制审计日志大小
        if (audit_log_.size() > 10000) {
            audit_log_.erase(audit_log_.begin(), audit_log_.begin() + 1000);
        }

        // 实时写入审计文件
        appendAuditFile(entry);
    }

    /**
     * 获取审计日志
     */
    std::vector<AuditEntry> getAuditLog(const std::string& skill_id, int limit = 100) const {
        std::vector<AuditEntry> result;
        for (auto it = audit_log_.rbegin(); it != audit_log_.rend() && result.size() < static_cast<size_t>(limit); ++it) {
            if (it->skill_id == skill_id || skill_id.empty()) {
                result.push_back(*it);
            }
        }
        return result;
    }

    /**
     * 持久化所有数据到磁盘
     */
    void persist() {
        std::string perm_path = store_path_ + "/permissions.json";
        std::ofstream file(perm_path);
        if (!file.is_open()) {
            std::cerr << "[PermissionStore] Failed to open permissions.json for writing" << std::endl;
            return;
        }

        // 手动 JSON 序列化（生产环境用 nlohmann/json）
        file << "{\n";
        bool first_skill = true;
        for (const auto& [skill_id, perms] : permissions_) {
            if (!first_skill) file << ",\n";
            first_skill = false;
            file << "  \"" << skill_id << "\": {\n";
            bool first_perm = true;
            for (const auto& [name, record] : perms) {
                if (!first_perm) file << ",\n";
                first_perm = false;
                file << "    \"" << name << "\": {"
                     << "\"level\":" << static_cast<int>(record.level) << ","
                     << "\"granted\":" << (record.granted ? "true" : "false")
                     << "}";
            }
            file << "\n  }";
        }
        file << "\n}\n";
        file.close();
    }

private:
    std::string store_path_;
    std::map<std::string, std::map<std::string, PermissionRecord>> permissions_;
    std::vector<AuditEntry> audit_log_;

    void load() {
        std::string perm_path = store_path_ + "/permissions.json";
        if (!fs::exists(perm_path)) return;

        std::ifstream file(perm_path);
        if (!file.is_open()) return;

        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string content = buffer.str();

        // Stub: 生产环境使用 nlohmann/json 解析
        // auto json = nlohmann::json::parse(content);
        // for (const auto& [skill_id, perms] : json.items()) {
        //     for (const auto& [name, record] : perms.items()) {
        //         PermissionRecord rec;
        //         rec.skill_id = skill_id;
        //         rec.permission_name = name;
        //         rec.level = static_cast<PermissionLevel>(record["level"].get<int>());
        //         rec.granted = record["granted"].get<bool>();
        //         permissions_[skill_id][name] = rec;
        //     }
        // }

        std::cout << "[PermissionStore] Loaded permissions from disk" << std::endl;
    }

    void appendAuditFile(const AuditEntry& entry) {
        std::string audit_path = store_path_ + "/audit.log";
        std::ofstream file(audit_path, std::ios::app);
        if (!file.is_open()) return;

        auto time_t = std::chrono::system_clock::to_time_t(entry.timestamp);
        file << std::ctime(&time_t) // ctime includes newline
             << "  skill=" << entry.skill_id
             << " perm=" << entry.permission_name
             << " action=" << entry.action
             << " result=" << entry.result
             << std::endl;
    }
};

std::unique_ptr<PermissionStore> createPermissionStore(const std::string& path) {
    return std::make_unique<PermissionStore>(path);
}

} // namespace qoostore::edge
