#include "qoostore/skill_manager.h"
#include <filesystem>
#include <fstream>
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
        // 解析 .qooskills 包（ZIP 格式）
        std::string skill_id = extractSkillId(package_path);
        if (skill_id.empty()) {
            callback("", false, "Invalid package: cannot extract skill_id");
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

        callback(skill_id, true, "");
    }

    void installFromUrl(const std::string& url, const std::string& license_key,
                         InstallCallback callback) override {
        std::string temp_path = skills_root_ + "/temp/" + std::to_string(std::time(nullptr)) + ".qooskills";
        fs::create_directories(skills_root_ + "/temp");

        // 下载包（由 Downloader 处理，这里简化）
        std::cout << "[SkillManager] Downloading from: " << url << std::endl;

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
        fs::remove_all(it->second.install_path);
        fs::remove_all(skills_root_ + "/data/" + skill_id);

        installed_skills_.erase(it);
        saveInstalledSkills();

        callback(skill_id, true);
    }

    void update(const std::string& skill_id, const std::string& package_url,
                 UpdateCallback callback) override {
        auto it = installed_skills_.find(skill_id);
        if (it == installed_skills_.end()) {
            callback(skill_id, "", false);
            return;
        }

        it->second.status = SkillStatus::UPDATING;
        if (status_callback_) {
            status_callback_(skill_id, SkillStatus::UPDATING);
        }

        std::string temp_path = skills_root_ + "/temp/" + skill_id + "_update.qooskills";
        fs::create_directories(skills_root_ + "/temp");

        // 解压更新包
        std::string install_path = it->second.install_path;
        if (!extractPackage(temp_path, install_path)) {
            callback(skill_id, "", false);
            return;
        }

        SkillManifest manifest = readManifest(install_path);
        it->second.version = manifest.version;
        it->second.status = SkillStatus::ACTIVE;
        it->second.updated_at = std::time(nullptr);
        saveInstalledSkills();

        callback(skill_id, manifest.version, true);
    }

    void checkForUpdates() override {
        for (auto& [skill_id, skill] : installed_skills_) {
            std::cout << "[SkillManager] Checking updates for: " << skill_id << std::endl;
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

        // 简化 JSON 解析（生产环境使用 nlohmann/json 或 rapidjson）
        std::string line;
        while (std::getline(in, line)) {
            // 解析逻辑...
        }
    }

    void saveInstalledSkills() {
        std::string index_path = skills_root_ + "/installed.json";
        std::ofstream out(index_path);
        if (!out.is_open()) return;

        out << "{\n";
        bool first = true;
        for (const auto& [id, skill] : installed_skills_) {
            if (!first) out << ",\n";
            first = false;
            out << "  \"" << id << "\": {"
                << "\"name\":\"" << skill.name << "\","
                << "\"version\":\"" << skill.version << "\""
                << "}";
        }
        out << "\n}\n";
    }

    std::string extractSkillId(const std::string& package_path) {
        // 从包路径提取 skill_id
        return fs::path(package_path).stem().string();
    }

    bool extractPackage(const std::string& package_path, const std::string& dest_path) {
        // ZIP 解压（生产环境使用 libzip 或 minizip）
        std::cout << "[SkillManager] Extracting: " << package_path << " -> " << dest_path << std::endl;
        return fs::exists(package_path);
    }

    SkillManifest readManifest(const std::string& install_path) {
        SkillManifest manifest;
        std::string manifest_path = install_path + "/manifest.json";
        std::ifstream in(manifest_path);
        if (!in.is_open()) return manifest;

        // 简化 JSON 解析
        manifest.skill_id = fs::path(install_path).filename().string();
        manifest.name = manifest.skill_id;
        manifest.version = "1.0.0";
        manifest.entry_point = "main.py";
        manifest.runtime = "python3.11";
        manifest.permissions = {"camera", "microphone"};

        return manifest;
    }
};

// 工厂函数
std::unique_ptr<SkillManager> createSkillManager() {
    return std::make_unique<SkillManagerImpl>();
}

} // namespace edge
} // namespace qoostore
