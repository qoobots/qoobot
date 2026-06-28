#include "topological_map.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <queue>
#include <unordered_map>

namespace qoosvc::spatial {

TopologicalMapBuilder::TopologicalMapBuilder(const Config& config)
    : config_(config) {
}

TopologicalMapBuilder::~TopologicalMapBuilder() = default;

TopologicalMap TopologicalMapBuilder::build(const SemanticMap& semantic_map) {
    TopologicalMap topo_map;
    topo_map.metadata.map_id = semantic_map.grid.metadata.map_id + "_topo";
    topo_map.metadata.type = MapType::TOPOLOGICAL;

    // Create nodes for each room
    int32_t node_id = 0;
    for (const auto& room : semantic_map.rooms) {
        auto node = create_room_node(room);
        node.node_id = node_id++;
        node.tags.push_back("room:" + RoomClassifier::room_type_name(room.type));
        topo_map.nodes.push_back(std::move(node));
    }

    // Create nodes for doorways between rooms
    auto doorway_nodes = create_doorway_nodes(semantic_map);
    for (auto& node : doorway_nodes) {
        node.node_id = node_id++;
        node.tags.push_back("doorway");
        topo_map.nodes.push_back(std::move(node));
    }

    // Connect nodes with edges
    topo_map.edges = connect_nodes(topo_map.nodes, semantic_map.grid);

    return topo_map;
}

TopoNode TopologicalMapBuilder::create_room_node(const RoomAnnotation& room) {
    TopoNode node;

    // Place node at room centroid
    double cx = 0, cy = 0;
    for (const auto& pt : room.boundary) {
        cx += pt.x;
        cy += pt.y;
    }
    if (!room.boundary.empty()) {
        cx /= room.boundary.size();
        cy /= room.boundary.size();
    }

    node.pose = {cx, cy, 0, 0, 0, 0, "map"};
    node.label = RoomClassifier::room_type_name(room.type) + "_" +
                 std::to_string(room.room_id);

    return node;
}

std::vector<TopoNode> TopologicalMapBuilder::create_doorway_nodes(
    const SemanticMap& semantic_map) {

    std::vector<TopoNode> doorway_nodes;

    // Find narrow passages between rooms (potential doorways)
    // Analyze shared boundaries between adjacent rooms
    for (size_t i = 0; i < semantic_map.rooms.size(); ++i) {
        for (size_t j = i + 1; j < semantic_map.rooms.size(); ++j) {
            const auto& room_a = semantic_map.rooms[i];
            const auto& room_b = semantic_map.rooms[j];

            // Find closest pair of boundary points
            double min_dist = std::numeric_limits<double>::max();
            Point3D closest_a, closest_b;

            for (const auto& pa : room_a.boundary) {
                for (const auto& pb : room_b.boundary) {
                    double dist = pa.distance_to(pb);
                    if (dist < min_dist) {
                        min_dist = dist;
                        closest_a = pa;
                        closest_b = pb;
                    }
                }
            }

            // If rooms are close enough, create a doorway node between them
            if (min_dist < config_.doorway_connection_distance) {
                TopoNode node;
                node.pose = {
                    (closest_a.x + closest_b.x) / 2.0,
                    (closest_a.y + closest_b.y) / 2.0,
                    0, 0, 0, 0, "map"
                };
                node.label = "doorway_" + std::to_string(i) + "_" + std::to_string(j);
                node.tags = {"doorway", "connection",
                             RoomClassifier::room_type_name(room_a.type),
                             RoomClassifier::room_type_name(room_b.type)};
                doorway_nodes.push_back(node);
            }
        }
    }

    return doorway_nodes;
}

std::vector<TopoEdge> TopologicalMapBuilder::connect_nodes(
    const std::vector<TopoNode>& nodes,
    const OccupancyGrid& grid) {

    std::vector<TopoEdge> edges;

    for (size_t i = 0; i < nodes.size(); ++i) {
        for (size_t j = i + 1; j < nodes.size(); ++j) {
            double dist = nodes[i].pose.distance_to(nodes[j].pose);

            if (dist < config_.min_edge_distance) continue;

            // Check if path between nodes is free
            bool free = is_path_free(nodes[i].pose, nodes[j].pose, grid);

            // Determine traversability
            double traversability = free ? 1.0 : 0.3;

            TopoEdge edge;
            edge.from_node_id = nodes[i].node_id;
            edge.to_node_id = nodes[j].node_id;
            edge.distance = dist;
            edge.traversability = traversability;

            // Classify passage type
            if (dist > 10.0) {
                edge.passage_type = "corridor";
            } else if (dist > 3.0) {
                edge.passage_type = "open";
            } else {
                edge.passage_type = "door";
            }

            // Only add edges that are reasonably traversable
            if (traversability > 0.2 || dist < 5.0) {
                edges.push_back(edge);

                // Add reverse edge for undirected graph
                TopoEdge reverse = edge;
                std::swap(reverse.from_node_id, reverse.to_node_id);
                edges.push_back(reverse);
            }
        }
    }

    return edges;
}

bool TopologicalMapBuilder::is_path_free(const Pose3D& from, const Pose3D& to,
                                          const OccupancyGrid& grid) {
    // Sample along the line and check occupancy
    double dist = from.distance_to(to);
    int samples = std::max(2, static_cast<int>(dist / grid.resolution));

    for (int i = 0; i <= samples; ++i) {
        double t = static_cast<double>(i) / samples;
        double x = from.x + (to.x - from.x) * t;
        double y = from.y + (to.y - from.y) * t;

        auto gp = grid.world_to_grid({x, y, 0});
        if (grid.is_in_bounds(gp.x, gp.y) && grid.is_occupied(gp.x, gp.y)) {
            return false;
        }
    }

    return true;
}

// ============================================================================
// Static Methods
// ============================================================================

std::vector<int32_t> TopologicalMapBuilder::find_shortest_path(
    const TopologicalMap& map, int32_t from, int32_t to) {

    if (from == to) return {from};

    // Build adjacency list
    std::unordered_map<int32_t, std::vector<std::pair<int32_t, double>>> adj;
    for (const auto& edge : map.edges) {
        if (edge.traversability > 0.1) {
            double cost = edge.distance / edge.traversability;
            adj[edge.from_node_id].push_back({edge.to_node_id, cost});
        }
    }

    // Dijkstra
    std::unordered_map<int32_t, double> dist;
    std::unordered_map<int32_t, int32_t> prev;
    using PQElement = std::pair<double, int32_t>;
    std::priority_queue<PQElement, std::vector<PQElement>, std::greater<PQElement>> pq;

    for (const auto& node : map.nodes) {
        dist[node.node_id] = std::numeric_limits<double>::max();
    }
    dist[from] = 0;
    pq.push({0, from});

    while (!pq.empty()) {
        auto [d, u] = pq.top();
        pq.pop();

        if (d > dist[u]) continue;
        if (u == to) break;

        for (const auto& [v, w] : adj[u]) {
            double nd = d + w;
            if (nd < dist[v]) {
                dist[v] = nd;
                prev[v] = u;
                pq.push({nd, v});
            }
        }
    }

    // Reconstruct path
    std::vector<int32_t> path;
    if (dist[to] == std::numeric_limits<double>::max()) {
        return path;  // No path found
    }

    for (int32_t at = to; at != from; at = prev[at]) {
        path.push_back(at);
    }
    path.push_back(from);
    std::reverse(path.begin(), path.end());

    return path;
}

int32_t TopologicalMapBuilder::find_nearest_node(const TopologicalMap& map,
                                                   const Pose3D& pose) {
    int32_t nearest = -1;
    double min_dist = std::numeric_limits<double>::max();

    for (const auto& node : map.nodes) {
        double dist = pose.distance_to(node.pose);
        if (dist < min_dist) {
            min_dist = dist;
            nearest = node.node_id;
        }
    }

    return nearest;
}

} // namespace qoosvc::spatial
