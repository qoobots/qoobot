#pragma once

#include "skill_types.h"
#include <string>
#include <vector>

namespace qoostore {
namespace edge {

/**
 * PermissionManager — 权限管控
 * 对标 Android PermissionManager
 */
class PermissionManager {
public:
    virtual ~PermissionManager() = default;

    // 权限注册
    virtual void registerPermission(const Permission& permission) = 0;
    virtual void declareSkillPermissions(const std::string& skill_id,
                                          const std::vector<std::string>& permissions) = 0;

    // 权限检查
    virtual bool checkPermission(const std::string& skill_id,
                                  const std::string& permission) const = 0;
    virtual bool hasPermission(const std::string& skill_id,
                                const std::string& permission) const = 0;

    // 权限授予/撤销
    virtual void grantPermission(const std::string& skill_id,
                                  const std::string& permission) = 0;
    virtual void revokePermission(const std::string& skill_id,
                                   const std::string& permission) = 0;
    virtual void grantAllDeclared(const std::string& skill_id) = 0;
    virtual void revokeAll(const std::string& skill_id) = 0;

    // 查询
    virtual std::vector<Permission> getSkillPermissions(const std::string& skill_id) const = 0;
    virtual std::vector<Permission> getGrantedPermissions(const std::string& skill_id) const = 0;
    virtual PermissionLevel getPermissionLevel(const std::string& permission_name) const = 0;

    // 持久化
    virtual void loadPermissions() = 0;
    virtual void savePermissions() = 0;
};

} // namespace edge
} // namespace qoostore
