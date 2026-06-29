/**
 * @file ir_graph.h
 * @brief 设备 IR 图数据结构 — IrGraph、IrBuilder、IrValidator
 *
 * IrGraph 是 qoocore 编译器中模型内部表示的图结构。
 * 它是前端框架（ONNX/Torch）与后端硬件（NPU/GPU/CPU）之间的桥梁。
 *
 * 设计原则：
 *   - 有向无环图（DAG），节点为 IrNode，边为命名数据流
 *   - 支持拓扑排序（编译顺序）、反向遍历（梯度/调试）
 *   - 轻量级，不依赖 MLIR/LLVM（可选集成）
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#pragma once

#include "qoocore/compiler.h"

#include <algorithm>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace qoocore {
namespace ir {

// ── IrGraph — 计算图数据结构 ────────────────────────────────────────
/**
 * @brief 设备 IR 图 — 持有所有节点、边和全局元数据。
 *
 * 图的边是隐式的：每个 IrNode.inputs/outputs 中的名称即为边。
 * 输入/输出名称必须唯一（SSA 风格）。
 */
class IrGraph {
public:
    IrGraph() = default;
    explicit IrGraph(std::string name) : name_(std::move(name)) {}

    // ── 节点管理 ─────────────────────────────────────────────────────
    /**
     * @brief 添加节点。
     * @return 节点指针（非拥有），用于后续链式构建
     * @throws std::invalid_argument 若节点 ID 已存在
     */
    IrNode* add_node(IrNode node) {
        if (nodes_.find(node.id) != nodes_.end()) {
            throw std::invalid_argument("Duplicate node ID: " + node.id);
        }
        auto [it, _] = nodes_.emplace(node.id, std::move(node));
        return &it->second;
    }

    /**
     * @brief 获取节点（可变）。
     */
    IrNode* get_node(const std::string& id) {
        auto it = nodes_.find(id);
        return it != nodes_.end() ? &it->second : nullptr;
    }

    /**
     * @brief 获取节点（只读）。
     */
    const IrNode* get_node(const std::string& id) const {
        auto it = nodes_.find(id);
        return it != nodes_.end() ? &it->second : nullptr;
    }

    /**
     * @brief 移除节点（同时断开所有边）。
     */
    void remove_node(const std::string& id) {
        nodes_.erase(id);
    }

    /**
     * @brief 节点数量。
     */
    [[nodiscard]] std::size_t node_count() const noexcept {
        return nodes_.size();
    }

    /**
     * @brief 遍历所有节点。
     */
    template <typename Func>
    void for_each_node(Func&& f) const {
        for (const auto& [id, node] : nodes_) {
            f(node);
        }
    }

    // ── 图级信息 ─────────────────────────────────────────────────────
    [[nodiscard]] const std::string& name() const noexcept { return name_; }
    void set_name(std::string name) { name_ = std::move(name); }

    /**
     * @brief 设置图输入节点 ID 列表。
     */
    void set_inputs(std::vector<std::string> inputs) {
        inputs_ = std::move(inputs);
    }
    [[nodiscard]] const std::vector<std::string>& inputs() const noexcept {
        return inputs_;
    }

    /**
     * @brief 设置图输出节点 ID 列表。
     */
    void set_outputs(std::vector<std::string> outputs) {
        outputs_ = std::move(outputs);
    }
    [[nodiscard]] const std::vector<std::string>& outputs() const noexcept {
        return outputs_;
    }

    // ── 拓扑排序 ─────────────────────────────────────────────────────
    /**
     * @brief 拓扑排序（Kahn 算法）。
     * @return 按拓扑顺序排列的节点 ID 列表
     * @throws std::runtime_error 若图存在环
     *
     * 编译器和代码生成器按此顺序处理节点。
     */
    [[nodiscard]] std::vector<std::string> topological_sort() const {
        // 构建入度表和邻接表
        std::unordered_map<std::string, int> in_degree;
        std::unordered_map<std::string, std::vector<std::string>> adj;

        for (const auto& [id, node] : nodes_) {
            if (in_degree.find(id) == in_degree.end()) {
                in_degree[id] = 0;
            }
            for (const auto& input : node.inputs) {
                adj[input].push_back(id);
                in_degree[id]++;
            }
        }

        // Kahn 算法
        std::queue<std::string> q;
        for (const auto& [id, degree] : in_degree) {
            if (degree == 0) q.push(id);
        }

        std::vector<std::string> result;
        while (!q.empty()) {
            std::string id = q.front();
            q.pop();
            result.push_back(id);

            for (const auto& neighbor : adj[id]) {
                if (--in_degree[neighbor] == 0) {
                    q.push(neighbor);
                }
            }
        }

        if (result.size() != nodes_.size()) {
            throw std::runtime_error(
                "Cycle detected in IR graph '" + name_ +
                "' (" + std::to_string(result.size()) + "/" +
                std::to_string(nodes_.size()) + " nodes sorted)");
        }

        return result;
    }

    /**
     * @brief 获取所有输入边（扇入）。
     */
    [[nodiscard]] std::vector<const IrNode*> predecessors(
        const std::string& node_id) const {
        std::vector<const IrNode*> result;
        for (const auto& [id, node] : nodes_) {
            for (const auto& output : node.outputs) {
                if (output == node_id) {
                    result.push_back(&node);
                    break;
                }
            }
        }
        return result;
    }

    /**
     * @brief 获取所有输出边（扇出）。
     */
    [[nodiscard]] std::vector<const IrNode*> successors(
        const std::string& node_id) const {
        auto node = get_node(node_id);
        if (!node) return {};

        std::vector<const IrNode*> result;
        for (const auto& output : node->outputs) {
            auto succ = get_node(output);
            if (succ) result.push_back(succ);
        }
        return result;
    }

    /**
     * @brief 计算图的总 FLOPs。
     */
    [[nodiscard]] std::size_t total_flops() const noexcept {
        std::size_t total = 0;
        for (const auto& [id, node] : nodes_) {
            if (node.flops.has_value()) total += *node.flops;
        }
        return total;
    }

    /**
     * @brief 计算图的总内存占用（字节）。
     */
    [[nodiscard]] std::size_t total_memory_bytes() const noexcept {
        std::size_t total = 0;
        for (const auto& [id, node] : nodes_) {
            if (node.memory_bytes.has_value()) total += *node.memory_bytes;
        }
        return total;
    }

private:
    std::string name_{"unnamed_graph"};
    std::unordered_map<std::string, IrNode> nodes_;
    std::vector<std::string> inputs_;
    std::vector<std::string> outputs_;
};

// ── IrBuilder — IR 图构建器（Builder 模式）──────────────────────────
/**
 * @brief 流式构建 IrGraph 的帮助类。
 *
 * 用法：
 * ```cpp
 * auto graph = IrBuilder("mobilenet_v2")
 *     .add_input("input_tensor")
 *     .conv2d("conv1", "input_tensor", 32, 3, 2)
 *     .relu("relu1", "conv1")
 *     .global_avg_pool("pool", "relu1")
 *     .add_output("pool")
 *     .build();
 * ```
 */
class IrBuilder {
public:
    explicit IrBuilder(std::string graph_name = "graph")
        : graph_(std::move(graph_name)) {}

    /**
     * @brief 声明图输入。
     */
    IrBuilder& add_input(const std::string& name) {
        inputs_.push_back(name);
        return *this;
    }

    /**
     * @brief 声明图输出。
     */
    IrBuilder& add_output(const std::string& name) {
        outputs_.push_back(name);
        return *this;
    }

    // ── 常见算子快捷方法 ────────────────────────────────────────────

    IrBuilder& conv2d(const std::string& id,
                      const std::string& input,
                      int out_channels, int kernel_size, int stride = 1,
                      int padding = 0, const std::string& activation = "relu") {
        IrNode node;
        node.id = id;
        node.op_type = "Conv2D";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        node.attrs["out_channels"] = out_channels;
        node.attrs["kernel_size"] = kernel_size;
        node.attrs["stride"] = stride;
        node.attrs["padding"] = padding;
        if (!activation.empty()) node.attrs["activation"] = activation;
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& depthwise_conv2d(const std::string& id,
                                 const std::string& input,
                                 int kernel_size, int stride = 1) {
        IrNode node;
        node.id = id;
        node.op_type = "DepthwiseConv2D";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        node.attrs["kernel_size"] = kernel_size;
        node.attrs["stride"] = stride;
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& relu(const std::string& id, const std::string& input) {
        IrNode node;
        node.id = id;
        node.op_type = "ReLU";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& relu6(const std::string& id, const std::string& input) {
        IrNode node;
        node.id = id;
        node.op_type = "ReLU6";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& hard_swish(const std::string& id, const std::string& input) {
        IrNode node;
        node.id = id;
        node.op_type = "HardSwish";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& batch_norm(const std::string& id, const std::string& input) {
        IrNode node;
        node.id = id;
        node.op_type = "BatchNorm";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& add(const std::string& id,
                   const std::string& lhs, const std::string& rhs) {
        IrNode node;
        node.id = id;
        node.op_type = "Add";
        node.inputs = {lhs, rhs};
        node.outputs = {id + "_out"};
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& global_avg_pool(const std::string& id,
                                const std::string& input) {
        IrNode node;
        node.id = id;
        node.op_type = "GlobalAvgPool";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& max_pool2d(const std::string& id, const std::string& input,
                          int kernel_size, int stride) {
        IrNode node;
        node.id = id;
        node.op_type = "MaxPool2D";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        node.attrs["kernel_size"] = kernel_size;
        node.attrs["stride"] = stride;
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& matmul(const std::string& id,
                      const std::string& a, const std::string& b) {
        IrNode node;
        node.id = id;
        node.op_type = "MatMul";
        node.inputs = {a, b};
        node.outputs = {id + "_out"};
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& softmax(const std::string& id, const std::string& input,
                       int axis = -1) {
        IrNode node;
        node.id = id;
        node.op_type = "Softmax";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        node.attrs["axis"] = axis;
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& reshape(const std::string& id, const std::string& input,
                       const std::vector<int>& shape) {
        IrNode node;
        node.id = id;
        node.op_type = "Reshape";
        node.inputs = {input};
        node.outputs = {id + "_out"};
        node.attrs["shape"] = shape;
        graph_.add_node(std::move(node));
        return *this;
    }

    IrBuilder& concat(const std::string& id,
                      const std::vector<std::string>& inputs, int axis = 1) {
        IrNode node;
        node.id = id;
        node.op_type = "Concat";
        node.inputs = inputs;
        node.outputs = {id + "_out"};
        node.attrs["axis"] = axis;
        graph_.add_node(std::move(node));
        return *this;
    }

    /**
     * @brief 添加自定义算子节点。
     */
    IrBuilder& custom_op(const std::string& id,
                          const std::string& op_type,
                          const std::vector<std::string>& inputs) {
        IrNode node;
        node.id = id;
        node.op_type = op_type;
        node.inputs = inputs;
        node.outputs = {id + "_out"};
        graph_.add_node(std::move(node));
        return *this;
    }

    /**
     * @brief 构建并返回 IrGraph。
     */
    [[nodiscard]] IrGraph build() {
        graph_.set_inputs(std::move(inputs_));
        graph_.set_outputs(std::move(outputs_));
        return std::move(graph_);
    }

    /**
     * @brief 获取当前图引用（用于检查）。
     */
    [[nodiscard]] const IrGraph& graph() const noexcept { return graph_; }

private:
    IrGraph graph_;
    std::vector<std::string> inputs_;
    std::vector<std::string> outputs_;
};

// ── IrValidator — IR 图验证器 ───────────────────────────────────────
/**
 * @brief 验证 IrGraph 的正确性。
 *
 * 检查项：
 *   - 无孤立节点
 *   - 无悬空引用（输入/输出引用了不存在的节点）
 *   - 无环（DAG 性质）
 *   - 输入/输出节点存在
 *   - 算子类型合法
 */
class IrValidator {
public:
    struct Issue {
        enum class Severity { WARNING, ERROR };
        Severity severity;
        std::string node_id;
        std::string message;
    };

    /**
     * @brief 验证图，返回所有问题。
     */
    [[nodiscard]] static std::vector<Issue> validate(const IrGraph& graph) {
        std::vector<Issue> issues;

        // 1. 检查输入/输出节点存在
        for (const auto& input : graph.inputs()) {
            if (!graph.get_node(input)) {
                issues.push_back({Issue::Severity::ERROR, input,
                                  "Graph input '" + input + "' not found in nodes"});
            }
        }
        for (const auto& output : graph.outputs()) {
            if (!graph.get_node(output)) {
                issues.push_back({Issue::Severity::ERROR, output,
                                  "Graph output '" + output + "' not found in nodes"});
            }
        }

        // 2. 检查节点引用完整性
        std::unordered_set<std::string> all_ids;
        graph.for_each_node([&](const IrNode& node) {
            all_ids.insert(node.id);
        });

        graph.for_each_node([&](const IrNode& node) {
            // 检查 inputs
            for (const auto& input : node.inputs) {
                if (all_ids.find(input) == all_ids.end()) {
                    // 不是节点 ID，可能是图输入张量名（允许）
                    bool is_graph_input = false;
                    for (const auto& gi : graph.inputs()) {
                        if (gi == input) { is_graph_input = true; break; }
                    }
                    if (!is_graph_input) {
                        issues.push_back({Issue::Severity::WARNING, node.id,
                                          "Input '" + input + "' not found in graph"});
                    }
                }
            }
            // 检查 outputs
            for (const auto& output : node.outputs) {
                if (all_ids.find(output) == all_ids.end()) {
                    // 不是节点 ID，可能是图输出张量名（允许）
                    bool is_graph_output = false;
                    for (const auto& go : graph.outputs()) {
                        if (go == output) { is_graph_output = true; break; }
                    }
                    if (!is_graph_output) {
                        issues.push_back({Issue::Severity::WARNING, node.id,
                                          "Output '" + output + "' not found in graph"});
                    }
                }
            }
        });

        // 3. 检查 DAG 性质（无环）
        try {
            graph.topological_sort();
        } catch (const std::runtime_error& e) {
            issues.push_back({Issue::Severity::ERROR, "",
                              std::string("Graph contains a cycle: ") + e.what()});
        }

        // 4. 检查孤立节点
        if (graph.node_count() > 0) {
            graph.for_each_node([&](const IrNode& node) {
                if (node.inputs.empty() && node.outputs.empty()) {
                    issues.push_back({Issue::Severity::WARNING, node.id,
                                      "Isolated node (no inputs and no outputs)"});
                }
            });
        }

        return issues;
    }

    /**
     * @brief 验证图，若存在 ERROR 级别问题则返回 false。
     */
    [[nodiscard]] static bool is_valid(const IrGraph& graph) {
        auto issues = validate(graph);
        for (const auto& issue : issues) {
            if (issue.severity == Issue::Severity::ERROR) return false;
        }
        return true;
    }
};

}  // namespace ir
}  // namespace qoocore
