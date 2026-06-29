/**
 * @file visualization_panel.cpp
 * @brief 可视化面板实现
 * @copyright QooBot Project
 * @version 0.1.0
 */
#include "qoocore/profiler/visualization_panel.h"
#include <sstream>
#include <iomanip>
#include <cmath>

namespace qoocore {
namespace profiler {

namespace {
std::string escape_json(const std::string& s) {
    std::string out;
    for (char c : s) {
        switch (c) {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            default: out += c;
        }
    }
    return out;
}
} // anonymous

VisualizationPanel::VisualizationPanel(const VisualizationConfig& config)
    : config_(config) {}

void VisualizationPanel::build_graph(
    const std::vector<NodeInfo>& nodes,
    const std::vector<EdgeInfo>& edges)
{
    nodes_ = nodes;
    edges_ = edges;
}

std::string VisualizationPanel::export_graph_json() const {
    std::ostringstream ss;
    ss << "{\n  \"nodes\": [\n";

    for (std::size_t i = 0; i < nodes_.size(); ++i) {
        const auto& n = nodes_[i];
        ss << "    {\"id\":\"" << escape_json(n.name)
           << "\",\"type\":\"" << escape_json(n.op_type)
           << "\",\"latency_us\":" << n.latency_us
           << ",\"memory_bytes\":" << n.memory_bytes
           << ",\"x\":" << n.x << ",\"y\":" << n.y
           << ",\"width\":" << n.width << ",\"height\":" << n.height
           << "}";
        if (i < nodes_.size() - 1) ss << ",";
        ss << "\n";
    }

    ss << "  ],\n  \"edges\": [\n";
    for (std::size_t i = 0; i < edges_.size(); ++i) {
        const auto& e = edges_[i];
        ss << "    {\"from\":\"" << escape_json(e.from)
           << "\",\"to\":\"" << escape_json(e.to)
           << "\",\"tensor_size\":" << e.tensor_size << "}";
        if (i < edges_.size() - 1) ss << ",";
        ss << "\n";
    }

    ss << "  ]\n}";
    return ss.str();
}

std::string VisualizationPanel::export_graph_dot() const {
    std::ostringstream ss;
    ss << "digraph qoocore_model {\n";
    ss << "  rankdir=TB;\n";
    ss << "  node [shape=box, style=filled, fillcolor=lightblue];\n\n";

    for (const auto& n : nodes_) {
        ss << "  \"" << n.name << "\" [label=\""
           << n.name << "\\n" << n.op_type
           << "\\n" << std::fixed << std::setprecision(1)
           << n.latency_us << "us\"];\n";
    }

    ss << "\n";
    for (const auto& e : edges_) {
        ss << "  \"" << e.from << "\" -> \"" << e.to
           << "\" [label=\"" << (e.tensor_size / 1024) << "KB\"];\n";
    }

    ss << "}\n";
    return ss.str();
}

void VisualizationPanel::build_memory_heatmap(
    const std::vector<MemoryHeatmapCell>& cells)
{
    heatmap_ = cells;
}

std::string VisualizationPanel::export_heatmap_json() const {
    std::ostringstream ss;
    ss << "{\n  \"cells\": [\n";

    for (std::size_t i = 0; i < heatmap_.size(); ++i) {
        const auto& c = heatmap_[i];
        ss << "    {\"row\":" << c.row
           << ",\"col\":" << c.col
           << ",\"utilization\":" << c.utilization
           << ",\"label\":\"" << escape_json(c.label) << "\"}";
        if (i < heatmap_.size() - 1) ss << ",";
        ss << "\n";
    }

    ss << "  ]\n}";
    return ss.str();
}

void VisualizationPanel::build_pipeline_timeline(
    const std::vector<PipelineStage>& stages)
{
    pipeline_ = stages;
}

std::string VisualizationPanel::export_timeline_json() const {
    std::ostringstream ss;
    ss << "{\n  \"stages\": [\n";

    for (std::size_t i = 0; i < pipeline_.size(); ++i) {
        const auto& s = pipeline_[i];
        ss << "    {\"name\":\"" << escape_json(s.name)
           << "\",\"start_us\":" << s.start_us
           << ",\"end_us\":" << s.end_us
           << ",\"duration_us\":" << (s.end_us - s.start_us)
           << ",\"color\":\"" << escape_json(s.color) << "\"}";
        if (i < pipeline_.size() - 1) ss << ",";
        ss << "\n";
    }

    ss << "  ]\n}";
    return ss.str();
}

std::string VisualizationPanel::export_chrome_trace() const {
    std::ostringstream ss;
    ss << "{\n  \"traceEvents\": [\n";

    for (std::size_t i = 0; i < pipeline_.size(); ++i) {
        const auto& s = pipeline_[i];
        ss << "    {\"ph\":\"X\",\"name\":\"" << escape_json(s.name)
           << "\",\"ts\":" << s.start_us
           << ",\"dur\":" << (s.end_us - s.start_us)
           << ",\"pid\":1,\"tid\":1,\"cat\":\"inference\""
           << ",\"cname\":\"" << escape_json(s.color) << "\"}";
        if (i < pipeline_.size() - 1) ss << ",";
        ss << "\n";
    }

    ss << "  ]\n}";
    return ss.str();
}

} // namespace profiler
} // namespace qoocore
