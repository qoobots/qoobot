#pragma once

#include "edge_types.h"
#include <memory>
#include <string>
#include <vector>
#include <functional>

namespace qooedge {

/**
 * EdgeSync — 端-云数据同步引擎
 *
 * 管理机器人端与云端之间的数据同步：
 *   - 模型权重同步（.qoomodel 新版本下载）
 *   - 地图数据同步（SLAM 地图上传/下载）
 *   - 知识图谱同步（经验数据上传）
 *   - 日志指标同步（监控数据上传）
 *   - 配置策略同步（云端策略下发）
 *
 * 同步策略：全量/增量/差分/延迟
 *
 * 对标：Android SyncAdapter / Firebase Realtime Sync
 */
class EdgeSync {
public:
    virtual ~EdgeSync() = default;

    /**
     * 初始化同步引擎
     * @param cloud_endpoint 云端同步服务地址
     * @param device_id 设备唯一标识
     */
    virtual bool initialize(const std::string& cloud_endpoint,
                             const std::string& device_id) = 0;

    /**
     * 启动同步任务
     * @param task 同步任务描述
     * @param callback 进度回调
     */
    virtual void startSync(const SyncTask& task, SyncCallback callback) = 0;

    /**
     * 取消同步任务
     */
    virtual void cancelSync(const std::string& sync_id) = 0;

    /**
     * 设置同步策略
     */
    virtual void setSyncPolicy(SyncStrategy default_strategy) = 0;

    /**
     * 设置网络条件约束（仅在 WiFi/充电时同步）
     */
    virtual void setNetworkConstraints(bool wifi_only,
                                        bool charging_only) = 0;

    /**
     * 获取同步状态
     */
    virtual std::vector<SyncProgress> getActiveSyncs() const = 0;

    /**
     * 检查资源是否有更新
     * @param resource_path 资源路径
     * @return 云端是否有更新版本
     */
    virtual bool checkForUpdate(const std::string& resource_path) = 0;

    /**
     * 获取资源版本
     * @param resource_path 资源路径
     * @return 当前本地版本号
     */
    virtual std::string getResourceVersion(const std::string& resource_path) const = 0;

    /**
     * 立即强制执行同步
     */
    virtual void forceSyncNow() = 0;

    /**
     * 设置同步间隔（秒）
     */
    virtual void setSyncInterval(uint32_t interval_sec) = 0;
};

// 工厂函数
std::unique_ptr<EdgeSync> createEdgeSync();

} // namespace qooedge
