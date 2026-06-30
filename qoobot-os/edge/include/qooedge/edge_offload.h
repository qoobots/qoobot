#pragma once

#include "edge_types.h"
#include <string>
#include <vector>
#include <functional>

namespace qooedge {

/**
 * EdgeOffload — 端-云任务卸载决策引擎
 *
 * 基于网络状态、任务特性和设备负载，动态决定推理任务在本地执行、
 * 卸载到云端、或分发给边缘对等节点。核心是一个多因素决策模型。
 *
 * 决策因素：
 *   1. 网络延迟预算
 *   2. 任务实时性要求
 *   3. 本地 NPU/GPU 负载
 *   4. 能耗约束
 *   5. 数据敏感性（隐私）
 *
 * 对标：Split Computing / Neurosurgeon 框架
 */
class EdgeOffload {
public:
    virtual ~EdgeOffload() = default;

    /**
     * 初始化卸载引擎
     * @param config_path 决策模型配置路径
     */
    virtual bool initialize(const std::string& config_path) = 0;

    /**
     * 对推理任务做出卸载决策
     * @param task 推理任务
     * @param local_load 本地 NPU/GPU 负载 (0.0-1.0)
     * @param network_budget 当前可用的网络延迟预算
     * @return 卸载决策
     */
    virtual OffloadDecision decide(const OffloadTask& task,
                                    double local_load,
                                    const NetworkBudget& network_budget) = 0;

    /**
     * 批量任务卸载决策（考虑流水线并行）
     */
    virtual std::vector<OffloadDecision> decideBatch(
        const std::vector<OffloadTask>& tasks,
        double local_load,
        const NetworkBudget& network_budget) = 0;

    /**
     * 更新网络延迟预算（周期性测量）
     */
    virtual void updateNetworkBudget(const NetworkBudget& budget) = 0;

    /**
     * 获取当前网络预算
     */
    virtual NetworkBudget getNetworkBudget() const = 0;

    /**
     * 设置离线模式
     * @param offline true=强制本地执行，false=允许云端卸载
     */
    virtual void setOfflineMode(bool offline) = 0;
    virtual bool isOfflineMode() const = 0;

    /**
     * 获取卸载决策统计
     */
    virtual std::string getDecisionStats() const = 0;

    /**
     * 设置能耗预算（mAh/s）
     */
    virtual void setEnergyBudget(double mah_per_second) = 0;
};

// 工厂函数
std::unique_ptr<EdgeOffload> createEdgeOffload();

} // namespace qooedge
