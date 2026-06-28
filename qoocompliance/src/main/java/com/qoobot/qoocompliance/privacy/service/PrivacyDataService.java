package com.qoobot.qoocompliance.privacy.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

/**
 * Privacy & Data Protection compliance service.
 *
 * Covers:
 * - GDPR compliance (EU)
 * - CCPA/CPRA compliance (US)
 * - PIPL compliance (China)
 * - DPIA (Data Protection Impact Assessment)
 * - Sensor privacy (camera/mic/LiDAR data handling)
 * - Cross-border data transfer
 * - Data minimization
 * - Data subject rights management
 */
@Service
public class PrivacyDataService {

    // ===================================================================
    // GDPR Compliance Assessment
    // ===================================================================

    public PrivacyAssessment assessGDPR(String productId, PrivacyRequest request) {
        PrivacyAssessment assessment = new PrivacyAssessment(
                UUID.randomUUID().toString(), productId, "GDPR",
                "欧盟通用数据保护条例 GDPR", "IN_PROGRESS", Instant.now()
        );

        List<PrivacyCheck> checks = new ArrayList<>();

        // Lawful basis
        checks.add(new PrivacyCheck("GDPR-LAW-001", "数据处理合法性基础",
                "明确至少一个合法性基础 (同意/合同/法定义务/合法权益)",
                evaluate(request.hasLawfulBasis()), "P0"));
        checks.add(new PrivacyCheck("GDPR-CON-001", "同意管理",
                "用户同意自由给予、具体、知情、明确 (GDPR Art.7)",
                evaluate(request.hasConsentManagement()), "P0"));
        checks.add(new PrivacyCheck("GDPR-CON-002", "同意撤回",
                "用户可随时撤回同意，与给予同意一样简单",
                evaluate(request.hasConsentWithdrawal()), "P1"));

        // Data subject rights
        checks.add(new PrivacyCheck("GDPR-RTS-001", "访问权 (Art.15)",
                "用户可请求访问其个人数据",
                evaluate(request.hasAccessRight()), "P0"));
        checks.add(new PrivacyCheck("GDPR-RTS-002", "删除权/被遗忘权 (Art.17)",
                "用户可请求删除其个人数据",
                evaluate(request.hasErasureRight()), "P0"));
        checks.add(new PrivacyCheck("GDPR-RTS-003", "数据可携带权 (Art.20)",
                "用户可导出结构化机器可读格式数据",
                evaluate(request.hasPortabilityRight()), "P1"));
        checks.add(new PrivacyCheck("GDPR-RTS-004", "限制处理权 (Art.18)",
                "用户可限制其数据处理",
                evaluate(request.hasRestrictionRight()), "P1"));
        checks.add(new PrivacyCheck("GDPR-RTS-005", "反对权 (Art.21)",
                "用户可反对直接营销/自动化决策",
                evaluate(request.hasObjectionRight()), "P1"));

        // Transparency
        checks.add(new PrivacyCheck("GDPR-TRN-001", "隐私通知",
                "简洁、透明、易懂的隐私政策 (Art.12-14)",
                evaluate(request.hasPrivacyNotice()), "P0"));
        checks.add(new PrivacyCheck("GDPR-TRN-002", "数据处理记录",
                "维护数据处理活动记录 RoPA (Art.30)",
                evaluate(request.hasRopa()), "P1"));

        // Data Protection by Design
        checks.add(new PrivacyCheck("GDPR-DPD-001", "数据保护设计 (Art.25)",
                "从设计阶段嵌入数据保护措施",
                evaluate(request.hasPrivacyByDesign()), "P0"));
        checks.add(new PrivacyCheck("GDPR-DPD-002", "数据最小化",
                "仅收集处理目的所需最少数据",
                evaluate(request.hasDataMinimization()), "P0"));
        checks.add(new PrivacyCheck("GDPR-DPD-003", "存储限制",
                "制定数据保留策略和自动删除机制",
                evaluate(request.hasRetentionPolicy()), "P1"));

        // Security
        checks.add(new PrivacyCheck("GDPR-SEC-001", "技术安全措施",
                "加密/假名化/访问控制/日志记录 (Art.32)",
                evaluate(request.hasTechnicalSecurity()), "P0"));
        checks.add(new PrivacyCheck("GDPR-SEC-002", "数据泄露通知",
                "72小时内通知监管机构 (Art.33-34)",
                evaluate(request.hasBreachNotification()), "P0"));

        // DPO & DPA
        checks.add(new PrivacyCheck("GDPR-DPO-001", "数据保护官 (DPO)",
                "是否需任命 DPO 并已任命 (Art.37)",
                evaluate(request.hasDPO()), "P0"));
        checks.add(new PrivacyCheck("GDPR-DPA-001", "数据处理协议 (DPA)",
                "与数据处理者签署 DPA (Art.28)",
                evaluate(request.hasDPA()), "P0"));

        // Cross-border transfer
        checks.add(new PrivacyCheck("GDPR-XFR-001", "跨境数据传输",
                "使用 SCC/BCR/充分性认定 (Art.44-49)",
                evaluate(request.hasCrossBorderSafeguard()), "P0"));
        checks.add(new PrivacyCheck("GDPR-XFR-002", "传输影响评估 (TIA)",
                "对第三国法律环境进行传输影响评估",
                evaluate(request.hasTIA()), "P1"));

        assessment.setChecks(checks);
        assessment.setOverallResult(computeOverall(checks));
        return assessment;
    }

    // ===================================================================
    // CCPA/CPRA Compliance
    // ===================================================================

    public PrivacyAssessment assessCCPA(String productId, PrivacyRequest request) {
        PrivacyAssessment assessment = new PrivacyAssessment(
                UUID.randomUUID().toString(), productId, "CCPA",
                "加州消费者隐私法案 CCPA/CPRA", "IN_PROGRESS", Instant.now()
        );

        List<PrivacyCheck> checks = new ArrayList<>();

        checks.add(new PrivacyCheck("CCPA-NOT-001", "收集通知",
                "收集时或收集前告知消费者个人信息类别和使用目的",
                evaluate(request.hasPrivacyNotice()), "P0"));
        checks.add(new PrivacyCheck("CCPA-NOT-002", "财务激励通知",
                "如提供财务激励需提供通知",
                evaluate(true), "P2"));

        // Consumer rights
        checks.add(new PrivacyCheck("CCPA-RTS-001", "知情权",
                "消费者可请求了解收集的个人信息类别",
                evaluate(request.hasAccessRight()), "P0"));
        checks.add(new PrivacyCheck("CCPA-RTS-002", "删除权",
                "消费者可请求删除其个人信息",
                evaluate(request.hasErasureRight()), "P0"));
        checks.add(new PrivacyCheck("CCPA-RTS-003", "选择退出权 (Opt-Out)",
                "消费者可选择不出售/不分享个人信息",
                evaluate(request.hasOptOut()), "P0"));
        checks.add(new PrivacyCheck("CCPA-RTS-004", "更正权",
                "消费者可请求更正不准确的个人信息",
                evaluate(request.hasCorrectionRight()), "P1"));
        checks.add(new PrivacyCheck("CCPA-RTS-005", "限制使用敏感个人信息",
                "消费者可限制敏感个人信息的使用和披露",
                evaluate(request.hasSensitiveDataLimit()), "P0"));

        // Sensitive data
        checks.add(new PrivacyCheck("CCPA-SEN-001", "敏感个人信息识别",
                "识别并分类敏感个人信息（精确位置/生物特征/健康数据等）",
                evaluate(request.hasSensitiveDataClassification()), "P0"));

        // Automated decision-making
        checks.add(new PrivacyCheck("CCPA-ADM-001", "自动化决策",
                "涉及自动化决策时提供退出选项和信息",
                evaluate(request.hasAutomatedDecisionOptOut()), "P1"));

        // Data Protection Assessment
        checks.add(new PrivacyCheck("CCPA-DPA-001", "数据保护评估",
                "对高风险处理活动进行年度网络安全审计",
                evaluate(request.hasRiskAssessment()), "P0"));

        assessment.setChecks(checks);
        assessment.setOverallResult(computeOverall(checks));
        return assessment;
    }

    // ===================================================================
    // PIPL Compliance (China)
    // ===================================================================

    public PrivacyAssessment assessPIPL(String productId, PrivacyRequest request) {
        PrivacyAssessment assessment = new PrivacyAssessment(
                UUID.randomUUID().toString(), productId, "PIPL",
                "中国个人信息保护法 PIPL", "IN_PROGRESS", Instant.now()
        );

        List<PrivacyCheck> checks = new ArrayList<>();

        checks.add(new PrivacyCheck("PIPL-CON-001", "告知-同意原则",
                "处理个人信息前取得个人充分知情同意",
                evaluate(request.hasConsentManagement()), "P0"));
        checks.add(new PrivacyCheck("PIPL-CON-002", "单独同意",
                "敏感个人信息/跨境传输需单独同意",
                evaluate(request.hasSeparateConsent()), "P0"));
        checks.add(new PrivacyCheck("PIPL-RTS-001", "查阅复制权",
                "个人有权查阅复制其个人信息",
                evaluate(request.hasAccessRight()), "P0"));
        checks.add(new PrivacyCheck("PIPL-RTS-002", "更正删除权",
                "个人有权更正删除其个人信息",
                evaluate(request.hasErasureRight()), "P0"));
        checks.add(new PrivacyCheck("PIPL-RTS-003", "可携带权",
                "个人有权将个人信息转移至指定处理者",
                evaluate(request.hasPortabilityRight()), "P1"));
        checks.add(new PrivacyCheck("PIPL-MIN-001", "最小必要原则",
                "仅收集处理目的所需最少个人信息",
                evaluate(request.hasDataMinimization()), "P0"));
        checks.add(new PrivacyCheck("PIPL-SEC-001", "安全保护措施",
                "采取加密/去标识化/访问控制等技术措施",
                evaluate(request.hasTechnicalSecurity()), "P0"));
        checks.add(new PrivacyCheck("PIPL-XFR-001", "跨境传输安全评估",
                "通过国家网信部门安全评估或标准合同/认证",
                evaluate(request.hasCrossBorderSafeguard()), "P0"));
        checks.add(new PrivacyCheck("PIPL-PIA-001", "个人信息保护影响评估",
                "处理敏感信息/自动化决策/跨境传输前进行 PIA",
                evaluate(request.hasPIA()), "P0"));
        checks.add(new PrivacyCheck("PIPL-OFF-001", "个人信息保护负责人",
                "指定个人信息保护负责人",
                evaluate(request.hasDPO()), "P0"));
        checks.add(new PrivacyCheck("PIPL-BRC-001", "泄露通知",
                "发生泄露立即通知主管部门和个人",
                evaluate(request.hasBreachNotification()), "P0"));
        checks.add(new PrivacyCheck("PIPL-AUD-001", "合规审计",
                "定期进行个人信息保护合规审计",
                evaluate(request.hasComplianceAudit()), "P1"));

        assessment.setChecks(checks);
        assessment.setOverallResult(computeOverall(checks));
        return assessment;
    }

    // ===================================================================
    // DPIA — Data Protection Impact Assessment
    // ===================================================================

    public DPIAReport conductDPIA(String productId, DPIARequest request) {
        DPIAReport report = new DPIAReport(
                UUID.randomUUID().toString(), productId, request.processingActivity(),
                Instant.now()
        );

        List<DPIACheck> checks = new ArrayList<>();

        // Step 1: Describe the processing
        checks.add(new DPIACheck("DPIA-DES-001", "处理活动描述",
                "详细描述数据处理的性质、范围、背景和目的",
                request.hasDescription() ? "PASS" : "FAIL", "P0"));

        // Step 2: Necessity & proportionality
        checks.add(new DPIACheck("DPIA-NEC-001", "必要性评估",
                "评估处理活动是否为实现目的所必需",
                request.isNecessary() ? "PASS" : "FAIL", "P0"));
        checks.add(new DPIACheck("DPIA-PRO-001", "比例性评估",
                "处理方式与目的相称，不过度",
                request.isProportional() ? "PASS" : "FAIL", "P1"));

        // Step 3: Risk assessment
        checks.add(new DPIACheck("DPIA-RSK-001", "风险识别",
                "识别数据处理对个人权利自由的风险",
                request.hasRiskIdentification() ? "PASS" : "FAIL", "P0"));
        checks.add(new DPIACheck("DPIA-RSK-002", "风险严重性评估",
                "评估风险的严重性和可能性",
                request.hasRiskEvaluation() ? "PASS" : "FAIL", "P0"));

        // Step 4: Mitigation measures
        checks.add(new DPIACheck("DPIA-MIT-001", "缓解措施",
                "制定并记录风险缓解措施",
                request.hasMitigation() ? "PASS" : "FAIL", "P0"));
        checks.add(new DPIACheck("DPIA-MIT-002", "残余风险评估",
                "评估缓解后的残余风险水平",
                request.hasResidualRisk() ? "PASS" : "FAIL", "P1"));

        // Step 5: Consultation
        checks.add(new DPIACheck("DPIA-CON-001", "事先咨询",
                "高残余风险时咨询监管机构",
                request.hasConsultation() ? "PASS" : "PENDING", "P0"));
        checks.add(new DPIACheck("DPIA-REV-001", "定期审查",
                "制定 DPIA 定期审查计划",
                request.hasReviewPlan() ? "PASS" : "FAIL", "P1"));

        report.setChecks(checks);
        report.setOverallResult(computeDPIAOverall(checks));
        return report;
    }

    // ===================================================================
    // Sensor Privacy Assessment
    // ===================================================================

    public SensorPrivacyReport assessSensorPrivacy(String productId, SensorPrivacyRequest request) {
        SensorPrivacyReport report = new SensorPrivacyReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<SensorCheck> checks = new ArrayList<>();

        // Camera
        checks.add(new SensorCheck("SEN-CAM-001", "摄像头默认关闭",
                "摄像头物理/电子默认关闭，需主动开启",
                request.isCameraDefaultOff() ? "PASS" : "FAIL", "P0"));
        checks.add(new SensorCheck("SEN-CAM-002", "摄像头指示灯",
                "摄像头工作时物理指示灯亮起",
                request.hasCameraIndicator() ? "PASS" : "FAIL", "P0"));
        checks.add(new SensorCheck("SEN-CAM-003", "本地处理优先",
                "图像数据优先本地处理，仅必要时上传",
                request.isCameraLocalFirst() ? "PASS" : "FAIL", "P1"));

        // Microphone
        checks.add(new SensorCheck("SEN-MIC-001", "麦克风默认静音",
                "麦克风默认静音，需主动开启",
                request.isMicDefaultMuted() ? "PASS" : "FAIL", "P0"));
        checks.add(new SensorCheck("SEN-MIC-002", "麦克风指示灯",
                "麦克风工作时物理指示灯亮起",
                request.hasMicIndicator() ? "PASS" : "FAIL", "P0"));
        checks.add(new SensorCheck("SEN-MIC-003", "唤醒词处理",
                "唤醒词本地处理，不上传原始音频",
                request.isWakeWordLocal() ? "PASS" : "FAIL", "P0"));

        // LiDAR / Depth
        checks.add(new SensorCheck("SEN-LID-001", "LiDAR 数据脱敏",
                "LiDAR 点云中人脸/人体数据脱敏处理",
                request.hasLidarAnonymization() ? "PASS" : "FAIL", "P1"));
        checks.add(new SensorCheck("SEN-LID-002", "空间数据最小化",
                "仅收集导航所需空间数据",
                request.hasSpatialDataMinimization() ? "PASS" : "FAIL", "P1"));

        // Biometric data
        checks.add(new SensorCheck("SEN-BIO-001", "生物特征数据",
                "人脸/声纹等生物特征数据加密存储，不跨境传输",
                request.hasBiometricProtection() ? "PASS" : "FAIL", "P0"));
        checks.add(new SensorCheck("SEN-BIO-002", "生物特征同意",
                "收集生物特征前取得明确单独同意",
                request.hasBiometricConsent() ? "PASS" : "FAIL", "P0"));

        // Location
        checks.add(new SensorCheck("SEN-LOC-001", "位置数据控制",
                "精确位置数据用户可控开关",
                request.hasLocationControl() ? "PASS" : "FAIL", "P1"));

        report.setChecks(checks);
        report.setOverallResult(computeSensorOverall(checks));
        return report;
    }

    // ===================================================================
    // Cross-Border Data Transfer
    // ===================================================================

    public CrossBorderReport assessCrossBorder(String productId, CrossBorderRequest request) {
        CrossBorderReport report = new CrossBorderReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<CrossBorderCheck> checks = new ArrayList<>();

        // Data flow mapping
        checks.add(new CrossBorderCheck("XFR-MAP-001", "数据流向图",
                "绘制完整数据跨境流向图（源/目的/类别/量级）",
                request.hasDataFlowMap() ? "PASS" : "FAIL", "P0"));
        checks.add(new CrossBorderCheck("XFR-CAT-001", "数据分类",
                "跨境数据分类（一般/重要/敏感个人信息）",
                request.hasDataClassification() ? "PASS" : "FAIL", "P0"));

        // Transfer safeguards (EU)
        checks.add(new CrossBorderCheck("XFR-SCC-001", "标准合同条款 (SCC)",
                "签署最新版 EU SCC (2021/914)",
                request.hasSCC() ? "PASS" : "PENDING", "P0"));
        checks.add(new CrossBorderCheck("XFR-BCR-001", "约束性公司规则 (BCR)",
                "跨国集团 BCR 获监管批准",
                request.hasBCR() ? "PASS" : "PENDING", "P1"));
        checks.add(new CrossBorderCheck("XFR-ADE-001", "充分性认定",
                "接收方所在国/地区获充分性认定",
                request.hasAdequacyDecision() ? "PASS" : "PENDING", "P0"));

        // China safeguards
        checks.add(new CrossBorderCheck("XFR-CNSA-001", "网信办安全评估",
                "通过国家网信部门组织的安全评估",
                request.hasCACAssessment() ? "PASS" : "PENDING", "P0"));
        checks.add(new CrossBorderCheck("XFR-CNSCC-001", "个人信息出境标准合同",
                "与境外接收方签署标准合同并备案",
                request.hasChinaSCC() ? "PASS" : "PENDING", "P0"));
        checks.add(new CrossBorderCheck("XFR-CNCERT-001", "个人信息保护认证",
                "通过专业机构个人信息保护认证",
                request.hasChinaCertification() ? "PASS" : "PENDING", "P1"));

        // Technical measures
        checks.add(new CrossBorderCheck("XFR-TEC-001", "传输加密",
                "跨境传输使用 TLS 1.3/AES-256 加密",
                request.hasTransmissionEncryption() ? "PASS" : "FAIL", "P0"));
        checks.add(new CrossBorderCheck("XFR-TEC-002", "去标识化",
                "传输前对个人信息进行去标识化处理",
                request.hasDeidentification() ? "PASS" : "FAIL", "P1"));
        checks.add(new CrossBorderCheck("XFR-TEC-003", "审计日志",
                "记录所有跨境数据传输操作日志",
                request.hasAuditLog() ? "PASS" : "FAIL", "P1"));

        // TIA (Transfer Impact Assessment)
        checks.add(new CrossBorderCheck("XFR-TIA-001", "传输影响评估",
                "对接收方法律环境和保护水平进行评估",
                request.hasTIA() ? "PASS" : "FAIL", "P0"));

        report.setChecks(checks);
        report.setOverallResult(computeXfrOverall(checks));
        return report;
    }

    // ===================================================================
    // Data Subject Rights Management
    // ===================================================================

    public DSRDashboard getDSRDashboard(String productId) {
        DSRDashboard dashboard = new DSRDashboard();
        dashboard.setProductId(productId);

        dashboard.setRightsCoverage(List.of(
                new RightStatus("ACCESS", "查阅/访问权", "IMPLEMENTED",
                        "GET /api/v1/privacy/data-export"),
                new RightStatus("ERASURE", "删除/被遗忘权", "IMPLEMENTED",
                        "POST /api/v1/privacy/data-deletion"),
                new RightStatus("PORTABILITY", "数据可携带权", "IMPLEMENTED",
                        "GET /api/v1/privacy/data-export?format=json"),
                new RightStatus("RECTIFICATION", "更正权", "IMPLEMENTED",
                        "PUT /api/v1/privacy/data-correction"),
                new RightStatus("RESTRICTION", "限制处理权", "IMPLEMENTED",
                        "POST /api/v1/privacy/processing-restriction"),
                new RightStatus("OBJECTION", "反对权", "IMPLEMENTED",
                        "POST /api/v1/privacy/processing-objection"),
                new RightStatus("OPT_OUT", "选择退出权", "IMPLEMENTED",
                        "POST /api/v1/privacy/opt-out"),
                new RightStatus("AUTOMATED", "自动化决策相关权", "IMPLEMENTED",
                        "POST /api/v1/privacy/human-review")
        ));

        dashboard.setRequestStats(new DSRStats(0, 0, 0, 0));
        dashboard.setLastUpdated(Instant.now());
        return dashboard;
    }

    // ===================================================================
    // Helpers
    // ===================================================================

    private String evaluate(boolean condition) {
        return condition ? "PASS" : "FAIL";
    }

    private String computeOverall(List<PrivacyCheck> checks) {
        long failed = checks.stream().filter(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority())).count();
        if (failed > 0) return "NON_COMPLIANT";
        long allFailed = checks.stream().filter(c -> "FAIL".equals(c.result())).count();
        if (allFailed > 0) return "PARTIALLY_COMPLIANT";
        return "COMPLIANT";
    }

    private String computeDPIAOverall(List<DPIACheck> checks) {
        long failed = checks.stream().filter(c -> "FAIL".equals(c.result())).count();
        return failed == 0 ? "COMPLETED" : "INCOMPLETE";
    }

    private String computeSensorOverall(List<SensorCheck> checks) {
        long failed = checks.stream().filter(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority())).count();
        if (failed > 0) return "HIGH_RISK";
        long allFailed = checks.stream().filter(c -> "FAIL".equals(c.result())).count();
        return allFailed == 0 ? "COMPLIANT" : "MEDIUM_RISK";
    }

    private String computeXfrOverall(List<CrossBorderCheck> checks) {
        long failed = checks.stream().filter(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority())).count();
        if (failed > 0) return "BLOCKED";
        long pending = checks.stream().filter(c -> "PENDING".equals(c.result())).count();
        return pending == 0 ? "COMPLIANT" : "IN_PROGRESS";
    }

    // ===================================================================
    // DTOs
    // ===================================================================

    public static class PrivacyAssessment {
        private String assessmentId;
        private String productId;
        private String regulation;
        private String regulationName;
        private String status;
        private Instant createdAt;
        private List<PrivacyCheck> checks = new ArrayList<>();
        private String overallResult;

        public PrivacyAssessment() {}
        public PrivacyAssessment(String assessmentId, String productId, String regulation,
                                 String regulationName, String status, Instant createdAt) {
            this.assessmentId = assessmentId;
            this.productId = productId;
            this.regulation = regulation;
            this.regulationName = regulationName;
            this.status = status;
            this.createdAt = createdAt;
        }

        public String getAssessmentId() { return assessmentId; }
        public void setAssessmentId(String id) { this.assessmentId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getRegulation() { return regulation; }
        public void setRegulation(String r) { this.regulation = r; }
        public String getRegulationName() { return regulationName; }
        public void setRegulationName(String n) { this.regulationName = n; }
        public String getStatus() { return status; }
        public void setStatus(String s) { this.status = s; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<PrivacyCheck> getChecks() { return checks; }
        public void setChecks(List<PrivacyCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record PrivacyCheck(String checkId, String title, String description,
                                String result, String priority) {}

    public record PrivacyRequest(boolean hasLawfulBasis, boolean hasConsentManagement,
                                  boolean hasConsentWithdrawal, boolean hasAccessRight,
                                  boolean hasErasureRight, boolean hasPortabilityRight,
                                  boolean hasRestrictionRight, boolean hasObjectionRight,
                                  boolean hasPrivacyNotice, boolean hasRopa,
                                  boolean hasPrivacyByDesign, boolean hasDataMinimization,
                                  boolean hasRetentionPolicy, boolean hasTechnicalSecurity,
                                  boolean hasBreachNotification, boolean hasDPO, boolean hasDPA,
                                  boolean hasCrossBorderSafeguard, boolean hasTIA,
                                  boolean hasOptOut, boolean hasCorrectionRight,
                                  boolean hasSensitiveDataLimit, boolean hasSensitiveDataClassification,
                                  boolean hasAutomatedDecisionOptOut, boolean hasRiskAssessment,
                                  boolean hasSeparateConsent, boolean hasPIA,
                                  boolean hasComplianceAudit) {}

    public static class DPIAReport {
        private String reportId;
        private String productId;
        private String processingActivity;
        private Instant createdAt;
        private List<DPIACheck> checks = new ArrayList<>();
        private String overallResult;

        public DPIAReport() {}
        public DPIAReport(String reportId, String productId, String processingActivity, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.processingActivity = processingActivity;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getProcessingActivity() { return processingActivity; }
        public void setProcessingActivity(String a) { this.processingActivity = a; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<DPIACheck> getChecks() { return checks; }
        public void setChecks(List<DPIACheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record DPIACheck(String checkId, String title, String description,
                             String result, String priority) {}

    public record DPIARequest(String processingActivity, boolean hasDescription,
                               boolean isNecessary, boolean isProportional,
                               boolean hasRiskIdentification, boolean hasRiskEvaluation,
                               boolean hasMitigation, boolean hasResidualRisk,
                               boolean hasConsultation, boolean hasReviewPlan) {}

    public static class SensorPrivacyReport {
        private String reportId;
        private String productId;
        private Instant createdAt;
        private List<SensorCheck> checks = new ArrayList<>();
        private String overallResult;

        public SensorPrivacyReport() {}
        public SensorPrivacyReport(String reportId, String productId, Instant createdAt) {
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
        public List<SensorCheck> getChecks() { return checks; }
        public void setChecks(List<SensorCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record SensorCheck(String checkId, String title, String description,
                               String result, String priority) {}

    public record SensorPrivacyRequest(boolean isCameraDefaultOff, boolean hasCameraIndicator,
                                        boolean isCameraLocalFirst, boolean isMicDefaultMuted,
                                        boolean hasMicIndicator, boolean isWakeWordLocal,
                                        boolean hasLidarAnonymization, boolean hasSpatialDataMinimization,
                                        boolean hasBiometricProtection, boolean hasBiometricConsent,
                                        boolean hasLocationControl) {}

    public static class CrossBorderReport {
        private String reportId;
        private String productId;
        private Instant createdAt;
        private List<CrossBorderCheck> checks = new ArrayList<>();
        private String overallResult;

        public CrossBorderReport() {}
        public CrossBorderReport(String reportId, String productId, Instant createdAt) {
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
        public List<CrossBorderCheck> getChecks() { return checks; }
        public void setChecks(List<CrossBorderCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record CrossBorderCheck(String checkId, String title, String description,
                                    String result, String priority) {}

    public record CrossBorderRequest(boolean hasDataFlowMap, boolean hasDataClassification,
                                      boolean hasSCC, boolean hasBCR, boolean hasAdequacyDecision,
                                      boolean hasCACAssessment, boolean hasChinaSCC,
                                      boolean hasChinaCertification, boolean hasTransmissionEncryption,
                                      boolean hasDeidentification, boolean hasAuditLog, boolean hasTIA) {}

    public static class DSRDashboard {
        private String productId;
        private List<RightStatus> rightsCoverage = new ArrayList<>();
        private DSRStats requestStats;
        private Instant lastUpdated;

        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public List<RightStatus> getRightsCoverage() { return rightsCoverage; }
        public void setRightsCoverage(List<RightStatus> r) { this.rightsCoverage = r; }
        public DSRStats getRequestStats() { return requestStats; }
        public void setRequestStats(DSRStats s) { this.requestStats = s; }
        public Instant getLastUpdated() { return lastUpdated; }
        public void setLastUpdated(Instant t) { this.lastUpdated = t; }
    }

    public record RightStatus(String rightId, String rightName, String implementationStatus,
                               String apiEndpoint) {}

    public record DSRStats(int totalRequests, int completed, int inProgress, int rejected) {}
}
