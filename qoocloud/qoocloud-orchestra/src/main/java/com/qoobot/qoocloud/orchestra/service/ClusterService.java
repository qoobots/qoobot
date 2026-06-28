package com.qoobot.qoocloud.orchestra.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * ClusterService — 集群管理服务
 * 多机器人发现、注册、编组、拓扑管理
 */
@Service
public class ClusterService {

    private final Map<String, Cluster> clusters = new ConcurrentHashMap<>();
    private final Map<String, ClusterRobot> robotAssignments = new ConcurrentHashMap<>();

    /**
     * Create a new robot cluster.
     */
    public Cluster createCluster(String name, String description, String ownerId) {
        String clusterId = "cluster_" + UUID.randomUUID().toString().substring(0, 8);
        Cluster cluster = new Cluster();
        cluster.clusterId = clusterId;
        cluster.name = name;
        cluster.description = description;
        cluster.ownerId = ownerId;
        cluster.status = "active";
        cluster.createdAt = Instant.now();
        clusters.put(clusterId, cluster);
        return cluster;
    }

    /**
     * Register a robot to a cluster.
     */
    public void registerRobot(String clusterId, String deviceId, String role) {
        Cluster cluster = clusters.get(clusterId);
        if (cluster == null) return;

        ClusterRobot robot = new ClusterRobot();
        robot.clusterId = clusterId;
        robot.deviceId = deviceId;
        robot.role = role;
        robot.joinedAt = Instant.now();
        robot.status = "online";

        robotAssignments.put(deviceId, robot);
        cluster.robotCount++;
    }

    /**
     * List all clusters.
     */
    public List<Cluster> listClusters() {
        return new ArrayList<>(clusters.values());
    }

    /**
     * Get robots in a cluster.
     */
    public List<ClusterRobot> getClusterRobots(String clusterId) {
        return robotAssignments.values().stream()
                .filter(r -> r.clusterId.equals(clusterId))
                .toList();
    }

    /**
     * Get cluster topology.
     */
    public Map<String, Object> getTopology(String clusterId) {
        Cluster cluster = clusters.get(clusterId);
        if (cluster == null) return Map.of("status", "not_found");

        Map<String, Object> topology = new HashMap<>();
        topology.put("clusterId", clusterId);
        topology.put("name", cluster.name);
        topology.put("robotCount", cluster.robotCount);
        topology.put("robots", getClusterRobots(clusterId));
        return topology;
    }

    // Inner types

    public static class Cluster {
        public String clusterId;
        public String name;
        public String description;
        public String ownerId;
        public String status;
        public int robotCount;
        public Instant createdAt;
    }

    public static class ClusterRobot {
        public String clusterId;
        public String deviceId;
        public String role;
        public String status;
        public Instant joinedAt;
    }
}
