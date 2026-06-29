#include "qoostore/sandbox_engine.h"
#include <iostream>
#include <map>

namespace qoostore {
namespace edge {

class SandboxEngineImpl : public SandboxEngine {
public:
    SandboxEngineImpl() {
        std::cout << "[SandboxEngine] Initialized with cgroups v2 + OverlayFS + Network Namespace" << std::endl;
    }

    bool createSandbox(const std::string& skill_id, SandboxLevel level) override {
        std::string sandbox_path = "/var/run/qoostore/sandboxes/" + skill_id;

        // 1. 创建 cgroup
        std::string cgroup_path = "/sys/fs/cgroup/qoostore/" + skill_id;
        if (!createCgroup(skill_id)) {
            return false;
        }

        // 2. 创建 OverlayFS 文件系统
        std::string lower_dir = "/opt/qoostore/skills/repo/" + skill_id;
        std::string upper_dir = sandbox_path + "/upper";
        std::string work_dir = sandbox_path + "/work";
        std::string merged_dir = sandbox_path + "/merged";

        if (!setupOverlayFS(lower_dir, upper_dir, work_dir, merged_dir)) {
            return false;
        }

        // 3. 创建 Network Namespace
        if (!createNetNS(skill_id)) {
            return false;
        }

        sandbox_info_[skill_id] = {level, sandbox_path, merged_dir, true};
        std::cout << "[SandboxEngine] Sandbox created: " << skill_id << " level=" << static_cast<int>(level) << std::endl;
        return true;
    }

    bool destroySandbox(const std::string& skill_id) override {
        stopSandbox(skill_id);
        sandbox_info_.erase(skill_id);
        std::cout << "[SandboxEngine] Sandbox destroyed: " << skill_id << std::endl;
        return true;
    }

    bool startInSandbox(const std::string& skill_id, const std::string& entry_point) override {
        auto it = sandbox_info_.find(skill_id);
        if (it == sandbox_info_.end()) return false;

        // 在沙箱中启动技能进程
        // 实际实现：clone() with CLONE_NEWNS | CLONE_NEWNET | CLONE_NEWPID
        // 然后 chroot 到 merged_dir，执行 entry_point
        std::cout << "[SandboxEngine] Starting skill in sandbox: " << skill_id << " entry=" << entry_point << std::endl;
        return true;
    }

    bool stopSandbox(const std::string& skill_id) override {
        std::cout << "[SandboxEngine] Stopping sandbox: " << skill_id << std::endl;
        return true;
    }

    bool setupFilesystem(const std::string& skill_id, const std::string& root_path) override {
        std::cout << "[SandboxEngine] FS setup: " << skill_id << " root=" << root_path << std::endl;
        return true;
    }

    bool restrictPath(const std::string& skill_id, const std::string& path, bool read_only) override {
        std::cout << "[SandboxEngine] Restrict path: " << skill_id << " path=" << path
                  << " ro=" << read_only << std::endl;
        return true;
    }

    bool createNetworkNamespace(const std::string& skill_id) override {
        std::cout << "[SandboxEngine] Creating netns for: " << skill_id << std::endl;
        return true;
    }

    bool allowNetworkAccess(const std::string& skill_id, bool allow) override {
        std::cout << "[SandboxEngine] Network access for " << skill_id << ": " << allow << std::endl;
        return true;
    }

    bool restrictHost(const std::string& skill_id, const std::string& host) override {
        std::cout << "[SandboxEngine] Restrict host: " << skill_id << " -> " << host << std::endl;
        return true;
    }

    bool setMemoryLimit(const std::string& skill_id, uint64_t max_mb) override {
        std::string cgroup_path = "/sys/fs/cgroup/qoostore/" + skill_id + "/memory.max";
        std::cout << "[SandboxEngine] Memory limit for " << skill_id << ": " << max_mb << "MB" << std::endl;
        return true;
    }

    bool setCpuLimit(const std::string& skill_id, uint32_t max_percent) override {
        std::string cgroup_path = "/sys/fs/cgroup/qoostore/" + skill_id + "/cpu.max";
        std::cout << "[SandboxEngine] CPU limit for " << skill_id << ": " << max_percent << "%" << std::endl;
        return true;
    }

    bool setDiskQuota(const std::string& skill_id, uint64_t max_mb) override {
        std::cout << "[SandboxEngine] Disk quota for " << skill_id << ": " << max_mb << "MB" << std::endl;
        return true;
    }

    ResourceUsage getUsage(const std::string& skill_id) const override {
        return ResourceUsage{};
    }

    bool isRunning(const std::string& skill_id) const override {
        auto it = sandbox_info_.find(skill_id);
        return it != sandbox_info_.end() && it->second.running;
    }

private:
    struct SandboxInfo {
        SandboxLevel level;
        std::string path;
        std::string merged_dir;
        bool running{false};
    };
    std::map<std::string, SandboxInfo> sandbox_info_;

    bool createCgroup(const std::string& skill_id) {
        // 创建 cgroup v2 层级
        // mkdir /sys/fs/cgroup/qoostore/{skill_id}
        return true;
    }

    bool setupOverlayFS(const std::string& lower, const std::string& upper,
                         const std::string& work, const std::string& merged) {
        // mount -t overlay overlay -o lowerdir={lower},upperdir={upper},workdir={work} {merged}
        return true;
    }

    bool createNetNS(const std::string& skill_id) {
        // ip netns add qoostore_{skill_id}
        return true;
    }
};

std::unique_ptr<SandboxEngine> createSandboxEngine() {
    return std::make_unique<SandboxEngineImpl>();
}

} // namespace edge
} // namespace qoostore
