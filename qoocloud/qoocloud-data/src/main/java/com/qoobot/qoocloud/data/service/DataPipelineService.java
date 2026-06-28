package com.qoobot.qoocloud.data.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;

/**
 * DataPipelineService — 数据管道服务
 * 实时/批量数据上传、ETL 处理、存储分层
 */
@Service
public class DataPipelineService {

    private static final Logger log = LoggerFactory.getLogger(DataPipelineService.class);

    private final RedisTemplate<String, String> redisTemplate;
    private final PrivacyFilterService privacyFilter;

    // 管道配置
    private final Map<String, PipelineConfig> pipelines = new ConcurrentHashMap<>();
    // 管道状态
    private final Map<String, PipelineStatus> pipelineStatuses = new ConcurrentHashMap<>();
    // 数据缓冲区（内存中暂存待处理的批次）
    private final Deque<DataBatch> pendingBatches = new ConcurrentLinkedDeque<>();
    // 存储分层统计
    private final Map<StorageTier, TierStats> tierStats = new ConcurrentHashMap<>();

    public DataPipelineService(RedisTemplate<String, String> redisTemplate,
                                PrivacyFilterService privacyFilter) {
        this.redisTemplate = redisTemplate;
        this.privacyFilter = privacyFilter;

        // 初始化存储分层统计
        for (StorageTier tier : StorageTier.values()) {
            tierStats.put(tier, new TierStats());
        }
    }

    /**
     * 创建数据处理管道。
     */
    public PipelineConfig createPipeline(String name, String source, List<String> transforms,
                                          String sink, StorageTier tier) {
        String pipelineId = "pipe_" + UUID.randomUUID().toString().substring(0, 8);

        PipelineConfig config = new PipelineConfig();
        config.pipelineId = pipelineId;
        config.name = name;
        config.source = source;
        config.transforms = transforms;
        config.sink = sink;
        config.storageTier = tier;
        config.status = "active";
        config.createdAt = Instant.now();

        pipelines.put(pipelineId, config);

        PipelineStatus status = new PipelineStatus();
        status.pipelineId = pipelineId;
        status.totalProcessed = 0;
        status.totalErrors = 0;
        pipelineStatuses.put(pipelineId, status);

        log.info("Data pipeline created: {} ({})", name, pipelineId);
        return config;
    }

    /**
     * 上传数据到管道（实时模式）。
     */
    public DataUploadResult uploadRealtime(String pipelineId, String deviceId,
                                            String dataType, String payload,
                                            Map<String, String> tags) {
        PipelineConfig config = pipelines.get(pipelineId);
        if (config == null) {
            return DataUploadResult.error("Pipeline not found: " + pipelineId);
        }

        String uploadId = "up_" + UUID.randomUUID().toString().substring(0, 8);
        Instant startTime = Instant.now();

        try {
            // Step 1: 隐私过滤
            String filteredPayload = privacyFilter.filterPII(payload);
            double privacyRisk = privacyFilter.computePrivacyRisk(filteredPayload,
                    tags != null ? new ArrayList<>(tags.values()) : List.of());

            // Step 2: ETL 转换
            String transformed = applyTransforms(filteredPayload, config.transforms);

            // Step 3: 存储分层
            storeByTier(uploadId, transformed, config.storageTier, dataType);

            // Step 4: 更新管道状态
            PipelineStatus status = pipelineStatuses.get(pipelineId);
            if (status != null) {
                status.totalProcessed++;
                status.lastProcessedAt = Instant.now();
                status.totalBytesProcessed += transformed.length();
            }

            // Step 5: 更新分层统计
            TierStats stats = tierStats.get(config.storageTier);
            if (stats != null) {
                stats.totalItems++;
                stats.totalBytes += transformed.length();
                stats.lastUpdated = Instant.now();
            }

            long latencyMs = Duration.between(startTime, Instant.now()).toMillis();

            return new DataUploadResult(uploadId, "processed", config.storageTier.name(),
                    privacyRisk, latencyMs, null);

        } catch (Exception e) {
            PipelineStatus status = pipelineStatuses.get(pipelineId);
            if (status != null) {
                status.totalErrors++;
            }
            log.error("Data upload failed for pipeline {}: {}", pipelineId, e.getMessage());
            return DataUploadResult.error("Upload failed: " + e.getMessage());
        }
    }

    /**
     * 批量上传数据。
     */
    public BatchUploadResult uploadBatch(String pipelineId, String deviceId,
                                          List<DataItem> items) {
        String batchId = "batch_" + UUID.randomUUID().toString().substring(0, 8);

        DataBatch batch = new DataBatch();
        batch.batchId = batchId;
        batch.pipelineId = pipelineId;
        batch.deviceId = deviceId;
        batch.items = items;
        batch.createdAt = Instant.now();

        pendingBatches.add(batch);

        // 异步处理批次
        int processed = 0;
        int failed = 0;
        long totalBytes = 0;

        for (DataItem item : items) {
            try {
                String filtered = privacyFilter.filterPII(item.payload);
                PipelineConfig config = pipelines.get(pipelineId);
                if (config != null) {
                    String transformed = applyTransforms(filtered, config.transforms);
                    storeByTier(item.itemId, transformed, config.storageTier, item.dataType);
                    totalBytes += transformed.length();
                }
                processed++;
            } catch (Exception e) {
                failed++;
                log.error("Batch item {} failed: {}", item.itemId, e.getMessage());
            }
        }

        batch.processedAt = Instant.now();
        batch.processedCount = processed;
        batch.failedCount = failed;

        // 更新管道状态
        PipelineStatus status = pipelineStatuses.get(pipelineId);
        if (status != null) {
            status.totalProcessed += processed;
            status.totalErrors += failed;
            status.totalBytesProcessed += totalBytes;
            status.lastProcessedAt = Instant.now();
        }

        return new BatchUploadResult(batchId, items.size(), processed, failed, totalBytes);
    }

    /**
     * 获取管道状态。
     */
    public Optional<PipelineStatus> getPipelineStatus(String pipelineId) {
        return Optional.ofNullable(pipelineStatuses.get(pipelineId));
    }

    /**
     * 获取所有管道。
     */
    public List<PipelineConfig> listPipelines() {
        return new ArrayList<>(pipelines.values());
    }

    /**
     * 获取存储分层统计。
     */
    public Map<StorageTier, TierStats> getStorageTierStats() {
        return Map.copyOf(tierStats);
    }

    /**
     * 暂停/恢复管道。
     */
    public void setPipelineStatus(String pipelineId, String status) {
        PipelineConfig config = pipelines.get(pipelineId);
        if (config != null) {
            config.status = status;
            log.info("Pipeline {} status changed to {}", pipelineId, status);
        }
    }

    /**
     * ETL 转换处理。
     */
    private String applyTransforms(String payload, List<String> transforms) {
        String result = payload;
        for (String transform : transforms) {
            switch (transform) {
                case "normalize":
                    result = result.trim().replaceAll("\\s+", " ");
                    break;
                case "compress":
                    // 模拟压缩
                    if (result.length() > 1024) {
                        result = "[compressed:" + result.substring(0, 100) + "...]";
                    }
                    break;
                case "deduplicate":
                    // 去重逻辑：检查 Redis 中是否存在相同哈希
                    String hash = Integer.toHexString(result.hashCode());
                    if (Boolean.TRUE.equals(redisTemplate.hasKey("qoocloud:data:dedup:" + hash))) {
                        result = "[deduplicated]";
                    } else {
                        redisTemplate.opsForValue().set(
                                "qoocloud:data:dedup:" + hash, "1", Duration.ofHours(24));
                    }
                    break;
                case "enrich":
                    // 丰富化：添加时间戳等元数据
                    result = "{\"timestamp\":\"" + Instant.now() + "\",\"data\":" + result + "}";
                    break;
                default:
                    break;
            }
        }
        return result;
    }

    /**
     * 按存储分层存储数据。
     */
    private void storeByTier(String itemId, String data, StorageTier tier, String dataType) {
        String key = switch (tier) {
            case HOT -> "qoocloud:data:hot:" + dataType + ":" + itemId;
            case WARM -> "qoocloud:data:warm:" + dataType + ":" + itemId;
            case COLD -> "qoocloud:data:cold:" + dataType + ":" + itemId;
            case ARCHIVE -> "qoocloud:data:archive:" + dataType + ":" + itemId;
        };

        Duration ttl = switch (tier) {
            case HOT -> Duration.ofDays(7);
            case WARM -> Duration.ofDays(30);
            case COLD -> Duration.ofDays(90);
            case ARCHIVE -> Duration.ofDays(365);
        };

        redisTemplate.opsForValue().set(key, data, ttl);
    }

    // --- Inner Types ---

    public enum StorageTier {
        HOT,     // 热数据：7天 TTL，高频访问
        WARM,    // 温数据：30天 TTL，中等频率
        COLD,    // 冷数据：90天 TTL，低频访问
        ARCHIVE  // 归档数据：365天 TTL，合规保留
    }

    public static class PipelineConfig {
        public String pipelineId;
        public String name;
        public String source;         // 数据源类型：device_telemetry, experience, sensor_raw
        public List<String> transforms; // ETL 转换列表：normalize, compress, deduplicate, enrich
        public String sink;           // 数据目标：redis, postgres, minio, kafka
        public StorageTier storageTier;
        public String status;         // active, paused, error
        public Instant createdAt;
    }

    public static class PipelineStatus {
        public String pipelineId;
        public long totalProcessed;
        public long totalErrors;
        public long totalBytesProcessed;
        public Instant lastProcessedAt;
    }

    public static class TierStats {
        public long totalItems;
        public long totalBytes;
        public Instant lastUpdated;
    }

    public record DataItem(
            String itemId,
            String dataType,
            String payload,
            Map<String, String> tags
    ) {}

    public record DataUploadResult(
            String uploadId,
            String status,
            String storageTier,
            double privacyRisk,
            long latencyMs,
            String error
    ) {
        public static DataUploadResult error(String error) {
            return new DataUploadResult(null, "failed", null, 0, 0, error);
        }
    }

    public record BatchUploadResult(
            String batchId,
            int totalItems,
            int processed,
            int failed,
            long totalBytes
    ) {}

    private static class DataBatch {
        String batchId;
        String pipelineId;
        String deviceId;
        List<DataItem> items;
        Instant createdAt;
        Instant processedAt;
        int processedCount;
        int failedCount;
    }
}
