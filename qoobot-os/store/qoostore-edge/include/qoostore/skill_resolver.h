#pragma once

#include "qoostore/skill_types.h"
#include <string>
#include <vector>
#include <map>
#include <set>
#include <functional>
#include <optional>

namespace qoostore {
namespace edge {

/**
 * DependencyNode — 依赖图中的单个技能节点
 */
struct DependencyNode {
    std::string skill_id;
    std::string required_version;   // 最小版本要求，如 ">=1.2.0"
    bool optional{false};           // 可选依赖（缺失不阻止安装）
    std::string reason;             // 依赖原因描述
};

/**
 * ResolutionResult — 依赖解析结果
 */
struct ResolutionResult {
    bool success{false};
    std::vector<std::string> install_order;   // 拓扑排序后的安装顺序
    std::vector<std::string> missing;          // 缺失的必需依赖
    std::vector<std::string> conflict;         // 版本冲突
    std::vector<std::string> optional_missing; // 缺失的可选依赖
    std::string error;
};

/**
 * SkillResolver — 技能依赖解析与安装编排
 *
 * 职责：
 *   1. 解析技能 manifest 中的 depends 字段
 *   2. 构建依赖图并拓扑排序
 *   3. 检测循环依赖和版本冲突
 *   4. 生成安装顺序
 *
 * 对标：npm/pip 的依赖解析器
 */
class SkillResolver {
public:
    virtual ~SkillResolver() = default;

    /**
     * 注册一个已安装技能的版本信息
     * @param skill_id 技能 ID
     * @param version 当前安装版本
     */
    virtual void registerInstalled(const std::string& skill_id, const std::string& version) = 0;

    /**
     * 注册一个可用技能的依赖信息
     * @param skill_id 技能 ID
     * @param version 版本号
     * @param dependencies 依赖列表
     */
    virtual void registerAvailable(const std::string& skill_id,
                                    const std::string& version,
                                    const std::vector<DependencyNode>& dependencies) = 0;

    /**
     * 解析指定技能的依赖关系
     * @param skill_id 目标技能 ID
     * @param version 目标版本
     * @return 解析结果，包含安装顺序
     */
    virtual ResolutionResult resolve(const std::string& skill_id,
                                      const std::string& version) = 0;

    /**
     * 检查指定技能的依赖是否全部满足
     * @param skill_id 技能 ID
     * @return 是否全部满足
     */
    virtual bool checkDependencies(const std::string& skill_id) = 0;

    /**
     * 获取技能的所有传递依赖
     * @param skill_id 技能 ID
     * @return 所有依赖的技能 ID 列表
     */
    virtual std::vector<std::string> getTransitiveDeps(const std::string& skill_id) = 0;

    /**
     * 检测依赖图中的循环依赖
     * @return 包含循环的技能 ID 列表
     */
    virtual std::vector<std::vector<std::string>> detectCycles() = 0;
};

// 工厂函数
std::unique_ptr<SkillResolver> createSkillResolver();

} // namespace edge
} // namespace qoostore
