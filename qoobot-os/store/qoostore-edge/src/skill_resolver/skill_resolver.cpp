/**
 * skill_resolver.cpp — 技能依赖解析器实现
 *
 * 实现功能：
 *   1. 拓扑排序安装顺序
 *   2. 循环依赖检测（深度优先搜索）
 *   3. 版本约束检查（>=, =, ~>,
 *   4. 传递依赖发现
 *   5. 缺失依赖报告
 */

#include "qoostore/skill_resolver.h"
#include <algorithm>
#include <iostream>
#include <queue>
#include <regex>

namespace qoostore {
namespace edge {

// ============================================================================
// 版本比较工具
// ============================================================================

namespace {

/**
 * 语义化版本解析
 */
struct SemVer {
    int major = 0, minor = 0, patch = 0;
    std::string pre_release;

    bool valid = false;

    static std::optional<SemVer> parse(const std::string& version) {
        SemVer sv;
        std::regex re(R"(^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$)");
        std::smatch m;
        if (!std::regex_match(version, m, re)) return std::nullopt;
        sv.major = std::stoi(m[1]);
        sv.minor = std::stoi(m[2]);
        sv.patch = std::stoi(m[3]);
        if (m[4].matched) sv.pre_release = m[4];
        sv.valid = true;
        return sv;
    }

    bool operator<(const SemVer& other) const {
        if (major != other.major) return major < other.major;
        if (minor != other.minor) return minor < other.minor;
        if (patch != other.patch) return patch < other.patch;
        // 有预发布版本号 < 无预发布版本号
        if (pre_release.empty() != other.pre_release.empty())
            return !pre_release.empty();
        return pre_release < other.pre_release;
    }

    bool operator==(const SemVer& other) const {
        return major == other.major && minor == other.minor &&
               patch == other.patch && pre_release == other.pre_release;
    }

    bool operator<=(const SemVer& other) const {
        return *this < other || *this == other;
    }
};

/**
 * 检查版本是否满足约束
 * 支持格式：
 *   - ">=1.2.3"  大于等于
 *   - "=1.2.3"   精确匹配
 *   - "~>1.2.3"  兼容版本（>=1.2.3 且 <1.3.0）
 *   - ">1.2.3"   大于
 *   - "1.2.3"    精确匹配（简写）
 *   - "*"        任意版本
 *   - "" (空)    任意版本
 */
bool satisfiesVersion(const std::string& version, const std::string& constraint) {
    if (constraint.empty() || constraint == "*") return true;

    std::string op;
    std::string ver_str;

    if (constraint.starts_with(">=")) { op = ">="; ver_str = constraint.substr(2); }
    else if (constraint.starts_with("<=")) { op = "<="; ver_str = constraint.substr(2); }
    else if (constraint.starts_with("~>")) { op = "~>"; ver_str = constraint.substr(2); }
    else if (constraint.starts_with(">"))  { op = ">";  ver_str = constraint.substr(1); }
    else if (constraint.starts_with("<"))  { op = "<";  ver_str = constraint.substr(1); }
    else if (constraint.starts_with("="))  { op = "=";  ver_str = constraint.substr(1); }
    else { op = "="; ver_str = constraint; }

    auto current = SemVer::parse(version);
    auto required = SemVer::parse(ver_str);
    if (!current || !required) return false;

    if (op == ">=") return *current >= *required;
    if (op == "<=") return *current <= *required;
    if (op == ">")  return *required < *current;
    if (op == "<")  return *current < *required;
    if (op == "=")  return *current == *required;
    if (op == "~>") {
        // 兼容版本：>= required 且 < next_major
        SemVer next_major{required->major + 1, 0, 0};
        return *current >= *required && *current < next_major;
    }
    return false;
}

} // anonymous namespace

// ============================================================================
// SkillResolverImpl
// ============================================================================

class SkillResolverImpl : public SkillResolver {
public:
    void registerInstalled(const std::string& skill_id, const std::string& version) override {
        installed_[skill_id] = version;
    }

    void registerAvailable(const std::string& skill_id,
                            const std::string& version,
                            const std::vector<DependencyNode>& dependencies) override {
        auto& entry = registry_[skill_id];
        entry.version = version;
        entry.deps = dependencies;
    }

    ResolutionResult resolve(const std::string& skill_id,
                               const std::string& version) override {
        ResolutionResult result;

        // 检查目标技能是否在注册表中
        auto it = registry_.find(skill_id);
        if (it == registry_.end()) {
            result.error = "Skill not found in registry: " + skill_id;
            return result;
        }

        // 检查是否已安装且版本满足要求
        auto inst_it = installed_.find(skill_id);
        if (inst_it != installed_.end()) {
            if (satisfiesVersion(inst_it->second, ">=" + version)) {
                result.success = true;
                return result; // 已安装，无需操作
            }
        }

        // 构建依赖图
        std::map<std::string, std::vector<std::string>> graph;
        std::map<std::string, int> in_degree;
        std::set<std::string> to_install;

        std::function<bool(const std::string&, const std::string&, std::set<std::string>&)>
        collect_deps = [&](const std::string& sid, const std::string& ver,
                            std::set<std::string>& visited) -> bool {
            if (visited.count(sid)) {
                // 已在当前路径中 → 循环依赖
                result.conflict.push_back(sid);
                return false;
            }

            auto avail_it = registry_.find(sid);
            if (avail_it == registry_.end()) {
                result.missing.push_back(sid);
                return false;
            }

            auto inst_it = installed_.find(sid);
            if (inst_it != installed_.end() &&
                satisfiesVersion(inst_it->second, ">=" + ver)) {
                return true; // 已满足，无需递归
            }

            visited.insert(sid);
            to_install.insert(sid);

            for (const auto& dep : avail_it->second.deps) {
                if (dep.optional) {
                    auto dep_inst = installed_.find(dep.skill_id);
                    auto dep_avail = registry_.find(dep.skill_id);
                    if (dep_inst == installed_.end() && dep_avail == registry_.end()) {
                        result.optional_missing.push_back(dep.skill_id);
                        continue;
                    }
                    // 可选依赖满足则安装，不满足则跳过
                    if (dep_inst != installed_.end()) {
                        if (!satisfiesVersion(dep_inst->second, dep.required_version)) {
                            result.optional_missing.push_back(dep.skill_id);
                            continue;
                        }
                    }
                }

                if (!collect_deps(dep.skill_id, dep.required_version, visited)) {
                    if (dep.optional) {
                        result.optional_missing.push_back(dep.skill_id);
                        continue;
                    }
                    return false;
                }

                // 添加边：dep → sid
                graph[dep.skill_id].push_back(sid);
                in_degree[sid]++;
                if (in_degree.find(dep.skill_id) == in_degree.end()) {
                    in_degree[dep.skill_id] = 0;
                }
            }

            visited.erase(sid);
            return true;
        };

        // 初始化入度
        in_degree[skill_id] = 0;

        // 收集依赖
        std::set<std::string> visited;
        bool ok = collect_deps(skill_id, version, visited);

        if (!ok && !result.missing.empty()) {
            result.error = "Missing required dependencies: ";
            for (size_t i = 0; i < result.missing.size(); i++) {
                if (i > 0) result.error += ", ";
                result.error += result.missing[i];
            }
            return result;
        }

        // 拓扑排序（Kahn 算法）
        std::queue<std::string> q;
        for (const auto& [node, degree] : in_degree) {
            if (degree == 0 && to_install.count(node)) {
                q.push(node);
            }
        }

        // 确保所有待安装节点都在入度表中
        for (const auto& node : to_install) {
            if (in_degree.find(node) == in_degree.end()) {
                in_degree[node] = 0;
                q.push(node);
            }
        }

        while (!q.empty()) {
            std::string node = q.front(); q.pop();
            result.install_order.push_back(node);

            if (graph.count(node)) {
                for (const auto& neighbor : graph[node]) {
                    if (--in_degree[neighbor] == 0) {
                        q.push(neighbor);
                    }
                }
            }
        }

        // 检测未解析的节点（循环依赖）
        for (const auto& [node, degree] : in_degree) {
            if (degree > 0 && to_install.count(node)) {
                result.conflict.push_back(node);
            }
        }

        if (!result.conflict.empty()) {
            result.error = "Circular dependency detected";
            return result;
        }

        result.success = true;
        return result;
    }

    bool checkDependencies(const std::string& skill_id) override {
        auto it = registry_.find(skill_id);
        if (it == registry_.end()) return false;

        for (const auto& dep : it->second.deps) {
            auto inst_it = installed_.find(dep.skill_id);
            if (inst_it == installed_.end()) {
                if (dep.optional) continue;
                return false;
            }
            if (!satisfiesVersion(inst_it->second, dep.required_version)) {
                if (dep.optional) continue;
                return false;
            }
        }
        return true;
    }

    std::vector<std::string> getTransitiveDeps(const std::string& skill_id) override {
        std::vector<std::string> result;
        std::set<std::string> visited;

        std::function<void(const std::string&)> dfs = [&](const std::string& sid) {
            if (visited.count(sid)) return;
            visited.insert(sid);

            auto it = registry_.find(sid);
            if (it == registry_.end()) return;

            for (const auto& dep : it->second.deps) {
                if (!visited.count(dep.skill_id)) {
                    result.push_back(dep.skill_id);
                    dfs(dep.skill_id);
                }
            }
        };

        dfs(skill_id);
        return result;
    }

    std::vector<std::vector<std::string>> detectCycles() override {
        std::vector<std::vector<std::string>> cycles;
        std::set<std::string> global_visited;
        std::set<std::string> path;
        std::vector<std::string> current_path;

        std::function<void(const std::string&)> dfs = [&](const std::string& sid) {
            if (global_visited.count(sid)) return;
            if (path.count(sid)) {
                // 找到循环
                std::vector<std::string> cycle;
                bool in_cycle = false;
                for (const auto& node : current_path) {
                    if (node == sid) in_cycle = true;
                    if (in_cycle) cycle.push_back(node);
                }
                cycle.push_back(sid);
                cycles.push_back(cycle);
                return;
            }

            path.insert(sid);
            current_path.push_back(sid);

            auto it = registry_.find(sid);
            if (it != registry_.end()) {
                for (const auto& dep : it->second.deps) {
                    dfs(dep.skill_id);
                }
            }

            current_path.pop_back();
            path.erase(sid);
            global_visited.insert(sid);
        };

        for (const auto& [sid, _] : registry_) {
            dfs(sid);
        }

        return cycles;
    }

private:
    struct RegistryEntry {
        std::string version;
        std::vector<DependencyNode> deps;
    };

    std::map<std::string, std::string> installed_;
    std::map<std::string, RegistryEntry> registry_;
};

std::unique_ptr<SkillResolver> createSkillResolver() {
    return std::make_unique<SkillResolverImpl>();
}

} // namespace edge
} // namespace qoostore
