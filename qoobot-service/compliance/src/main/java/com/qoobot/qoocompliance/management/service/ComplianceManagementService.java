package com.qoobot.qoocompliance.management.service;

import com.qoobot.qoocompliance.domain.CertificationProgress;
import com.qoobot.qoocompliance.domain.ComplianceReview;
import com.qoobot.qoocompliance.repository.CertificationProgressRepository;
import com.qoobot.qoocompliance.repository.ComplianceReviewRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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

    private final CertificationProgressRepository certRepo;
    private final ComplianceReviewRepository reviewRepo;

    public ComplianceManagementService(CertificationProgressRepository certRepo,
                                        ComplianceReviewRepository reviewRepo) {
        this.certRepo = certRepo;
        this.reviewRepo = reviewRepo;
    }

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

    @Transactional
    public CertProgress createCertProgress(String productId, CertProgressRequest request) {
        CertificationProgress entity = new CertificationProgress();
        entity.setProductId(productId);
        entity.setCertType(request.certificationName());
        entity.setMarket(request.targetMarket());
        entity.setStatus("INITIATED");
        entity.setNotes("{\"targetDate\":\"" + request.targetDate() + "\",\"milestones\":[]}");

        CertificationProgress saved = certRepo.save(entity);
        return new CertProgress(
                saved.getId().toString(), productId, request.certificationName(),
                request.targetMarket(), request.targetDate(),
                "INITIATED", 0, 0, Instant.now()
        );
    }

    @Transactional
    public CertProgress updateCertMilestone(String trackingId, MilestoneUpdate update) {
        Long id = Long.parseLong(trackingId);
        Optional<CertificationProgress> opt = certRepo.findById(id);
        if (opt.isEmpty()) return null;

        CertificationProgress entity = opt.get();

        // Update status if the update contains a different status
        if (update.status() != null && !update.status().isEmpty()) {
            entity.setStatus(update.status());
        }

        // Append milestone info to notes as JSON
        String notes = entity.getNotes();
        if (notes == null) notes = "{\"milestones\":[]}";

        // Simple JSON manipulation: append milestone to the milestones array
        String milestoneJson = String.format(
                "{\"name\":\"%s\",\"description\":\"%s\",\"targetDate\":\"%s\",\"completedDate\":\"%s\",\"status\":\"%s\"}",
                escapeJson(update.name()), escapeJson(update.description()),
                escapeJson(update.targetDate()), escapeJson(update.completedDate()),
                escapeJson(update.status())
        );

        if (notes.contains("\"milestones\":[")) {
            int insertPos = notes.indexOf("\"milestones\":[") + "\"milestones\":[".length();
            String prefix = notes.substring(0, insertPos);
            String suffix = notes.substring(insertPos);
            String comma = suffix.trim().startsWith("]") ? "" : ",";
            notes = prefix + comma + milestoneJson + suffix;
        } else {
            notes = "{\"milestones\":[" + milestoneJson + "]}";
        }
        entity.setNotes(notes);

        CertificationProgress saved = certRepo.save(entity);

        // Parse milestone count from notes for the DTO
        int totalMilestones = countJsonArrayElements(saved.getNotes(), "milestones");
        int completedMilestones = countCompletedMilestones(saved.getNotes());

        return new CertProgress(
                saved.getId().toString(), saved.getProductId(),
                saved.getCertType(), saved.getMarket(),
                extractTargetDate(saved.getNotes()),
                saved.getStatus(), completedMilestones, totalMilestones,
                toInstant(saved.getUpdatedAt())
        );
    }

    public List<CertProgress> getProductCertifications(String productId) {
        return certRepo.findByProductId(productId).stream()
                .map(this::toDto)
                .toList();
    }

    public CertProgress getCertProgress(String trackingId) {
        Long id = Long.parseLong(trackingId);
        return certRepo.findById(id).map(this::toDto).orElse(null);
    }

    // ===================================================================
    // Compliance Review Records
    // ===================================================================

    @Transactional
    public ReviewRecord createReview(String productId, ReviewRequest request) {
        ComplianceReview entity = new ComplianceReview();
        entity.setProductId(productId);
        entity.setReviewType(request.reviewType());
        entity.setReviewerName(request.reviewer());
        entity.setStatus(request.status());

        // Store severity as prefix in findings, append recommendations
        String combinedFindings = "[" + request.severity() + "] " + request.findings();
        if (request.recommendations() != null && !request.recommendations().isEmpty()) {
            combinedFindings += " | Recommendations: " + request.recommendations();
        }
        entity.setFindings(combinedFindings);

        ComplianceReview saved = reviewRepo.save(entity);
        return new ReviewRecord(
                saved.getId().toString(), saved.getProductId(), saved.getReviewType(),
                saved.getReviewerName(), request.findings(), request.recommendations(),
                request.severity(), saved.getStatus(),
                toInstant(saved.getCreatedAt())
        );
    }

    public List<ReviewRecord> getProductReviews(String productId, String status) {
        List<ComplianceReview> entities;
        if (status != null && !status.isEmpty()) {
            entities = reviewRepo.findByProductIdAndStatus(productId, status);
        } else {
            entities = reviewRepo.findByProductId(productId);
        }
        return entities.stream().map(this::toDto).toList();
    }

    @Transactional
    public ReviewRecord updateReviewStatus(String productId, String reviewId, String status) {
        Long id = Long.parseLong(reviewId);
        Optional<ComplianceReview> opt = reviewRepo.findById(id);
        if (opt.isEmpty()) return null;

        ComplianceReview entity = opt.get();
        // Verify productId matches
        if (!entity.getProductId().equals(productId)) return null;

        entity.setStatus(status);
        ComplianceReview saved = reviewRepo.save(entity);
        return toDto(saved);
    }

    public ReviewSummary getReviewSummary(String productId) {
        List<ComplianceReview> reviews = reviewRepo.findByProductId(productId);
        long totalReviews = reviews.size();
        long openReviews = reviews.stream().filter(r -> "OPEN".equals(r.getStatus())).count();
        long resolvedReviews = reviews.stream().filter(r -> "RESOLVED".equals(r.getStatus())).count();
        long criticalOpen = reviews.stream()
                .filter(r -> "OPEN".equals(r.getStatus())
                        && r.getFindings() != null
                        && r.getFindings().startsWith("[CRITICAL]"))
                .count();

        return new ReviewSummary(
                productId, (int) totalReviews, openReviews,
                resolvedReviews, criticalOpen, Instant.now()
        );
    }

    // ===================================================================
    // Compliance Dashboard
    // ===================================================================

    public ComplianceDashboard getDashboard(String productId) {
        ComplianceDashboard dashboard = new ComplianceDashboard();
        dashboard.setProductId(productId);
        dashboard.setTemplatesAvailable(getTemplates(null).size());

        List<CertificationProgress> certs = certRepo.findByProductId(productId);
        dashboard.setActiveCertifications(certs.size());
        dashboard.setCompletedCertifications(
                (int) certs.stream().filter(c -> "COMPLETED".equals(c.getStatus())).count());

        ReviewSummary summary = getReviewSummary(productId);
        dashboard.setOpenReviews(summary.openReviews());
        dashboard.setCriticalFindings(summary.criticalOpen());

        dashboard.setLastUpdated(Instant.now());
        return dashboard;
    }

    // ===================================================================
    // Entity → DTO Conversion
    // ===================================================================

    private CertProgress toDto(CertificationProgress entity) {
        int totalMilestones = countJsonArrayElements(entity.getNotes(), "milestones");
        int completedMilestones = countCompletedMilestones(entity.getNotes());
        String targetDate = extractTargetDate(entity.getNotes());

        return new CertProgress(
                entity.getId().toString(),
                entity.getProductId(),
                entity.getCertType(),
                entity.getMarket(),
                targetDate,
                entity.getStatus(),
                completedMilestones,
                totalMilestones,
                toInstant(entity.getUpdatedAt())
        );
    }

    private ReviewRecord toDto(ComplianceReview entity) {
        // Parse severity from findings prefix like "[CRITICAL] actual findings | Recommendations: ..."
        String severity = "MEDIUM";
        String actualFindings = entity.getFindings();
        String recommendations = "";

        if (entity.getFindings() != null) {
            Pattern severityPattern = Pattern.compile("^\\[(\\w+)\\]\\s*(.*)");
            Matcher matcher = severityPattern.matcher(entity.getFindings());
            if (matcher.find()) {
                severity = matcher.group(1);
                String remaining = matcher.group(2);
                // Split findings from recommendations
                int recIndex = remaining.indexOf(" | Recommendations: ");
                if (recIndex >= 0) {
                    actualFindings = remaining.substring(0, recIndex);
                    recommendations = remaining.substring(recIndex + " | Recommendations: ".length());
                } else {
                    actualFindings = remaining;
                }
            }
        }

        return new ReviewRecord(
                entity.getId().toString(),
                entity.getProductId(),
                entity.getReviewType(),
                entity.getReviewerName(),
                actualFindings,
                recommendations,
                severity,
                entity.getStatus(),
                toInstant(entity.getCreatedAt())
        );
    }

    // ===================================================================
    // Helper methods
    // ===================================================================

    private static Instant toInstant(LocalDateTime ldt) {
        return ldt != null ? ldt.toInstant(ZoneOffset.UTC) : Instant.now();
    }

    private static String escapeJson(String s) {
        if (s == null) return "";
        return s.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static int countJsonArrayElements(String json, String arrayKey) {
        if (json == null) return 0;
        String searchKey = "\"" + arrayKey + "\":[";
        int startIdx = json.indexOf(searchKey);
        if (startIdx < 0) return 0;

        String sub = json.substring(startIdx + searchKey.length());
        int bracketIdx = sub.indexOf("]");
        if (bracketIdx < 0) return 0;

        String arrayContent = sub.substring(0, bracketIdx).trim();
        if (arrayContent.isEmpty()) return 0;

        // Count by "name" occurrences (each milestone has a "name" field)
        int count = 0;
        int idx = 0;
        while ((idx = arrayContent.indexOf("\"name\"", idx)) >= 0) {
            count++;
            idx += "\"name\"".length();
        }
        return count;
    }

    private static int countCompletedMilestones(String json) {
        if (json == null) return 0;
        int count = 0;
        int idx = 0;
        while ((idx = json.indexOf("\"status\":\"COMPLETED\"", idx)) >= 0) {
            count++;
            idx += "\"status\":\"COMPLETED\"".length();
        }
        return count;
    }

    private static String extractTargetDate(String json) {
        if (json == null) return null;
        int idx = json.indexOf("\"targetDate\":\"");
        if (idx < 0) return null;
        int start = idx + "\"targetDate\":\"".length();
        int end = json.indexOf("\"", start);
        return end > start ? json.substring(start, end) : null;
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
