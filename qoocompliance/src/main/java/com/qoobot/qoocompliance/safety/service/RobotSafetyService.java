package com.qoobot.qoocompliance.safety.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

/**
 * Robot safety standards compliance engine.
 *
 * Covers:
 * - ISO 13482 (personal care robot safety)
 * - ISO 10218 (industrial robot safety)
 * - ISO 13849 (safety-related parts of control systems)
 * - Functional safety SIL assessment
 * - HAZOP / FMEA risk analysis
 * - Collaborative robot safety (ISO/TS 15066)
 * - Mobile robot safety (ISO 3691-4)
 */
@Service
public class RobotSafetyService {

    // ===================================================================
    // ISO 13482 — Personal care robot safety
    // ===================================================================

    /**
     * Conduct ISO 13482 compliance assessment for a robot product.
     */
    public SafetyAssessment assessISO13482(String productId, SafetyAssessmentRequest request) {
        SafetyAssessment assessment = new SafetyAssessment(
                UUID.randomUUID().toString(), productId, "ISO_13482",
                "个人护理机器人安全 — ISO 13482:2014", "IN_PROGRESS", Instant.now()
        );

        List<SafetyCheck> checks = new ArrayList<>();

        // Hazard identification
        checks.add(new SafetyCheck("13482-HAZ-001", "危险源识别",
                "识别所有潜在危险源（机械、电气、热、辐射、噪声）",
                evaluateCheck(request.hasHazardAnalysis()), "P0"));
        checks.add(new SafetyCheck("13482-HAZ-002", "风险评估",
                "对每个危险源进行风险等级评估（严重度×概率）",
                evaluateCheck(request.hasRiskAssessment()), "P0"));

        // Safety functions
        checks.add(new SafetyCheck("13482-SAF-001", "安全相关控制系统",
                "控制系统满足 ISO 13849 PLr 要求",
                evaluateCheck(request.hasSafetyControlSystem()), "P0"));
        checks.add(new SafetyCheck("13482-SAF-002", "紧急停止功能",
                "紧急停止装置符合 IEC 60204-1",
                evaluateCheck(request.hasEmergencyStop()), "P0"));
        checks.add(new SafetyCheck("13482-SAF-003", "速度与力限制",
                "协作模式下速度和力在安全阈值内",
                evaluateCheck(request.hasSpeedForceLimit()), "P1"));
        checks.add(new SafetyCheck("13482-SAF-004", "稳定性验证",
                "机器人静态和动态稳定性测试通过",
                evaluateCheck(request.hasStabilityTest()), "P1"));

        // Protective measures
        checks.add(new SafetyCheck("13482-PRO-001", "防护装置",
                "固定/互锁防护装置设计合规",
                evaluateCheck(request.hasGuards()), "P0"));
        checks.add(new SafetyCheck("13482-PRO-002", "安全距离",
                "安全距离符合 ISO 13857 要求",
                evaluateCheck(request.hasSafetyDistance()), "P1"));

        // Information for use
        checks.add(new SafetyCheck("13482-INF-001", "安全标志与警示",
                "安全标志、警示标签符合 ISO 3864",
                evaluateCheck(request.hasSafetySigns()), "P2"));
        checks.add(new SafetyCheck("13482-INF-002", "使用说明书",
                "使用说明书包含安全操作指南",
                evaluateCheck(request.hasUserManual()), "P2"));

        assessment.setChecks(checks);
        assessment.setOverallResult(computeOverall(checks));
        return assessment;
    }

    // ===================================================================
    // ISO 10218 — Industrial robot safety
    // ===================================================================

    /**
     * Conduct ISO 10218 compliance assessment.
     */
    public SafetyAssessment assessISO10218(String productId, SafetyAssessmentRequest request) {
        SafetyAssessment assessment = new SafetyAssessment(
                UUID.randomUUID().toString(), productId, "ISO_10218",
                "工业机器人安全 — ISO 10218-1/-2:2011", "IN_PROGRESS", Instant.now()
        );

        List<SafetyCheck> checks = new ArrayList<>();

        checks.add(new SafetyCheck("10218-DES-001", "机器人本体设计",
                "机械结构、材料、防护等级满足要求",
                evaluateCheck(request.hasMechanicalDesign()), "P0"));
        checks.add(new SafetyCheck("10218-DES-002", "轴限制",
                "各轴软硬限位功能正常",
                evaluateCheck(request.hasAxisLimits()), "P0"));
        checks.add(new SafetyCheck("10218-CTL-001", "控制器安全功能",
                "安全控制器满足 PL d/Cat.3 以上",
                evaluateCheck(request.hasSafetyController()), "P0"));
        checks.add(new SafetyCheck("10218-CTL-002", "模式选择",
                "自动/手动/示教模式安全切换",
                evaluateCheck(request.hasModeSelector()), "P0"));
        checks.add(new SafetyCheck("10218-INT-001", "末端执行器安全",
                "末端执行器接口安全互锁",
                evaluateCheck(request.hasEndEffectorSafety()), "P1"));
        checks.add(new SafetyCheck("10218-INT-002", "机器人系统集成",
                "机器人系统与周边设备安全集成",
                evaluateCheck(request.hasSystemIntegration()), "P1"));
        checks.add(new SafetyCheck("10218-MNT-001", "维护安全",
                "维护操作安全规程（LOTO等）",
                evaluateCheck(request.hasMaintenanceSafety()), "P2"));
        checks.add(new SafetyCheck("10218-TST-001", "安全验证测试",
                "所有安全功能经过型式试验验证",
                evaluateCheck(request.hasValidationTest()), "P0"));

        assessment.setChecks(checks);
        assessment.setOverallResult(computeOverall(checks));
        return assessment;
    }

    // ===================================================================
    // ISO 13849 — Safety-related parts of control systems
    // ===================================================================

    /**
     * Conduct ISO 13849 PL (Performance Level) assessment.
     */
    public PLAssessment assessISO13849(String productId, PLAssessmentRequest request) {
        PLAssessment assessment = new PLAssessment(
                UUID.randomUUID().toString(), productId, "ISO_13849",
                Instant.now()
        );

        // Calculate PL based on:
        // - Category (B, 1, 2, 3, 4)
        // - MTTFd (Mean Time To Dangerous Failure)
        // - DC (Diagnostic Coverage)
        // - CCF (Common Cause Failure) score
        String category = request.category();
        double mttfd = request.mttfdYears();
        double dc = request.diagnosticCoverage();
        int ccfScore = request.ccfScore();

        // PL determination logic per ISO 13849-1 Table 11
        String pl;
        if (category.equals("4") && mttfd >= 30 && dc >= 99 && ccfScore >= 65) {
            pl = "e"; // Highest
        } else if ((category.equals("4") || category.equals("3")) && mttfd >= 30 && dc >= 90 && ccfScore >= 65) {
            pl = "d";
        } else if (category.equals("3") && mttfd >= 10 && dc >= 60 && ccfScore >= 65) {
            pl = "c";
        } else if (category.equals("2") && mttfd >= 3 && dc >= 60) {
            pl = "b";
        } else {
            pl = "a"; // Lowest
        }

        assessment.setCategory(category);
        assessment.setMttfdYears(mttfd);
        assessment.setDiagnosticCoverage(dc);
        assessment.setCcfScore(ccfScore);
        assessment.setCalculatedPL("PL_" + pl);
        assessment.setRequiredPL(request.requiredPL());
        assessment.setCompliant("PL_" + pl + "".compareTo(request.requiredPL()) >= 0);

        List<String> recommendations = new ArrayList<>();
        if (!assessment.isCompliant()) {
            recommendations.add("提升架构类别到 Cat.3 以上");
            recommendations.add("增加诊断覆盖率 (DC >= 60%)");
            recommendations.add("提升 MTTFd 至 10 年以上");
            recommendations.add("增强共因失效防护措施 (CCF >= 65)");
        }
        assessment.setRecommendations(recommendations);

        return assessment;
    }

    // ===================================================================
    // Functional Safety SIL Assessment (IEC 61508)
    // ===================================================================

    /**
     * Conduct Functional Safety SIL (Safety Integrity Level) assessment.
     */
    public SILAssessment assessFunctionalSafety(String productId, SILAssessmentRequest request) {
        SILAssessment assessment = new SILAssessment(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        // SIL determination based on:
        // - PFDavg (Probability of Failure on Demand) for low demand
        // - PFH (Probability of Failure per Hour) for high demand
        String targetSIL = request.targetSIL();
        boolean isHighDemand = request.highDemand();

        List<SILCheck> checks = new ArrayList<>();

        // PFD/PFH calculation
        double pfh = request.pfh(); // Probability of Failure per Hour
        checks.add(new SILCheck("SIL-CAL-001", "PFH/PFDavg 计算",
                String.format("PFH = %.2e (目标 %s)", pfh, targetSIL),
                isSILCompliant(pfh, targetSIL, isHighDemand) ? "PASS" : "FAIL", "P0"));

        // Hardware Fault Tolerance (HFT)
        int hft = request.hft();
        checks.add(new SILCheck("SIL-HFT-001", "硬件容错 (HFT)",
                String.format("HFT = %d (目标 >= %d)", hft, hftRequired(targetSIL)),
                hft >= hftRequired(targetSIL) ? "PASS" : "FAIL", "P0"));

        // Safe Failure Fraction (SFF)
        double sff = request.safeFailureFraction();
        checks.add(new SILCheck("SIL-SFF-001", "安全失效分数 (SFF)",
                String.format("SFF = %.1f%% (目标 >= 60%%)", sff * 100),
                sff >= 0.60 ? "PASS" : "FAIL", "P0"));

        // Systematic capability
        checks.add(new SILCheck("SIL-SYS-001", "系统能力 (SC)",
                String.format("SC = %d (目标 >= %s)", request.systematicCapability(), targetSIL),
                request.systematicCapability() >= silToNumber(targetSIL) ? "PASS" : "FAIL", "P1"));

        // Software requirements
        checks.add(new SILCheck("SIL-SW-001", "软件安全生命周期",
                "遵循 IEC 61508-3 软件开发 V 模型",
                request.hasSoftwareLifecycle() ? "PASS" : "FAIL", "P1"));
        checks.add(new SILCheck("SIL-SW-002", "软件验证与确认",
                "完成单元测试/集成测试/系统测试",
                request.hasSoftwareVnV() ? "PASS" : "FAIL", "P1"));

        // Management of Functional Safety
        checks.add(new SILCheck("SIL-MGT-001", "功能安全管理",
                "建立功能安全管理体系 (FSMS)",
                request.hasFSMS() ? "PASS" : "FAIL", "P1"));
        checks.add(new SILCheck("SIL-MGT-002", "功能安全评估",
                "独立第三方功能安全评估完成",
                request.hasIndependentAssessment() ? "PASS" : "FAIL", "P0"));

        boolean allPassed = checks.stream().allMatch(c -> "PASS".equals(c.result()));
        assessment.setChecks(checks);
        assessment.setTargetSIL(targetSIL);
        assessment.setAchievedSIL(allPassed ? targetSIL : silDowngrade(targetSIL));
        assessment.setCompliant(allPassed);

        return assessment;
    }

    // ===================================================================
    // HAZOP (Hazard and Operability Study)
    // ===================================================================

    /**
     * Conduct a HAZOP study for a robot system.
     */
    public HAZOPReport conductHAZOP(String productId, HAZOPRequest request) {
        HAZOPReport report = new HAZOPReport(
                UUID.randomUUID().toString(), productId, "HAZOP",
                request.nodeName(), Instant.now()
        );

        List<HAZOPEntry> entries = new ArrayList<>();

        // Standard HAZOP guide words applied to robot parameters
        String[] guideWords = {"NO", "MORE", "LESS", "AS_WELL_AS", "PART_OF",
                "REVERSE", "OTHER_THAN", "EARLY", "LATE", "BEFORE", "AFTER"};
        String[] parameters = {"SPEED", "FORCE", "POSITION", "TEMPERATURE",
                "PRESSURE", "VOLTAGE", "CURRENT", "COMMUNICATION", "TIMING"};

        for (String param : parameters) {
            for (String gw : guideWords) {
                HAZOPEntry entry = analyzeDeviation(param, gw, request);
                if (entry.riskLevel().equals("HIGH") || entry.riskLevel().equals("CRITICAL")) {
                    entries.add(entry);
                }
            }
        }

        report.setEntries(entries);
        report.setCriticalCount((int) entries.stream().filter(e -> "CRITICAL".equals(e.riskLevel())).count());
        report.setHighCount((int) entries.stream().filter(e -> "HIGH".equals(e.riskLevel())).count());
        report.setRequiresMitigation(report.getCriticalCount() > 0);

        return report;
    }

    // ===================================================================
    // FMEA (Failure Mode and Effects Analysis)
    // ===================================================================

    /**
     * Conduct FMEA for a robot subsystem.
     */
    public FMEAReport conductFMEA(String productId, FMEARequest request) {
        FMEAReport report = new FMEAReport(
                UUID.randomUUID().toString(), productId, request.subsystem(),
                Instant.now()
        );

        List<FMEAEntry> entries = new ArrayList<>();
        for (FMEARequest.Component comp : request.components()) {
            for (String failureMode : comp.potentialFailureModes()) {
                FMEAEntry entry = new FMEAEntry(
                        UUID.randomUUID().toString(),
                        comp.name(),
                        comp.function(),
                        failureMode,
                        determineFailureEffect(failureMode, comp.function()),
                        severityRating(comp, failureMode),
                        occurrenceRating(comp),
                        detectionRating(comp),
                        severityRating(comp, failureMode) * occurrenceRating(comp) * detectionRating(comp)
                );
                entries.add(entry);
            }
        }

        report.setEntries(entries);
        report.setRpnThreshold(request.rpnThreshold() > 0 ? request.rpnThreshold() : 100);
        report.setHighRpnEntries(entries.stream()
                .filter(e -> e.rpn() >= report.getRpnThreshold())
                .toList());

        return report;
    }

    // ===================================================================
    // Collaborative Robot Safety (ISO/TS 15066)
    // ===================================================================

    /**
     * Assess collaborative robot safety per ISO/TS 15066.
     */
    public CollabSafetyAssessment assessCollabSafety(String productId, CollabSafetyRequest request) {
        CollabSafetyAssessment assessment = new CollabSafetyAssessment(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<SafetyCheck> checks = new ArrayList<>();

        // Four collaborative operation modes
        checks.add(new SafetyCheck("COLLAB-001", "安全级监控停止 (Safety-rated Monitored Stop)",
                "机器人停止时人可进入协作空间", evaluateCheck(request.hasMonitoredStop()), "P0"));
        checks.add(new SafetyCheck("COLLAB-002", "手动引导 (Hand Guiding)",
                "人手引导操作时力和速度受控", evaluateCheck(request.hasHandGuiding()), "P0"));
        checks.add(new SafetyCheck("COLLAB-003", "速度与分离监控 (Speed & Separation Monitoring)",
                "动态安全距离实时计算", evaluateCheck(request.hasSpeedSeparation()), "P0"));
        checks.add(new SafetyCheck("COLLAB-004", "力与功率限制 (Power & Force Limiting)",
                "准静态接触力/暂态接触力在 ISO/TS 15066 阈值内", evaluateCheck(request.hasPowerForceLimit()), "P0"));

        // Contact force analysis
        checks.add(new SafetyCheck("COLLAB-005", "准静态接触力分析",
                "头/颈/胸/腹/臂/手各部位接触力在阈值内",
                request.hasQuasiStaticAnalysis() ? "PASS" : "FAIL", "P0"));
        checks.add(new SafetyCheck("COLLAB-006", "暂态接触力分析",
                "碰撞瞬间力/压强在安全阈值内",
                request.hasTransientAnalysis() ? "PASS" : "FAIL", "P1"));

        // End effector design
        checks.add(new SafetyCheck("COLLAB-007", "末端执行器安全设计",
                "圆角设计/能量吸收/无夹点",
                request.hasSafeEndEffector() ? "PASS" : "FAIL", "P1"));

        assessment.setChecks(checks);
        assessment.setOverallResult(computeOverall(checks));
        return assessment;
    }

    // ===================================================================
    // Mobile Robot Safety (ISO 3691-4)
    // ===================================================================

    /**
     * Assess mobile robot safety per ISO 3691-4.
     */
    public MobileSafetyAssessment assessMobileSafety(String productId, MobileSafetyRequest request) {
        MobileSafetyAssessment assessment = new MobileSafetyAssessment(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<SafetyCheck> checks = new ArrayList<>();

        checks.add(new SafetyCheck("MOB-001", "人员检测",
                "安全激光扫描仪/3D视觉人员检测区域覆盖",
                request.hasPersonDetection() ? "PASS" : "FAIL", "P0"));
        checks.add(new SafetyCheck("MOB-002", "速度控制",
                "不同区域自动速度限制（行人区/混合区/专用区）",
                request.hasSpeedControl() ? "PASS" : "FAIL", "P0"));
        checks.add(new SafetyCheck("MOB-003", "制动系统",
                "安全制动距离/制动性能符合要求",
                request.hasBrakingSystem() ? "PASS" : "FAIL", "P0"));
        checks.add(new SafetyCheck("MOB-004", "稳定性",
                "满载/空载/斜坡稳定性测试通过",
                request.hasStabilityTest() ? "PASS" : "FAIL", "P1"));
        checks.add(new SafetyCheck("MOB-005", "跌落防护",
                "台阶/坡道边缘检测与防护",
                request.hasEdgeDetection() ? "PASS" : "FAIL", "P1"));
        checks.add(new SafetyCheck("MOB-006", "载荷处理",
                "载荷稳定性/重心变化安全评估",
                request.hasLoadSafety() ? "PASS" : "FAIL", "P1"));
        checks.add(new SafetyCheck("MOB-007", "声光警示",
                "移动时声音/灯光警示装置",
                request.hasWarningDevices() ? "PASS" : "FAIL", "P2"));

        assessment.setChecks(checks);
        assessment.setOverallResult(computeOverall(checks));
        return assessment;
    }

    // ===================================================================
    // Safety Certification Progress Tracking
    // ===================================================================

    /**
     * Get overall safety certification status for a product.
     */
    public SafetyCertificationStatus getCertificationStatus(String productId) {
        SafetyCertificationStatus status = new SafetyCertificationStatus();
        status.setProductId(productId);
        status.setStandards(List.of(
                new StandardStatus("ISO 13482", "个人护理机器人安全", "NOT_STARTED"),
                new StandardStatus("ISO 10218-1/-2", "工业机器人安全", "NOT_STARTED"),
                new StandardStatus("ISO 13849-1", "安全控制系统 PL", "NOT_STARTED"),
                new StandardStatus("IEC 61508", "功能安全 SIL", "NOT_STARTED"),
                new StandardStatus("ISO/TS 15066", "协作机器人安全", "NOT_STARTED"),
                new StandardStatus("ISO 3691-4", "移动机器人安全", "NOT_STARTED"),
                new StandardStatus("IEC 62061", "机械安全-SIL", "NOT_STARTED")
        ));
        status.setLastUpdated(Instant.now());
        return status;
    }

    // ===================================================================
    // Helper Methods
    // ===================================================================

    private String evaluateCheck(boolean condition) {
        return condition ? "PASS" : "FAIL";
    }

    private String computeOverall(List<SafetyCheck> checks) {
        long failed = checks.stream().filter(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority())).count();
        if (failed > 0) return "NON_COMPLIANT";
        long allFailed = checks.stream().filter(c -> "FAIL".equals(c.result())).count();
        if (allFailed > 0) return "PARTIALLY_COMPLIANT";
        return "COMPLIANT";
    }

    private boolean isSILCompliant(double pfh, String targetSIL, boolean highDemand) {
        return switch (targetSIL) {
            case "SIL4" -> pfh < 1e-9;
            case "SIL3" -> pfh < 1e-8;
            case "SIL2" -> pfh < 1e-7;
            case "SIL1" -> pfh < 1e-6;
            default -> false;
        };
    }

    private int hftRequired(String sil) {
        return switch (sil) {
            case "SIL4" -> 2;
            case "SIL3" -> 1;
            case "SIL2" -> 1;
            case "SIL1" -> 0;
            default -> 0;
        };
    }

    private int silToNumber(String sil) {
        return switch (sil) {
            case "SIL4" -> 4;
            case "SIL3" -> 3;
            case "SIL2" -> 2;
            case "SIL1" -> 1;
            default -> 0;
        };
    }

    private String silDowngrade(String sil) {
        return switch (sil) {
            case "SIL4" -> "SIL3";
            case "SIL3" -> "SIL2";
            case "SIL2" -> "SIL1";
            default -> "None";
        };
    }

    private HAZOPEntry analyzeDeviation(String param, String guideWord, HAZOPRequest request) {
        String deviation = guideWord + "_" + param;
        String cause = String.format("%s 的 %s 偏差", param, guideWord);
        String consequence = "可能导致安全功能丧失或人员伤害";
        String riskLevel = isCriticalCombination(param, guideWord) ? "HIGH" : "MEDIUM";
        return new HAZOPEntry(deviation, param, guideWord, cause, consequence,
                isCriticalCombination(param, guideWord) ? 4 : 2,
                isCriticalCombination(param, guideWord) ? 4 : 3, riskLevel,
                "增加冗余监测 / 安全限值");
    }

    private boolean isCriticalCombination(String param, String guideWord) {
        return (param.equals("SPEED") && guideWord.equals("MORE")) ||
                (param.equals("FORCE") && guideWord.equals("MORE")) ||
                (param.equals("COMMUNICATION") && guideWord.equals("NO")) ||
                (param.equals("POSITION") && guideWord.equals("REVERSE"));
    }

    private String determineFailureEffect(String failureMode, String function) {
        return String.format("%s 发生 %s 时可能导致 %s 功能丧失", function, failureMode, function);
    }

    private int severityRating(FMEARequest.Component comp, String failureMode) {
        if (failureMode.contains("complete") || failureMode.contains("total")) return 9;
        if (failureMode.contains("partial") || failureMode.contains("degraded")) return 6;
        return 3;
    }

    private int occurrenceRating(FMEARequest.Component comp) {
        return comp.isNewDesign() ? 5 : 3;
    }

    private int detectionRating(FMEARequest.Component comp) {
        return comp.hasDetectionMethod() ? 3 : 7;
    }

    // ===================================================================
    // DTOs
    // ===================================================================

    public static class SafetyAssessment {
        private String assessmentId;
        private String productId;
        private String standard;
        private String standardName;
        private String status;
        private Instant createdAt;
        private List<SafetyCheck> checks = new ArrayList<>();
        private String overallResult;

        public SafetyAssessment() {}
        public SafetyAssessment(String assessmentId, String productId, String standard,
                                String standardName, String status, Instant createdAt) {
            this.assessmentId = assessmentId;
            this.productId = productId;
            this.standard = standard;
            this.standardName = standardName;
            this.status = status;
            this.createdAt = createdAt;
        }

        public String getAssessmentId() { return assessmentId; }
        public void setAssessmentId(String id) { this.assessmentId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getStandard() { return standard; }
        public void setStandard(String s) { this.standard = s; }
        public String getStandardName() { return standardName; }
        public void setStandardName(String n) { this.standardName = n; }
        public String getStatus() { return status; }
        public void setStatus(String s) { this.status = s; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<SafetyCheck> getChecks() { return checks; }
        public void setChecks(List<SafetyCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record SafetyCheck(String checkId, String title, String description,
                               String result, String priority) {}

    public record SafetyAssessmentRequest(
            boolean hasHazardAnalysis, boolean hasRiskAssessment, boolean hasSafetyControlSystem,
            boolean hasEmergencyStop, boolean hasSpeedForceLimit, boolean hasStabilityTest,
            boolean hasGuards, boolean hasSafetyDistance, boolean hasSafetySigns,
            boolean hasUserManual, boolean hasMechanicalDesign, boolean hasAxisLimits,
            boolean hasSafetyController, boolean hasModeSelector, boolean hasEndEffectorSafety,
            boolean hasSystemIntegration, boolean hasMaintenanceSafety, boolean hasValidationTest
    ) {}

    public static class PLAssessment {
        private String assessmentId;
        private String productId;
        private String standard;
        private Instant createdAt;
        private String category;
        private double mttfdYears;
        private double diagnosticCoverage;
        private int ccfScore;
        private String calculatedPL;
        private String requiredPL;
        private boolean compliant;
        private List<String> recommendations = new ArrayList<>();

        public PLAssessment() {}
        public PLAssessment(String assessmentId, String productId, String standard, Instant createdAt) {
            this.assessmentId = assessmentId;
            this.productId = productId;
            this.standard = standard;
            this.createdAt = createdAt;
        }

        public String getAssessmentId() { return assessmentId; }
        public void setAssessmentId(String id) { this.assessmentId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getStandard() { return standard; }
        public void setStandard(String s) { this.standard = s; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public String getCategory() { return category; }
        public void setCategory(String c) { this.category = c; }
        public double getMttfdYears() { return mttfdYears; }
        public void setMttfdYears(double m) { this.mttfdYears = m; }
        public double getDiagnosticCoverage() { return diagnosticCoverage; }
        public void setDiagnosticCoverage(double d) { this.diagnosticCoverage = d; }
        public int getCcfScore() { return ccfScore; }
        public void setCcfScore(int c) { this.ccfScore = c; }
        public String getCalculatedPL() { return calculatedPL; }
        public void setCalculatedPL(String pl) { this.calculatedPL = pl; }
        public String getRequiredPL() { return requiredPL; }
        public void setRequiredPL(String pl) { this.requiredPL = pl; }
        public boolean isCompliant() { return compliant; }
        public void setCompliant(boolean c) { this.compliant = c; }
        public List<String> getRecommendations() { return recommendations; }
        public void setRecommendations(List<String> r) { this.recommendations = r; }
    }

    public record PLAssessmentRequest(String category, double mttfdYears,
                                       double diagnosticCoverage, int ccfScore, String requiredPL) {}

    public static class SILAssessment {
        private String assessmentId;
        private String productId;
        private Instant createdAt;
        private String targetSIL;
        private String achievedSIL;
        private boolean compliant;
        private List<SILCheck> checks = new ArrayList<>();

        public SILAssessment() {}
        public SILAssessment(String assessmentId, String productId, Instant createdAt) {
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
        public String getTargetSIL() { return targetSIL; }
        public void setTargetSIL(String s) { this.targetSIL = s; }
        public String getAchievedSIL() { return achievedSIL; }
        public void setAchievedSIL(String s) { this.achievedSIL = s; }
        public boolean isCompliant() { return compliant; }
        public void setCompliant(boolean c) { this.compliant = c; }
        public List<SILCheck> getChecks() { return checks; }
        public void setChecks(List<SILCheck> c) { this.checks = c; }
    }

    public record SILCheck(String checkId, String title, String description,
                            String result, String priority) {}

    public record SILAssessmentRequest(String targetSIL, boolean highDemand, double pfh,
                                        int hft, double safeFailureFraction, int systematicCapability,
                                        boolean hasSoftwareLifecycle, boolean hasSoftwareVnV,
                                        boolean hasFSMS, boolean hasIndependentAssessment) {}

    public static class HAZOPReport {
        private String reportId;
        private String productId;
        private String studyType;
        private String nodeName;
        private Instant createdAt;
        private List<HAZOPEntry> entries = new ArrayList<>();
        private int criticalCount;
        private int highCount;
        private boolean requiresMitigation;

        public HAZOPReport() {}
        public HAZOPReport(String reportId, String productId, String studyType,
                           String nodeName, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.studyType = studyType;
            this.nodeName = nodeName;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getStudyType() { return studyType; }
        public void setStudyType(String t) { this.studyType = t; }
        public String getNodeName() { return nodeName; }
        public void setNodeName(String n) { this.nodeName = n; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<HAZOPEntry> getEntries() { return entries; }
        public void setEntries(List<HAZOPEntry> e) { this.entries = e; }
        public int getCriticalCount() { return criticalCount; }
        public void setCriticalCount(int c) { this.criticalCount = c; }
        public int getHighCount() { return highCount; }
        public void setHighCount(int h) { this.highCount = h; }
        public boolean isRequiresMitigation() { return requiresMitigation; }
        public void setRequiresMitigation(boolean r) { this.requiresMitigation = r; }
    }

    public record HAZOPEntry(String deviation, String parameter, String guideWord,
                              String cause, String consequence, int severity,
                              int likelihood, String riskLevel, String mitigation) {}

    public record HAZOPRequest(String nodeName) {}

    public static class FMEAReport {
        private String reportId;
        private String productId;
        private String subsystem;
        private Instant createdAt;
        private List<FMEAEntry> entries = new ArrayList<>();
        private int rpnThreshold;
        private List<FMEAEntry> highRpnEntries = new ArrayList<>();

        public FMEAReport() {}
        public FMEAReport(String reportId, String productId, String subsystem, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.subsystem = subsystem;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getSubsystem() { return subsystem; }
        public void setSubsystem(String s) { this.subsystem = s; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<FMEAEntry> getEntries() { return entries; }
        public void setEntries(List<FMEAEntry> e) { this.entries = e; }
        public int getRpnThreshold() { return rpnThreshold; }
        public void setRpnThreshold(int t) { this.rpnThreshold = t; }
        public List<FMEAEntry> getHighRpnEntries() { return highRpnEntries; }
        public void setHighRpnEntries(List<FMEAEntry> e) { this.highRpnEntries = e; }
    }

    public record FMEAEntry(String entryId, String component, String function,
                             String failureMode, String failureEffect, int severity,
                             int occurrence, int detection, int rpn) {}

    public record FMEARequest(String subsystem, int rpnThreshold, List<Component> components) {
        public record Component(String name, String function, List<String> potentialFailureModes,
                                 boolean isNewDesign, boolean hasDetectionMethod) {}
    }

    public static class CollabSafetyAssessment {
        private String assessmentId;
        private String productId;
        private Instant createdAt;
        private List<SafetyCheck> checks = new ArrayList<>();
        private String overallResult;

        public CollabSafetyAssessment() {}
        public CollabSafetyAssessment(String assessmentId, String productId, Instant createdAt) {
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
        public List<SafetyCheck> getChecks() { return checks; }
        public void setChecks(List<SafetyCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record CollabSafetyRequest(boolean hasMonitoredStop, boolean hasHandGuiding,
                                       boolean hasSpeedSeparation, boolean hasPowerForceLimit,
                                       boolean hasQuasiStaticAnalysis, boolean hasTransientAnalysis,
                                       boolean hasSafeEndEffector) {}

    public static class MobileSafetyAssessment {
        private String assessmentId;
        private String productId;
        private Instant createdAt;
        private List<SafetyCheck> checks = new ArrayList<>();
        private String overallResult;

        public MobileSafetyAssessment() {}
        public MobileSafetyAssessment(String assessmentId, String productId, Instant createdAt) {
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
        public List<SafetyCheck> getChecks() { return checks; }
        public void setChecks(List<SafetyCheck> c) { this.checks = c; }
        public String getOverallResult() { return overallResult; }
        public void setOverallResult(String r) { this.overallResult = r; }
    }

    public record MobileSafetyRequest(boolean hasPersonDetection, boolean hasSpeedControl,
                                       boolean hasBrakingSystem, boolean hasStabilityTest,
                                       boolean hasEdgeDetection, boolean hasLoadSafety,
                                       boolean hasWarningDevices) {}

    public static class SafetyCertificationStatus {
        private String productId;
        private List<StandardStatus> standards = new ArrayList<>();
        private Instant lastUpdated;

        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public List<StandardStatus> getStandards() { return standards; }
        public void setStandards(List<StandardStatus> s) { this.standards = s; }
        public Instant getLastUpdated() { return lastUpdated; }
        public void setLastUpdated(Instant t) { this.lastUpdated = t; }
    }

    public record StandardStatus(String standard, String description, String status) {}
}
