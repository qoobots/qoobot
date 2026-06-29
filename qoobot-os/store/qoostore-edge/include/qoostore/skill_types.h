#pragma once

#include <string>
#include <vector>
#include <map>
#include <cstdint>
#include <functional>

namespace qoostore {
namespace edge {

// ============================================================================
// 类型定义
// ============================================================================

enum class SkillStatus {
    INSTALLING,
    ACTIVE,
    UPDATING,
    UNINSTALLING,
    REMOVED,
    DISABLED,
    ERROR
};

enum class PermissionLevel {
    NORMAL,      // 无需用户确认（日志/统计）
    DANGEROUS,   // 需用户授权（摄像头/麦克风/位置）
    SIGNATURE    // 仅系统签名技能可用（急停/安全）
};

enum class SandboxLevel {
    UNRESTRICTED,  // 出厂技能
    RESTRICTED,    // 第三方技能（默认）
    ISOLATED       // 高隔离级别
};

struct SkillManifest {
    std::string skill_id;
    std::string name;
    std::string version;
    std::string min_qos_version;
    std::string category;
    std::string entry_point;
    std::string runtime;
    std::vector<std::string> permissions;
    SandboxLevel sandbox_level{SandboxLevel::RESTRICTED};
    uint64_t max_memory_mb{512};
    uint32_t max_cpu_percent{30};
};

struct InstalledSkill {
    std::string skill_id;
    std::string name;
    std::string version;
    std::string install_path;
    SkillStatus status{SkillStatus::ACTIVE};
    std::string license_key;
    uint64_t installed_at{0};
    uint64_t updated_at{0};
};

struct Permission {
    std::string name;           // "camera", "microphone", "location", "motor.arm"
    std::string description;
    PermissionLevel level{PermissionLevel::DANGEROUS};
    bool granted{false};
};

struct ResourceUsage {
    double cpu_percent{0.0};
    uint64_t memory_mb{0};
    uint64_t disk_mb{0};
    uint64_t network_rx_bytes{0};
    uint64_t network_tx_bytes{0};
};

struct CrashReport {
    std::string skill_id;
    std::string version;
    std::string signal;
    std::string backtrace;
    uint64_t timestamp{0};
};

// ============================================================================
// 回调类型
// ============================================================================

using InstallCallback = std::function<void(const std::string& skill_id, bool success, const std::string& error)>;
using UpdateCallback = std::function<void(const std::string& skill_id, const std::string& new_version, bool success)>;
using UninstallCallback = std::function<void(const std::string& skill_id, bool success)>;
using CrashCallback = std::function<void(const CrashReport& report)>;
using StatusCallback = std::function<void(const std::string& skill_id, SkillStatus status)>;

} // namespace edge
} // namespace qoostore
