/**
 * @file visualization_panel.h
 * @brief 可视化面板 — 模型图可视化、内存占用热力图、流水线时间轴
 * @copyright QooBot Project
 * @version 0.1.0
 */
#pragma once
#include "qoocore/core.h"
#include <cstdint>
#include <string>
#include <vector>
#include <functional>

namespace qoocore {
namespace profiler {

struct NodeInfo {
    std::string name;
    std::string op_type;
    std::vector<std::string> inputs;
    std::vector<std::string> outputs;
    float latency_us{0.0f};
    std::size_t memory_bytes{0};
    std::size_t flops{0};
    int x{0}, y{0}, width{100}, height{40};  ///< 布局坐标
};

struct EdgeInfo {
    std::string from;
    std::string to;
    std::size_t tensor_size{0};
};

struct MemoryHeatmapCell {
    int row{0}, col{0};
    float utilization{0.0f};   ///< 0.0~1.0
    std::string label;
};

struct PipelineStage {
    std::string name;
    double start_us{0.0};
    double end_us{0.0};
    std::string color;
};

struct VisualizationConfig {
    bool show_latency{true};
    bool show_memory{true};
    bool show_flops{true};
    std::uint32_t max_nodes_display{500};
};

class VisualizationPanel {
public:
    explicit VisualizationPanel(const VisualizationConfig& config);
    ~VisualizationPanel() = default;

    // 模型图可视化
    void build_graph(const std::vector<NodeInfo>& nodes,
                     const std::vector<EdgeInfo>& edges);
    std::string export_graph_json() const;
    std::string export_graph_dot() const;

    // 内存热力图
    void build_memory_heatmap(const std::vector<MemoryHeatmapCell>& cells);
    std::string export_heatmap_json() const;

    // 流水线时间轴
    void build_pipeline_timeline(const std::vector<PipelineStage>& stages);
    std::string export_timeline_json() const;
    std::string export_chrome_trace() const;

    VisualizationConfig config() const { return config_; }

private:
    VisualizationConfig config_;
    std::vector<NodeInfo> nodes_;
    std::vector<EdgeInfo> edges_;
    std::vector<MemoryHeatmapCell> heatmap_;
    std::vector<PipelineStage> pipeline_;
};

} // namespace profiler
} // namespace qoocore
