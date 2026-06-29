package com.qoobot.qoocloud.data.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * DataGovernanceService — 数据治理服务
 * 数据生命周期管理、合规存储、用户数据导出/删除（GDPR/个人信息保护法合规）。
 *
 * 功能对标：AWS Lake Formation + GDPR Right to Erasure
 */
@Service
public class DataGovernanceService {

    private static final Logger log = LoggerFactory.getLogger(DataGovernanceService.class);

    // 数据生命周期策略
    private final Map<String, LifecyclePolicy> lifecyclePolicies = new ConcurrentHashMap<>();

    // 数据保留规则
    private final Map<String, RetentionRule> retentionRules = new ConcurrentHashMap<>();

    // 用户数据导出请求记录
    private final Map<String, DataExportRequest> exportRequests = new ConcurrentHashMap<>();

    // 用户数据删除请求记录
    private final Map<String, DataDeletionRequest> deletionRequests = new ConcurrentHashMap<>();

    // ==================== 数据生命周期策略 ====================

    /**
     * 定义数据生命周期策略。
     *
     * @param dataCategory  数据类别（experience/image/log/telemetry/analytics）
     * @param retentionDays 保留天数（-1 表示永久）
     * @param storageTier   存储层级（HOT/WARM/COLD/ARCHIVE）
     * @param anonymizeAfterDays 多少天后脱敏（0 表示不脱敏）
     */
    public Map<String, Object> defineLifecyclePolicy(String dataCategory, int retentionDays,
                                                      String storageTier, int anonymizeAfterDays) {
        LifecyclePolicy policy = new LifecyclePolicy(
                dataCategory, retentionDays, storageTier, anonymizeAfterDays
        );
        lifecyclePolicies.put(dataCategory, policy);

        log.info("Lifecycle policy defined: category={}, retention={}d, tier={}, anonymize={}d",
                dataCategory, retentionDays, storageTier, anonymizeAfterDays);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dataCategory", dataCategory);
        result.put("retentionDays", retentionDays);
        result.put("storageTier", storageTier);
        result.put("anonymizeAfterDays", anonymizeAfterDays);
        result.put("status", "active");
        return result;
    }

    /**
     * 列出所有数据生命周期策略。
     */
    public List<Map<String, Object>> listLifecyclePolicies() {
        List<Map<String, Object>> list = new ArrayList<>();
        for (LifecyclePolicy p : lifecyclePolicies.values()) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("dataCategory", p.dataCategory);
            m.put("retentionDays", p.retentionDays);
            m.put("storageTier", p.storageTier);
            m.put("anonymizeAfterDays", p.anonymizeAfterDays);
            list.add(m);
        }
        return list;
    }

    /**
     * 检查数据是否过期。
     */
    public Map<String, Object> checkDataExpiry(String dataCategory, Instant createdAt) {
        LifecyclePolicy policy = lifecyclePolicies.get(dataCategory);
        if (policy == null || policy.retentionDays == -1) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("dataCategory", dataCategory);
            result.put("expired", false);
            result.put("reason", policy == null ? "no policy defined" : "permanent retention");
            return result;
        }

        Instant expiryDate = createdAt.plus(policy.retentionDays, ChronoUnit.DAYS);
        boolean expired = Instant.now().isAfter(expiryDate);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dataCategory", dataCategory);
        result.put("createdAt", createdAt.toString());
        result.put("expiryDate", expiryDate.toString());
        result.put("expired", expired);
        result.put("retentionDays", policy.retentionDays);
        result.put("recommendedAction", expired ? "archive_or_delete" : "keep");
        return result;
    }

    // ==================== 数据保留规则 ====================

    /**
     * 设置数据保留规则。
     */
    public Map<String, Object> setRetentionRule(String ruleId, String dataType,
                                                 int hotDays, int warmDays,
                                                 int coldDays, boolean archiveEnabled) {
        RetentionRule rule = new RetentionRule(ruleId, dataType, hotDays, warmDays,
                coldDays, archiveEnabled);
        retentionRules.put(ruleId, rule);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("ruleId", ruleId);
        result.put("dataType", dataType);
        result.put("tiers", Map.of(
                "HOT", hotDays + " days",
                "WARM", warmDays + " days",
                "COLD", coldDays + " days",
                "ARCHIVE", archiveEnabled ? "enabled" : "disabled"
        ));
        return result;
    }

    /**
     * 计算数据的存储分层建议。
     */
    public Map<String, Object> computeStorageTier(String dataType, Instant createdAt) {
        RetentionRule rule = retentionRules.values().stream()
                .filter(r -> r.dataType.equals(dataType))
                .findFirst()
                .orElse(null);

        if (rule == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("dataType", dataType);
            result.put("recommendedTier", "HOT");
            result.put("reason", "no retention rule defined, defaulting to HOT");
            return result;
        }

        long ageDays = ChronoUnit.DAYS.between(createdAt, Instant.now());
        String tier;

        if (ageDays <= rule.hotDays) {
            tier = "HOT";
        } else if (ageDays <= rule.hotDays + rule.warmDays) {
            tier = "WARM";
        } else if (ageDays <= rule.hotDays + rule.warmDays + rule.coldDays) {
            tier = "COLD";
        } else if (rule.archiveEnabled) {
            tier = "ARCHIVE";
        } else {
            tier = "EXPIRED";
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("dataType", dataType);
        result.put("createdAt", createdAt.toString());
        result.put("ageDays", ageDays);
        result.put("recommendedTier", tier);
        return result;
    }

    // ==================== 用户数据导出（GDPR 合规） ====================

    /**
     * 请求导出用户数据。
     */
    public Map<String, Object> requestDataExport(String userId, List<String> dataCategories,
                                                  String exportFormat) {
        String exportId = "export_" + UUID.randomUUID().toString().substring(0, 8);
        DataExportRequest request = new DataExportRequest(
                exportId, userId, dataCategories, exportFormat, "pending"
        );
        exportRequests.put(exportId, request);

        log.info("Data export requested: userId={}, categories={}, format={}",
                userId, dataCategories, exportFormat);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("exportId", exportId);
        result.put("userId", userId);
        result.put("dataCategories", dataCategories);
        result.put("exportFormat", exportFormat);
        result.put("status", "pending");
        result.put("estimatedCompletionMinutes", 30);
        return result;
    }

    /**
     * 查询导出状态。
     */
    public Map<String, Object> getExportStatus(String exportId) {
        DataExportRequest request = exportRequests.get(exportId);
        if (request == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("exportId", exportId);
            result.put("found", false);
            return result;
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("exportId", request.exportId);
        result.put("userId", request.userId);
        result.put("status", request.status);
        result.put("dataCategories", request.dataCategories);
        result.put("exportFormat", request.exportFormat);
        result.put("requestedAt", request.requestedAt.toString());

        if ("completed".equals(request.status)) {
            result.put("downloadUrl", "https://qoocloud.example.com/exports/" + exportId);
            result.put("expiresAt", request.requestedAt.plus(7, ChronoUnit.DAYS).toString());
        }
        return result;
    }

    /**
     * 列出用户的所有导出请求。
     */
    public List<Map<String, Object>> listUserExports(String userId) {
        return exportRequests.values().stream()
                .filter(r -> r.userId.equals(userId))
                .map(r -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("exportId", r.exportId);
                    m.put("status", r.status);
                    m.put("dataCategories", r.dataCategories);
                    m.put("exportFormat", r.exportFormat);
                    m.put("requestedAt", r.requestedAt.toString());
                    return m;
                })
                .collect(java.util.stream.Collectors.toList());
    }

    // ==================== 用户数据删除（Right to Erasure） ====================

    /**
     * 请求删除用户数据。
     */
    public Map<String, Object> requestDataDeletion(String userId, List<String> dataCategories,
                                                    String reason) {
        String deletionId = "delete_" + UUID.randomUUID().toString().substring(0, 8);
        DataDeletionRequest request = new DataDeletionRequest(
                deletionId, userId, dataCategories, reason, "pending"
        );
        deletionRequests.put(deletionId, request);

        log.warn("Data deletion requested: userId={}, categories={}, reason={}",
                userId, dataCategories, reason);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("deletionId", deletionId);
        result.put("userId", userId);
        result.put("dataCategories", dataCategories);
        result.put("status", "pending");
        result.put("estimatedCompletionHours", 72);
        result.put("complianceNote",
                "Deletion will be processed within 72 hours per GDPR Article 17");
        return result;
    }

    /**
     * 查询删除状态。
     */
    public Map<String, Object> getDeletionStatus(String deletionId) {
        DataDeletionRequest request = deletionRequests.get(deletionId);
        if (request == null) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("deletionId", deletionId);
            result.put("found", false);
            return result;
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("deletionId", request.deletionId);
        result.put("userId", request.userId);
        result.put("status", request.status);
        result.put("dataCategories", request.dataCategories);
        result.put("reason", request.reason);
        result.put("requestedAt", request.requestedAt.toString());

        if ("completed".equals(request.status)) {
            result.put("completionNote", "All specified data has been permanently deleted");
            result.put("certificateId", "cert_" + request.deletionId);
        }
        return result;
    }

    /**
     * 数据删除审计日志。
     */
    public List<Map<String, Object>> getDeletionAuditLog(int limit) {
        return deletionRequests.values().stream()
                .sorted(Comparator.comparing(r -> r.requestedAt, Comparator.reverseOrder()))
                .limit(limit)
                .map(r -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("deletionId", r.deletionId);
                    m.put("userId", r.userId);
                    m.put("status", r.status);
                    m.put("dataCategories", r.dataCategories);
                    m.put("reason", r.reason);
                    m.put("requestedAt", r.requestedAt.toString());
                    return m;
                })
                .collect(java.util.stream.Collectors.toList());
    }

    // ==================== 合规报告 ====================

    /**
     * 生成数据治理合规报告。
     */
    public Map<String, Object> generateComplianceReport() {
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("generatedAt", Instant.now().toString());
        report.put("framework", "GDPR + PIPL (个人信息保护法)");

        // 策略统计
        report.put("lifecyclePoliciesCount", lifecyclePolicies.size());
        report.put("retentionRulesCount", retentionRules.size());

        // 请求统计
        long pendingExports = exportRequests.values().stream()
                .filter(r -> "pending".equals(r.status)).count();
        long completedExports = exportRequests.values().stream()
                .filter(r -> "completed".equals(r.status)).count();
        long pendingDeletions = deletionRequests.values().stream()
                .filter(r -> "pending".equals(r.status)).count();
        long completedDeletions = deletionRequests.values().stream()
                .filter(r -> "completed".equals(r.status)).count();

        report.put("exportRequests", Map.of(
                "pending", pendingExports,
                "completed", completedExports
        ));
        report.put("deletionRequests", Map.of(
                "pending", pendingDeletions,
                "completed", completedDeletions
        ));

        // 合规状态
        report.put("complianceStatus", pendingDeletions == 0 ? "compliant" : "attention_required");

        return report;
    }

    // ==================== 内部类 ====================

    static class LifecyclePolicy {
        final String dataCategory;
        final int retentionDays;      // -1 = permanent
        final String storageTier;     // HOT/WARM/COLD/ARCHIVE
        final int anonymizeAfterDays; // 0 = never

        LifecyclePolicy(String dataCategory, int retentionDays, String storageTier,
                        int anonymizeAfterDays) {
            this.dataCategory = dataCategory;
            this.retentionDays = retentionDays;
            this.storageTier = storageTier;
            this.anonymizeAfterDays = anonymizeAfterDays;
        }
    }

    static class RetentionRule {
        final String ruleId;
        final String dataType;
        final int hotDays;
        final int warmDays;
        final int coldDays;
        final boolean archiveEnabled;

        RetentionRule(String ruleId, String dataType, int hotDays, int warmDays,
                      int coldDays, boolean archiveEnabled) {
            this.ruleId = ruleId;
            this.dataType = dataType;
            this.hotDays = hotDays;
            this.warmDays = warmDays;
            this.coldDays = coldDays;
            this.archiveEnabled = archiveEnabled;
        }
    }

    static class DataExportRequest {
        final String exportId;
        final String userId;
        final List<String> dataCategories;
        final String exportFormat;
        final String status;
        final Instant requestedAt;

        DataExportRequest(String exportId, String userId, List<String> dataCategories,
                          String exportFormat, String status) {
            this.exportId = exportId;
            this.userId = userId;
            this.dataCategories = dataCategories;
            this.exportFormat = exportFormat;
            this.status = status;
            this.requestedAt = Instant.now();
        }
    }

    static class DataDeletionRequest {
        final String deletionId;
        final String userId;
        final List<String> dataCategories;
        final String reason;
        final String status;
        final Instant requestedAt;

        DataDeletionRequest(String deletionId, String userId, List<String> dataCategories,
                            String reason, String status) {
            this.deletionId = deletionId;
            this.userId = userId;
            this.dataCategories = dataCategories;
            this.reason = reason;
            this.status = status;
            this.requestedAt = Instant.now();
        }
    }
}
