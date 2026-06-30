#include "qoostore/skill_manager.h"
#include "json_utils.hpp"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <sys/stat.h>

namespace fs = std::filesystem;

namespace qoostore {
namespace edge {

class SkillManagerImpl : public SkillManager {
public:
    SkillManagerImpl(const std::string& skills_root = "/data/qoostore/skills")
        : skills_root_(skills_root) {
        fs::create_directories(skills_root_);
        fs::create_directories(skills_root_ + "/repo");
        fs::create_directories(skills_root_ + "/data");
        loadInstalledSkills();
    }

    void installFromPackage(const std::string& package_path,
                             InstallCallback callback) override {
        std::string skill_id = extractSkillId(package_path);
        if (skill_id.empty()) {
            callback("", false, "Invalid package: cannot extract skill_id");
            return;
        }

        // 检查是否已安装
        if (installed_skills_.count(skill_id)) {
            callback(skill_id, false, "Skill already installed: " + skill_id);
            return;
        }

        std::string install_path = skills_root_ + "/repo/" + skill_id;
        std::string data_path = skills_root_ + "/data/" + skill_id;

        fs::create_directories(install_path);
        fs::create_directories(data_path);

        // 解压技能文件
        if (!extractPackage(package_path, install_path)) {
            callback(skill_id, false, "Failed to extract package");
            return;
        }

        // 读取 manifest.json
        SkillManifest manifest = readManifest(install_path);
        if (manifest.skill_id.empty()) {
            callback(skill_id, false, "Invalid manifest.json");
            return;
        }

        // 注册技能
        InstalledSkill skill;
        skill.skill_id = manifest.skill_id;
        skill.name = manifest.name;
        skill.version = manifest.version;
        skill.install_path = install_path;
        skill.status = SkillStatus::ACTIVE;
        skill.installed_at = std::time(nullptr);

        installed_skills_[skill.skill_id] = skill;
        saveInstalledSkills();

        if (status_callback_) {
            status_callback_(skill.skill_id, SkillStatus::ACTIVE);
        }

        std::cout << "[SkillManager] Installed: " << skill_id << " v" << manifest.version << std::endl;
        callback(skill_id, true, "");
    }

    void installFromUrl(const std::string& url, const std::string& license_key,
                         InstallCallback callback) override {
        std::string temp_path = skills_root_ + "/temp/" + std::to_string(std::time(nullptr)) + ".qooskills";
        fs::create_directories(skills_root_ + "/temp");

        // 下载包（由 SkillDownloader 处理，这里执行安装流程）
        std::cout << "[SkillManager] Installing from URL: " << url << std::endl;

        // 模拟下载完成后的安装
        installFromPackage(temp_path, callback);
    }

    void uninstall(const std::string& skill_id,
                    UninstallCallback callback) override {
        auto it = installed_skills_.find(skill_id);
        if (it == installed_skills_.end()) {
            callback(skill_id, false);
            return;
        }

        it->second.status = SkillStatus::UNINSTALLING;
        if (status_callback_) {
            status_callback_(skill_id, SkillStatus::UNINSTALLING);
        }

        // 删除技能文件
        std::error_code ec;
        fs::remove_all(it->second.install_path, ec);
        fs::remove_all(skills_root_ + "/data/" + skill_id, ec);

        installed_skills_.erase(it);
        saveInstalledSkills();

        std::cout << "[SkillManager] Uninstalled: " << skill_id << std::endl;
        callback(skill_id, true);
    }

    void update(const std::string& skill_id, const std::string& package_url,
                 UpdateCallback callback) override {
        auto it = installed_skills_.find(skill_id);
        if (it == installed_skills_.end()) {
            callback(skill_id, "", false);
            return;
        }

        std::string old_version = it->second.version;
        it->second.status = SkillStatus::UPDATING;
        if (status_callback_) {
            status_callback_(skill_id, SkillStatus::UPDATING);
        }

        std::string temp_path = skills_root_ + "/temp/" + skill_id + "_update.qooskills";
        fs::create_directories(skills_root_ + "/temp");

        // 解压更新包（覆盖安装路径）
        std::string install_path = it->second.install_path;
        if (!extractPackage(temp_path, install_path)) {
            it->second.status = SkillStatus::ACTIVE;
            callback(skill_id, "", false);
            return;
        }

        SkillManifest manifest = readManifest(install_path);
        it->second.version = manifest.version;
        it->second.status = SkillStatus::ACTIVE;
        it->second.updated_at = std::time(nullptr);
        saveInstalledSkills();

        std::cout << "[SkillManager] Updated: " << skill_id
                  << " v" << old_version << " → v" << manifest.version << std::endl;
        callback(skill_id, manifest.version, true);
    }

    void checkForUpdates() override {
        for (auto& [skill_id, skill] : installed_skills_) {
            std::cout << "[SkillManager] Checking updates for: " << skill_id
                      << " (v" << skill.version << ")" << std::endl;
        }
    }

    void enable(const std::string& skill_id) override {
        auto it = installed_skills_.find(skill_id);
        if (it != installed_skills_.end()) {
            it->second.status = SkillStatus::ACTIVE;
            saveInstalledSkills();
            if (status_callback_) {
                status_callback_(skill_id, SkillStatus::ACTIVE);
            }
            std::cout << "[SkillManager] Enabled: " << skill_id << std::endl;
        }
    }

    void disable(const std::string& skill_id) override {
        auto it = installed_skills_.find(skill_id);
        if (it != installed_skills_.end()) {
            it->second.status = SkillStatus::DISABLED;
            saveInstalledSkills();
            if (status_callback_) {
                status_callback_(skill_id, SkillStatus::DISABLED);
            }
            std::cout << "[SkillManager] Disabled: " << skill_id << std::endl;
        }
    }

    std::vector<InstalledSkill> listInstalled() const override {
        std::vector<InstalledSkill> result;
        for (const auto& [id, skill] : installed_skills_) {
            result.push_back(skill);
        }
        return result;
    }

    InstalledSkill getSkill(const std::string& skill_id) const override {
        auto it = installed_skills_.find(skill_id);
        if (it != installed_skills_.end()) {
            return it->second;
        }
        return InstalledSkill{};
    }

    bool isInstalled(const std::string& skill_id) const override {
        return installed_skills_.find(skill_id) != installed_skills_.end();
    }

    std::string getSkillPath(const std::string& skill_id) const override {
        return skills_root_ + "/repo/" + skill_id;
    }

    std::string getSkillDataPath(const std::string& skill_id) const override {
        return skills_root_ + "/data/" + skill_id;
    }

    void onStatusChanged(StatusCallback callback) override {
        status_callback_ = std::move(callback);
    }

private:
    std::string skills_root_;
    std::map<std::string, InstalledSkill> installed_skills_;
    StatusCallback status_callback_;

    void loadInstalledSkills() {
        std::string index_path = skills_root_ + "/installed.json";
        std::ifstream in(index_path);
        if (!in.is_open()) return;

        std::stringstream buffer;
        buffer << in.rdbuf();
        std::string content = buffer.str();

        try {
            auto root = json::parse(content);
            if (root.is_object()) {
                for (auto& [id, obj] : root.as_object()) {
                    if (!obj.is_object()) continue;
                    InstalledSkill skill;
                    skill.skill_id = id;
                    skill.name = obj.get_string("name", id);
                    skill.version = obj.get_string("version", "0.0.0");
                    skill.install_path = obj.get_string("install_path", "");
                    int status_val = static_cast<int>(obj.get_int("status", 1));
                    skill.status = static_cast<SkillStatus>(status_val);
                    skill.installed_at = static_cast<uint64_t>(obj.get_int("installed_at", 0));
                    skill.updated_at = static_cast<uint64_t>(obj.get_int("updated_at", 0));
                    installed_skills_[id] = skill;
                }
            }
        } catch (const json::ParseError& e) {
            std::cerr << "[SkillManager] Failed to parse installed.json: " << e.what() << std::endl;
        }
    }

    void saveInstalledSkills() {
        std::string index_path = skills_root_ + "/installed.json";
        std::ofstream out(index_path);
        if (!out.is_open()) {
            std::cerr << "[SkillManager] Failed to write installed.json" << std::endl;
            return;
        }

        json::Value root(json::Object{});
        for (const auto& [id, skill] : installed_skills_) {
            json::Value entry(json::Object{});
            entry["name"] = skill.name;
            entry["version"] = skill.version;
            entry["install_path"] = skill.install_path;
            entry["status"] = static_cast<int>(skill.status);
            entry["installed_at"] = static_cast<int64_t>(skill.installed_at);
            entry["updated_at"] = static_cast<int64_t>(skill.updated_at);
            root[id] = entry;
        }

        out << root.dump(2);
        out.close();
    }

    std::string extractSkillId(const std::string& package_path) {
        return fs::path(package_path).stem().string();
    }

    bool extractPackage(const std::string& package_path, const std::string& dest_path) {
        // 生产环境使用 libzip/minizip 解压 .qooskills (ZIP) 包
        // 当前开发环境：模拟解压，从 manifest.json 模板创建技能目录结构
        std::cout << "[SkillManager] Extracting: " << package_path << " -> " << dest_path << std::endl;

        if (!fs::exists(package_path)) {
            std::cerr << "[SkillManager] Package not found: " << package_path << std::endl;
            return false;
        }

        // 创建技能目录结构（开发环境模拟）
        std::string skill_id = extractSkillId(package_path);
        fs::create_directories(dest_path + "/skill");
        fs::create_directories(dest_path + "/icons");
        fs::create_directories(dest_path + "/config");

        // 生成 manifest.json
        std::string manifest_path = dest_path + "/manifest.json";
        std::ofstream manifest(manifest_path);
        manifest << "{\n"
                 << "  \"skillId\": \"" << skill_id << "\",\n"
                 << "  \"name\": \"" << skill_id << "\",\n"
                 << "  \"version\": \"1.0.0\",\n"
                 << "  \"entryPoint\": \"main.py\",\n"
                 << "  \"runtime\": \"python3.11\",\n"
                 << "  \"sandboxLevel\": \"restricted\",\n"
                 << "  \"permissions\": [\"camera\", \"microphone\"]\n"
                 << "}\n";
        manifest.close();

        return true;
    }

    SkillManifest readManifest(const std::string& install_path) {
        SkillManifest manifest;
        std::string manifest_path = install_path + "/manifest.json";
        std::ifstream in(manifest_path);
        if (!in.is_open()) return manifest;

        std::stringstream buffer;
        buffer << in.rdbuf();

        try {
            auto root = json::parse(buffer.str());
            if (root.is_object()) {
                manifest.skill_id = root.get_string("skillId", "");
                manifest.name = root.get_string("name", "");
                manifest.version = root.get_string("version", "1.0.0");
                manifest.min_qos_version = root.get_string("minQOSVersion", "");
                manifest.entry_point = root.get_string("entryPoint", "main.py");
                manifest.runtime = root.get_string("runtime", "python3.11");

                std::string sandbox = root.get_string("sandboxLevel", "restricted");
                if (sandbox == "unrestricted") manifest.sandbox_level = SandboxLevel::UNRESTRICTED;
                else if (sandbox == "isolated") manifest.sandbox_level = SandboxLevel::ISOLATED;
                else manifest.sandbox_level = SandboxLevel::RESTRICTED;

                manifest.max_memory_mb = static_cast<uint64_t>(root.get_int("maxMemoryMB", 512));
                manifest.max_cpu_percent = static_cast<uint32_t>(root.get_int("maxCPUPercent", 30));

                // 解析权限数组
                if (root.has("permissions") && root["permissions"].is_array()) {
                    for (const auto& perm : root["permissions"].as_array()) {
                        if (perm.is_string()) {
                            manifest.permissions.push_back(perm.as_string());
                        }
                    }
                }
            }
        } catch (const json::ParseError& e) {
            std::cerr << "[SkillManager] Failed to parse manifest.json: " << e.what() << std::endl;
        }

        return manifest;
    }
};

// 工厂函数
std::unique_ptr<SkillManager> createSkillManager() {
    return std::make_unique<SkillManagerImpl>();
}

} // namespace edge
} // namespace qoostore
