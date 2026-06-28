package com.qoobot.qoocloud.teleop.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 控制指令低延迟转发服务
 *
 * 操作员端 → qoocloud-teleop → 机器人端 控制指令中继
 * 提供指令校验、速率限制、序列号管理、延迟统计
 */
@Service
public class ControlRelayService {

    private static final Logger log = LoggerFactory.getLogger(ControlRelayService.class);

    private final SessionService sessionService;

    // 每个会话的指令序列号
    private final Map<String, Long> sequenceNumbers = new ConcurrentHashMap<>();

    // 速率限制：每个会话的最近指令时间戳
    private final Map<String, Deque<Long>> rateLimitWindows = new ConcurrentHashMap<>();
    private static final int RATE_LIMIT_PER_SECOND = 100;
    private static final long RATE_WINDOW_MS = 1000;

    // 指令范围校验
    private static final double MAX_BASE_SPEED = 2.0;      // m/s
    private static final double MAX_BASE_OMEGA = 3.14;     // rad/s
    private static final double MAX_JOINT_VELOCITY = 10.0; // rad/s
    private static final double MAX_JOINT_TORQUE = 100.0;  // Nm

    public ControlRelayService(SessionService sessionService) {
        this.sessionService = sessionService;
    }

    /**
     * 中继控制指令（核心方法）
     *
     * @param sessionId 会话ID
     * @param commandType 指令类型: fullbody/joint/gripper/head/estop/mode_switch/heartbeat
     * @param commandData 指令数据 (JSON)
     * @param clientTimestamp 客户端时间戳
     * @return 校验后的指令数据，包含序列号和延迟
     */
    public Map<String, Object> relayCommand(String sessionId, String commandType,
                                             Map<String, Object> commandData,
                                             long clientTimestamp) {
        long relayedAt = Instant.now().toEpochMilli();

        // 1. 速率限制检查
        if (!checkRateLimit(sessionId)) {
            throw new IllegalStateException("Rate limit exceeded for session: " + sessionId);
        }

        // 2. 范围校验
        List<String> violations = validateCommand(commandType, commandData);
        if (!violations.isEmpty()) {
            log.warn("Command validation failed: {} session={} violations={}",
                commandType, sessionId, violations);
            throw new IllegalArgumentException("Command validation failed: " + violations);
        }

        // 3. 分配序列号
        long sequence = sequenceNumbers.merge(sessionId, 1L, Long::sum);

        // 4. 更新延迟统计
        int latencyMs = (int) (relayedAt - clientTimestamp);
        sessionService.updateLatency(sessionId, latencyMs);

        // 5. 构建中继后的指令
        Map<String, Object> relayed = new LinkedHashMap<>();
        relayed.put("sessionId", sessionId);
        relayed.put("sequence", sequence);
        relayed.put("commandType", commandType);
        relayed.put("commandData", commandData);
        relayed.put("sentAt", clientTimestamp);
        relayed.put("relayedAt", relayedAt);
        relayed.put("latencyMs", latencyMs);

        log.debug("Command relayed: {} seq={} type={} latency={}ms",
            sessionId, sequence, commandType, latencyMs);

        return relayed;
    }

    /**
     * 速率限制检查（滑动窗口）
     */
    private boolean checkRateLimit(String sessionId) {
        Deque<Long> window = rateLimitWindows.computeIfAbsent(sessionId,
            k -> new ArrayDeque<>());
        long now = System.currentTimeMillis();
        long windowStart = now - RATE_WINDOW_MS;

        // 清除过期时间戳
        while (!window.isEmpty() && window.peekFirst() < windowStart) {
            window.pollFirst();
        }

        if (window.size() >= RATE_LIMIT_PER_SECOND) {
            return false;
        }

        window.addLast(now);
        return true;
    }

    /**
     * 指令范围校验
     */
    private List<String> validateCommand(String commandType, Map<String, Object> data) {
        List<String> violations = new ArrayList<>();

        switch (commandType) {
            case "fullbody":
                validateFullbody(data, violations);
                break;
            case "joint":
                validateJoint(data, violations);
                break;
            case "gripper":
                validateGripper(data, violations);
                break;
            case "head":
                validateHead(data, violations);
                break;
            case "estop":
            case "mode_switch":
            case "heartbeat":
                // 这些指令不需要范围校验
                break;
            default:
                violations.add("Unknown command type: " + commandType);
        }

        return violations;
    }

    @SuppressWarnings("unchecked")
    private void validateFullbody(Map<String, Object> data, List<String> violations) {
        Map<String, Object> base = (Map<String, Object>) data.get("base");
        if (base != null) {
            double vx = toDouble(base.get("vx"));
            double vy = toDouble(base.get("vy"));
            double omega = toDouble(base.get("omega"));
            if (Math.abs(vx) > MAX_BASE_SPEED)
                violations.add("Base vx exceeds limit: " + vx);
            if (Math.abs(vy) > MAX_BASE_SPEED)
                violations.add("Base vy exceeds limit: " + vy);
            if (Math.abs(omega) > MAX_BASE_OMEGA)
                violations.add("Base omega exceeds limit: " + omega);
        }
        List<Map<String, Object>> joints = (List<Map<String, Object>>) data.get("joints");
        if (joints != null) {
            for (Map<String, Object> joint : joints) {
                double vel = toDouble(joint.get("velocity"));
                double torque = toDouble(joint.get("torque_ff"));
                if (Math.abs(vel) > MAX_JOINT_VELOCITY)
                    violations.add("Joint velocity exceeds limit: " + vel);
                if (Math.abs(torque) > MAX_JOINT_TORQUE)
                    violations.add("Joint torque exceeds limit: " + torque);
            }
        }
        double speedOverride = toDouble(data.get("speed_override"));
        if (speedOverride < 0 || speedOverride > 1.0) {
            violations.add("Speed override out of range: " + speedOverride);
        }
    }

    private void validateJoint(Map<String, Object> data, List<String> violations) {
        double vel = toDouble(getNested(data, "setpoint", "velocity"));
        double torque = toDouble(getNested(data, "setpoint", "torque_ff"));
        if (Math.abs(vel) > MAX_JOINT_VELOCITY)
            violations.add("Joint velocity exceeds limit: " + vel);
        if (Math.abs(torque) > MAX_JOINT_TORQUE)
            violations.add("Joint torque exceeds limit: " + torque);
    }

    private void validateGripper(Map<String, Object> data, List<String> violations) {
        double force = toDouble(getNested(data, "setpoint", "grasp_force"));
        if (force < 0 || force > 200.0)
            violations.add("Gripper force out of range: " + force);
    }

    private void validateHead(Map<String, Object> data, List<String> violations) {
        Map<String, Object> setpoint = (Map<String, Object>) data.get("setpoint");
        if (setpoint != null) {
            double pitch = toDouble(setpoint.get("pitch"));
            double yaw = toDouble(setpoint.get("yaw"));
            if (Math.abs(pitch) > Math.PI / 2)
                violations.add("Head pitch exceeds limit: " + pitch);
            if (Math.abs(yaw) > Math.PI)
                violations.add("Head yaw exceeds limit: " + yaw);
        }
    }

    private double toDouble(Object value) {
        if (value instanceof Number n) return n.doubleValue();
        return 0.0;
    }

    @SuppressWarnings("unchecked")
    private Object getNested(Map<String, Object> data, String... keys) {
        Object current = data;
        for (String key : keys) {
            if (current instanceof Map) {
                current = ((Map<String, Object>) current).get(key);
            } else {
                return null;
            }
        }
        return current;
    }

    /**
     * 获取当前序列号
     */
    public long getCurrentSequence(String sessionId) {
        return sequenceNumbers.getOrDefault(sessionId, 0L);
    }

    /**
     * 重置会话序列号
     */
    public void resetSequence(String sessionId) {
        sequenceNumbers.remove(sessionId);
        rateLimitWindows.remove(sessionId);
    }
}
