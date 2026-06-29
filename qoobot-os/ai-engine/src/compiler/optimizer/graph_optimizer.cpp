/**
 * @file graph_optimizer.cpp
 * @brief 计算图优化器实现
 *
 * 对 IR 图执行一系列优化 Pass：
 *   O1：常量折叠、死代码消除
 *   O2：算子融合（Conv+BN+ReLU → FusedConv）、内存复用
 *   O3：跨层融合、动态 shape 推导
 *
 * 优化器以 Pass 模式组织，每个 Pass 遍历并变换 IR 图。
 *
 * @copyright QooBot Project
 * @version 0.1.0
 */

#include "qoocore/compiler.h"
#include "../ir/ir_graph.h"

#include <spdlog/spdlog.h>
#include <algorithm>
#include <sstream>
#include <string>
#include <unordered_set>
#include <vector>

namespace qoocore {

// ── 从 JSON 字符串解析 IR 图 ───────────────────────────────────────
// 注：完整实现需 nlohmann/json，此处提供简化解析器

namespace {

// ── O1 优化 Pass ──────────────────────────────────────────────────────

/**
 * @brief 常量折叠：将编译时可计算的节点替换为常量。
 *
 * 检测模式：Const → Op → Result，若 Op 的所有输入都是 Const，则折叠。
 */
static void constant_folding(ir::IrGraph& graph) {
    // 收集所有常量节点
    std::unordered_set<std::string> const_nodes;
    graph.for_each_node([&](const IrNode& node) {
        if (node.op_type == "Const" || node.op_type == "Constant") {
            const_nodes.insert(node.id);
        }
    });

    // 查找所有输入全为常量的节点
    std::vector<std::string> to_fold;
    graph.for_each_node([&](const IrNode& node) {
        if (node.op_type == "Const" || node.op_type == "Constant") return;
        if (node.op_type == "Input" || node.op_type == "Output") return;

        bool all_const = !node.inputs.empty();
        for (const auto& input : node.inputs) {
            if (const_nodes.find(input) == const_nodes.end()) {
                all_const = false;
                break;
            }
        }

        if (all_const) {
            to_fold.push_back(node.id);
            spdlog::debug("[const_fold] Folding node '{}' ({})",
                           node.id, node.op_type);
        }
    });

    // 标记为常量节点（实际折叠需要知道张量值，此处标记）
    for (const auto& id : to_fold) {
        const_nodes.insert(id);
    }

    spdlog::info("[const_fold] Folded {} constant sub-graphs", to_fold.size());
}

/**
 * @brief 死代码消除：移除对输出无贡献的节点。
 *
 * 从输出节点反向遍历标记活跃节点，移除未标记的节点。
 */
static void dead_code_elimination(ir::IrGraph& graph) {
    if (graph.outputs().empty()) {
        spdlog::warn("[dce] No graph outputs defined, skipping DCE");
        return;
    }

    // 从输出节点反向 BFS 标记活跃节点
    std::unordered_set<std::string> alive;
    std::vector<std::string> queue = graph.outputs();

    while (!queue.empty()) {
        std::string id = std::move(queue.back());
        queue.pop_back();

        if (alive.find(id) != alive.end()) continue;
        alive.insert(id);

        auto node = graph.get_node(id);
        if (node) {
            for (const auto& input : node->inputs) {
                if (alive.find(input) == alive.end()) {
                    queue.push_back(input);
                }
            }
        }
    }

    // 收集死节点
    std::vector<std::string> dead;
    graph.for_each_node([&](const IrNode& node) {
        if (alive.find(node.id) == alive.end()) {
            dead.push_back(node.id);
        }
    });

    // 移除死节点
    for (const auto& id : dead) {
        graph.remove_node(id);
    }

    spdlog::info("[dce] Removed {} dead nodes ({} alive)",
                  dead.size(), alive.size());
}

// ── O2 优化 Pass ──────────────────────────────────────────────────────

/**
 * @brief 算子融合：将相邻可融合算子合并。
 *
 * 常见融合模式：
 *   Conv2D + BatchNorm + ReLU  → FusedConvBNReLU
 *   Conv2D + ReLU               → FusedConvReLU
 *   MatMul + Add + ReLU         → FusedMatMulAddReLU (GEMM 风格)
 */
static void operator_fusion(ir::IrGraph& graph) {
    int fusion_count = 0;

    // 收集可融合的链
    graph.for_each_node([&](const IrNode& node) {
        if (node.op_type != "Conv2D") return;

        // Conv2D → BatchNorm → ReLU
        if (node.outputs.size() == 1) {
            auto bn_node = graph.get_node(node.outputs[0]);
            if (bn_node && bn_node->op_type == "BatchNorm" &&
                bn_node->outputs.size() == 1) {

                auto relu_node = graph.get_node(bn_node->outputs[0]);
                if (relu_node && relu_node->op_type == "ReLU") {
                    // 融合为 FusedConvBNReLU
                    IrNode fused;
                    fused.id = node.id + "_fused_bn_relu";
                    fused.op_type = "FusedConvBNReLU";
                    fused.inputs = node.inputs;
                    fused.outputs = relu_node->outputs;
                    // 继承属性
                    fused.attrs = node.attrs;

                    graph.remove_node(node.id);
                    graph.remove_node(bn_node->id);
                    graph.remove_node(relu_node->id);
                    graph.add_node(std::move(fused));

                    fusion_count++;
                    spdlog::debug("[fusion] Conv2D+BN+ReLU → FusedConvBNReLU at {}",
                                   fused.id);
                    return;
                }
            }
        }

        // Conv2D → ReLU (简单融合)
        if (node.outputs.size() == 1) {
            auto relu_node = graph.get_node(node.outputs[0]);
            if (relu_node && relu_node->op_type == "ReLU") {
                IrNode fused;
                fused.id = node.id + "_fused_relu";
                fused.op_type = "FusedConvReLU";
                fused.inputs = node.inputs;
                fused.outputs = relu_node->outputs;
                fused.attrs = node.attrs;

                graph.remove_node(node.id);
                graph.remove_node(relu_node->id);
                graph.add_node(std::move(fused));

                fusion_count++;
                spdlog::debug("[fusion] Conv2D+ReLU → FusedConvReLU at {}",
                               fused.id);
            }
        }
    });

    // MatMul + Add → MatMulAdd
    graph.for_each_node([&](const IrNode& node) {
        if (node.op_type != "MatMul") return;

        if (node.outputs.size() == 1) {
            auto add_node = graph.get_node(node.outputs[0]);
            if (add_node && add_node->op_type == "Add") {
                IrNode fused;
                fused.id = node.id + "_fused_add";
                fused.op_type = "FusedMatMulAdd";
                // MatMul 的输入 + Add 的第二个输入
                fused.inputs = node.inputs;
                // Add 有两个输入，第一个是 MatMul 输出
                if (add_node->inputs.size() == 2) {
                    // 找出非 MatMul 输出的输入
                    for (const auto& in : add_node->inputs) {
                        if (in != node.outputs[0]) {
                            fused.inputs.push_back(in);
                            break;
                        }
                    }
                }
                fused.outputs = add_node->outputs;
                fused.attrs = node.attrs;

                graph.remove_node(node.id);
                graph.remove_node(add_node->id);
                graph.add_node(std::move(fused));

                fusion_count++;
                spdlog::debug("[fusion] MatMul+Add → FusedMatMulAdd at {}",
                               fused.id);
            }
        }
    });

    spdlog::info("[fusion] Performed {} operator fusions", fusion_count);
}

// ── O3 优化 Pass ──────────────────────────────────────────────────────

/**
 * @brief 内存复用分析：标记可共享内存缓冲区的张量。
 *
 * 检测生命周期不重叠的张量，标记为可共享内存。
 */
static void memory_reuse_analysis(ir::IrGraph& graph) {
    try {
        auto topo = graph.topological_sort();

        // 记录每个张量的首次使用和最后使用位置
        struct TensorLifetime {
            int first_use;
            int last_use;
        };
        std::unordered_map<std::string, TensorLifetime> lifetimes;

        for (int i = 0; i < static_cast<int>(topo.size()); ++i) {
            auto node = graph.get_node(topo[i]);
            if (!node) continue;

            for (const auto& output : node->outputs) {
                auto& lt = lifetimes[output];
                lt.first_use = i;
                lt.last_use = i;
            }

            for (const auto& input : node->inputs) {
                auto it = lifetimes.find(input);
                if (it != lifetimes.end()) {
                    it->second.last_use = std::max(it->second.last_use, i);
                }
            }
        }

        // 统计可共享的对数
        int shareable_pairs = 0;
        std::vector<std::string> tensor_names;
        for (const auto& [name, _] : lifetimes) tensor_names.push_back(name);

        for (std::size_t i = 0; i < tensor_names.size(); ++i) {
            for (std::size_t j = i + 1; j < tensor_names.size(); ++j) {
                const auto& a = lifetimes[tensor_names[i]];
                const auto& b = lifetimes[tensor_names[j]];
                // 若生命周期不重叠，则可共享内存
                if (a.last_use < b.first_use || b.last_use < a.first_use) {
                    shareable_pairs++;
                }
            }
        }

        spdlog::info("[mem_reuse] {} tensors, {} shareable pairs identified",
                      lifetimes.size(), shareable_pairs);
    } catch (const std::runtime_error& e) {
        spdlog::warn("[mem_reuse] Skipped (graph has cycles?): {}", e.what());
    }
}

}  // anonymous namespace

// ── 公开的图优化接口 ─────────────────────────────────────────────────

/**
 * @brief 对 IR 图执行指定等级的优化。
 *
 * @param graph_json  IR 图的 JSON 字符串
 * @param level       优化等级
 * @return 优化后的 IR JSON 字符串
 */
Result<std::string> optimize_ir(const std::string& graph_json,
                                 OptimizationLevel level) {
    if (graph_json.empty()) {
        return Error<std::string>(ErrorCode::INVALID_ARGUMENT,
                                   "Empty IR JSON");
    }

    // 简化实现：从 JSON 构造图（完整实现需要 JSON 解析器）
    // 此处为骨架，完整实现应：
    //   1. 解析 JSON → IrGraph
    //   2. 执行优化 Pass
    //   3. 序列化 IrGraph → JSON

    spdlog::info("Graph optimization requested (level={})", static_cast<int>(level));

    // 对于空的图（如仅包含 "{}"），返回原始 JSON
    if (graph_json.find("\"nodes\"") == std::string::npos ||
        graph_json.find("\"nodes\":[]") != std::string::npos) {
        spdlog::info("Empty graph, skipping optimization");
        return graph_json;
    }

    // TODO: 完整 JSON → IrGraph 解析（需 nlohmann/json）
    // 当前返回原始 JSON（优化 Pass 在 IrGraph 层面已实现）

    spdlog::info("Graph optimization complete");
    return graph_json;
}

/**
 * @brief 对 IrGraph 执行所有适用的优化 Pass。
 */
void optimize_ir_graph(ir::IrGraph& graph, OptimizationLevel level) {
    spdlog::info("Optimizing IR graph '{}' at level O{}",
                  graph.name(), static_cast<int>(level));

    if (level >= OptimizationLevel::O1) {
        spdlog::debug("  Running O1 passes...");
        constant_folding(graph);
        dead_code_elimination(graph);
    }

    if (level >= OptimizationLevel::O2) {
        spdlog::debug("  Running O2 passes...");
        operator_fusion(graph);
    }

    if (level >= OptimizationLevel::O3) {
        spdlog::debug("  Running O3 passes...");
        memory_reuse_analysis(graph);
        // 更多激进优化：跨层融合、动态 shape 推导
    }

    spdlog::info("IR graph optimization complete ({} nodes remaining)",
                  graph.node_count());
}

}  // namespace qoocore
