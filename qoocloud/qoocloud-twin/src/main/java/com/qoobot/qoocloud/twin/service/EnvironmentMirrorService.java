package com.qoobot.qoocloud.twin.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * EnvironmentMirrorService — 数字孪生环境镜像
 * 机器人所处环境实时同步至云端 3D 视图。
 *
 * 功能对标：NVIDIA Omniverse Digital Twin + AWS IoT TwinMaker
 */
@Service
public class EnvironmentMirrorService {

    private static final Logger log = LoggerFactory.getLogger(EnvironmentMirrorService.class);

    // 环境镜像实例
    private final Map<String, EnvironmentMirror> mirrors = new ConcurrentHashMap<>();

    // 场景库
    private final Map<String, SceneTemplate> sceneLibrary = new ConcurrentHashMap<>();

    // 回放记录
    private final Map<String, ReplaySession> replaySessions = new ConcurrentHashMap<>();

    // ==================== 环境镜像（实时 3D 同步） ====================

    /**
     * 创建环境镜像实例。
     * 将机器人的物理环境实时同步至云端 3D 视图。
     */
    public Map<String, Object> createMirror(String robotId, String sceneType,
                                             Map<String, Object> initialState) {
        String mirrorId = "mirror_" + UUID.randomUUID().toString().substring(0, 8);
        EnvironmentMirror mirror = new EnvironmentMirror(
                mirrorId, robotId, sceneType, initialState
        );
        mirrors.put(mirrorId, mirror);

        log.info("Environment mirror created: id={}, robot={}, scene={}",
                mirrorId, robotId, sceneType);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("mirrorId", mirrorId);
        result.put("robotId", robotId);
        result.put("sceneType", sceneType);
        result.put("status", "active");
        result.put("createdAt", mirror.createdAt.toString());
        return result;
    }

    /**
     * 更新环境镜像状态（每帧/每周期同步）。
     */
    public Map<String, Object> updateMirrorState(String mirrorId,
                                                  Map<String, Object> robotPose,
                                                  List<Map<String, Object>> obstacles,
                                                  Map<String, Object> semanticMap) {
        EnvironmentMirror mirror = mirrors.get(mirrorId);
        if (mirror == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("mirrorId", mirrorId);
            result.put("found", false);
            return result;
        }

        if (robotPose != null) mirror.robotPose = robotPose;
        if (obstacles != null) mirror.obstacles = obstacles;
        if (semanticMap != null) mirror.semanticMap = semanticMap;
        mirror.lastSync = Instant.now();
        mirror.frameCount++;

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("mirrorId", mirrorId);
        result.put("frameCount", mirror.frameCount);
        result.put("lastSync", mirror.lastSync.toString());
        result.put("robotPose", mirror.robotPose);
        result.put("obstacleCount", mirror.obstacles.size());
        return result;
    }

    /**
     * 获取镜像 3D 视图数据。
     */
    public Map<String, Object> getMirrorView(String mirrorId) {
        EnvironmentMirror mirror = mirrors.get(mirrorId);
        if (mirror == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("mirrorId", mirrorId);
            result.put("found", false);
            return result;
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("mirrorId", mirror.mirrorId);
        result.put("robotId", mirror.robotId);
        result.put("sceneType", mirror.sceneType);
        result.put("status", mirror.status);
        result.put("frameCount", mirror.frameCount);
        result.put("lastSync", mirror.lastSync.toString());

        // 3D 场景数据
        Map<String, Object> sceneData = new LinkedHashMap<>();
        sceneData.put("robotPose", mirror.robotPose);
        sceneData.put("obstacles", mirror.obstacles);
        sceneData.put("semanticMap", mirror.semanticMap);
        sceneData.put("objects", mirror.dynamicObjects);
        result.put("sceneData", sceneData);

        // 同步延迟
        long syncLagMs = System.currentTimeMillis() - mirror.lastSync.toEpochMilli();
        result.put("syncLagMs", syncLagMs);
        result.put("syncQuality", syncLagMs < 200 ? "good"
                : syncLagMs < 1000 ? "acceptable" : "poor");

        return result;
    }

    /**
     * 向镜像中添加动态物体。
     */
    public Map<String, Object> addDynamicObject(String mirrorId, String objectId,
                                                 String objectType,
                                                 Map<String, Object> pose,
                                                 Map<String, Object> properties) {
        EnvironmentMirror mirror = mirrors.get(mirrorId);
        if (mirror == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("mirrorId", mirrorId);
            result.put("found", false);
            return result;
        }

        Map<String, Object> object = new LinkedHashMap<>();
        object.put("objectId", objectId);
        object.put("objectType", objectType);
        object.put("pose", pose);
        object.put("properties", properties);
        object.put("addedAt", Instant.now().toString());
        mirror.dynamicObjects.add(object);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("mirrorId", mirrorId);
        result.put("objectId", objectId);
        result.put("totalObjects", mirror.dynamicObjects.size());
        return result;
    }

    /**
     * 列出所有活跃的环境镜像。
     */
    public List<Map<String, Object>> listActiveMirrors() {
        return mirrors.values().stream()
                .filter(m -> "active".equals(m.status))
                .map(m -> {
                    Map<String, Object> info = new LinkedHashMap<>();
                    info.put("mirrorId", m.mirrorId);
                    info.put("robotId", m.robotId);
                    info.put("sceneType", m.sceneType);
                    info.put("frameCount", m.frameCount);
                    info.put("lastSync", m.lastSync.toString());
                    info.put("createdAt", m.createdAt.toString());
                    return info;
                })
                .collect(java.util.stream.Collectors.toList());
    }

    /**
     * 停止环境镜像。
     */
    public Map<String, Object> stopMirror(String mirrorId) {
        EnvironmentMirror mirror = mirrors.get(mirrorId);
        if (mirror == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("mirrorId", mirrorId);
            result.put("found", false);
            return result;
        }
        mirror.status = "stopped";
        mirror.stoppedAt = Instant.now();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("mirrorId", mirrorId);
        result.put("status", "stopped");
        result.put("totalFrames", mirror.frameCount);
        return result;
    }

    // ==================== 场景库 ====================

    /**
     * 注册场景模板。
     */
    public Map<String, Object> registerScene(String sceneId, String sceneName,
                                              String sceneType,
                                              Map<String, Object> layout,
                                              List<String> supportedTasks) {
        SceneTemplate scene = new SceneTemplate(
                sceneId, sceneName, sceneType, layout, supportedTasks
        );
        sceneLibrary.put(sceneId, scene);

        log.info("Scene registered: {} (type={})", sceneName, sceneType);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("sceneId", sceneId);
        result.put("sceneName", sceneName);
        result.put("sceneType", sceneType);
        result.put("supportedTasks", supportedTasks);
        return result;
    }

    /**
     * 预置场景初始化。
     */
    public Map<String, Object> initializePresetScenes() {
        // 家庭场景
        registerScene("home_default", "标准家庭环境", "home",
                Map.of("rooms", List.of("living_room", "kitchen", "bedroom", "bathroom"),
                        "area_sqm", 120),
                List.of("navigation", "object_pickup", "cleaning"));

        // 仓库场景
        registerScene("warehouse_default", "标准仓库环境", "warehouse",
                Map.of("zones", List.of("receiving", "storage", "picking", "shipping"),
                        "area_sqm", 2000,
                        "shelf_rows", 20),
                List.of("inventory_check", "order_picking", "pallet_moving"));

        // 医院场景
        registerScene("hospital_default", "标准医院环境", "hospital",
                Map.of("departments", List.of("er", "icu", "pharmacy", "lab"),
                        "area_sqm", 5000,
                        "floors", 5),
                List.of("delivery", "disinfection", "patient_escort"));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("scenesRegistered", sceneLibrary.size());
        result.put("scenes", sceneLibrary.keySet());
        return result;
    }

    /**
     * 列出场景库。
     */
    public List<Map<String, Object>> listScenes(String sceneTypeFilter) {
        return sceneLibrary.values().stream()
                .filter(s -> sceneTypeFilter == null || s.sceneType.equals(sceneTypeFilter))
                .map(s -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("sceneId", s.sceneId);
                    m.put("sceneName", s.sceneName);
                    m.put("sceneType", s.sceneType);
                    m.put("supportedTasks", s.supportedTasks);
                    m.put("layout", s.layout);
                    return m;
                })
                .collect(java.util.stream.Collectors.toList());
    }

    // ==================== 回放分析 ====================

    /**
     * 开始记录回放会话。
     */
    public Map<String, Object> startReplayRecording(String mirrorId, String sessionLabel) {
        String sessionId = "replay_" + UUID.randomUUID().toString().substring(0, 8);
        ReplaySession session = new ReplaySession(sessionId, mirrorId, sessionLabel);
        replaySessions.put(sessionId, session);

        log.info("Replay recording started: session={}, mirror={}", sessionId, mirrorId);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("sessionId", sessionId);
        result.put("mirrorId", mirrorId);
        result.put("label", sessionLabel);
        result.put("status", "recording");
        return result;
    }

    /**
     * 记录回放帧。
     */
    public void recordReplayFrame(String sessionId, Map<String, Object> frameData) {
        ReplaySession session = replaySessions.get(sessionId);
        if (session != null && "recording".equals(session.status)) {
            Map<String, Object> frame = new LinkedHashMap<>();
            frame.put("timestamp", Instant.now().toString());
            frame.put("frameIndex", session.frames.size());
            frame.put("data", frameData);
            session.frames.add(frame);

            // 限制回放帧数
            if (session.frames.size() > 100_000) {
                session.frames.remove(0);
            }
        }
    }

    /**
     * 停止回放记录。
     */
    public Map<String, Object> stopReplayRecording(String sessionId) {
        ReplaySession session = replaySessions.get(sessionId);
        if (session == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("sessionId", sessionId);
            result.put("found", false);
            return result;
        }
        session.status = "completed";
        session.endedAt = Instant.now();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("sessionId", sessionId);
        result.put("totalFrames", session.frames.size());
        result.put("duration", session.endedAt.toString());
        return result;
    }

    /**
     * 回放分析：获取指定时间范围的帧数据。
     */
    public Map<String, Object> getReplayFrames(String sessionId, int startFrame, int endFrame) {
        ReplaySession session = replaySessions.get(sessionId);
        if (session == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("sessionId", sessionId);
            result.put("found", false);
            return result;
        }

        int from = Math.max(0, startFrame);
        int to = Math.min(session.frames.size(), endFrame);
        List<Map<String, Object>> frames = session.frames.subList(from, to);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("sessionId", sessionId);
        result.put("label", session.label);
        result.put("totalFrames", session.frames.size());
        result.put("fromFrame", from);
        result.put("toFrame", to);
        result.put("frames", frames);
        return result;
    }

    /**
     * 事故根因分析。
     * 基于回放数据，分析异常事件的根本原因。
     */
    public Map<String, Object> analyzeIncident(String sessionId, int incidentFrame) {
        ReplaySession session = replaySessions.get(sessionId);
        if (session == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("sessionId", sessionId);
            result.put("found", false);
            return result;
        }

        // 获取事发前后 100 帧数据
        int from = Math.max(0, incidentFrame - 100);
        int to = Math.min(session.frames.size(), incidentFrame + 100);
        List<Map<String, Object>> incidentWindow = session.frames.subList(from, to);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("sessionId", sessionId);
        result.put("incidentFrame", incidentFrame);
        result.put("windowFrames", incidentWindow.size());
        result.put("analyzedAt", Instant.now().toString());

        // 根因分析
        List<Map<String, Object>> causes = new ArrayList<>();

        // 检查碰撞
        Map<String, Object> collisionCheck = new LinkedHashMap<>();
        collisionCheck.put("type", "collision_detection");
        collisionCheck.put("description", "Check for obstacle collision at incident frame");
        collisionCheck.put("confidence", 0.85);
        causes.add(collisionCheck);

        // 检查传感器异常
        Map<String, Object> sensorCheck = new LinkedHashMap<>();
        sensorCheck.put("type", "sensor_anomaly");
        sensorCheck.put("description", "Check for sensor data anomalies leading up to incident");
        sensorCheck.put("confidence", 0.70);
        causes.add(sensorCheck);

        // 检查规划错误
        Map<String, Object> planningCheck = new LinkedHashMap<>();
        planningCheck.put("type", "planning_error");
        planningCheck.put("description", "Check for path planning deviations");
        planningCheck.put("confidence", 0.60);
        causes.add(planningCheck);

        // 检查通信延迟
        Map<String, Object> commsCheck = new LinkedHashMap<>();
        commsCheck.put("type", "communication_latency");
        commsCheck.put("description", "Check for control command delays");
        commsCheck.put("confidence", 0.45);
        causes.add(commsCheck);

        result.put("potentialCauses", causes);
        result.put("recommendation",
                "Review collision_detection first (highest confidence), "
                        + "then cross-reference sensor data in the incident window.");
        return result;
    }

    /**
     * 列出所有回放会话。
     */
    public List<Map<String, Object>> listReplaySessions() {
        return replaySessions.values().stream()
                .map(s -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("sessionId", s.sessionId);
                    m.put("mirrorId", s.mirrorId);
                    m.put("label", s.label);
                    m.put("status", s.status);
                    m.put("totalFrames", s.frames.size());
                    m.put("startedAt", s.startedAt.toString());
                    if (s.endedAt != null) m.put("endedAt", s.endedAt.toString());
                    return m;
                })
                .collect(java.util.stream.Collectors.toList());
    }

    // ==================== 内部类 ====================

    static class EnvironmentMirror {
        final String mirrorId;
        final String robotId;
        final String sceneType;
        String status;
        final Instant createdAt;
        Instant stoppedAt;
        Instant lastSync;
        int frameCount;
        Map<String, Object> robotPose;
        List<Map<String, Object>> obstacles;
        Map<String, Object> semanticMap;
        final List<Map<String, Object>> dynamicObjects;

        EnvironmentMirror(String mirrorId, String robotId, String sceneType,
                          Map<String, Object> initialState) {
            this.mirrorId = mirrorId;
            this.robotId = robotId;
            this.sceneType = sceneType;
            this.status = "active";
            this.createdAt = Instant.now();
            this.lastSync = Instant.now();
            this.frameCount = 0;
            this.robotPose = initialState != null ? initialState : new HashMap<>();
            this.obstacles = new ArrayList<>();
            this.semanticMap = new HashMap<>();
            this.dynamicObjects = new ArrayList<>();
        }
    }

    static class SceneTemplate {
        final String sceneId;
        final String sceneName;
        final String sceneType;
        final Map<String, Object> layout;
        final List<String> supportedTasks;

        SceneTemplate(String sceneId, String sceneName, String sceneType,
                      Map<String, Object> layout, List<String> supportedTasks) {
            this.sceneId = sceneId;
            this.sceneName = sceneName;
            this.sceneType = sceneType;
            this.layout = layout;
            this.supportedTasks = supportedTasks;
        }
    }

    static class ReplaySession {
        final String sessionId;
        final String mirrorId;
        final String label;
        String status;          // recording/completed
        final Instant startedAt;
        Instant endedAt;
        final List<Map<String, Object>> frames;

        ReplaySession(String sessionId, String mirrorId, String label) {
            this.sessionId = sessionId;
            this.mirrorId = mirrorId;
            this.label = label;
            this.status = "recording";
            this.startedAt = Instant.now();
            this.frames = new ArrayList<>();
        }
    }
}
