/**
 * qoostore_cli.cpp — qoostore-edge 命令行管理工具
 *
 * 提供对技能运行环境的命令行管理接口：
 *   qoostore-cli list                    列出已安装技能
 *   qoostore-cli info <skill_id>         查看技能详情
 *   qoostore-cli install <package_path>  安装技能包
 *   qoostore-cli uninstall <skill_id>    卸载技能
 *   qoostore-cli enable <skill_id>       启用技能
 *   qoostore-cli disable <skill_id>      停用技能
 *   qoostore-cli resolve <skill_id>      解析依赖关系
 *   qoostore-cli deps <skill_id>         查看传递依赖
 *   qoostore-cli status                  系统状态
 */

#include "qoostore/skill_manager.h"
#include "qoostore/permission_manager.h"
#include "qoostore/skill_resolver.h"
#include "json_utils.hpp"

#include <iostream>
#include <iomanip>
#include <string>
#include <vector>

// 工厂函数声明
namespace qoostore::edge {
std::unique_ptr<SkillManager> createSkillManager();
std::unique_ptr<PermissionManager> createPermissionManager();
std::unique_ptr<SkillResolver> createSkillResolver();
}

void printUsage() {
    std::cout << "qoostore-cli — QooStore Edge CLI v0.2.0\n\n";
    std::cout << "Usage: qoostore-cli <command> [options]\n\n";
    std::cout << "Commands:\n";
    std::cout << "  list                         List installed skills\n";
    std::cout << "  info <skill_id>              Show skill details\n";
    std::cout << "  install <package_path>       Install a skill package\n";
    std::cout << "  uninstall <skill_id>         Uninstall a skill\n";
    std::cout << "  enable <skill_id>            Enable a skill\n";
    std::cout << "  disable <skill_id>           Disable a skill\n";
    std::cout << "  resolve <skill_id>           Resolve dependencies\n";
    std::cout << "  deps <skill_id>              Show transitive dependencies\n";
    std::cout << "  status                       Show daemon status\n";
    std::cout << "  help                         Show this help\n";
}

void cmdList() {
    auto mgr = qoostore::edge::createSkillManager();
    auto skills = mgr->listInstalled();

    if (skills.empty()) {
        std::cout << "No skills installed.\n";
        return;
    }

    std::cout << std::left << std::setw(40) << "Skill ID"
              << std::setw(15) << "Version"
              << std::setw(12) << "Status"
              << "Name\n";
    std::cout << std::string(80, '-') << "\n";

    for (const auto& skill : skills) {
        std::string status_str;
        switch (skill.status) {
            case qoostore::edge::SkillStatus::ACTIVE: status_str = "ACTIVE"; break;
            case qoostore::edge::SkillStatus::DISABLED: status_str = "DISABLED"; break;
            case qoostore::edge::SkillStatus::INSTALLING: status_str = "INSTALLING"; break;
            case qoostore::edge::SkillStatus::UPDATING: status_str = "UPDATING"; break;
            case qoostore::edge::SkillStatus::ERROR: status_str = "ERROR"; break;
            default: status_str = "UNKNOWN";
        }

        std::cout << std::left << std::setw(40) << skill.skill_id
                  << std::setw(15) << skill.version
                  << std::setw(12) << status_str
                  << skill.name << "\n";
    }
}

void cmdInfo(const std::string& skill_id) {
    auto mgr = qoostore::edge::createSkillManager();
    if (!mgr->isInstalled(skill_id)) {
        std::cout << "Skill not found: " << skill_id << "\n";
        return;
    }

    auto skill = mgr->getSkill(skill_id);
    auto perm_mgr = qoostore::edge::createPermissionManager();

    std::cout << "Skill: " << skill.skill_id << "\n";
    std::cout << "  Name:       " << skill.name << "\n";
    std::cout << "  Version:    " << skill.version << "\n";
    std::cout << "  Path:       " << skill.install_path << "\n";
    std::cout << "  Status:     " << static_cast<int>(skill.status) << "\n";
    std::cout << "  Installed:  " << skill.installed_at << "\n";
    if (skill.updated_at > 0)
        std::cout << "  Updated:    " << skill.updated_at << "\n";

    // 权限信息
    auto perms = perm_mgr->getSkillPermissions(skill_id);
    if (!perms.empty()) {
        std::cout << "  Permissions:\n";
        for (const auto& p : perms) {
            std::cout << "    - " << p.name << " (granted: " << (p.granted ? "yes" : "no") << ")\n";
        }
    }
}

void cmdInstall(const std::string& package_path) {
    auto mgr = qoostore::edge::createSkillManager();
    std::cout << "Installing from: " << package_path << "...\n";

    mgr->installFromPackage(package_path,
        [](const std::string& skill_id, bool success, const std::string& error) {
            if (success) {
                std::cout << "Successfully installed: " << skill_id << "\n";
            } else {
                std::cerr << "Install failed: " << error << "\n";
            }
        });
}

void cmdUninstall(const std::string& skill_id) {
    auto mgr = qoostore::edge::createSkillManager();
    std::cout << "Uninstalling: " << skill_id << "...\n";

    mgr->uninstall(skill_id,
        [](const std::string& sid, bool success) {
            if (success) {
                std::cout << "Successfully uninstalled: " << sid << "\n";
            } else {
                std::cerr << "Uninstall failed: " << sid << "\n";
            }
        });
}

void cmdEnable(const std::string& skill_id) {
    auto mgr = qoostore::edge::createSkillManager();
    mgr->enable(skill_id);
    std::cout << "Enabled: " << skill_id << "\n";
}

void cmdDisable(const std::string& skill_id) {
    auto mgr = qoostore::edge::createSkillManager();
    mgr->disable(skill_id);
    std::cout << "Disabled: " << skill_id << "\n";
}

void cmdResolve(const std::string& skill_id) {
    auto resolver = qoostore::edge::createSkillResolver();

    // 模拟注册一些可用技能
    resolver->registerAvailable("com.qoobot.navigation", "1.0.0", {});
    resolver->registerAvailable("com.qoobot.vision", "1.0.0", {});
    resolver->registerAvailable("com.qoobot.cleaning", "1.2.0", {
        {"com.qoobot.navigation", ">=1.0.0", false, "Navigation"}
    });

    auto result = resolver->resolve(skill_id, "1.0.0");
    if (result.success) {
        std::cout << "Dependency resolution: SUCCESS\n";
        std::cout << "Install order:\n";
        for (size_t i = 0; i < result.install_order.size(); i++) {
            std::cout << "  " << (i + 1) << ". " << result.install_order[i] << "\n";
        }
        if (!result.optional_missing.empty()) {
            std::cout << "Optional missing: ";
            for (size_t i = 0; i < result.optional_missing.size(); i++) {
                if (i > 0) std::cout << ", ";
                std::cout << result.optional_missing[i];
            }
            std::cout << "\n";
        }
    } else {
        std::cout << "Dependency resolution: FAILED\n";
        std::cout << "Error: " << result.error << "\n";
        if (!result.missing.empty()) {
            std::cout << "Missing: ";
            for (size_t i = 0; i < result.missing.size(); i++) {
                if (i > 0) std::cout << ", ";
                std::cout << result.missing[i];
            }
            std::cout << "\n";
        }
    }
}

void cmdDeps(const std::string& skill_id) {
    auto resolver = qoostore::edge::createSkillResolver();

    // 模拟注册依赖关系
    resolver->registerAvailable("com.qoobot.navigation", "1.0.0", {});
    resolver->registerAvailable("com.qoobot.slam", "1.0.0", {
        {"com.qoobot.navigation", ">=1.0.0", false, "Navigation API"}
    });
    resolver->registerAvailable("com.qoobot.cleaning", "1.2.0", {
        {"com.qoobot.slam", ">=1.0.0", false, "SLAM mapping"},
        {"com.qoobot.navigation", ">=1.0.0", false, "Navigation"}
    });

    auto deps = resolver->getTransitiveDeps(skill_id);
    if (deps.empty()) {
        std::cout << "No dependencies for: " << skill_id << "\n";
    } else {
        std::cout << "Transitive dependencies for " << skill_id << ":\n";
        for (const auto& dep : deps) {
            std::cout << "  - " << dep << "\n";
        }
    }
}

void cmdStatus() {
    auto mgr = qoostore::edge::createSkillManager();
    auto skills = mgr->listInstalled();

    std::cout << "QooStore Edge Status\n";
    std::cout << "  Installed skills: " << skills.size() << "\n";

    int active = 0, disabled = 0;
    for (const auto& s : skills) {
        if (s.status == qoostore::edge::SkillStatus::ACTIVE) active++;
        if (s.status == qoostore::edge::SkillStatus::DISABLED) disabled++;
    }
    std::cout << "  Active:   " << active << "\n";
    std::cout << "  Disabled: " << disabled << "\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        printUsage();
        return 1;
    }

    std::string command = argv[1];

    if (command == "help" || command == "--help" || command == "-h") {
        printUsage();
        return 0;
    }

    if (command == "list") {
        cmdList();
    } else if (command == "info" && argc >= 3) {
        cmdInfo(argv[2]);
    } else if (command == "install" && argc >= 3) {
        cmdInstall(argv[2]);
    } else if (command == "uninstall" && argc >= 3) {
        cmdUninstall(argv[2]);
    } else if (command == "enable" && argc >= 3) {
        cmdEnable(argv[2]);
    } else if (command == "disable" && argc >= 3) {
        cmdDisable(argv[2]);
    } else if (command == "resolve" && argc >= 3) {
        cmdResolve(argv[2]);
    } else if (command == "deps" && argc >= 3) {
        cmdDeps(argv[2]);
    } else if (command == "status") {
        cmdStatus();
    } else {
        std::cerr << "Unknown command: " << command << "\n";
        printUsage();
        return 1;
    }

    return 0;
}
