package com.qoobot.qoocloud.inference.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * PromptService — Prompt 管理服务
 * 系统 Prompt 模板库、A/B 测试、效果评估
 */
@Service
public class PromptService {

    private static final Logger log = LoggerFactory.getLogger(PromptService.class);

    private final RedisTemplate<String, String> redisTemplate;

    // 内存缓存 Prompt 模板
    private final Map<String, PromptTemplate> templates = new ConcurrentHashMap<>();
    // A/B 测试配置
    private final Map<String, ABTestConfig> abTests = new ConcurrentHashMap<>();
    // Prompt 效果评分
    private final Map<String, List<PromptRating>> ratings = new ConcurrentHashMap<>();

    public PromptService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * 创建 Prompt 模板。
     */
    public PromptTemplate createTemplate(PromptTemplate template) {
        template.templateId = "prompt_" + UUID.randomUUID().toString().substring(0, 8);
        template.version = 1;
        template.status = "draft";
        template.createdAt = Instant.now();
        template.updatedAt = Instant.now();
        templates.put(template.templateId, template);

        // 持久化到 Redis
        redisTemplate.opsForValue().set(
                "qoocloud:prompt:template:" + template.templateId,
                com.qoobot.qoocloud.common.util.JsonUtils.toJson(template),
                Duration.ofDays(90));

        log.info("Prompt template created: {} ({})", template.name, template.templateId);
        return template;
    }

    /**
     * 更新 Prompt 模板（版本递增）。
     */
    public PromptTemplate updateTemplate(String templateId, String content,
                                          Map<String, String> variables) {
        PromptTemplate template = templates.get(templateId);
        if (template == null) {
            throw new RuntimeException("Prompt template not found: " + templateId);
        }

        template.version++;
        template.content = content;
        template.variables = variables != null ? variables : Map.of();
        template.updatedAt = Instant.now();

        templates.put(templateId, template);

        redisTemplate.opsForValue().set(
                "qoocloud:prompt:template:" + templateId,
                com.qoobot.qoocloud.common.util.JsonUtils.toJson(template),
                Duration.ofDays(90));

        log.info("Prompt template updated: {} v{}", template.name, template.version);
        return template;
    }

    /**
     * 发布 Prompt 模板（从 draft → active）。
     */
    public PromptTemplate publishTemplate(String templateId) {
        PromptTemplate template = templates.get(templateId);
        if (template == null) {
            throw new RuntimeException("Prompt template not found: " + templateId);
        }
        template.status = "active";
        template.publishedAt = Instant.now();
        templates.put(templateId, template);
        return template;
    }

    /**
     * 获取 Prompt 模板列表。
     */
    public List<PromptTemplate> listTemplates(String category, String status) {
        return templates.values().stream()
                .filter(t -> category == null || t.category.equals(category))
                .filter(t -> status == null || t.status.equals(status))
                .sorted(Comparator.comparing(PromptTemplate::getUpdatedAt).reversed())
                .toList();
    }

    /**
     * 获取单个 Prompt 模板。
     */
    public Optional<PromptTemplate> getTemplate(String templateId) {
        return Optional.ofNullable(templates.get(templateId));
    }

    /**
     * 渲染 Prompt：将变量填充到模板中。
     */
    public String renderPrompt(String templateId, Map<String, String> variableValues) {
        PromptTemplate template = templates.get(templateId);
        if (template == null) {
            throw new RuntimeException("Prompt template not found: " + templateId);
        }

        String result = template.content;
        for (Map.Entry<String, String> entry : variableValues.entrySet()) {
            result = result.replace("{{" + entry.getKey() + "}}", entry.getValue());
        }
        return result;
    }

    /**
     * 创建 A/B 测试。
     */
    public ABTestConfig createABTest(String name, String templateIdA, String templateIdB,
                                       double trafficSplit) {
        String testId = "abtest_" + UUID.randomUUID().toString().substring(0, 8);

        PromptTemplate templateA = templates.get(templateIdA);
        PromptTemplate templateB = templates.get(templateIdB);

        if (templateA == null || templateB == null) {
            throw new RuntimeException("One or both prompt templates not found");
        }

        ABTestConfig config = new ABTestConfig();
        config.testId = testId;
        config.name = name;
        config.templateIdA = templateIdA;
        config.templateIdB = templateIdB;
        config.trafficSplit = trafficSplit;
        config.status = "running";
        config.startedAt = Instant.now();
        config.metrics = new ABTestMetrics();

        abTests.put(testId, config);

        log.info("A/B test created: {} ({} vs {})", name, templateIdA, templateIdB);
        return config;
    }

    /**
     * 获取 A/B 测试的路由决策。
     */
    public String getABTestPromptId(String testId, String deviceId) {
        ABTestConfig config = abTests.get(testId);
        if (config == null || !"running".equals(config.status)) {
            return null;
        }

        // 基于设备 ID 哈希确定分组（确保同一设备始终在同一组）
        int hash = Math.abs(deviceId.hashCode()) % 100;
        return hash < (config.trafficSplit * 100) ? config.templateIdA : config.templateIdB;
    }

    /**
     * 记录 A/B 测试结果。
     */
    public void recordABTestResult(String testId, String promptId, boolean success,
                                    double qualityScore, long latencyMs) {
        ABTestConfig config = abTests.get(testId);
        if (config == null) return;

        config.metrics.totalRequests++;

        if (promptId.equals(config.templateIdA)) {
            config.metrics.aRequests++;
            if (success) config.metrics.aSuccesses++;
            config.metrics.aTotalScore += qualityScore;
            config.metrics.aTotalLatency += latencyMs;
        } else {
            config.metrics.bRequests++;
            if (success) config.metrics.bSuccesses++;
            config.metrics.bTotalScore += qualityScore;
            config.metrics.bTotalLatency += latencyMs;
        }
    }

    /**
     * 完成 A/B 测试并选择优胜者。
     */
    public ABTestResult completeABTest(String testId) {
        ABTestConfig config = abTests.get(testId);
        if (config == null) {
            throw new RuntimeException("A/B test not found: " + testId);
        }

        config.status = "completed";
        config.endedAt = Instant.now();

        ABTestMetrics m = config.metrics;
        double aSuccessRate = m.aRequests > 0 ? (double) m.aSuccesses / m.aRequests : 0;
        double bSuccessRate = m.bRequests > 0 ? (double) m.bSuccesses / m.bRequests : 0;
        double aAvgScore = m.aRequests > 0 ? m.aTotalScore / m.aRequests : 0;
        double bAvgScore = m.bRequests > 0 ? m.bTotalScore / m.bRequests : 0;

        String winner;
        String reason;
        if (aSuccessRate > bSuccessRate + 0.02) {
            winner = config.templateIdA;
            reason = String.format("A success rate %.2f%% > B %.2f%%",
                    aSuccessRate * 100, bSuccessRate * 100);
        } else if (bSuccessRate > aSuccessRate + 0.02) {
            winner = config.templateIdB;
            reason = String.format("B success rate %.2f%% > A %.2f%%",
                    bSuccessRate * 100, aSuccessRate * 100);
        } else if (aAvgScore > bAvgScore) {
            winner = config.templateIdA;
            reason = String.format("A avg score %.3f > B %.3f", aAvgScore, bAvgScore);
        } else {
            winner = config.templateIdB;
            reason = String.format("B avg score %.3f > A %.3f", bAvgScore, aAvgScore);
        }

        ABTestResult result = new ABTestResult(testId, config.name, winner, reason,
                aSuccessRate, bSuccessRate, aAvgScore, bAvgScore,
                m.aRequests, m.bRequests, m.totalRequests);

        log.info("A/B test completed: {} — Winner: {} ({})", testId, winner, reason);
        return result;
    }

    /**
     * 提交 Prompt 效果评分。
     */
    public void ratePrompt(String templateId, String deviceId, double score, String feedback) {
        PromptRating rating = new PromptRating();
        rating.templateId = templateId;
        rating.deviceId = deviceId;
        rating.score = score;
        rating.feedback = feedback;
        rating.timestamp = Instant.now();

        ratings.computeIfAbsent(templateId, k -> new ArrayList<>()).add(rating);

        // 持久化
        redisTemplate.opsForList().leftPush(
                "qoocloud:prompt:ratings:" + templateId,
                com.qoobot.qoocloud.common.util.JsonUtils.toJson(rating));
    }

    /**
     * 获取 Prompt 评分统计。
     */
    public PromptStats getPromptStats(String templateId) {
        List<PromptRating> promptRatings = ratings.getOrDefault(templateId, List.of());
        if (promptRatings.isEmpty()) {
            return new PromptStats(templateId, 0, 0, 0);
        }

        double total = 0;
        for (PromptRating r : promptRatings) {
            total += r.score;
        }
        return new PromptStats(templateId, total / promptRatings.size(),
                promptRatings.size(), promptRatings.get(promptRatings.size() - 1).timestamp);
    }

    // --- Inner Types ---

    public static class PromptTemplate {
        public String templateId;
        public String name;
        public String description;
        public String category;    // SYSTEM, TASK, DIALOGUE, VISION, SAFETY
        public String content;      // 模板内容，支持 {{variable}} 占位符
        public Map<String, String> variables = new HashMap<>();
        public int version;
        public String status;       // draft, active, deprecated
        public String createdBy;
        public Instant createdAt;
        public Instant updatedAt;
        public Instant publishedAt;

        public String getTemplateId() { return templateId; }
        public String getName() { return name; }
        public String getDescription() { return description; }
        public String getCategory() { return category; }
        public String getContent() { return content; }
        public int getVersion() { return version; }
        public String getStatus() { return status; }
        public Instant getUpdatedAt() { return updatedAt; }
    }

    public static class ABTestConfig {
        public String testId;
        public String name;
        public String templateIdA;
        public String templateIdB;
        public double trafficSplit;  // 0.0-1.0, A 的比例
        public String status;        // running, completed
        public Instant startedAt;
        public Instant endedAt;
        public ABTestMetrics metrics = new ABTestMetrics();
    }

    public static class ABTestMetrics {
        public long totalRequests = 0;
        public long aRequests = 0;
        public long aSuccesses = 0;
        public double aTotalScore = 0;
        public long aTotalLatency = 0;
        public long bRequests = 0;
        public long bSuccesses = 0;
        public double bTotalScore = 0;
        public long bTotalLatency = 0;
    }

    public record ABTestResult(
            String testId,
            String testName,
            String winnerTemplateId,
            String reason,
            double aSuccessRate,
            double bSuccessRate,
            double aAvgScore,
            double bAvgScore,
            long aRequests,
            long bRequests,
            long totalRequests
    ) {}

    public static class PromptRating {
        public String templateId;
        public String deviceId;
        public double score;       // 1-5
        public String feedback;
        public Instant timestamp;
    }

    public record PromptStats(
            String templateId,
            double averageScore,
            int totalRatings,
            Instant lastRating
    ) {}
}
