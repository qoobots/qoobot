/**
 * package_parser.cpp — .qooskills 技能包解析器
 * 职责：ZIP 解压、manifest.json 解析、包结构验证
 * 对标 Android PackageParser
 */
#include "qoostore/skill_types.h"
#include <fstream>
#include <sstream>
#include <filesystem>
#include <regex>
#include <algorithm>
#include <iostream>

namespace qoostore::edge {

namespace fs = std::filesystem;

/**
 * 技能包解析器
 * 解析 .qooskills (ZIP) 格式的技能包
 */
class PackageParser {
public:
    struct ParseResult {
        bool success = false;
        SkillManifest manifest;
        std::string error;
        std::string extracted_path;
        std::vector<std::string> files;
    };

    /**
     * 解析技能包
     * @param package_path .qooskills 文件路径
     * @param extract_to 解压目标目录
     * @return 解析结果
     */
    ParseResult parse(const std::string& package_path, const std::string& extract_to) {
        ParseResult result;

        // 验证文件存在
        if (!fs::exists(package_path)) {
            result.error = "Package file not found: " + package_path;
            return result;
        }

        // 验证文件扩展名
        if (!package_path.ends_with(".qooskills")) {
            result.error = "Invalid package extension, expected .qooskills: " + package_path;
            return result;
        }

        // 创建解压目录
        std::string skill_id = extractSkillIdFromPath(package_path);
        std::string extract_dir = extract_to + "/" + skill_id;
        fs::create_directories(extract_dir);

        // 解压 ZIP（生产环境使用 libzip/minizip）
        if (!extractZip(package_path, extract_dir)) {
            result.error = "Failed to extract package: " + package_path;
            return result;
        }

        // 解析 manifest.json
        std::string manifest_path = extract_dir + "/manifest.json";
        if (!fs::exists(manifest_path)) {
            result.error = "manifest.json not found in package";
            return result;
        }

        std::string manifest_content = readFile(manifest_path);
        if (!parseManifest(manifest_content, result.manifest)) {
            result.error = "Failed to parse manifest.json";
            return result;
        }

        // 验证必需文件
        std::string entry_path = extract_dir + "/skill/" + result.manifest.entry_point;
        if (!fs::exists(entry_path)) {
            result.error = "Entry point not found: " + result.manifest.entry_point;
            return result;
        }

        // 验证 icons/
        std::string icon_path = extract_dir + "/icons/icon_512.png";
        if (!fs::exists(icon_path)) {
            result.error = "Required icon not found: icons/icon_512.png";
            return result;
        }

        // 验证签名文件
        std::string sig_path = extract_dir + "/signature.sig";
        if (!fs::exists(sig_path)) {
            result.error = "Signature file not found: signature.sig";
            return result;
        }

        // 收集文件列表
        for (const auto& entry : fs::recursive_directory_iterator(extract_dir)) {
            if (entry.is_regular_file()) {
                result.files.push_back(entry.path().string());
            }
        }

        result.success = true;
        result.extracted_path = extract_dir;
        return result;
    }

    /**
     * 验证包结构
     */
    bool validateStructure(const std::string& extract_dir) {
        std::vector<std::string> required = {
            "manifest.json",
            "signature.sig",
            "skill/",
            "icons/icon_512.png",
            "icons/icon_128.png"
        };

        for (const auto& req : required) {
            std::string full_path = extract_dir + "/" + req;
            if (req.ends_with("/")) {
                if (!fs::is_directory(full_path)) {
                    std::cerr << "[PackageParser] Missing directory: " << req << std::endl;
                    return false;
                }
            } else {
                if (!fs::exists(full_path)) {
                    std::cerr << "[PackageParser] Missing file: " << req << std::endl;
                    return false;
                }
            }
        }
        return true;
    }

private:
    /**
     * 从文件路径提取 skill_id
     * 例如：/path/to/com.example.cleaning-1.2.3.qooskills -> com.example.cleaning
     */
    std::string extractSkillIdFromPath(const std::string& path) {
        std::string filename = fs::path(path).filename().string();
        // 去掉 .qooskills 扩展名
        size_t ext_pos = filename.rfind(".qooskills");
        if (ext_pos != std::string::npos) {
            filename = filename.substr(0, ext_pos);
        }
        // 去掉版本号后缀 -x.y.z
        std::regex version_suffix("-[0-9]+\\.[0-9]+\\.[0-9]+$");
        filename = std::regex_replace(filename, version_suffix, "");
        return filename;
    }

    /**
     * 解压 ZIP 文件（生产环境用 libzip/minizip）
     */
    bool extractZip(const std::string& zip_path, const std::string& dest_dir) {
        // Stub: 生产环境使用 libzip 或 minizip
        std::cout << "[PackageParser] Extracting: " << zip_path << " -> " << dest_dir << std::endl;
        // TODO: 集成 libzip/minizip 实现真实解压
        return true;
    }

    /**
     * 解析 manifest.json
     */
    bool parseManifest(const std::string& json, SkillManifest& manifest) {
        // Stub: 生产环境使用 nlohmann/json
        // 简单的手动解析用于开发环境
        auto extractString = [&](const std::string& key) -> std::string {
            std::string search = "\"" + key + "\":";
            size_t pos = json.find(search);
            if (pos == std::string::npos) return "";
            pos = json.find("\"", pos + search.length());
            if (pos == std::string::npos) return "";
            size_t end = json.find("\"", pos + 1);
            if (end == std::string::npos) return "";
            return json.substr(pos + 1, end - pos - 1);
        };

        auto extractInt = [&](const std::string& key) -> int {
            std::string search = "\"" + key + "\":";
            size_t pos = json.find(search);
            if (pos == std::string::npos) return 0;
            pos += search.length();
            while (pos < json.length() && (json[pos] == ' ' || json[pos] == '\t')) pos++;
            std::string num;
            while (pos < json.length() && (std::isdigit(json[pos]) || json[pos] == '-')) {
                num += json[pos++];
            }
            return num.empty() ? 0 : std::stoi(num);
        };

        manifest.skill_id = extractString("skillId");
        manifest.name = extractString("name");
        manifest.version = extractString("version");
        manifest.min_qos_version = extractString("minQOSVersion");
        manifest.entry_point = extractString("entryPoint");
        manifest.runtime = extractString("runtime");

        std::string category = extractString("category");
        manifest.category = category; // 生产环境转 enum

        std::string sandbox = extractString("sandboxLevel");
        if (sandbox == "unrestricted") manifest.sandbox_level = SandboxLevel::UNRESTRICTED;
        else if (sandbox == "isolated") manifest.sandbox_level = SandboxLevel::ISOLATED;
        else manifest.sandbox_level = SandboxLevel::RESTRICTED;

        manifest.max_memory_mb = extractInt("maxMemoryMB");
        if (manifest.max_memory_mb == 0) manifest.max_memory_mb = 512;
        manifest.max_cpu_percent = extractInt("maxCPUPercent");
        if (manifest.max_cpu_percent == 0) manifest.max_cpu_percent = 30;

        // 解析 permissions 数组（简化处理）
        std::string perms_search = "\"permissions\":";
        size_t perms_pos = json.find(perms_search);
        if (perms_pos != std::string::npos) {
            size_t bracket_start = json.find("[", perms_pos);
            size_t bracket_end = json.find("]", bracket_start);
            if (bracket_start != std::string::npos && bracket_end != std::string::npos) {
                std::string perms_str = json.substr(bracket_start + 1, bracket_end - bracket_start - 1);
                size_t p = 0;
                while (p < perms_str.length()) {
                    size_t q1 = perms_str.find("\"", p);
                    if (q1 == std::string::npos) break;
                    size_t q2 = perms_str.find("\"", q1 + 1);
                    if (q2 == std::string::npos) break;
                    manifest.permissions.push_back(perms_str.substr(q1 + 1, q2 - q1 - 1));
                    p = q2 + 1;
                }
            }
        }

        return !manifest.skill_id.empty() && !manifest.name.empty();
    }

    /**
     * 读取文件内容
     */
    std::string readFile(const std::string& path) {
        std::ifstream file(path);
        if (!file.is_open()) return "";
        std::stringstream buffer;
        buffer << file.rdbuf();
        return buffer.str();
    }
};

// 工厂函数
std::unique_ptr<PackageParser> createPackageParser() {
    return std::make_unique<PackageParser>();
}

} // namespace qoostore::edge
