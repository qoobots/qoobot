#pragma once

#include "skill_types.h"
#include <string>
#include <vector>

namespace qoostore {
namespace edge {

/**
 * SandboxEngine — 技能沙箱隔离引擎
 * 使用 Linux cgroups + OverlayFS + Network Namespace 实现三层隔离
 */
class SandboxEngine {
public:
    virtual ~SandboxEngine() = default;

    // 沙箱生命周期
    virtual bool createSandbox(const std::string& skill_id, SandboxLevel level) = 0;
    virtual bool destroySandbox(const std::string& skill_id) = 0;
    virtual bool startInSandbox(const std::string& skill_id, const std::string& entry_point) = 0;
    virtual bool stopSandbox(const std::string& skill_id) = 0;

    // 文件系统隔离 (OverlayFS)
    virtual bool setupFilesystem(const std::string& skill_id, const std::string& root_path) = 0;
    virtual bool restrictPath(const std::string& skill_id, const std::string& path, bool read_only) = 0;

    // 网络隔离 (Network Namespace)
    virtual bool createNetworkNamespace(const std::string& skill_id) = 0;
    virtual bool allowNetworkAccess(const std::string& skill_id, bool allow) = 0;
    virtual bool restrictHost(const std::string& skill_id, const std::string& host) = 0;

    // 资源配额 (cgroups)
    virtual bool setMemoryLimit(const std::string& skill_id, uint64_t max_mb) = 0;
    virtual bool setCpuLimit(const std::string& skill_id, uint32_t max_percent) = 0;
    virtual bool setDiskQuota(const std::string& skill_id, uint64_t max_mb) = 0;

    // 查询
    virtual ResourceUsage getUsage(const std::string& skill_id) const = 0;
    virtual bool isRunning(const std::string& skill_id) const = 0;
};

} // namespace edge
} // namespace qoostore
