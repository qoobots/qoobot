#pragma once

#include "skill_types.h"
#include <string>
#include <vector>

namespace qoostore {
namespace edge {

/**
 * RuntimeMonitor — 运行时监控
 * CPU/内存/网络使用监控，异常检测，崩溃收集
 */
class RuntimeMonitor {
public:
    virtual ~RuntimeMonitor() = default;

    // 监控生命周期
    virtual void startMonitoring(const std::string& skill_id) = 0;
    virtual void stopMonitoring(const std::string& skill_id) = 0;
    virtual void startMonitoringAll() = 0;
    virtual void stopMonitoringAll() = 0;

    // 资源使用
    virtual ResourceUsage getResourceUsage(const std::string& skill_id) const = 0;
    virtual std::vector<std::pair<std::string, ResourceUsage>> getAllUsage() const = 0;

    // 异常检测
    virtual bool isAnomalous(const std::string& skill_id) const = 0;
    virtual std::string getAnomalyReason(const std::string& skill_id) const = 0;

    // 崩溃收集
    virtual void onCrash(CrashCallback callback) = 0;
    virtual void reportCrash(const CrashReport& report) = 0;
    virtual std::vector<CrashReport> getCrashHistory(const std::string& skill_id) const = 0;

    // 统计上报
    virtual void reportStats(const std::string& skill_id, const ResourceUsage& usage) = 0;
    virtual void flushStats() = 0;

    // 强制终止
    virtual void killSkill(const std::string& skill_id) = 0;
    virtual void suspendSkill(const std::string& skill_id) = 0;
    virtual void resumeSkill(const std::string& skill_id) = 0;
};

} // namespace edge
} // namespace qoostore
