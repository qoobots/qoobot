package com.qoobot.qoocloud.inference.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedDeque;

/**
 * AuditService — 推理审计服务
 * 请求日志、Token 用量统计、成本分析、审计追踪
 */
@Service
public class AuditService {

    private static final Logger log = LoggerFactory.getLogger(AuditService.class);

    private final RedisTemplate<String, String> redisTemplate;

    // 内存中保留最近 N 条审计记录作为热缓存
    private static final int MAX_IN_MEMORY_RECORDS = 1000;
    private final Deque<AuditRecord> recentRecords = new ConcurrentLinkedDeque<>();

    // Token 用量计数器
    private final Map<String, TokenUsage> dailyTokenUsage = new LinkedHashMap<>();

    // 成本配置 (USD per 1K tokens)
    private static final double COST_PER_1K_INPUT_TOKENS = 0.003;
    private static final double COST_PER_1K_OUTPUT_TOKENS = 0.015;
    private static final double COST_PER_GPU_SECOND = 0.0005;

    public AuditService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * 记录推理请求审计信息。
     */
    public void recordAudit(AuditRequest request) {
        AuditRecord record = new AuditRecord();
        record.requestId = request.requestId();
        record.timestamp = Instant.now();
        record.deviceId = request.deviceId();
        record.userId = request.userId();
        record.modelName = request.modelName();
        record.modelVersion = request.modelVersion();
        record.inputTokens = request.inputTokens();
        record.outputTokens = request.outputTokens();
        record.latencyMs = request.latencyMs();
        record.gpuTimeMs = request.gpuTimeMs();
        record.success = request.success();
        record.errorMessage = request.errorMessage();
        record.apiEndpoint = request.apiEndpoint();

        // 计算成本
        record.cost = calculateCost(request.inputTokens(), request.outputTokens(), request.gpuTimeMs());

        // 内存缓存
        recentRecords.addFirst(record);
        while (recentRecords.size() > MAX_IN_MEMORY_RECORDS) {
            recentRecords.pollLast();
        }

        // Redis 持久化（异步写入审计日志流）
        String redisKey = "qoocloud:audit:log:" + Instant.now().toString().substring(0, 10);
        redisTemplate.opsForList().leftPush(redisKey,
                com.qoobot.qoocloud.common.util.JsonUtils.toJson(record));
        redisTemplate.expire(redisKey, Duration.ofDays(30));

        // 更新每日 Token 用量
        String dayKey = Instant.now().toString().substring(0, 10);
        TokenUsage usage = dailyTokenUsage.computeIfAbsent(dayKey, k -> new TokenUsage());
        usage.totalInputTokens += request.inputTokens();
        usage.totalOutputTokens += request.outputTokens();
        usage.totalRequests++;
        usage.totalCost += record.cost;
        if (!request.success()) {
            usage.failedRequests++;
        }

        // 更新 Redis 中的用量计数器
        redisTemplate.opsForHash().increment("qoocloud:usage:daily:" + dayKey,
                "inputTokens", request.inputTokens());
        redisTemplate.opsForHash().increment("qoocloud:usage:daily:" + dayKey,
                "outputTokens", request.outputTokens());
        redisTemplate.opsForHash().increment("qoocloud:usage:daily:" + dayKey,
                "totalRequests", 1);
        redisTemplate.opsForHash().increment("qoocloud:usage:daily:" + dayKey,
                "totalCost", (long) (record.cost * 10000)); // 存储为整数避免浮点精度问题
    }

    /**
     * 获取推理审计日志。
     */
    public List<AuditRecord> getAuditLogs(int limit, String modelName, String userId) {
        return recentRecords.stream()
                .filter(r -> modelName == null || r.modelName.equals(modelName))
                .filter(r -> userId == null || r.userId.equals(userId))
                .limit(limit)
                .toList();
    }

    /**
     * 获取指定日期范围内的审计记录。
     */
    public List<AuditRecord> getAuditLogsByDate(String fromDate, String toDate, int limit) {
        List<AuditRecord> result = new ArrayList<>();
        // 从 Redis 按日期拉取
        java.time.LocalDate start = java.time.LocalDate.parse(fromDate);
        java.time.LocalDate end = java.time.LocalDate.parse(toDate);

        for (java.time.LocalDate date = start; !date.isAfter(end) && result.size() < limit;
             date = date.plusDays(1)) {
            String key = "qoocloud:audit:log:" + date.toString();
            List<String> records = redisTemplate.opsForList().range(key, 0, limit - result.size() - 1);
            if (records != null) {
                for (String json : records) {
                    AuditRecord record = com.qoobot.qoocloud.common.util.JsonUtils.fromJson(
                            json, AuditRecord.class);
                    if (record != null) {
                        result.add(record);
                    }
                }
            }
        }
        return result;
    }

    /**
     * 获取 Token 用量统计。
     */
    public TokenUsageReport getTokenUsageReport(String fromDate, String toDate) {
        TokenUsageReport report = new TokenUsageReport();
        report.fromDate = fromDate;
        report.toDate = toDate;
        report.generatedAt = Instant.now();

        long totalInputTokens = 0;
        long totalOutputTokens = 0;
        long totalRequests = 0;
        double totalCost = 0;
        long failedRequests = 0;

        java.time.LocalDate start = java.time.LocalDate.parse(fromDate);
        java.time.LocalDate end = java.time.LocalDate.parse(toDate);

        List<TokenUsageReport.DailyBreakdown> dailyBreakdowns = new ArrayList<>();

        for (java.time.LocalDate date = start; !date.isAfter(end); date = date.plusDays(1)) {
            String dayKey = date.toString();
            Map<Object, Object> hash = redisTemplate.opsForHash().entries(
                    "qoocloud:usage:daily:" + dayKey);

            long inputTokens = parseLong(hash.get("inputTokens"));
            long outputTokens = parseLong(hash.get("outputTokens"));
            long requests = parseLong(hash.get("totalRequests"));
            long costRaw = parseLong(hash.get("totalCost"));

            totalInputTokens += inputTokens;
            totalOutputTokens += outputTokens;
            totalRequests += requests;
            totalCost += costRaw / 10000.0;

            TokenUsageReport.DailyBreakdown breakdown = new TokenUsageReport.DailyBreakdown();
            breakdown.date = dayKey;
            breakdown.inputTokens = inputTokens;
            breakdown.outputTokens = outputTokens;
            breakdown.totalTokens = inputTokens + outputTokens;
            breakdown.requests = requests;
            breakdown.cost = costRaw / 10000.0;
            dailyBreakdowns.add(breakdown);
        }

        report.totalInputTokens = totalInputTokens;
        report.totalOutputTokens = totalOutputTokens;
        report.totalTokens = totalInputTokens + totalOutputTokens;
        report.totalRequests = totalRequests;
        report.totalCost = totalCost;
        report.dailyBreakdown = dailyBreakdowns;

        return report;
    }

    /**
     * 获取成本分析。
     */
    public CostAnalysis getCostAnalysis(String month) {
        CostAnalysis analysis = new CostAnalysis();
        analysis.month = month;

        // 按模型聚合成本
        Map<String, Double> modelCosts = new LinkedHashMap<>();
        double grandTotal = 0;

        for (AuditRecord record : recentRecords) {
            if (record.timestamp.toString().startsWith(month)) {
                modelCosts.merge(record.modelName, record.cost, Double::sum);
                grandTotal += record.cost;
            }
        }

        analysis.totalCost = grandTotal;
        analysis.modelBreakdown = modelCosts.entrySet().stream()
                .map(e -> new CostAnalysis.ModelCostBreakdown(
                        e.getKey(), e.getValue(), grandTotal > 0 ? e.getValue() / grandTotal : 0))
                .sorted((a, b) -> Double.compare(b.cost(), a.cost()))
                .toList();

        return analysis;
    }

    /**
     * 计算单次推理成本。
     */
    private double calculateCost(long inputTokens, long outputTokens, long gpuTimeMs) {
        double inputCost = (inputTokens / 1000.0) * COST_PER_1K_INPUT_TOKENS;
        double outputCost = (outputTokens / 1000.0) * COST_PER_1K_OUTPUT_TOKENS;
        double gpuCost = (gpuTimeMs / 1000.0) * COST_PER_GPU_SECOND;
        return inputCost + outputCost + gpuCost;
    }

    private long parseLong(Object value) {
        if (value == null) return 0;
        if (value instanceof Number) return ((Number) value).longValue();
        try {
            return Long.parseLong(value.toString());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    // --- DTOs ---

    public record AuditRequest(
            String requestId,
            String deviceId,
            String userId,
            String modelName,
            String modelVersion,
            long inputTokens,
            long outputTokens,
            long latencyMs,
            long gpuTimeMs,
            boolean success,
            String errorMessage,
            String apiEndpoint
    ) {}

    public static class AuditRecord {
        public String requestId;
        public Instant timestamp;
        public String deviceId;
        public String userId;
        public String modelName;
        public String modelVersion;
        public long inputTokens;
        public long outputTokens;
        public long latencyMs;
        public long gpuTimeMs;
        public boolean success;
        public String errorMessage;
        public String apiEndpoint;
        public double cost;
    }

    public static class TokenUsageReport {
        public String fromDate;
        public String toDate;
        public Instant generatedAt;
        public long totalInputTokens;
        public long totalOutputTokens;
        public long totalTokens;
        public long totalRequests;
        public double totalCost;
        public List<DailyBreakdown> dailyBreakdown = new ArrayList<>();

        public static class DailyBreakdown {
            public String date;
            public long inputTokens;
            public long outputTokens;
            public long totalTokens;
            public long requests;
            public double cost;
        }
    }

    public static class CostAnalysis {
        public String month;
        public double totalCost;
        public List<ModelCostBreakdown> modelBreakdown = new ArrayList<>();

        public record ModelCostBreakdown(String modelName, double cost, double percentage) {}
    }

    private static class TokenUsage {
        long totalInputTokens = 0;
        long totalOutputTokens = 0;
        long totalRequests = 0;
        long failedRequests = 0;
        double totalCost = 0;
    }
}
