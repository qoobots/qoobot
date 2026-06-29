package com.qoobot.qoocloud.teleop.service;

import com.qoobot.qoocloud.teleop.entity.TeachingRecord;
import com.qoobot.qoocloud.teleop.repository.TeachingRecordRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 示教录制与回放服务
 *
 * 管理操作示教数据的采集、存储、检索和回放控制。
 * 支持：
 * - 示教会话创建/停止
 * - 轨迹数据帧追加
 * - 示教记录查询（按机器人/操作员/标签）
 * - 回放状态管理
 */
@Service
public class TeachingService {

    private static final Logger log = LoggerFactory.getLogger(TeachingService.class);

    private final TeachingRecordRepository recordRepo;
    private final SessionService sessionService;

    // 活跃的示教会话
    private final Map<String, ActiveTeaching> activeTeachings = new ConcurrentHashMap<>();

    private static final long MAX_DURATION_MS = 1_800_000; // 30分钟
    private static final int MAX_FRAMES = 1_000_000;

    public TeachingService(TeachingRecordRepository recordRepo,
                           SessionService sessionService) {
        this.recordRepo = recordRepo;
        this.sessionService = sessionService;
    }

    /**
     * 开始示教录制
     */
    public TeachingRecord startRecording(String sessionId, String robotId,
                                          String operatorId, String name,
                                          String description, List<String> tags) {
        // 检查是否已在录制
        if (activeTeachings.containsKey(sessionId)) {
            throw new IllegalStateException("Already recording for session: " + sessionId);
        }

        // 验证会话存在
        sessionService.getSession(sessionId);

        TeachingRecord record = new TeachingRecord();
        record.setSessionId(sessionId);
        record.setRobotId(robotId);
        record.setOperatorId(operatorId);
        record.setName(name);
        record.setDescription(description);
        record.setTags(toJson(tags));
        record.setCreatedAt(Instant.now());

        record = recordRepo.save(record);

        ActiveTeaching active = new ActiveTeaching();
        active.record = record;
        active.startTime = Instant.now();
        active.frameCount = 0;
        activeTeachings.put(sessionId, active);

        log.info("Teaching recording started: {} session={} name={}",
            record.getRecordId(), sessionId, name);
        return record;
    }

    /**
     * 追加示教数据帧
     */
    public TeachingFrameResult appendFrame(String sessionId, Map<String, Object> frameData) {
        ActiveTeaching active = activeTeachings.get(sessionId);
        if (active == null) {
            throw new IllegalStateException("No active recording for session: " + sessionId);
        }

        // 检查时长限制
        long elapsed = Instant.now().toEpochMilli() - active.startTime.toEpochMilli();
        if (elapsed > MAX_DURATION_MS) {
            throw new IllegalStateException("Max recording duration exceeded");
        }

        // 检查帧数限制
        if (active.frameCount >= MAX_FRAMES) {
            throw new IllegalStateException("Max frame count exceeded");
        }

        active.frameCount++;
        active.lastFrameTime = Instant.now();

        TeachingFrameResult result = new TeachingFrameResult();
        result.recordId = active.record.getRecordId();
        result.frameIndex = active.frameCount;
        result.elapsedMs = elapsed;
        result.accepted = true;

        return result;
    }

    /**
     * 停止示教录制
     */
    public TeachingRecord stopRecording(String sessionId) {
        ActiveTeaching active = activeTeachings.remove(sessionId);
        if (active == null) {
            throw new NoSuchElementException("No active recording for session: " + sessionId);
        }

        TeachingRecord record = active.record;
        record.setDurationMs(
            active.lastFrameTime != null
                ? active.lastFrameTime.toEpochMilli() - active.startTime.toEpochMilli()
                : 0L);
        record.setFrameCount(active.frameCount);
        record.setDataFormat("v1.0");

        // 质量评估（基于帧数的简单评估）
        float quality = Math.min(1.0f, active.frameCount / 1000.0f);
        record.setQualityScore(quality);

        record = recordRepo.save(record);

        log.info("Teaching recording stopped: {} frames={} duration={}ms quality={}",
            record.getRecordId(), active.frameCount, record.getDurationMs(), quality);
        return record;
    }

    /**
     * 获取示教记录
     */
    public TeachingRecord getRecord(String recordId) {
        return recordRepo.findById(recordId)
            .orElseThrow(() -> new NoSuchElementException("Record not found: " + recordId));
    }

    /**
     * 按机器人查询示教记录
     */
    public List<TeachingRecord> listByRobot(String robotId) {
        return recordRepo.findByRobotIdOrderByCreatedAtDesc(robotId);
    }

    /**
     * 按操作员查询示教记录
     */
    public List<TeachingRecord> listByOperator(String operatorId) {
        return recordRepo.findByOperatorIdOrderByCreatedAtDesc(operatorId);
    }

    /**
     * 按会话查询示教记录
     */
    public List<TeachingRecord> listBySession(String sessionId) {
        return recordRepo.findBySessionId(sessionId);
    }

    /**
     * 搜索示教记录
     */
    public List<TeachingRecord> search(String keyword) {
        return recordRepo.searchByName(keyword);
    }

    /**
     * 按标签查询示教记录
     */
    public List<TeachingRecord> findByTag(String tag) {
        return recordRepo.findByTag("\"" + tag + "\"");
    }

    /**
     * 删除示教记录
     */
    public void deleteRecord(String recordId) {
        if (!recordRepo.existsById(recordId)) {
            throw new NoSuchElementException("Record not found: " + recordId);
        }
        recordRepo.deleteById(recordId);
        log.info("Teaching record deleted: {}", recordId);
    }

    /**
     * 验证示教记录
     */
    public TeachingRecord verifyRecord(String recordId, String verifiedBy) {
        TeachingRecord record = getRecord(recordId);
        record.setIsVerified(true);
        record = recordRepo.save(record);
        log.info("Teaching record verified: {} by {}", recordId, verifiedBy);
        return record;
    }

    /**
     * 获取示教统计
     */
    public Map<String, Object> getTeachingStats(String robotId) {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalRecords", recordRepo.count());
        stats.put("activeRecordings", activeTeachings.size());
        if (robotId != null) {
            stats.put("robotRecords", recordRepo.countByRobotId(robotId));
        }
        return stats;
    }

    private String toJson(Object obj) {
        try {
            return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(obj);
        } catch (Exception e) {
            return "[]";
        }
    }

    // ========== 内部类 ==========

    private static class ActiveTeaching {
        TeachingRecord record;
        Instant startTime;
        Instant lastFrameTime;
        int frameCount;
    }

    public static class TeachingFrameResult {
        public String recordId;
        public int frameIndex;
        public long elapsedMs;
        public boolean accepted;
    }
}
