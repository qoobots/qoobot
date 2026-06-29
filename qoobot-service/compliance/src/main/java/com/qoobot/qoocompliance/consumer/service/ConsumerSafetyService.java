package com.qoobot.qoocompliance.consumer.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

/**
 * Consumer Safety compliance service.
 *
 * Covers:
 * - CE Machinery Directive 2006/42/EC
 * - Low Voltage Directive (LVD) 2014/35/EU
 * - UL safety certification (UL 3300 for service robots)
 * - Children's safety (Toy Safety Directive / ASTM F963)
 * - Product liability
 */
@Service
public class ConsumerSafetyService {

    // ===================================================================
    // CE Machinery Directive 2006/42/EC
    // ===================================================================

    public ConsumerSafetyReport assessMachineryDirective(String productId, MachineryRequest request) {
        ConsumerSafetyReport report = new ConsumerSafetyReport(
                UUID.randomUUID().toString(), productId, "CE_MACHINERY",
                "CE 机械指令 2006/42/EC", "IN_PROGRESS", Instant.now()
        );

        List<SafetyRequirement> requirements = new ArrayList<>();

        // Essential Health & Safety Requirements (EHSR)
        requirements.add(new SafetyRequirement("MD-EHSR-001", "风险评估",
                "完成全面风险评估，覆盖全生命周期",
                request.hasRiskAssessment() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-EHSR-002", "安全集成",
                "安全原则融入设计和制造",
                request.hasSafetyIntegration() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-EHSR-003", "材料与产品",
                "使用材料不危及人员安全与健康",
                request.hasMaterialSafety() ? "PASS" : "FAIL", "P1"));
        requirements.add(new SafetyRequirement("MD-EHSR-004", "照明",
                "无自然光照时提供适当人工照明",
                evaluate(true), "P2"));

        // Controls
        requirements.add(new SafetyRequirement("MD-CTL-001", "控制系统安全",
                "控制系统设计安全可靠，容错",
                request.hasSafeControlSystem() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-CTL-002", "启动/停止装置",
                "启动和停止装置明确标识，可安全操作",
                request.hasStartStopDevices() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-CTL-003", "紧急停止",
                "至少一个紧急停止装置，红色蘑菇头",
                request.hasEmergencyStop() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-CTL-004", "模式选择器",
                "操作模式选择器可锁定，各模式安全",
                request.hasModeSelector() ? "PASS" : "FAIL", "P1"));

        // Mechanical hazards
        requirements.add(new SafetyRequirement("MD-MEC-001", "机械防护",
                "运动部件防护装置/围栏/光栅",
                request.hasMechanicalGuards() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-MEC-002", "稳定性",
                "设计和制造确保足够稳定性",
                request.hasStability() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-MEC-003", "跌落/弹出防护",
                "防止物体跌落或弹出风险",
                request.hasEjectionProtection() ? "PASS" : "FAIL", "P1"));

        // Documentation
        requirements.add(new SafetyRequirement("MD-DOC-001", "技术文件",
                "编制完整技术构造文件 (TCF)",
                request.hasTCF() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-DOC-002", "使用说明书",
                "提供原始语言+目的国语言使用说明书",
                request.hasUserManual() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-DOC-003", "EC 符合性声明",
                "签署 EC Declaration of Conformity",
                request.hasDoC() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("MD-DOC-004", "CE 标识",
                "加贴 CE 标识，清晰可见不可擦除",
                request.hasCEMarking() ? "PASS" : "FAIL", "P0"));

        report.setRequirements(requirements);
        report.setOverallResult(computeOverall(requirements));
        return report;
    }

    // ===================================================================
    // Low Voltage Directive 2014/35/EU
    // ===================================================================

    public ConsumerSafetyReport assessLVD(String productId, LVDRequest request) {
        ConsumerSafetyReport report = new ConsumerSafetyReport(
                UUID.randomUUID().toString(), productId, "LVD",
                "低电压指令 2014/35/EU", "IN_PROGRESS", Instant.now()
        );

        List<SafetyRequirement> requirements = new ArrayList<>();

        requirements.add(new SafetyRequirement("LVD-ELC-001", "电击防护",
                "直接/间接接触防护，双重绝缘或加强绝缘",
                request.hasShockProtection() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("LVD-ELC-002", "绝缘耐压测试",
                "绝缘电阻和耐压测试通过",
                request.hasInsulationTest() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("LVD-ELC-003", "接地连续性",
                "保护接地连续性测试通过",
                request.hasGroundingTest() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("LVD-ELC-004", "泄漏电流",
                "泄漏电流在安全限值内",
                request.hasLeakageCurrentTest() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("LVD-ELC-005", "过载保护",
                "过载/短路保护装置",
                request.hasOverloadProtection() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("LVD-THE-001", "温升测试",
                "正常/异常工作条件下温升在限值内",
                request.hasTemperatureTest() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("LVD-MEC-001", "机械强度",
                "外壳机械强度测试通过",
                request.hasMechanicalStrength() ? "PASS" : "FAIL", "P1"));
        requirements.add(new SafetyRequirement("LVD-FIR-001", "防火",
                "防火外壳和材料阻燃等级",
                request.hasFireProtection() ? "PASS" : "FAIL", "P0"));

        report.setRequirements(requirements);
        report.setOverallResult(computeOverall(requirements));
        return report;
    }

    // ===================================================================
    // UL Safety (UL 3300 for Service Robots)
    // ===================================================================

    public ConsumerSafetyReport assessUL(String productId, ULRequest request) {
        ConsumerSafetyReport report = new ConsumerSafetyReport(
                UUID.randomUUID().toString(), productId, "UL",
                "UL 3300 服务/教育/商用机器人安全", "IN_PROGRESS", Instant.now()
        );

        List<SafetyRequirement> requirements = new ArrayList<>();

        requirements.add(new SafetyRequirement("UL-ELC-001", "电气安全",
                "电气绝缘/耐压/泄漏电流测试",
                request.hasElectricalTest() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("UL-BAT-001", "电池安全",
                "UL 2580/UL 1642 电池安全测试",
                request.hasBatteryTest() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("UL-CHG-001", "充电系统",
                "充电器安全 UL 1012/UL 1310",
                request.hasChargerTest() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("UL-MOB-001", "移动安全",
                "运动部件防护、防跌落、防碰撞",
                request.hasMobilityTest() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("UL-SEN-001", "传感器安全",
                "激光/LED 等光学传感器眼安全 (IEC 60825)",
                request.hasSensorSafety() ? "PASS" : "FAIL", "P1"));
        requirements.add(new SafetyRequirement("UL-SW-001", "软件安全",
                "安全相关软件 UL 1998/UL 60730-1",
                request.hasSoftwareSafety() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("UL-FIR-001", "防火外壳",
                "外壳阻燃等级 5VA/5VB 以上",
                request.hasFireEnclosure() ? "PASS" : "FAIL", "P0"));

        report.setRequirements(requirements);
        report.setOverallResult(computeOverall(requirements));
        return report;
    }

    // ===================================================================
    // Children's Safety
    // ===================================================================

    public ConsumerSafetyReport assessChildrenSafety(String productId, ChildrenSafetyRequest request) {
        ConsumerSafetyReport report = new ConsumerSafetyReport(
                UUID.randomUUID().toString(), productId, "CHILDREN_SAFETY",
                "儿童安全合规", "IN_PROGRESS", Instant.now()
        );

        List<SafetyRequirement> requirements = new ArrayList<>();

        // Toy Safety Directive 2009/48/EC (EU)
        requirements.add(new SafetyRequirement("CHD-EU-001", "机械物理性能 (EN 71-1)",
                "小零件/锐边/尖端/间隙测试",
                request.hasMechanicalTest() ? "PASS" : "PENDING", "P0"));
        requirements.add(new SafetyRequirement("CHD-EU-002", "易燃性 (EN 71-2)",
                "材料阻燃和易燃性测试",
                request.hasFlammabilityTest() ? "PASS" : "PENDING", "P0"));
        requirements.add(new SafetyRequirement("CHD-EU-003", "化学安全 (EN 71-3)",
                "重金属迁移量 (19种元素) 测试",
                request.hasChemicalTest() ? "PASS" : "PENDING", "P0"));

        // ASTM F963 (US)
        requirements.add(new SafetyRequirement("CHD-US-001", "机械安全 (ASTM F963)",
                "滥用测试/小零件/锐边/声压级",
                request.hasAstmMechanical() ? "PASS" : "PENDING", "P0"));
        requirements.add(new SafetyRequirement("CHD-US-002", "重金属 (ASTM F963)",
                "8 种可溶重金属元素限量",
                request.hasAstmChemical() ? "PASS" : "PENDING", "P0"));

        // Child-specific robot safety
        requirements.add(new SafetyRequirement("CHD-ROB-001", "儿童接触力限制",
                "儿童接触部位力/压强阈值降低 50%",
                request.hasChildForceLimit() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("CHD-ROB-002", "防夹手设计",
                "关节/活动部件间隙 < 5mm 或 > 12mm",
                request.hasAntiPinch() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("CHD-ROB-003", "家长控制",
                "家长控制功能：使用限制/内容过滤/远程监控",
                request.hasParentalControl() ? "PASS" : "FAIL", "P0"));
        requirements.add(new SafetyRequirement("CHD-ROB-004", "声音限制",
                "发声设备声压级 ≤ 85 dB(A) (近距离)",
                request.hasSoundLimit() ? "PASS" : "FAIL", "P1"));

        report.setRequirements(requirements);
        report.setOverallResult(computeOverall(requirements));
        return report;
    }

    // ===================================================================
    // Product Liability
    // ===================================================================

    public LiabilityAssessment assessProductLiability(String productId, LiabilityRequest request) {
        LiabilityAssessment assessment = new LiabilityAssessment(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<LiabilityCheck> checks = new ArrayList<>();

        // EU Product Liability Directive 85/374/EEC (revised 2024)
        checks.add(new LiabilityCheck("LIA-EU-001", "缺陷产品定义",
                "识别可能构成产品缺陷的设计/制造/说明缺陷",
                request.hasDefectIdentification() ? "PASS" : "FAIL", "P0"));
        checks.add(new LiabilityCheck("LIA-EU-002", "产品责任保险",
                "购买适当产品责任保险",
                request.hasInsurance() ? "PASS" : "FAIL", "P0"));
        checks.add(new LiabilityCheck("LIA-EU-003", "产品追溯",
                "建立产品批次追溯系统",
                request.hasTraceability() ? "PASS" : "FAIL", "P0"));

        // Warning labels
        checks.add(new LiabilityCheck("LIA-WRN-001", "警告标签",
                "适当警告标签和安全说明",
                request.hasWarningLabels() ? "PASS" : "FAIL", "P0"));
        checks.add(new LiabilityCheck("LIA-WRN-002", "年龄适用性",
                "明确标注适用年龄范围",
                request.hasAgeLabeling() ? "PASS" : "FAIL", "P1"));

        // Incident handling
        checks.add(new LiabilityCheck("LIA-INC-001", "事故报告机制",
                "建立产品事故收集和报告机制",
                request.hasIncidentReporting() ? "PASS" : "FAIL", "P0"));
        checks.add(new LiabilityCheck("LIA-INC-002", "召回计划",
                "制定产品召回预案",
                request.hasRecallPlan() ? "PASS" : "FAIL", "P0"));
        checks.add(new LiabilityCheck("LIA-INC-003", "事故后分析",
                "事故后根因分析和改进流程",
                request.hasPostIncidentAnalysis() ? "PASS" : "FAIL", "P1"));

        assessment.setChecks(checks);
        assessment.setOverallResult(checks.stream().noneMatch(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority()))
                ? "COMPLIANT" : "NON_COMPLIANT");
        return assessment;
    }

    // ===================================================================
    // Consumer Safety Dashboard
    // ===================================================================

    public ConsumerSafetyDashboard getDashboard(String productId) {
        ConsumerSafetyDashboard dashboard = new ConsumerSafetyDashboard();
        dashboard.setProductId(productId);

        dashboard.setCertifications(List.of(
                new CertRequirement("CE Machinery", "机械指令 2006/42/EC", "NOT_STARTED", 15),
                new CertRequirement("CE LVD", "低电压指令 2014/35/EU", "NOT_STARTED", 8),
                new CertRequirement("CE EMC", "电磁兼容指令 2014/30/EU", "NOT_STARTED", 11),
                new CertRequirement("CE RED", "无线电设备指令 2014/53/EU", "NOT_STARTED", 8),
                new CertRequirement("UL 3300", "服务机器人安全", "NOT_STARTED", 7),
                new CertRequirement("Toy Safety", "玩具安全 (EN 71 / ASTM F963)", "NOT_STARTED", 9),
                new CertRequirement("Product Liability", "产品责任", "NOT_STARTED", 8)
        ));

        dashboard.setLastUpdated(Instant.now());
        return dashboard;
    }

    // ===================================================================
    // Helpers
    // ===================================================================

    private String evaluate(boolean condition) {
        return condition ? "PASS" : "FAIL";
    }

    private String computeOverall(List<SafetyRequirement> reqs) {
        long failed = reqs.stream().filter(r -> "FAIL".equals(r.result()) && "P0".equals(r.priority())).count();
        if (failed > 0) return "NON_COMPLIANT";
        long pending = reqs.stream().filter(r -> "PENDING".equals(r.result())).count();
        if (pending > 0) return "IN_PROGRESS";
        return "COMPLIANT";
    }

    // ===================================================================
    // DTOs
    // ===================================================================

    public static class ConsumerSafetyReport {
        private String reportId;
        private String productId;
        private String directive;
        private String directiveName;
        private String status;
        private Instant createdAt;
        private List<SafetyRequirement> requirements = new ArrayList<>();
        private String overallResult;

        public ConsumerSafetyReport() {}
        public ConsumerSafetyReport(String reportId, String productId, String directive,
                                    String directiveName, String status, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.directive = directive;
            this.directiveName = directiveName;
            this.status = status;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getDirective() { return directive; }
        public void setDirective(String d) { this.directive = d; }
        public String getDirectiveName() { return directiveName; }
        public void setDirectiveName(String n) { this.directiveName = n; }
        public String getStatus() { return status; }
        public void setStatus(String s) { this.status = s; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<SafetyRequirement> getRequirements() { return requirements; }
        public void setRequirements(List<SafetyRequirement> r) { this.requirements = r; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record SafetyRequirement(String reqId, String title, String description,
                                     String result, String priority) {}

    public record MachineryRequest(boolean hasRiskAssessment, boolean hasSafetyIntegration,
                                    boolean hasMaterialSafety, boolean hasSafeControlSystem,
                                    boolean hasStartStopDevices, boolean hasEmergencyStop,
                                    boolean hasModeSelector, boolean hasMechanicalGuards,
                                    boolean hasStability, boolean hasEjectionProtection,
                                    boolean hasTCF, boolean hasUserManual, boolean hasDoC,
                                    boolean hasCEMarking) {}

    public record LVDRequest(boolean hasShockProtection, boolean hasInsulationTest,
                              boolean hasGroundingTest, boolean hasLeakageCurrentTest,
                              boolean hasOverloadProtection, boolean hasTemperatureTest,
                              boolean hasMechanicalStrength, boolean hasFireProtection) {}

    public record ULRequest(boolean hasElectricalTest, boolean hasBatteryTest,
                             boolean hasChargerTest, boolean hasMobilityTest,
                             boolean hasSensorSafety, boolean hasSoftwareSafety,
                             boolean hasFireEnclosure) {}

    public record ChildrenSafetyRequest(boolean hasMechanicalTest, boolean hasFlammabilityTest,
                                         boolean hasChemicalTest, boolean hasAstmMechanical,
                                         boolean hasAstmChemical, boolean hasChildForceLimit,
                                         boolean hasAntiPinch, boolean hasParentalControl,
                                         boolean hasSoundLimit) {}

    public static class LiabilityAssessment {
        private String assessmentId;
        private String productId;
        private Instant createdAt;
        private List<LiabilityCheck> checks = new ArrayList<>();
        private String overallResult;

        public LiabilityAssessment() {}
        public LiabilityAssessment(String assessmentId, String productId, Instant createdAt) {
            this.assessmentId = assessmentId;
            this.productId = productId;
            this.createdAt = createdAt;
        }

        public String getAssessmentId() { return assessmentId; }
        public void setAssessmentId(String id) { this.assessmentId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<LiabilityCheck> getChecks() { return checks; }
        public void setChecks(List<LiabilityCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record LiabilityCheck(String checkId, String title, String description,
                                  String result, String priority) {}

    public record LiabilityRequest(boolean hasDefectIdentification, boolean hasInsurance,
                                    boolean hasTraceability, boolean hasWarningLabels,
                                    boolean hasAgeLabeling, boolean hasIncidentReporting,
                                    boolean hasRecallPlan, boolean hasPostIncidentAnalysis) {}

    public static class ConsumerSafetyDashboard {
        private String productId;
        private List<CertRequirement> certifications = new ArrayList<>();
        private Instant lastUpdated;

        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public List<CertRequirement> getCertifications() { return certifications; }
        public void setCertifications(List<CertRequirement> c) { this.certifications = c; }
        public Instant getLastUpdated() { return lastUpdated; }
        public void setLastUpdated(Instant t) { this.lastUpdated = t; }
    }

    public record CertRequirement(String certification, String description,
                                   String status, int totalChecks) {}
}
