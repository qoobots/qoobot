package com.qoobot.qoocompliance.trade.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

/**
 * Export Control & Trade Compliance service.
 *
 * Covers:
 * - ECCN classification (US Export Administration Regulations)
 * - Encryption export declaration
 * - Entity list screening
 * - Sanctions compliance (OFAC/EU/UN)
 */
@Service
public class ExportControlService {

    // ===================================================================
    // ECCN Classification (US EAR)
    // ===================================================================

    public ECCNReport classifyECCN(String productId, ECCNRequest request) {
        ECCNReport report = new ECCNReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<ECCNCheck> checks = new ArrayList<>();

        // Determine if subject to EAR
        checks.add(new ECCNCheck("ECCN-JUR-001", "EAR 管辖权判定",
                "判断产品是否受 EAR 管辖",
                request.isSubjectToEAR() ? "受 EAR 管辖" : "不受 EAR 管辖", "P0"));

        // Category determination
        String category = determineCategory(request);
        checks.add(new ECCNCheck("ECCN-CAT-001", "CCL 类别判断",
                String.format("产品属于 CCL Category %s", category),
                "COMPLETED", "P0"));

        // Product group
        String productGroup = determineProductGroup(request);
        checks.add(new ECCNCheck("ECCN-PRG-001", "产品组判断",
                String.format("产品属于 Product Group %s", productGroup),
                "COMPLETED", "P0"));

        // ECCN derivation
        String eccn = deriveECCN(category, productGroup, request);
        checks.add(new ECCNCheck("ECCN-ECCN-001", "ECCN 分类结果",
                String.format("ECCN: %s", eccn),
                "COMPLETED", "P0"));

        // Reason for control
        List<String> controls = determineControls(eccn, request);
        checks.add(new ECCNCheck("ECCN-CTL-001", "管控原因",
                String.join(", ", controls),
                "COMPLETED", "P0"));

        // License determination
        boolean licenseRequired = !controls.isEmpty();
        checks.add(new ECCNCheck("ECCN-LIC-001", "许可证要求",
                licenseRequired ? "需要出口许可证" : "一般无需许可证 (NLR)",
                licenseRequired ? "FLAG" : "PASS", "P0"));

        // License exceptions
        if (licenseRequired) {
            List<String> exceptions = findLicenseExceptions(eccn, request);
            checks.add(new ECCNCheck("ECCN-EXC-001", "许可证例外",
                    exceptions.isEmpty() ? "无适用例外" : String.join(", ", exceptions),
                    exceptions.isEmpty() ? "WARN" : "PASS", "P0"));
        }

        report.setEccn(eccn);
        report.setChecks(checks);
        report.setLicenseRequired(licenseRequired);
        return report;
    }

    // ===================================================================
    // Encryption Export Declaration
    // ===================================================================

    public EncryptionReport assessEncryption(String productId, EncryptionRequest request) {
        EncryptionReport report = new EncryptionReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<EncryptionCheck> checks = new ArrayList<>();

        // Classification under Category 5 Part 2
        checks.add(new EncryptionCheck("ENC-CAT-001", "加密分类",
                "产品是否属于 Category 5 Part 2 (信息安全和加密)",
                request.isCat5Part2() ? "CAT5P2" : "NOT_CAT5P2", "P0"));

        // Mass market eligibility
        checks.add(new EncryptionCheck("ENC-MKT-001", "大众市场资格",
                "加密功能是否为大众市场产品标准功能",
                request.isMassMarket() ? "ELIGIBLE" : "NOT_ELIGIBLE", "P0"));

        // Encryption Registration (ENC)
        checks.add(new EncryptionCheck("ENC-REG-001", "加密注册 (ENC)",
                "BIS 加密注册 (半年度销售报告)",
                request.hasENCRegistration() ? "REGISTERED" : "NOT_REGISTERED", "P0"));

        // CCATS (if needed)
        checks.add(new EncryptionCheck("ENC-CAT-001", "CCATS 申请",
                "商品分类自动化追踪系统申请",
                request.hasCCATS() ? "SUBMITTED" : "NOT_REQUIRED", "P1"));

        // Self-classification report
        checks.add(new EncryptionCheck("ENC-SCR-001", "自分类报告",
                "加密商品自分类报告 (Supplement No. 8 to Part 742)",
                request.hasSelfClassification() ? "COMPLETED" : "PENDING", "P0"));

        // De minimis / foreign-made
        checks.add(new EncryptionCheck("ENC-DEM-001", "De Minimis 规则",
                "含美国原产受控加密成分比例 < 25%",
                request.meetsDeMinimis() ? "MEETS" : "EXCEEDS", "P0"));

        // Wassenaar notification
        checks.add(new EncryptionCheck("ENC-WAS-001", "Wassenaar 通知",
                "瓦森纳安排加密出口通知",
                request.hasWassenaarNotification() ? "NOTIFIED" : "NOT_REQUIRED", "P1"));

        report.setChecks(checks);
        report.setOverallStatus(checks.stream().noneMatch(c ->
                "NOT_REGISTERED".equals(c.result()) || "EXCEEDS".equals(c.result()))
                ? "COMPLIANT" : "ACTION_REQUIRED");
        return report;
    }

    // ===================================================================
    // Entity List Screening
    // ===================================================================

    public ScreeningReport screenEntities(String productId, ScreeningRequest request) {
        ScreeningReport report = new ScreeningReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<ScreeningResult> results = new ArrayList<>();

        // BIS Entity List
        results.add(screenAgainstList(request.parties(), "BIS Entity List",
                "美国商务部实体清单", "P0"));

        // BIS Denied Persons List
        results.add(screenAgainstList(request.parties(), "BIS Denied Persons List",
                "美国商务部被拒人员名单", "P0"));

        // BIS Unverified List
        results.add(screenAgainstList(request.parties(), "BIS Unverified List",
                "美国商务部未经核实名单", "P0"));

        // OFAC SDN List
        results.add(screenAgainstList(request.parties(), "OFAC SDN List",
                "美国财政部特别指定国民名单", "P0"));

        // EU Consolidated Sanctions List
        results.add(screenAgainstList(request.parties(), "EU Sanctions List",
                "欧盟综合制裁名单", "P1"));

        // UN Sanctions List
        results.add(screenAgainstList(request.parties(), "UN Sanctions List",
                "联合国制裁名单", "P1"));

        // China Unreliable Entity List
        results.add(screenAgainstList(request.parties(), "China UEL",
                "中国不可靠实体清单", "P1"));

        report.setResults(results);
        report.setHits(results.stream().filter(r -> r.hitCount() > 0).count());
        report.setRequiresAction(report.getHits() > 0);
        return report;
    }

    // ===================================================================
    // Sanctions Compliance
    // ===================================================================

    public SanctionsReport assessSanctions(String productId, SanctionsRequest request) {
        SanctionsReport report = new SanctionsReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<SanctionsCheck> checks = new ArrayList<>();

        // Destination control
        checks.add(new SanctionsCheck("SAN-DST-001", "目的地国家检查",
                String.format("目的地: %s", request.destinationCountry()),
                isSanctionedCountry(request.destinationCountry()) ? "BLOCKED" : "CLEAR",
                "P0"));

        // End-user screening
        checks.add(new SanctionsCheck("SAN-END-001", "最终用户审查",
                String.format("最终用户: %s", request.endUser()),
                request.endUserScreened() ? "CLEAR" : "UNSCREENED",
                "P0"));

        // End-use verification
        checks.add(new SanctionsCheck("SAN-USE-001", "最终用途核查",
                String.format("用途: %s", request.endUse()),
                isRestrictedEndUse(request.endUse()) ? "RESTRICTED" : "CLEAR",
                "P0"));

        // Comprehensive sanctions (Cuba, Iran, North Korea, Syria, Crimea)
        checks.add(new SanctionsCheck("SAN-EMB-001", "全面禁运国家",
                isComprehensivelyEmbargoed(request.destinationCountry()) ?
                        "EMBARGOED" : "NOT_EMBARGOED",
                isComprehensivelyEmbargoed(request.destinationCountry()) ? "BLOCKED" : "CLEAR",
                "P0"));

        // Military end-use/user (MEU)
        checks.add(new SanctionsCheck("SAN-MEU-001", "军事最终用途/用户",
                request.isMilitaryEndUse() ? "MEU_APPLIES" : "NOT_MEU",
                request.isMilitaryEndUse() ? "RESTRICTED" : "CLEAR",
                "P0"));

        // Russia/Belarus sanctions
        checks.add(new SanctionsCheck("SAN-RUS-001", "俄罗斯/白俄罗斯制裁",
                isRussiaBelarus(request.destinationCountry()) ? "SANCTIONED" : "NOT_SANCTIONED",
                isRussiaBelarus(request.destinationCountry()) ? "BLOCKED" : "CLEAR",
                "P0"));

        // Export control classification number check
        checks.add(new SanctionsCheck("SAN-ECCN-001", "ECCN 管控检查",
                String.format("ECCN: %s", request.eccn()),
                request.eccn().startsWith("EAR99") ? "CLEAR" : "REVIEW",
                "P0"));

        // OFAC 50% rule
        checks.add(new SanctionsCheck("SAN-OFAC-001", "OFAC 50% 规则",
                "被制裁实体持有 ≥50% 权益的实体同样受制裁",
                request.ofac50RuleChecked() ? "CHECKED" : "NOT_CHECKED",
                "P0"));

        report.setChecks(checks);
        report.setBlocked(checks.stream().anyMatch(c -> "BLOCKED".equals(c.result())));
        report.setRequiresLicense(checks.stream().anyMatch(c -> "RESTRICTED".equals(c.result()) || "REVIEW".equals(c.result())));
        return report;
    }

    // ===================================================================
    // Trade Compliance Dashboard
    // ===================================================================

    public TradeDashboard getDashboard(String productId) {
        TradeDashboard dashboard = new TradeDashboard();
        dashboard.setProductId(productId);

        dashboard.setComplianceAreas(List.of(
                new ComplianceArea("ECCN Classification", "出口管制分类编码", "NOT_STARTED"),
                new ComplianceArea("Encryption Export", "加密出口管制", "NOT_STARTED"),
                new ComplianceArea("Entity Screening", "实体清单审查", "NOT_STARTED"),
                new ComplianceArea("Sanctions", "制裁合规", "NOT_STARTED"),
                new ComplianceArea("Anti-boycott", "反抵制合规", "NOT_STARTED"),
                new ComplianceArea("Customs", "海关合规", "NOT_STARTED")
        ));

        dashboard.setLastUpdated(Instant.now());
        return dashboard;
    }

    // ===================================================================
    // Helpers
    // ===================================================================

    private String determineCategory(ECCNRequest request) {
        if (request.hasAIAccelerator()) return "3 (Electronics)";
        if (request.hasRobotics()) return "2 (Materials Processing)";
        return "4 (Computers)";
    }

    private String determineProductGroup(ECCNRequest request) {
        if (request.hasEncryption()) return "D (Software)";
        if (request.hasAIAccelerator()) return "A (Systems, Equipment, Components)";
        return "E (Technology)";
    }

    private String deriveECCN(String category, String productGroup, ECCNRequest request) {
        if (request.hasEncryption()) return "5D002";
        if (request.hasAIAccelerator()) return "3A090";
        if (request.hasRobotics()) return "2B999";
        return "EAR99";
    }

    private List<String> determineControls(String eccn, ECCNRequest request) {
        List<String> controls = new ArrayList<>();
        switch (eccn) {
            case "5D002":
                controls.add("NS1 (National Security)");
                controls.add("AT1 (Anti-Terrorism)");
                if (request.hasEncryption()) controls.add("EI (Encryption Item)");
                break;
            case "3A090":
                controls.add("RS (Regional Stability)");
                controls.add("AT1 (Anti-Terrorism)");
                break;
            case "2B999":
                controls.add("AT1 (Anti-Terrorism)");
                break;
            default:
                // EAR99 — no specific controls
                break;
        }
        return controls;
    }

    private List<String> findLicenseExceptions(String eccn, ECCNRequest request) {
        List<String> exceptions = new ArrayList<>();
        if ("5D002".equals(eccn) && request.isMassMarketEncryption()) {
            exceptions.add("ENC (Encryption Commodities, Software & Technology)");
        }
        if ("3A090".equals(eccn)) {
            exceptions.add("NAC (Notified Advanced Computing)");
        }
        return exceptions;
    }

    private ScreeningResult screenAgainstList(List<String> parties, String listName,
                                               String listDescription, String priority) {
        // Simulated screening — in production this would check against actual lists
        boolean hit = parties.stream().anyMatch(p ->
                p.toUpperCase().contains("SANCTIONED") ||
                        p.toUpperCase().contains("BLOCKED"));
        return new ScreeningResult(listName, listDescription, priority, hit ? 1 : 0,
                hit ? "HIT" : "CLEAR");
    }

    private boolean isSanctionedCountry(String country) {
        return Set.of("CU", "IR", "KP", "SY", "UA-CRIMEA").contains(country);
    }

    private boolean isComprehensivelyEmbargoed(String country) {
        return Set.of("CU", "IR", "KP", "SY").contains(country);
    }

    private boolean isRestrictedEndUse(String endUse) {
        return endUse.toUpperCase().contains("MILITARY") ||
                endUse.toUpperCase().contains("WEAPON") ||
                endUse.toUpperCase().contains("MISSILE") ||
                endUse.toUpperCase().contains("NUCLEAR");
    }

    private boolean isRussiaBelarus(String country) {
        return "RU".equals(country) || "BY".equals(country);
    }

    // ===================================================================
    // DTOs
    // ===================================================================

    public static class ECCNReport {
        private String reportId;
        private String productId;
        private Instant createdAt;
        private String eccn;
        private List<ECCNCheck> checks = new ArrayList<>();
        private boolean licenseRequired;

        public ECCNReport() {}
        public ECCNReport(String reportId, String productId, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public String getEccn() { return eccn; }
        public void setEccn(String e) { this.eccn = e; }
        public List<ECCNCheck> getChecks() { return checks; }
        public void setChecks(List<ECCNCheck> c) { this.checks = c; }
        public boolean isLicenseRequired() { return licenseRequired; }
        public void setLicenseRequired(boolean r) { this.licenseRequired = r; }
    }

    public record ECCNCheck(String checkId, String title, String description,
                             String result, String priority) {}

    public record ECCNRequest(boolean isSubjectToEAR, boolean hasAIAccelerator,
                               boolean hasRobotics, boolean hasEncryption,
                               boolean isMassMarketEncryption, boolean isDualUse) {}

    public static class EncryptionReport {
        private String reportId;
        private String productId;
        private Instant createdAt;
        private List<EncryptionCheck> checks = new ArrayList<>();
        private String overallStatus;

        public EncryptionReport() {}
        public EncryptionReport(String reportId, String productId, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<EncryptionCheck> getChecks() { return checks; }
        public void setChecks(List<EncryptionCheck> c) { this.checks = c; }
        public String getOverallStatus() { return overallStatus; }
        public void setOverallStatus(String s) { this.overallStatus = s; }
    }

    public record EncryptionCheck(String checkId, String title, String description,
                                   String result, String priority) {}

    public record EncryptionRequest(boolean isCat5Part2, boolean isMassMarket,
                                     boolean hasENCRegistration, boolean hasCCATS,
                                     boolean hasSelfClassification, boolean meetsDeMinimis,
                                     boolean hasWassenaarNotification) {}

    public static class ScreeningReport {
        private String reportId;
        private String productId;
        private Instant screenedAt;
        private List<ScreeningResult> results = new ArrayList<>();
        private long hits;
        private boolean requiresAction;

        public ScreeningReport() {}
        public ScreeningReport(String reportId, String productId, Instant screenedAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.screenedAt = screenedAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public Instant getScreenedAt() { return screenedAt; }
        public void setScreenedAt(Instant t) { this.screenedAt = t; }
        public List<ScreeningResult> getResults() { return results; }
        public void setResults(List<ScreeningResult> r) { this.results = r; }
        public long getHits() { return hits; }
        public void setHits(long h) { this.hits = h; }
        public boolean isRequiresAction() { return requiresAction; }
        public void setRequiresAction(boolean a) { this.requiresAction = a; }
    }

    public record ScreeningResult(String listName, String description, String priority,
                                   int hitCount, String result) {}

    public record ScreeningRequest(List<String> parties) {}

    public static class SanctionsReport {
        private String reportId;
        private String productId;
        private Instant createdAt;
        private List<SanctionsCheck> checks = new ArrayList<>();
        private boolean blocked;
        private boolean requiresLicense;

        public SanctionsReport() {}
        public SanctionsReport(String reportId, String productId, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<SanctionsCheck> getChecks() { return checks; }
        public void setChecks(List<SanctionsCheck> c) { this.checks = c; }
        public boolean isBlocked() { return blocked; }
        public void setBlocked(boolean b) { this.blocked = b; }
        public boolean isRequiresLicense() { return requiresLicense; }
        public void setRequiresLicense(boolean r) { this.requiresLicense = r; }
    }

    public record SanctionsCheck(String checkId, String title, String description,
                                  String result, String priority) {}

    public record SanctionsRequest(String destinationCountry, String endUser,
                                    boolean endUserScreened, String endUse, String eccn,
                                    boolean isMilitaryEndUse, boolean ofac50RuleChecked) {}

    public static class TradeDashboard {
        private String productId;
        private List<ComplianceArea> complianceAreas = new ArrayList<>();
        private Instant lastUpdated;

        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public List<ComplianceArea> getComplianceAreas() { return complianceAreas; }
        public void setComplianceAreas(List<ComplianceArea> a) { this.complianceAreas = a; }
        public Instant getLastUpdated() { return lastUpdated; }
        public void setLastUpdated(Instant t) { this.lastUpdated = t; }
    }

    public record ComplianceArea(String area, String description, String status) {}
}
