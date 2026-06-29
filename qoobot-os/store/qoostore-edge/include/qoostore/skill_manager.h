#pragma once

#include "skill_types.h"
#include <string>
#include <vector>
#include <functional>

namespace qoostore {
namespace edge {

/**
 * SkillManager — 技能安装/卸载/更新/启用/停用管理
 * 对标 Android PackageManager
 */
class SkillManager {
public:
    virtual ~SkillManager() = default;

    // 安装
    virtual void installFromPackage(const std::string& package_path,
                                     InstallCallback callback) = 0;
    virtual void installFromUrl(const std::string& url, const std::string& license_key,
                                 InstallCallback callback) = 0;

    // 卸载
    virtual void uninstall(const std::string& skill_id,
                            UninstallCallback callback) = 0;

    // 更新
    virtual void update(const std::string& skill_id, const std::string& package_url,
                         UpdateCallback callback) = 0;
    virtual void checkForUpdates() = 0;

    // 启用/停用
    virtual void enable(const std::string& skill_id) = 0;
    virtual void disable(const std::string& skill_id) = 0;

    // 查询
    virtual std::vector<InstalledSkill> listInstalled() const = 0;
    virtual InstalledSkill getSkill(const std::string& skill_id) const = 0;
    virtual bool isInstalled(const std::string& skill_id) const = 0;

    // 技能仓库路径
    virtual std::string getSkillPath(const std::string& skill_id) const = 0;
    virtual std::string getSkillDataPath(const std::string& skill_id) const = 0;

    // 回调注册
    virtual void onStatusChanged(StatusCallback callback) = 0;
};

} // namespace edge
} // namespace qoostore
