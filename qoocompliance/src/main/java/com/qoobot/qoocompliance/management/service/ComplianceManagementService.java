package com.qoobot.qoocompliance.management.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

/**
 * Compliance Management supplement service.
 *
 * Covers:
 * - Technical documentation templates
 * - Certification progress tracking
 * - Compliance review records
 */
@Service
public class ComplianceManagementService {

    // ===================================================================
    // Technical Documentation Templates
    // ===================================================================

    public List<DocTemplate> getTemplates(String market) {
        List<DocTemplate> templates = new ArrayList<>();

        if (market == null || "EU".equals(market)) {
            templates.add(new DocTemplate("TCF-EU", "技术构造文件 (TCF)",
                    "EU", "CE 机械指令 Annex VII 要求的技术文件",
                    "DOCX", List.of("产品描述", "设计图纸", "风险评估", "协调标准清单",
                    "测试报告", "EC 符合性声明", "使用说明书")));
            templates.add(new DocTemplate("DOP-EU", "EC 符合性声明 (DoC)",
                    "EU", "CE 标识符合性声明模板",
                    "DOCX", List.of("制造商信息", "产品标识", "适用指令与标准",
                    "授权代表信息", "签署信息")));
            templates.add(new DocTemplate("GDPR-DPIA", "DPIA 模板",
                    "EU", "GDPR 数据保护影响评估模板",
                    "DOCX", List.of("处理活动描述", "必要性比例性评估",
                    "风险识别与评估", "缓解措施", "残余风险")));
            templates.add(new DocTemplate("AIA-TD", "EU AI Act 技术文档",
                    "EU", "高风险 AI 系统技术文档模板 (Annex IV)",
                    "DOCX", List.of("系统描述", "设计规格", "开发过程",
                    "性能指标", "风险管理", "合规评估")));
        }

        if (market == null || "US".equals(market)) {
            templates.add(new DocTemplate("FCC-SDOC", "FCC SDoC 声明",
                    "US", "FCC 供应商符合性声明",
                    "DOCX", List.of("责任方信息", "产品标识", "符合标准",
                    "测试实验室", "签署信息")));
            templates.add(new DocTemplate("UL-TR", "UL 测试报告",
                    "US", "UL 认证测试报告模板",
                    "DOCX", List.of("产品描述", "测试标准", "测试结果",
                    "结构检查", "关键元器件清单")));
        }

        if (market == null || "CN".equals(market)) {
            templates.add(new DocTemplate("SRRC-APP", "SRRC 型号核准申请表",
                    "CN", "中国无线电发射设备型号核准申请材料清单",
                    "DOCX", List.of("申请表", "技术规格书", "电路图",
                    "方框图", "天线规格", "用户手册")));
            templates.add(new DocTemplate("CCC-APP", "CCC 认证申请",
                    "CN", "中国强制性产品认证申请模板",
                    "DOCX", List.of("申请书", "产品描述", "关键元器件",
                    "工厂检查", "型式试验报告")));
            templates.add(new DocTemplate("PIPL-PIA", "个人信息保护影响评估",
                    "CN", "PIPL 要求的个人信息保护影响评估模板",
                    "DOCX", List.of("处理目的方式", "必要性评估",
                    "风险分析", "保护措施", "评估结论")));
        }

        if (market == null || "JP".equals(market)) {
            templates.add(new DocTemplate("MIC-TR", "MIC 技术基准适合证明",
                    "JP", "日本技适认证技术文档模板",
                    "DOCX", List.of("申请书", "技术基准确认表",
                    "测试报告", "外观照片", "方框图")));
        }

        return templates;
    }

    // ===================================================================
    // Certification Progress Tracking
    // ===================================================================

    private final Map<String, CertProgress> progressStore = new HashMap<>();

    public CertProgress createCertProgress(String productId, CertProgressRequest request) {
        CertProgress progress = new CertProgress(
                UUID.randomUUID().toString(), productId, request.certificationName(),
                request.targetMarket(), request.targetDate(),
                "INITIATED", 0, 0, Instant.now()
        );
        progressStore.put(progress.trackingId(), progress);
        return progress;
    }

    public CertProgress updateCertMilestone(String trackingId, MilestoneUpdate update) {
        CertProgress progress = progressStore.get(trackingId);
        if (progress == null) return null;

        List<CertProgress.Milestone> updatedMilestones = new ArrayList<>(progress.milestones());
        updatedMilestones.add(new CertProgress.Milestone(
                update.name(), update.description(), update.targetDate(),
                update.completedDate(), update.status()
        ));

        int completed = (int) updatedMilestones.stream().filter(m -> "COMPLETED".equals(m.status())).count();

        CertProgress updated = new CertProgress(
                progress.trackingId(), progress.productId(), progress.certificationName(),
                progress.targetMarket(), progress.targetDate(),
                completed == updatedMilestones.size() ? "COMPLETED" : "IN_PROGRESS",
                completed, updatedMilestones.size(), Instant.now()
        );

        progressStore.put(trackingId, updated);
        return updated;
    }

    public List<CertProgress> getProductCertifications(String productId) {
        return progressStore.values().stream()
                .filter(p -> p.productId().equals(productId))
                .toList();
    }

    public CertProgress getCertProgress(String trackingId) {
        return progressStore.get(trackingId);
    }

    // ===================================================================
    // Compliance Review Records
    // ===================================================================

    private final Map<String, List<ReviewRecord>> reviewStore = new HashMap<>();

    public ReviewRecord createReview(String productId, ReviewRequest request) {
        ReviewRecord record = new ReviewRecord(
                UUID.randomUUID().toString(), productId, request.reviewType(),
                request.reviewer(), request.findings(), request.recommendations(),
                request.severity(), request.status(), Instant.now()
        );
        reviewStore.computeIfAbsent(productId, k -> new ArrayList<>()).add(record);
        return record;
    }

    public List<ReviewRecord> getProductReviews(String productId, String status) {
        List<ReviewRecord> records = reviewStore.getOrDefault(productId, List.of());
        if (status != null) {
            records = records.stream().filter(r -> r.status().equals(status)).toList();
        }
        return records;
    }

    public ReviewRecord updateReviewStatus(String productId, String reviewId, String status) {
        List<ReviewRecord> records = reviewStore.get(productId);
        if (records == null) return null;

        for (int i = 0; i < records.size(); i++) {
            if (records.get(i).reviewId().equals(reviewId)) {
                ReviewRecord old = records.get(i);
                ReviewRecord updated = new ReviewRecord(
                        old.reviewId(), old.productId(), old.reviewType(),
                        old.reviewer(), old.findings(), old.recommendations(),
                        old.severity(), status, Instant.now()
                );
                records.set(i, updated);
                return updated;
            }
        }
        return null;
    }

    public ReviewSummary getReviewSummary(String productId) {
        List<ReviewRecord> records = reviewStore.getOrDefault(productId, List.of());
        return new ReviewSummary(
                productId,
                records.size(),
                records.stream().filter(r -> "OPEN".equals(r.status())).count(),
                records.stream().filter(r -> "RESOLVED".equals(r.status())).count(),
                records.stream().filter(r -> "CRITICAL".equals(r.severity()) && "OPEN".equals(r.status())).count(),
                Instant.now()
        );
    }

    // ===================================================================
    // Compliance Dashboard
    // ===================================================================

    public ComplianceDashboard getDashboard(String productId) {
        ComplianceDashboard dashboard = new ComplianceDashboard();
        dashboard.setProductId(productId);
        dashboard.setTemplatesAvailable(getTemplates(null).size());

        List<CertProgress> certs = getProductCertifications(productId);
        dashboard.setActiveCertifications(certs.size());
        dashboard.setCompletedCertifications(
                (int) certs.stream().filter(c -> "COMPLETED".equals(c.status())).count());

        ReviewSummary summary = getReviewSummary(productId);
        dashboard.setOpenReviews(summary.openReviews());
        dashboard.setCriticalFindings(summary.criticalOpen());

        dashboard.setLastUpdated(Instant.now());
        return dashboard;
    }

    // ===================================================================
    // DTOs
    // ===================================================================

    public record DocTemplate(String templateId, String name, String market,
                               String description, String format,
                               List<String> sections) {}

    public record CertProgress(String trackingId, String productId, String certificationName,
                                String targetMarket, String targetDate, String status,
                                int completedMilestones, int totalMilestones,
                                Instant lastUpdated) {
        public record Milestone(String name, String description, String targetDate,
                                 String completedDate, String status) {}
    }

    public record CertProgressRequest(String certificationName, String targetMarket,
                                       String targetDate) {}

    public record MilestoneUpdate(String name, String description, String targetDate,
                                   String completedDate, String status) {}

    public record ReviewRecord(String reviewId, String productId, String reviewType,
                                String reviewer, String findings, String recommendations,
                                String severity, String status, Instant createdAt) {}

    public record ReviewRequest(String reviewType, String reviewer, String findings,
                                 String recommendations, String severity, String status) {}

    public record ReviewSummary(String productId, int totalReviews, long openReviews,
                                 long resolvedReviews, long criticalOpen, Instant generatedAt) {}

    public static class ComplianceDashboard {
        private String productId;
        private int templatesAvailable;
        private int activeCertifications;
        private int completedCertifications;
        private long openReviews;
        private long criticalFindings;
        private Instant lastUpdated;

        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public int getTemplatesAvailable() { return templatesAvailable; }
        public void setTemplatesAvailable(int t) { this.templatesAvailable = t; }
        public int getActiveCertifications() { return activeCertifications; }
        public void setActiveCertifications(int a) { this.activeCertifications = a; }
        public int getCompletedCertifications() { return completedCertifications; }
        public void setCompletedCertifications(int c) { this.completedCertifications = c; }
        public long getOpenReviews() { return openReviews; }
        public void setOpenReviews(long o) { this.openReviews = o; }
        public long getCriticalFindings() { return criticalFindings; }
        public void setCriticalFindings(long c) { this.criticalFindings = c; }
        public Instant getLastUpdated() { return lastUpdated; }
        public void setLastUpdated(Instant t) { this.lastUpdated = t; }
    }
}
