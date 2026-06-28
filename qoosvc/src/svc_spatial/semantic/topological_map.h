#pragma once

#include "qoosvc/spatial/map_types.h"
#include <vector>

namespace qoosvc::spatial {

/**
 * TopologicalMapBuilder — Builds a graph-based topological map from semantic map.
 *
 * Creates nodes at room centers, doorways, and key intersections.
 * Edges represent traversable connections between nodes.
 */
class TopologicalMapBuilder {
public:
    struct Config {
        double doorway_connection_distance = 2.0;  // Max distance to connect doorways
        double min_edge_distance = 0.5;            // Min distance for an edge
    };

    explicit TopologicalMapBuilder(const Config& config);
    ~TopologicalMapBuilder();

    /**
     * Build a topological map from a semantic map.
     */
    TopologicalMap build(const SemanticMap& semantic_map);

    /**
     * Find the shortest path between two nodes (Dijkstra).
     */
    static std::vector<int32_t> find_shortest_path(const TopologicalMap& map,
                                                     int32_t from, int32_t to);

    /**
     * Find the nearest node to a given pose.
     */
    static int32_t find_nearest_node(const TopologicalMap& map, const Pose3D& pose);

private:
    // Create a node for each room center
    TopoNode create_room_node(const RoomAnnotation& room);

    // Create nodes for doorways (openings between rooms)
    std::vector<TopoNode> create_doorway_nodes(const SemanticMap& semantic_map);

    // Connect nodes with edges
    std::vector<TopoEdge> connect_nodes(const std::vector<TopoNode>& nodes,
                                         const OccupancyGrid& grid);

    // Check if a straight-line path between two poses is collision-free
    bool is_path_free(const Pose3D& from, const Pose3D& to,
                      const OccupancyGrid& grid);

    Config config_;
};

} // namespace qoosvc::spatial
