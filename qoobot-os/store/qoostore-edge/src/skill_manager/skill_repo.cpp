/**
 * skill_repo.cpp — 本地技能仓库管理
 * 职责：已安装技能索引、版本追踪、仓库清理、磁盘空间管理
 */
#include "qoostore/skill_types.h"
#include <fstream>
#include <sstream>
#include <filesystem>
#include <vector>
#include <map>
#include <algorithm>
#include <iostream>
#include <chrono>

namespace qoostore::edge {

namespace fs = std::filesystem;

/**
 * 本地技能仓库
 * 管理已安装技能的索引和磁盘空间
 */
class SkillRepo {
public:
    struct RepoInfo {
        std::string root_path;          // 仓库根路径
        size_t total_skills = 0;        // 总技能数
        size_t active_skills = 0;       // 激活技能数
        uint64_t total_size_bytes = 0;  // 总占用空间
        uint64_t available_bytes = 0;   // 可用空间
    };

    SkillRepo(const std::string& root_path = "/data/qoostore/skills")
        : root_path_(root_path) {
        fs::create_directories(root_path_ + "/repo");
        fs::create_directories(root_path_ + "/data");
        fs::create_directories(root_path_ + "/temp");
        loadIndex();
    }

    /**
     * 注册已安装技能
     */
    void registerSkill(const InstalledSkill& skill) {
        index_[skill.skill_id] = skill;
        saveIndex();
        std::cout << "[SkillRepo] Registered: " << skill.skill_id << " v" << skill.version << std::endl;
    }

    /**
     * 移除技能记录
     */
    void unregisterSkill(const std::string& skill_id) {
        index_.erase(skill_id);
        saveIndex();
        std::cout << "[SkillRepo] Unregistered: " << skill_id << std::endl;
    }

    /**
     * 更新技能版本
     */
    void updateSkillVersion(const std::string& skill_id, const std::string& new_version) {
        auto it = index_.find(skill_id);
        if (it != index_.end()) {
            it->second.version = new_version;
            it->second.updated_at = std::chrono::system_clock::now();
            saveIndex();
        }
    }

    /**
     * 查询已安装技能
     */
    std::optional<InstalledSkill> getSkill(const std::string& skill_id) const {
        auto it = index_.find(skill_id);
        if (it != index_.end()) {
            return it->second;
        }
        return std::nullopt;
    }

    /**
     * 获取所有已安装技能
     */
    std::vector<InstalledSkill> getAllSkills() const {
        std::vector<InstalledSkill> skills;
        skills.reserve(index_.size());
        for (const auto& [id, skill] : index_) {
            skills.push_back(skill);
        }
        return skills;
    }

    /**
     * 获取激活状态的技能
     */
    std::vector<InstalledSkill> getActiveSkills() const {
        std::vector<InstalledSkill> skills;
        for (const auto& [id, skill] : index_) {
            if (skill.status == SkillStatus::ACTIVE) {
                skills.push_back(skill);
            }
        }
        return skills;
    }

    /**
     * 检查技能是否已安装
     */
    bool isInstalled(const std::string& skill_id) const {
        return index_.find(skill_id) != index_.end();
    }

    /**
     * 获取技能安装路径
     */
    std::string getSkillPath(const std::string& skill_id) const {
        return root_path_ + "/repo/" + skill_id;
    }

    /**
     * 获取技能数据路径
     */
    std::string getSkillDataPath(const std::string& skill_id) const {
        return root_path_ + "/data/" + skill_id;
    }

    /**
     * 获取仓库信息
     */
    RepoInfo getRepoInfo() const {
        RepoInfo info;
        info.root_path = root_path_;
        info.total_skills = index_.size();

        for (const auto& [id, skill] : index_) {
            if (skill.status == SkillStatus::ACTIVE) {
                info.active_skills++;
            }
        }

        info.total_size_bytes = calculateDiskUsage();
        info.available_bytes = getAvailableSpace();

        return info;
    }

    /**
     * 清理临时文件
     */
    void cleanTempFiles() {
        std::string temp_dir = root_path_ + "/temp";
        if (fs::exists(temp_dir)) {
            for (const auto& entry : fs::directory_iterator(temp_dir)) {
                try {
                    fs::remove_all(entry.path());
                } catch (const std::exception& e) {
                    std::cerr << "[SkillRepo] Failed to clean: " << entry.path() << " - " << e.what() << std::endl;
                }
            }
        }
        std::cout << "[SkillRepo] Temp files cleaned" << std::endl;
    }

    /**
     * 检查磁盘空间是否充足
     */
    bool hasEnoughSpace(uint64_t required_bytes) const {
        uint64_t available = getAvailableSpace();
        // 保留 10% 的缓冲空间
        uint64_t min_free = getTotalSpace() / 10;
        return available > (required_bytes + min_free);
    }

private:
    std::string root_path_;
    std::map<std::string, InstalledSkill> index_;

    /**
     * 加载技能索引
     */
    void loadIndex() {
        std::string index_path = root_path_ + "/installed.json";
        if (!fs::exists(index_path)) return;

        std::ifstream file(index_path);
        if (!file.is_open()) return;

        std::stringstream buffer;
        buffer << file.rdbuf();
        std::string content = buffer.str();

        // Stub: 生产环境使用 nlohmann/json 解析
        // auto json = nlohmann::json::parse(content);
        // for (const auto& item : json) {
        //     InstalledSkill skill;
        //     skill.skill_id = item["skill_id"];
        //     // ... deserialize
        //     index_[skill.skill_id] = skill;
        // }
        std::cout << "[SkillRepo] Index loaded: " << index_.size() << " skills" << std::endl;
    }

    /**
     * 保存技能索引
     */
    void saveIndex() {
        std::string index_path = root_path_ + "/installed.json";
        std::ofstream file(index_path);
        if (!file.is_open()) return;

        // Stub: 生产环境使用 nlohmann/json 序列化
        file << "[\n";
        bool first = true;
        for (const auto& [id, skill] : index_) {
            if (!first) file << ",\n";
            first = false;
            file << "  {\n"
                 << "    \"skill_id\": \"" << skill.skill_id << "\",\n"
                 << "    \"name\": \"" << skill.name << "\",\n"
                 << "    \"version\": \"" << skill.version << "\",\n"
                 << "    \"status\": \"" << static_cast<int>(skill.status) << "\"\n"
                 << "  }";
        }
        file << "\n]\n";
        file.close();
    }

    /**
     * 计算磁盘使用量
     */
    uint64_t calculateDiskUsage() const {
        uint64_t total = 0;
        std::string repo_dir = root_path_ + "/repo";
        if (fs::exists(repo_dir)) {
            for (const auto& entry : fs::recursive_directory_iterator(repo_dir)) {
                if (entry.is_regular_file()) {
                    total += entry.file_size();
                }
            }
        }
        return total;
    }

    /**
     * 获取可用磁盘空间
     */
    uint64_t getAvailableSpace() const {
        std::error_code ec;
        auto space = fs::space(root_path_, ec);
        if (ec) return 0;
        return space.available;
    }

    /**
     * 获取总磁盘空间
     */
    uint64_t getTotalSpace() const {
        std::error_code ec;
        auto space = fs::space(root_path_, ec);
        if (ec) return 0;
        return space.capacity;
    }
};

std::unique_ptr<SkillRepo> createSkillRepo(const std::string& root_path) {
    return std::make_unique<SkillRepo>(root_path);
}

} // namespace qoostore::edge
