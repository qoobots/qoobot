package com.qoobot.qoocloud.data.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * KnowledgeSyncService — 知识库同步服务
 * 多机器人共享语义地图、物体识别库、操作技能知识
 */
@Service
public class KnowledgeSyncService {

    private static final Logger log = LoggerFactory.getLogger(KnowledgeSyncService.class);

    private final RedisTemplate<String, String> redisTemplate;
    private final PrivacyFilterService privacyFilter;

    // 知识条目存储
    private final Map<String, KnowledgeEntry> knowledgeBase = new ConcurrentHashMap<>();
    // 同步状态追踪
    private final Map<String, SyncSession> syncSessions = new ConcurrentHashMap<>();

    public KnowledgeSyncService(RedisTemplate<String, String> redisTemplate,
                                 PrivacyFilterService privacyFilter) {
        this.redisTemplate = redisTemplate;
        this.privacyFilter = privacyFilter;
    }

    /**
     * 上传知识条目。
     */
    public KnowledgeEntry uploadKnowledge(String deviceId, String knowledgeType,
                                           String title, String content,
                                           Map<String, String> metadata) {
        String entryId = "k_" + UUID.randomUUID().toString().substring(0, 8);

        // 隐私过滤
        String filteredContent = privacyFilter.filterPII(content);

        KnowledgeEntry entry = new KnowledgeEntry();
        entry.entryId = entryId;
        entry.deviceId = deviceId;
        entry.knowledgeType = knowledgeType;
        entry.title = title;
        entry.content = filteredContent;
        entry.metadata = metadata != null ? metadata : Map.of();
        entry.version = 1;
        entry.uploadedAt = Instant.now();
        entry.updatedAt = Instant.now();

        knowledgeBase.put(entryId, entry);

        // 持久化到 Redis
        redisTemplate.opsForValue().set(
                "qoocloud:knowledge:entry:" + entryId,
                com.qoobot.qoocloud.common.util.JsonUtils.toJson(entry),
                Duration.ofDays(90));

        log.info("Knowledge entry uploaded: {} ({}) from device {}",
                title, knowledgeType, deviceId);
        return entry;
    }

    /**
     * 更新知识条目（版本递增）。
     */
    public KnowledgeEntry updateKnowledge(String entryId, String content,
                                           Map<String, String> metadata) {
        KnowledgeEntry entry = knowledgeBase.get(entryId);
        if (entry == null) {
            throw new RuntimeException("Knowledge entry not found: " + entryId);
        }

        entry.version++;
        entry.content = privacyFilter.filterPII(content);
        if (metadata != null) {
            entry.metadata = metadata;
        }
        entry.updatedAt = Instant.now();

        knowledgeBase.put(entryId, entry);

        redisTemplate.opsForValue().set(
                "qoocloud:knowledge:entry:" + entryId,
                com.qoobot.qoocloud.common.util.JsonUtils.toJson(entry),
                Duration.ofDays(90));

        return entry;
    }

    /**
     * 搜索知识库。
     */
    public List<KnowledgeEntry> searchKnowledge(String query, String knowledgeType, int limit) {
        String lowerQuery = query.toLowerCase();
        return knowledgeBase.values().stream()
                .filter(e -> knowledgeType == null || e.knowledgeType.equals(knowledgeType))
                .filter(e -> e.title.toLowerCase().contains(lowerQuery) ||
                        e.content.toLowerCase().contains(lowerQuery))
                .sorted(Comparator.comparing(KnowledgeEntry::getUploadedAt).reversed())
                .limit(limit)
                .toList();
    }

    /**
     * 获取知识条目详情。
     */
    public Optional<KnowledgeEntry> getKnowledge(String entryId) {
        return Optional.ofNullable(knowledgeBase.get(entryId));
    }

    /**
     * 按类型列出知识条目。
     */
    public List<KnowledgeEntry> listByType(String knowledgeType, int limit) {
        return knowledgeBase.values().stream()
                .filter(e -> e.knowledgeType.equals(knowledgeType))
                .sorted(Comparator.comparing(KnowledgeEntry::getUploadedAt).reversed())
                .limit(limit)
                .toList();
    }

    /**
     * 获取设备贡献的知识条目。
     */
    public List<KnowledgeEntry> getDeviceContributions(String deviceId) {
        return knowledgeBase.values().stream()
                .filter(e -> e.deviceId.equals(deviceId))
                .sorted(Comparator.comparing(KnowledgeEntry::getUploadedAt).reversed())
                .toList();
    }

    /**
     * 启动知识同步会话（批量同步到指定设备）。
     */
    public SyncSession startSyncSession(String targetDeviceId, List<String> knowledgeTypes) {
        String sessionId = "sync_" + UUID.randomUUID().toString().substring(0, 8);

        List<KnowledgeEntry> entries = knowledgeBase.values().stream()
                .filter(e -> knowledgeTypes.isEmpty() || knowledgeTypes.contains(e.knowledgeType))
                .toList();

        SyncSession session = new SyncSession();
        session.sessionId = sessionId;
        session.targetDeviceId = targetDeviceId;
        session.totalEntries = entries.size();
        session.syncedEntries = 0;
        session.status = "in_progress";
        session.startedAt = Instant.now();

        syncSessions.put(sessionId, session);

        // 模拟同步：将知识条目推送到目标设备
        for (KnowledgeEntry entry : entries) {
            redisTemplate.opsForList().leftPush(
                    "qoocloud:knowledge:sync:" + targetDeviceId,
                    com.qoobot.qoocloud.common.util.JsonUtils.toJson(entry));
            session.syncedEntries++;
        }

        session.status = "completed";
        session.completedAt = Instant.now();
        syncSessions.put(sessionId, session);

        log.info("Knowledge sync completed: {} entries to device {}",
                entries.size(), targetDeviceId);
        return session;
    }

    /**
     * 获取同步会话状态。
     */
    public Optional<SyncSession> getSyncSession(String sessionId) {
        return Optional.ofNullable(syncSessions.get(sessionId));
    }

    /**
     * 获取知识库统计。
     */
    public KnowledgeStats getStats() {
        Map<String, Long> typeCount = new HashMap<>();
        Set<String> contributingDevices = new HashSet<>();

        for (KnowledgeEntry entry : knowledgeBase.values()) {
            typeCount.merge(entry.knowledgeType, 1L, Long::sum);
            contributingDevices.add(entry.deviceId);
        }

        return new KnowledgeStats(
                knowledgeBase.size(),
                typeCount,
                contributingDevices.size()
        );
    }

    /**
     * 删除知识条目。
     */
    public void deleteKnowledge(String entryId) {
        knowledgeBase.remove(entryId);
        redisTemplate.delete("qoocloud:knowledge:entry:" + entryId);
        log.info("Knowledge entry deleted: {}", entryId);
    }

    // --- Inner Types ---

    public static class KnowledgeEntry {
        public String entryId;
        public String deviceId;
        public String knowledgeType;  // semantic_map, object_model, skill_recipe, calibration, scene_graph
        public String title;
        public String content;
        public Map<String, String> metadata = new HashMap<>();
        public int version;
        public Instant uploadedAt;
        public Instant updatedAt;

        public String getEntryId() { return entryId; }
        public String getDeviceId() { return deviceId; }
        public String getKnowledgeType() { return knowledgeType; }
        public String getTitle() { return title; }
        public String getContent() { return content; }
        public Map<String, String> getMetadata() { return metadata; }
        public int getVersion() { return version; }
        public Instant getUploadedAt() { return uploadedAt; }
        public Instant getUpdatedAt() { return updatedAt; }
    }

    public static class SyncSession {
        public String sessionId;
        public String targetDeviceId;
        public int totalEntries;
        public int syncedEntries;
        public String status;
        public Instant startedAt;
        public Instant completedAt;
    }

    public record KnowledgeStats(
            int totalEntries,
            Map<String, Long> entriesByType,
            int contributingDevices
    ) {}
}
