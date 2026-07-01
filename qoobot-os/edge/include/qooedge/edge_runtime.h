#pragma once

#include "edge_types.h"
#include <memory>
#include <string>
#include <vector>
#include <functional>

namespace qooedge {

/**
 * EdgeRuntime — 边缘推理运行时
 *
 * 位于端侧 AI 引擎 (QooCore) 和云端推理 (QooCloud) 之间。
 * 提供本地优先的推理执行环境，支持任务队列、优先级调度和资源仲裁。
 *
 * 对标：AWS Greengrass / Azure IoT Edge 的推理运行时
 */
class EdgeRuntime {
public:
    virtual ~EdgeRuntime() = default;

    /**
     * 初始化运行时
     * @param model_registry_path 本地模型注册表路径
     * @return 是否初始化成功
     */
    virtual bool initialize(const std::string& model_registry_path) = 0;

    /**
     * 提交推理任务
     * @param task 卸载任务描述
     * @param callback 结果回调
     */
    virtual void submitTask(const OffloadTask& task, OffloadCallback callback) = 0;

    /**
     * 取消推理任务
     * @param task_id 任务 ID
     */
    virtual void cancelTask(const std::string& task_id) = 0;

    /**
     * 获取当前队列深度
     */
    virtual size_t getQueueDepth() const = 0;

    /**
     * 获取运行时统计信息
     * @return 格式：{"tasks_completed": N, "avg_latency_ms": X, ...}
     */
    virtual std::string getStatistics() const = 0;

    /**
     * 加载模型到本地缓存
     * @param model_name 模型名称
     * @param version 模型版本
     */
    virtual bool loadModel(const std::string& model_name,
                            const std::string& version) = 0;

    /**
     * 卸载模型释放内存
     * @param model_name 模型名称
     */
    virtual void unloadModel(const std::string& model_name) = 0;

    /**
     * 列出已加载的模型
     */
    virtual std::vector<std::string> listLoadedModels() const = 0;

    /**
     * 优雅关闭运行时
     */
    virtual void shutdown() = 0;
};

// 工厂函数
std::unique_ptr<EdgeRuntime> createEdgeRuntime();

} // namespace qooedge
