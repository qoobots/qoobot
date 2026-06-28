package com.qoobot.qoocloud.teleop.service;

import com.qoobot.qoocloud.teleop.entity.TeleopSession;
import com.qoobot.qoocloud.teleop.entity.TeleopSession.*;
import com.qoobot.qoocloud.teleop.repository.TeleopSessionRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 遥控会话生命周期管理
 *
 * 管理会话的完整生命周期：创建 → 连接 → 接管 → 遥控 → 交还 → 关闭
 * 使用 Redis 存储活跃会话状态，PostgreSQL 持久化历史记录
 */
@Service
public class SessionService {

    private static final Logger log = LoggerFactory.getLogger(SessionService.class);

    private final TeleopSessionRepository sessionRepo;
    private final RedisTemplate<String, Object> redisTemplate;

    // 内存中的活跃会话缓存
    private final Map<String, TeleopSession> activeSessions = new ConcurrentHashMap<>();

    // 配置常量
    private static final String REDIS_KEY_SESSION = "teleop:session:%s";
    private static final String REDIS_KEY_ROBOT_SESSION = "teleop:robot:%s:session";
    private static final String REDIS_KEY_OPERATOR_SESSION = "teleop:operator:%s:session";
    private static final long HEARTBEAT_TIMEOUT_MS = 3000;
    private static final long MAX_IDLE_MS = 600_000;     // 10分钟
    private static final long MAX_DURATION_MS = 14_400_000; // 4小时

    public SessionService(TeleopSessionRepository sessionRepo,
                          RedisTemplate<String, Object> redisTemplate) {
        this.sessionRepo = sessionRepo;
        this.redisTemplate = redisTemplate;
    }

    /**
     * 创建遥控会话
     */
    public TeleopSession createSession(String robotId, String operatorId,
                                        String operatorName, ControlMode requestedMode,
                                        List<String> mediaTypes, Map<String, String> metadata) {
        // 检查机器人是否已有活跃会话
        Optional<TeleopSession> existingRobot = sessionRepo.findActiveByRobotId(robotId);
        if (existingRobot.isPresent()) {
            throw new IllegalStateException(
                "Robot " + robotId + " already in session: " + existingRobot.get().getSessionId());
        }

        // 检查操作员是否已有活跃会话
        Optional<TeleopSession> existingOperator = sessionRepo.findActiveByOperatorId(operatorId);
        if (existingOperator.isPresent()) {
            throw new IllegalStateException(
                "Operator " + operatorId + " already in session: " + existingOperator.get().getSessionId());
        }

        TeleopSession session = new TeleopSession();
        session.setRobotId(robotId);
        session.setOperatorId(operatorId);
        session.setOperatorName(operatorName);
        session.setControlMode(requestedMode);
        session.setSessionStatus(SessionStatus.INITIATING);
        session.setMediaTypes(toJson(mediaTypes));
        session.setCreatedAt(Instant.now());
        session.setLastHeartbeat(Instant.now());

        // 持久化
        session = sessionRepo.save(session);

        // 缓存
        activeSessions.put(session.getSessionId(), session);
        redisTemplate.opsForValue().set(
            String.format(REDIS_KEY_SESSION, session.getSessionId()), session,
            Duration.ofMillis(MAX_DURATION_MS));
        redisTemplate.opsForValue().set(
            String.format(REDIS_KEY_ROBOT_SESSION, robotId), session.getSessionId());
        redisTemplate.opsForValue().set(
            String.format(REDIS_KEY_OPERATOR_SESSION, operatorId), session.getSessionId());

        log.info("Session created: {} robot={} operator={} mode={}",
            session.getSessionId(), robotId, operatorId, requestedMode);
        return session;
    }

    /**
     * 更新 WebRTC 连接状态
     */
    public TeleopSession updateWebRTC(String sessionId, String sdpOffer, String sdpAnswer,
                                       String iceCandidates) {
        TeleopSession session = getSession(sessionId);
        if (sdpOffer != null) session.setSdpOffer(sdpOffer);
        if (sdpAnswer != null) session.setSdpAnswer(sdpAnswer);
        if (iceCandidates != null) session.setIceCandidates(iceCandidates);

        if (session.getSessionStatus() == SessionStatus.INITIATING && sdpAnswer != null) {
            session.setSessionStatus(SessionStatus.CONNECTING);
        }
        if (session.getConnectedAt() == null && sdpAnswer != null) {
            session.setConnectedAt(Instant.now());
            session.setSessionStatus(SessionStatus.ACTIVE);
            log.info("WebRTC connected: {}", sessionId);
        }

        session = sessionRepo.save(session);
        activeSessions.put(sessionId, session);
        return session;
    }

    /**
     * 请求接管控制权 (AUTO/HYBRID → TELEOP)
     */
    public TeleopSession requestTakeover(String sessionId) {
        TeleopSession session = getSession(sessionId);
        if (session.getSessionStatus() != SessionStatus.ACTIVE) {
            throw new IllegalStateException("Session not active: " + sessionId);
        }
        session.setControlMode(ControlMode.TELEOP);
        session.setTakeoverAt(Instant.now());
        session = sessionRepo.save(session);
        activeSessions.put(sessionId, session);
        log.info("Takeover granted: {} robot={}", sessionId, session.getRobotId());
        return session;
    }

    /**
     * 交还控制权 (TELEOP → AUTO)
     */
    public TeleopSession handover(String sessionId) {
        TeleopSession session = getSession(sessionId);
        session.setControlMode(ControlMode.AUTO);
        session.setHandoverAt(Instant.now());
        session = sessionRepo.save(session);
        activeSessions.put(sessionId, session);
        log.info("Handover completed: {}", sessionId);
        return session;
    }

    /**
     * 更新心跳
     */
    public TeleopSession heartbeat(String sessionId) {
        TeleopSession session = getSession(sessionId);
        session.setLastHeartbeat(Instant.now());
        activeSessions.put(sessionId, session);
        // 仅更新 Redis 缓存
        redisTemplate.opsForValue().set(
            String.format(REDIS_KEY_SESSION, sessionId), session,
            Duration.ofMillis(MAX_DURATION_MS));
        return session;
    }

    /**
     * 更新延迟统计
     */
    public void updateLatency(String sessionId, int latencyMs) {
        TeleopSession session = activeSessions.get(sessionId);
        if (session != null) {
            if (latencyMs > session.getMaxLatencyMs()) {
                session.setMaxLatencyMs(latencyMs);
            }
            // 指数移动平均
            int newAvg = (int) (session.getAvgLatencyMs() * 0.9 + latencyMs * 0.1);
            session.setAvgLatencyMs(newAvg);
            session.setCommandCount(session.getCommandCount() + 1);
        }
    }

    /**
     * 更新流量统计
     */
    public void updateBytesSent(String sessionId, long videoBytes, long audioBytes) {
        TeleopSession session = activeSessions.get(sessionId);
        if (session != null) {
            if (videoBytes > 0) session.setVideoBytesSent(session.getVideoBytesSent() + videoBytes);
            if (audioBytes > 0) session.setAudioBytesSent(session.getAudioBytesSent() + audioBytes);
        }
    }

    /**
     * 关闭会话
     */
    public TeleopSession closeSession(String sessionId, String reason) {
        TeleopSession session = getSession(sessionId);
        session.setSessionStatus(SessionStatus.CLOSED);
        session.setClosedAt(Instant.now());
        session = sessionRepo.save(session);

        // 清理缓存
        activeSessions.remove(sessionId);
        redisTemplate.delete(String.format(REDIS_KEY_SESSION, sessionId));
        redisTemplate.delete(String.format(REDIS_KEY_ROBOT_SESSION, session.getRobotId()));
        redisTemplate.delete(String.format(REDIS_KEY_OPERATOR_SESSION, session.getOperatorId()));

        log.info("Session closed: {} reason={}", sessionId, reason);
        return session;
    }

    /**
     * 获取会话
     */
    public TeleopSession getSession(String sessionId) {
        TeleopSession session = activeSessions.get(sessionId);
        if (session == null) {
            session = sessionRepo.findById(sessionId)
                .orElseThrow(() -> new NoSuchElementException("Session not found: " + sessionId));
            if (session.getSessionStatus() != SessionStatus.CLOSED
                && session.getSessionStatus() != SessionStatus.TIMEOUT) {
                activeSessions.put(sessionId, session);
            }
        }
        return session;
    }

    /**
     * 定时任务：检测超时会话
     */
    public List<TeleopSession> checkTimeouts() {
        Instant timeout = Instant.now().minusMillis(HEARTBEAT_TIMEOUT_MS);
        List<TeleopSession> timedOut = sessionRepo.findTimedOutSessions(timeout);
        for (TeleopSession s : timedOut) {
            s.setSessionStatus(SessionStatus.TIMEOUT);
            s.setClosedAt(Instant.now());
            sessionRepo.save(s);
            activeSessions.remove(s.getSessionId());
            redisTemplate.delete(String.format(REDIS_KEY_SESSION, s.getSessionId()));
            log.warn("Session timeout: {} robot={}", s.getSessionId(), s.getRobotId());
        }
        return timedOut;
    }

    /**
     * 查询会话列表
     */
    public List<TeleopSession> listSessions(String robotId, String operatorId,
                                             SessionStatus statusFilter, int limit) {
        if (robotId != null) {
            return sessionRepo.findByRobotIdOrderByCreatedAtDesc(robotId)
                .stream().limit(limit).toList();
        }
        if (operatorId != null) {
            return sessionRepo.findByOperatorIdOrderByCreatedAtDesc(operatorId)
                .stream().limit(limit).toList();
        }
        if (statusFilter != null) {
            return sessionRepo.findBySessionStatus(statusFilter)
                .stream().limit(limit).toList();
        }
        return sessionRepo.findAll().stream().limit(limit).toList();
    }

    /**
     * 获取会话统计
     */
    public Map<String, Object> getSessionStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("activeSessions", activeSessions.size());
        stats.put("activeInRedis",
            redisTemplate.keys(String.format(REDIS_KEY_SESSION, "*")).size());
        return stats;
    }

    private String toJson(Object obj) {
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(obj);
        } catch (Exception e) {
            return "[]";
        }
    }
}
