package com.qoobot.qoocloud.observability.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * LogAggregationService — 日志聚合服务
 * 多设备日志统一采集、索引、检索
 */
@Service
public class LogAggregationService {

    private static final Logger log = LoggerFactory.getLogger(LogAggregationService.class);

    private final RedisTemplate<String, String> redisTemplate;

    // 日志索引（内存缓存）
    private static final int MAX_IN_MEMORY_LOGS = 5000;
    private final Deque<LogEntry> recentLogs = new ArrayDeque<>(MAX_IN_MEMORY_LOGS);

    // 日志统计
    private final Map<String, LogSourceStats> sourceStats = new ConcurrentHashMap<>();

    public LogAggregationService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * 采集设备日志。
     */
    public void ingestLog(String deviceId, String source, LogLevel level,
                           String message, Map<String, String> metadata) {
        LogEntry entry = new LogEntry();
        entry.logId = UUID.randomUUID().toString();
        entry.timestamp = Instant.now();
        entry.deviceId = deviceId;
        entry.source = source;
        entry.level = level;
        entry.message = message;
        entry.metadata = metadata != null ? metadata : Map.of();

        // 内存缓存
        synchronized (recentLogs) {
            recentLogs.addFirst(entry);
            while (recentLogs.size() > MAX_IN_MEMORY_LOGS) {
                recentLogs.pollLast();
            }
        }

        // Redis 持久化（按设备和级别分索引）
        String redisKey = "qoocloud:logs:" + deviceId + ":" +
                Instant.now().toString().substring(0, 10);
        redisTemplate.opsForList().leftPush(redisKey,
                com.qoobot.qoocloud.common.util.JsonUtils.toJson(entry));
        redisTemplate.expire(redisKey, Duration.ofDays(30));

        // 更新统计
        LogSourceStats stats = sourceStats.computeIfAbsent(deviceId, k -> new LogSourceStats());
        stats.totalLogs++;
        switch (level) {
            case ERROR -> stats.errorCount++;
            case WARN -> stats.warnCount++;
            case INFO -> stats.infoCount++;
            case DEBUG -> stats.debugCount++;
        }
        stats.lastLogAt = entry.timestamp;

        // 索引高价值日志（ERROR 和 WARN）
        if (level == LogLevel.ERROR || level == LogLevel.WARN) {
            redisTemplate.opsForZSet().add(
                    "qoocloud:logs:index:" + level.name().toLowerCase(),
                    com.qoobot.qoocloud.common.util.JsonUtils.toJson(entry),
                    entry.timestamp.toEpochMilli());
        }
    }

    /**
     * 批量采集日志。
     */
    public int ingestBatch(String deviceId, List<LogBatchItem> items) {
        int count = 0;
        for (LogBatchItem item : items) {
            ingestLog(deviceId, item.source, item.level, item.message, item.metadata);
            count++;
        }
        return count;
    }

    /**
     * 搜索日志。
     */
    public LogSearchResult searchLogs(String deviceId, LogLevel minLevel,
                                       String keyword, int limit) {
        List<LogEntry> results = new ArrayList<>();

        // 先查内存缓存
        synchronized (recentLogs) {
            for (LogEntry entry : recentLogs) {
                if (results.size() >= limit) break;

                boolean match = true;
                if (deviceId != null && !deviceId.equals(entry.deviceId)) match = false;
                if (minLevel != null && entry.level.ordinal() < minLevel.ordinal()) match = false;
                if (keyword != null && !entry.message.toLowerCase().contains(keyword.toLowerCase()))
                    match = false;

                if (match) results.add(entry);
            }
        }

        return new LogSearchResult(results, results.size(), limit);
    }

    /**
     * 获取设备日志统计。
     */
    public LogSourceStats getDeviceLogStats(String deviceId) {
        return sourceStats.getOrDefault(deviceId, new LogSourceStats());
    }

    /**
     * 获取所有设备的日志统计。
     */
    public Map<String, LogSourceStats> getAllLogStats() {
        return Map.copyOf(sourceStats);
    }

    /**
     * 获取按级别聚合的日志趋势。
     */
    public LogTrend getLogTrend(String deviceId, int hours) {
        Instant cutoff = Instant.now().minus(Duration.ofHours(hours));
        LogTrend trend = new LogTrend();
        trend.deviceId = deviceId;
        trend.hours = hours;

        long errorCount = 0;
        long warnCount = 0;
        long infoCount = 0;
        long debugCount = 0;

        synchronized (recentLogs) {
            for (LogEntry entry : recentLogs) {
                if (entry.deviceId.equals(deviceId) &&
                        entry.timestamp.isAfter(cutoff)) {
                    switch (entry.level) {
                        case ERROR -> errorCount++;
                        case WARN -> warnCount++;
                        case INFO -> infoCount++;
                        case DEBUG -> debugCount++;
                    }
                }
            }
        }

        trend.errorCount = errorCount;
        trend.warnCount = warnCount;
        trend.infoCount = infoCount;
        trend.debugCount = debugCount;
        trend.totalCount = errorCount + warnCount + infoCount + debugCount;
        trend.generatedAt = Instant.now();

        return trend;
    }

    /**
     * 获取最近的错误日志。
     */
    public List<LogEntry> getRecentErrors(int limit) {
        return searchLogs(null, LogLevel.ERROR, null, limit).results();
    }

    /**
     * 清理过期日志。
     */
    public int cleanupOldLogs(int retentionDays) {
        // 内存中的日志自动通过 MAX_IN_MEMORY_LOGS 限制
        // Redis 中的日志通过 TTL 自动过期
        return 0; // TTL-based cleanup, no manual action needed
    }

    // --- Inner Types ---

    public enum LogLevel {
        DEBUG, INFO, WARN, ERROR
    }

    public static class LogEntry {
        public String logId;
        public Instant timestamp;
        public String deviceId;
        public String source;     // qoobrain, qoocore, qoosvc, qooauth
        public LogLevel level;
        public String message;
        public Map<String, String> metadata = new HashMap<>();
    }

    public static class LogSourceStats {
        public long totalLogs;
        public long errorCount;
        public long warnCount;
        public long infoCount;
        public long debugCount;
        public Instant lastLogAt;
    }

    public record LogBatchItem(
            String source,
            LogLevel level,
            String message,
            Map<String, String> metadata
    ) {}

    public record LogSearchResult(
            List<LogEntry> results,
            int count,
            int limit
    ) {}

    public static class LogTrend {
        public String deviceId;
        public int hours;
        public long errorCount;
        public long warnCount;
        public long infoCount;
        public long debugCount;
        public long totalCount;
        public Instant generatedAt;
    }
}
