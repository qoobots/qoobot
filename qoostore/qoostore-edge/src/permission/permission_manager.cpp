#include "qoostore/permission_manager.h"
#include <iostream>
#include <fstream>
#include <map>

namespace qoostore {
namespace edge {

class PermissionManagerImpl : public PermissionManager {
public:
    PermissionManagerImpl() {
        registerSystemPermissions();
    }

    void registerPermission(const Permission& permission) override {
        all_permissions_[permission.name] = permission;
    }

    void declareSkillPermissions(const std::string& skill_id,
                                  const std::vector<std::string>& permissions) override {
        skill_declarations_[skill_id] = permissions;
        std::cout << "[PermissionManager] " << skill_id << " declared " << permissions.size() << " permissions" << std::endl;
    }

    bool checkPermission(const std::string& skill_id,
                          const std::string& permission) const override {
        // 检查技能是否有权限声明
        auto decl_it = skill_declarations_.find(skill_id);
        if (decl_it == skill_declarations_.end()) return false;

        const auto& declared = decl_it->second;
        if (std::find(declared.begin(), declared.end(), permission) == declared.end()) {
            return false;
        }

        // 检查是否已授权
        return hasPermission(skill_id, permission);
    }

    bool hasPermission(const std::string& skill_id,
                        const std::string& permission) const override {
        auto it = granted_permissions_.find(skill_id);
        if (it == granted_permissions_.end()) return false;

        const auto& granted = it->second;
        return std::find(granted.begin(), granted.end(), permission) != granted.end();
    }

    void grantPermission(const std::string& skill_id,
                          const std::string& permission) override {
        granted_permissions_[skill_id].push_back(permission);
        std::cout << "[PermissionManager] Granted " << permission << " to " << skill_id << std::endl;
        savePermissions();
    }

    void revokePermission(const std::string& skill_id,
                           const std::string& permission) override {
        auto it = granted_permissions_.find(skill_id);
        if (it != granted_permissions_.end()) {
            auto& granted = it->second;
            granted.erase(std::remove(granted.begin(), granted.end(), permission), granted.end());
        }
        std::cout << "[PermissionManager] Revoked " << permission << " from " << skill_id << std::endl;
        savePermissions();
    }

    void grantAllDeclared(const std::string& skill_id) override {
        auto decl_it = skill_declarations_.find(skill_id);
        if (decl_it == skill_declarations_.end()) return;

        for (const auto& perm : decl_it->second) {
            auto perm_it = all_permissions_.find(perm);
            if (perm_it != all_permissions_.end()) {
                // NORMAL 级别自动授予，DANGEROUS 需要用户确认
                if (perm_it->second.level == PermissionLevel::NORMAL) {
                    grantPermission(skill_id, perm);
                }
            }
        }
    }

    void revokeAll(const std::string& skill_id) override {
        granted_permissions_.erase(skill_id);
        savePermissions();
    }

    std::vector<Permission> getSkillPermissions(const std::string& skill_id) const override {
        std::vector<Permission> result;
        auto decl_it = skill_declarations_.find(skill_id);
        if (decl_it == skill_declarations_.end()) return result;

        for (const auto& perm_name : decl_it->second) {
            auto perm_it = all_permissions_.find(perm_name);
            if (perm_it != all_permissions_.end()) {
                Permission p = perm_it->second;
                p.granted = hasPermission(skill_id, perm_name);
                result.push_back(p);
            }
        }
        return result;
    }

    std::vector<Permission> getGrantedPermissions(const std::string& skill_id) const override {
        std::vector<Permission> result;
        auto it = granted_permissions_.find(skill_id);
        if (it == granted_permissions_.end()) return result;

        for (const auto& perm_name : it->second) {
            auto perm_it = all_permissions_.find(perm_name);
            if (perm_it != all_permissions_.end()) {
                Permission p = perm_it->second;
                p.granted = true;
                result.push_back(p);
            }
        }
        return result;
    }

    PermissionLevel getPermissionLevel(const std::string& permission_name) const override {
        auto it = all_permissions_.find(permission_name);
        return it != all_permissions_.end() ? it->second.level : PermissionLevel::DANGEROUS;
    }

    void loadPermissions() override {
        std::ifstream in("/data/qoostore/permissions.json");
        if (!in.is_open()) return;
        // JSON 解析...
        std::cout << "[PermissionManager] Permissions loaded" << std::endl;
    }

    void savePermissions() override {
        std::ofstream out("/data/qoostore/permissions.json");
        if (!out.is_open()) return;

        out << "{";
        bool first_skill = true;
        for (const auto& [skill_id, perms] : granted_permissions_) {
            if (!first_skill) out << ",";
            first_skill = false;
            out << "\"" << skill_id << "\":[";
            for (size_t i = 0; i < perms.size(); i++) {
                if (i > 0) out << ",";
                out << "\"" << perms[i] << "\"";
            }
            out << "]";
        }
        out << "}";
    }

private:
    std::map<std::string, Permission> all_permissions_;
    std::map<std::string, std::vector<std::string>> skill_declarations_;
    std::map<std::string, std::vector<std::string>> granted_permissions_;

    void registerSystemPermissions() {
        registerPermission({"camera", "访问摄像头", PermissionLevel::DANGEROUS, false});
        registerPermission({"microphone", "访问麦克风", PermissionLevel::DANGEROUS, false});
        registerPermission({"location", "访问位置信息", PermissionLevel::DANGEROUS, false});
        registerPermission({"motor.arm", "控制机械臂电机", PermissionLevel::DANGEROUS, false});
        registerPermission({"motor.base", "控制底盘电机", PermissionLevel::DANGEROUS, false});
        registerPermission({"network", "访问网络", PermissionLevel::NORMAL, false});
        registerPermission({"storage", "读写存储", PermissionLevel::NORMAL, false});
        registerPermission({"sensor.imu", "读取IMU数据", PermissionLevel::NORMAL, false});
        registerPermission({"emergency_stop", "触发急停", PermissionLevel::SIGNATURE, false});
        registerPermission({"system.config", "修改系统配置", PermissionLevel::SIGNATURE, false});
    }
};

std::unique_ptr<PermissionManager> createPermissionManager() {
    return std::make_unique<PermissionManagerImpl>();
}

} // namespace edge
} // namespace qoostore
