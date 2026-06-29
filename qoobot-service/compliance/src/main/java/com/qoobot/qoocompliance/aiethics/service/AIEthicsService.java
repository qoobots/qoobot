package com.qoobot.qoocompliance.aiethics.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;

/**
 * AI Ethics & Compliance service.
 *
 * Covers:
 * - EU AI Act compliance
 * - Algorithm transparency & explainability
 * - Bias detection & fairness assessment
 * - Ethical review process
 * - AI risk classification
 */
@Service
public class AIEthicsService {

    // ===================================================================
    // EU AI Act Compliance
    // ===================================================================

    public AIActAssessment assessEUAIAct(String productId, AIActRequest request) {
        AIActAssessment assessment = new AIActAssessment(
                UUID.randomUUID().toString(), productId, "EU AI Act",
                Instant.now()
        );

        List<AIComplianceCheck> checks = new ArrayList<>();

        // Step 1: Risk Classification
        String riskLevel = classifyRiskLevel(request);
        checks.add(new AIComplianceCheck("AIA-RSK-001", "AI 系统风险分类",
                String.format("系统分类: %s", riskLevel),
                "COMPLETED", "P0"));

        // Prohibited practices
        checks.add(new AIComplianceCheck("AIA-PRO-001", "禁止的 AI 实践检查",
                "无操纵性/剥削性/社会评分/实时远程生物识别等禁止行为",
                request.hasProhibitedPractices() ? "FAIL" : "PASS", "P0"));

        // High-risk requirements
        if ("HIGH_RISK".equals(riskLevel)) {
            checks.addAll(highRiskRequirements(request));
        }

        // Transparency obligations
        checks.addAll(transparencyRequirements(request, riskLevel));

        // GPAI (General Purpose AI) requirements
        if (request.isGPAI()) {
            checks.addAll(gpaiRequirements(request));
        }

        assessment.setRiskLevel(riskLevel);
        assessment.setChecks(checks);
        assessment.setCompliant(checks.stream().noneMatch(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority())));
        return assessment;
    }

    private List<AIComplianceCheck> highRiskRequirements(AIActRequest request) {
        List<AIComplianceCheck> checks = new ArrayList<>();

        checks.add(new AIComplianceCheck("AIA-HR-001", "风险管理体系",
                "建立、实施、记录和维护 AI 风险管理体系",
                request.hasRiskManagementSystem() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-002", "数据治理",
                "训练/验证/测试数据满足质量、代表性、无偏见要求",
                request.hasDataGovernance() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-003", "技术文档",
                "编制技术文档以证明符合性",
                request.hasTechnicalDoc() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-004", "记录保存",
                "自动记录系统运行日志（可追溯性）",
                request.hasRecordKeeping() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-005", "透明度与信息提供",
                "向部署者提供清晰充分的使用信息",
                request.hasTransparencyInfo() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-006", "人工监督",
                "设计有效的人工监督机制（HITL/HOTL/HOOTL）",
                request.hasHumanOversight() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-007", "准确性/鲁棒性/网络安全",
                "系统达到适当的准确性、鲁棒性和网络安全水平",
                request.hasAccuracyRobustness() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-008", "CE 标识",
                "高风险 AI 系统需加贴 CE 标识",
                request.hasCEMarking() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-009", "EU 数据库注册",
                "高风险 AI 系统在 EU 数据库注册",
                request.hasEURegistration() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-010", "合格评定",
                "通过公告机构合格评定或内部控制",
                request.hasConformityAssessment() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-HR-011", "严重事件报告",
                "严重事件和故障及时报告监管机构",
                request.hasIncidentReporting() ? "PASS" : "FAIL", "P1"));

        return checks;
    }

    private List<AIComplianceCheck> transparencyRequirements(AIActRequest request, String riskLevel) {
        List<AIComplianceCheck> checks = new ArrayList<>();

        checks.add(new AIComplianceCheck("AIA-TRN-001", "AI 交互告知",
                "与 AI 系统交互时告知用户（除非明显）",
                request.hasUserNotification() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-TRN-002", "情感识别/生物分类告知",
                "情感识别系统或生物分类系统需告知暴露用户",
                request.hasEmotionBioDisclosure() ? "PASS" : "FAIL", "P1"));
        checks.add(new AIComplianceCheck("AIA-TRN-003", "深度伪造标记",
                "AI 生成/操纵的音频/图像/视频需标记为人工生成",
                request.hasDeepfakeLabeling() ? "PASS" : "FAIL", "P1"));
        checks.add(new AIComplianceCheck("AIA-TRN-004", "AI 生成文本标记",
                "AI 生成的文本内容需标注",
                request.hasAIContentLabeling() ? "PASS" : "FAIL", "P2"));

        return checks;
    }

    private List<AIComplianceCheck> gpaiRequirements(AIActRequest request) {
        List<AIComplianceCheck> checks = new ArrayList<>();

        checks.add(new AIComplianceCheck("AIA-GPAI-001", "GPAI 技术文档",
                "提供模型训练/测试/评估等技术文档",
                request.hasGPAITechDoc() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-GPAI-002", "GPAI 下游集成信息",
                "向下游提供者提供集成所需信息",
                request.hasDownstreamInfo() ? "PASS" : "FAIL", "P0"));
        checks.add(new AIComplianceCheck("AIA-GPAI-003", "版权政策",
                "制定尊重版权的政策",
                request.hasCopyrightPolicy() ? "PASS" : "FAIL", "P1"));
        checks.add(new AIComplianceCheck("AIA-GPAI-004", "训练数据摘要",
                "公开训练数据内容摘要",
                request.hasTrainingDataSummary() ? "PASS" : "FAIL", "P1"));

        return checks;
    }

    private String classifyRiskLevel(AIActRequest request) {
        if (request.hasProhibitedPractices()) return "PROHIBITED";
        if (request.isHighRisk()) return "HIGH_RISK";
        if (request.isLimitedRisk()) return "LIMITED_RISK";
        return "MINIMAL_RISK";
    }

    // ===================================================================
    // Algorithm Transparency & Explainability
    // ===================================================================

    public TransparencyReport assessTransparency(String productId, TransparencyRequest request) {
        TransparencyReport report = new TransparencyReport(
                UUID.randomUUID().toString(), productId, Instant.now()
        );

        List<TransparencyCheck> checks = new ArrayList<>();

        // Model card
        checks.add(new TransparencyCheck("TRN-MOD-001", "模型卡片 (Model Card)",
                "提供标准模型卡片：架构/参数/训练数据/性能/局限性",
                request.hasModelCard() ? "PASS" : "FAIL", "P0"));

        // Explainability
        checks.add(new TransparencyCheck("TRN-EXP-001", "全局可解释性",
                "特征重要性/SHAP值/注意力可视化",
                request.hasGlobalExplainability() ? "PASS" : "FAIL", "P0"));
        checks.add(new TransparencyCheck("TRN-EXP-002", "局部可解释性",
                "单个推理结果的可解释性（LIME/SHAP/Integrated Gradients）",
                request.hasLocalExplainability() ? "PASS" : "FAIL", "P0"));
        checks.add(new TransparencyCheck("TRN-EXP-003", "反事实解释",
                "提供反事实解释（最小改变→不同结果）",
                request.hasCounterfactual() ? "PASS" : "FAIL", "P1"));

        // Decision documentation
        checks.add(new TransparencyCheck("TRN-DOC-001", "决策逻辑文档",
                "AI 决策逻辑和推理链文档化",
                request.hasDecisionLogicDoc() ? "PASS" : "FAIL", "P0"));
        checks.add(new TransparencyCheck("TRN-DOC-002", "置信度/不确定性",
                "提供推理结果的置信度或不确定性估计",
                request.hasConfidenceEstimation() ? "PASS" : "FAIL", "P1"));
        checks.add(new TransparencyCheck("TRN-DOC-003", "边界条件文档",
                "记录系统适用/不适用场景和边界条件",
                request.hasBoundaryConditions() ? "PASS" : "FAIL", "P1"));

        // Appeal mechanism
        checks.add(new TransparencyCheck("TRN-APL-001", "人工复审机制",
                "对 AI 决策提供人工复审渠道",
                request.hasHumanReview() ? "PASS" : "FAIL", "P0"));

        report.setChecks(checks);
        report.setOverallScore(calculateScore(checks));
        return report;
    }

    // ===================================================================
    // Bias Detection & Fairness Assessment
    // ===================================================================

    public BiasReport assessBias(String productId, BiasRequest request) {
        BiasReport report = new BiasReport(
                UUID.randomUUID().toString(), productId, request.modelName(),
                Instant.now()
        );

        List<BiasMetric> metrics = new ArrayList<>();

        // Demographic parity
        metrics.add(new BiasMetric("BIAS-DEM-001", "人口统计均等 (Demographic Parity)",
                String.format("%.4f", request.demographicParity()),
                request.demographicParity() < 0.05 ? "PASS" : "FAIL",
                "P0", "不同群体正例预测率差异 < 5%"));

        // Equal opportunity
        metrics.add(new BiasMetric("BIAS-EOP-001", "机会均等 (Equal Opportunity)",
                String.format("%.4f", request.equalOpportunity()),
                request.equalOpportunity() < 0.05 ? "PASS" : "FAIL",
                "P0", "不同群体真阳性率差异 < 5%"));

        // Equalized odds
        metrics.add(new BiasMetric("BIAS-EOD-001", "均等几率 (Equalized Odds)",
                String.format("%.4f", request.equalizedOdds()),
                request.equalizedOdds() < 0.10 ? "PASS" : "FAIL",
                "P1", "TPR + FPR 差异 < 10%"));

        // Disparate impact
        metrics.add(new BiasMetric("BIAS-DIS-001", "差异性影响 (Disparate Impact)",
                String.format("%.4f", request.disparateImpact()),
                request.disparateImpact() >= 0.80 ? "PASS" : "FAIL",
                "P0", "最差群体/最佳群体正面结果比 >= 0.8 (4/5规则)"));

        // Intersectional fairness
        metrics.add(new BiasMetric("BIAS-INT-001", "交叉公平性 (Intersectional)",
                String.format("%.4f", request.intersectionalFairness()),
                request.intersectionalFairness() < 0.10 ? "PASS" : "FAIL",
                "P1", "多属性交叉群体间最大差异 < 10%"));

        // Representation check
        metrics.add(new BiasMetric("BIAS-REP-001", "训练数据代表性",
                String.format("%.2f%%", request.representationScore() * 100),
                request.representationScore() >= 0.80 ? "PASS" : "FAIL",
                "P0", "训练数据各群体覆盖率 >= 80%"));

        // Bias mitigation
        metrics.add(new BiasMetric("BIAS-MIT-001", "偏见缓解措施",
                request.hasBiasMitigation() ? "已部署" : "未部署",
                request.hasBiasMitigation() ? "PASS" : "FAIL",
                "P0", "已部署重采样/重加权/对抗去偏等方法"));

        // Continuous monitoring
        metrics.add(new BiasMetric("BIAS-MON-001", "持续偏见监控",
                request.hasContinuousMonitoring() ? "已部署" : "未部署",
                request.hasContinuousMonitoring() ? "PASS" : "FAIL",
                "P1", "生产环境持续监控偏见指标漂移"));

        report.setMetrics(metrics);
        report.setOverallPassed(metrics.stream().noneMatch(m -> "FAIL".equals(m.result()) && "P0".equals(m.priority())));
        return report;
    }

    // ===================================================================
    // Ethical Review Process
    // ===================================================================

    public EthicalReviewReport conductEthicalReview(String productId, EthicalReviewRequest request) {
        EthicalReviewReport report = new EthicalReviewReport(
                UUID.randomUUID().toString(), productId, request.reviewType(),
                Instant.now()
        );

        List<EthicalCheck> checks = new ArrayList<>();

        // Beneficence
        checks.add(new EthicalCheck("ETH-BEN-001", "有益性 (Beneficence)",
                "AI 系统明确为人类带来益处，不造成伤害",
                request.isBeneficial() ? "PASS" : "FAIL", "P0"));

        // Non-maleficence
        checks.add(new EthicalCheck("ETH-NON-001", "不伤害 (Non-maleficence)",
                "已进行安全评估，确认不会造成可预见伤害",
                request.hasSafetyAssessment() ? "PASS" : "FAIL", "P0"));

        // Autonomy
        checks.add(new EthicalCheck("ETH-AUT-001", "尊重自主 (Autonomy)",
                "用户保留最终决策权，AI 为辅助工具",
                request.respectsAutonomy() ? "PASS" : "FAIL", "P0"));

        // Justice
        checks.add(new EthicalCheck("ETH-JUS-001", "公正性 (Justice)",
                "系统公平对待所有用户，无歧视性结果",
                request.isFair() ? "PASS" : "FAIL", "P0"));

        // Transparency
        checks.add(new EthicalCheck("ETH-TRN-001", "透明性 (Transparency)",
                "系统功能和局限性对用户透明",
                request.isTransparent() ? "PASS" : "FAIL", "P0"));

        // Accountability
        checks.add(new EthicalCheck("ETH-ACC-001", "可问责性 (Accountability)",
                "明确 AI 决策的责任人和申诉机制",
                request.hasAccountability() ? "PASS" : "FAIL", "P0"));

        // Privacy
        checks.add(new EthicalCheck("ETH-PRI-001", "隐私保护 (Privacy)",
                "AI 系统符合隐私保护要求",
                request.respectsPrivacy() ? "PASS" : "FAIL", "P0"));

        // Human values alignment
        checks.add(new EthicalCheck("ETH-VAL-001", "人类价值观对齐",
                "系统行为与人类价值观和社会规范一致",
                request.isValuesAligned() ? "PASS" : "FAIL", "P1"));

        // Stakeholder involvement
        checks.add(new EthicalCheck("ETH-STK-001", "利益相关者参与",
                "伦理审查涉及多方利益相关者（用户/社区/领域专家）",
                request.hasStakeholderInvolvement() ? "PASS" : "FAIL", "P1"));

        // Review committee
        checks.add(new EthicalCheck("ETH-COM-001", "伦理审查委员会",
                "由独立伦理审查委员会审查通过",
                request.hasEthicsCommittee() ? "PASS" : "FAIL", "P0"));

        report.setChecks(checks);
        report.setApproved(checks.stream().noneMatch(c -> "FAIL".equals(c.result()) && "P0".equals(c.priority())));
        report.setReviewers(request.reviewers());
        return report;
    }

    // ===================================================================
    // AI Ethics Dashboard
    // ===================================================================

    public AIEthicsDashboard getDashboard(String productId) {
        AIEthicsDashboard dashboard = new AIEthicsDashboard();
        dashboard.setProductId(productId);

        dashboard.setComplianceStatus(List.of(
                new RegulationStatus("EU AI Act", "欧盟人工智能法案", "NOT_ASSESSED",
                        "2026-08-02", "分阶段生效"),
                new RegulationStatus("NIST AI RMF", "美国 AI 风险管理框架", "NOT_ASSESSED",
                        "2023-01-26", "自愿性框架"),
                new RegulationStatus("AI Safety Summit", "全球 AI 安全峰会承诺", "NOT_ASSESSED",
                        "2023-11-01", "政治承诺"),
                new RegulationStatus("CN AI Regs", "中国生成式 AI 管理规定", "NOT_ASSESSED",
                        "2023-08-15", "已生效"),
                new RegulationStatus("ISO/IEC 42001", "AI 管理体系标准", "NOT_ASSESSED",
                        "2023-12-18", "自愿性标准")
        ));

        dashboard.setLastUpdated(Instant.now());
        return dashboard;
    }

    // ===================================================================
    // Helpers
    // ===================================================================

    private double calculateScore(List<TransparencyCheck> checks) {
        long total = checks.size();
        long passed = checks.stream().filter(c -> "PASS".equals(c.result())).count();
        return total > 0 ? (double) passed / total * 100 : 0;
    }

    // ===================================================================
    // DTOs
    // ===================================================================

    public static class AIActAssessment {
        private String assessmentId;
        private String productId;
        private String regulation;
        private Instant createdAt;
        private String riskLevel;
        private List<AIComplianceCheck> checks = new ArrayList<>();
        private boolean compliant;

        public AIActAssessment() {}
        public AIActAssessment(String assessmentId, String productId, String regulation, Instant createdAt) {
            this.assessmentId = assessmentId;
            this.productId = productId;
            this.regulation = regulation;
            this.createdAt = createdAt;
        }

        public String getAssessmentId() { return assessmentId; }
        public void setAssessmentId(String id) { this.assessmentId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getRegulation() { return regulation; }
        public void setRegulation(String r) { this.regulation = r; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public String getRiskLevel() { return riskLevel; }
        public void setRiskLevel(String r) { this.riskLevel = r; }
        public List<AIComplianceCheck> getChecks() { return checks; }
        public void setChecks(List<AIComplianceCheck> c) { this.checks = c; }
        public boolean isCompliant() { return compliant; }
        public void setCompliant(boolean c) { this.compliant = c; }
    }

    public record AIComplianceCheck(String checkId, String title, String description,
                                     String result, String priority) {}

    public record AIActRequest(boolean hasProhibitedPractices, boolean isHighRisk,
                                boolean isLimitedRisk, boolean isGPAI,
                                boolean hasRiskManagementSystem, boolean hasDataGovernance,
                                boolean hasTechnicalDoc, boolean hasRecordKeeping,
                                boolean hasTransparencyInfo, boolean hasHumanOversight,
                                boolean hasAccuracyRobustness, boolean hasCEMarking,
                                boolean hasEURegistration, boolean hasConformityAssessment,
                                boolean hasIncidentReporting, boolean hasUserNotification,
                                boolean hasEmotionBioDisclosure, boolean hasDeepfakeLabeling,
                                boolean hasAIContentLabeling, boolean hasGPAITechDoc,
                                boolean hasDownstreamInfo, boolean hasCopyrightPolicy,
                                boolean hasTrainingDataSummary) {}

    public static class TransparencyReport {
        private String reportId;
        private String productId;
        private Instant createdAt;
        private List<TransparencyCheck> checks = new ArrayList<>();
        private double overallScore;

        public TransparencyReport() {}
        public TransparencyReport(String reportId, String productId, Instant createdAt) {
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
        public List<TransparencyCheck> getChecks() { return checks; }
        public void setChecks(List<TransparencyCheck> c) { this.checks = c; }
        public double getOverallScore() { return overallScore; }
        public void setOverallScore(double s) { this.overallScore = s; }
    }

    public record TransparencyCheck(String checkId, String title, String description,
                                     String result, String priority) {}

    public record TransparencyRequest(boolean hasModelCard, boolean hasGlobalExplainability,
                                       boolean hasLocalExplainability, boolean hasCounterfactual,
                                       boolean hasDecisionLogicDoc, boolean hasConfidenceEstimation,
                                       boolean hasBoundaryConditions, boolean hasHumanReview) {}

    public static class BiasReport {
        private String reportId;
        private String productId;
        private String modelName;
        private Instant createdAt;
        private List<BiasMetric> metrics = new ArrayList<>();
        private boolean overallPassed;

        public BiasReport() {}
        public BiasReport(String reportId, String productId, String modelName, Instant createdAt) {
            this.reportId = reportId;
            this.productId = productId;
            this.modelName = modelName;
            this.createdAt = createdAt;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getModelName() { return modelName; }
        public void setModelName(String n) { this.modelName = n; }
        public Instant getCreatedAt() { return createdAt; }
        public void setCreatedAt(Instant t) { this.createdAt = t; }
        public List<BiasMetric> getMetrics() { return metrics; }
        public void setMetrics(List<BiasMetric> m) { this.metrics = m; }
        public boolean isOverallPassed() { return overallPassed; }
        public void setOverallPassed(boolean p) { this.overallPassed = p; }
    }

    public record BiasMetric(String metricId, String metricName, String value,
                              String result, String priority, String threshold) {}

    public record BiasRequest(String modelName, double demographicParity, double equalOpportunity,
                               double equalizedOdds, double disparateImpact, double intersectionalFairness,
                               double representationScore, boolean hasBiasMitigation,
                               boolean hasContinuousMonitoring) {}

    public static class EthicalReviewReport {
        private String reportId;
        private String productId;
        private String reviewType;
        private Instant reviewDate;
        private List<EthicalCheck> checks = new ArrayList<>();
        private boolean approved;
        private List<String> reviewers = new ArrayList<>();

        public EthicalReviewReport() {}
        public EthicalReviewReport(String reportId, String productId, String reviewType, Instant reviewDate) {
            this.reportId = reportId;
            this.productId = productId;
            this.reviewType = reviewType;
            this.reviewDate = reviewDate;
        }

        public String getReportId() { return reportId; }
        public void setReportId(String id) { this.reportId = id; }
        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public String getReviewType() { return reviewType; }
        public void setReviewType(String t) { this.reviewType = t; }
        public Instant getReviewDate() { return reviewDate; }
        public void setReviewDate(Instant d) { this.reviewDate = d; }
        public List<EthicalCheck> getChecks() { return checks; }
        public void setChecks(List<EthicalCheck> c) { this.checks = c; }
        public boolean isApproved() { return approved; }
        public void setApproved(boolean a) { this.approved = a; }
        public List<String> getReviewers() { return reviewers; }
        public void setReviewers(List<String> r) { this.reviewers = r; }
    }

    public record EthicalCheck(String checkId, String title, String description,
                                String result, String priority) {}

    public record EthicalReviewRequest(String reviewType, boolean isBeneficial,
                                        boolean hasSafetyAssessment, boolean respectsAutonomy,
                                        boolean isFair, boolean isTransparent,
                                        boolean hasAccountability, boolean respectsPrivacy,
                                        boolean isValuesAligned, boolean hasStakeholderInvolvement,
                                        boolean hasEthicsCommittee, List<String> reviewers) {}

    public static class AIEthicsDashboard {
        private String productId;
        private List<RegulationStatus> complianceStatus = new ArrayList<>();
        private Instant lastUpdated;

        public String getProductId() { return productId; }
        public void setProductId(String id) { this.productId = id; }
        public List<RegulationStatus> getComplianceStatus() { return complianceStatus; }
        public void setComplianceStatus(List<RegulationStatus> s) { this.complianceStatus = s; }
        public Instant getLastUpdated() { return lastUpdated; }
        public void setLastUpdated(Instant t) { this.lastUpdated = t; }
    }

    public record RegulationStatus(String regulation, String description, String status,
                                    String effectiveDate, String notes) {}
}
