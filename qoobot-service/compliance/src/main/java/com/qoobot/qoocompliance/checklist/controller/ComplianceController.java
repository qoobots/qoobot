package com.qoobot.qoocompliance.checklist.controller;

import com.qoobot.qoocompliance.aiethics.service.AIEthicsService;
import com.qoobot.qoocompliance.aiethics.service.AIEthicsService.*;
import com.qoobot.qoocompliance.checklist.service.ComplianceChecklistService;
import com.qoobot.qoocompliance.checklist.service.ComplianceChecklistService.*;
import com.qoobot.qoocompliance.consumer.service.ConsumerSafetyService;
import com.qoobot.qoocompliance.consumer.service.ConsumerSafetyService.*;
import com.qoobot.qoocompliance.environmental.service.EnvironmentalService;
import com.qoobot.qoocompliance.environmental.service.EnvironmentalService.*;
import com.qoobot.qoocompliance.management.service.ComplianceManagementService;
import com.qoobot.qoocompliance.management.service.ComplianceManagementService.*;
import com.qoobot.qoocompliance.privacy.service.PrivacyDataService;
import com.qoobot.qoocompliance.privacy.service.PrivacyDataService.*;
import com.qoobot.qoocompliance.safety.service.RobotSafetyService;
import com.qoobot.qoocompliance.safety.service.RobotSafetyService.*;
import com.qoobot.qoocompliance.trade.service.ExportControlService;
import com.qoobot.qoocompliance.trade.service.ExportControlService.*;
import com.qoobot.qoocompliance.wireless.service.WirelessEmcService;
import com.qoobot.qoocompliance.wireless.service.WirelessEmcService.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/compliance")
public class ComplianceController {

    private final ComplianceChecklistService checklistService;
    private final RobotSafetyService safetyService;
    private final WirelessEmcService wirelessService;
    private final PrivacyDataService privacyService;
    private final AIEthicsService aiEthicsService;
    private final ConsumerSafetyService consumerService;
    private final ExportControlService exportControlService;
    private final EnvironmentalService environmentalService;
    private final ComplianceManagementService managementService;

    public ComplianceController(ComplianceChecklistService checklistService,
                                RobotSafetyService safetyService,
                                WirelessEmcService wirelessService,
                                PrivacyDataService privacyService,
                                AIEthicsService aiEthicsService,
                                ConsumerSafetyService consumerService,
                                ExportControlService exportControlService,
                                EnvironmentalService environmentalService,
                                ComplianceManagementService managementService) {
        this.checklistService = checklistService;
        this.safetyService = safetyService;
        this.wirelessService = wirelessService;
        this.privacyService = privacyService;
        this.aiEthicsService = aiEthicsService;
        this.consumerService = consumerService;
        this.exportControlService = exportControlService;
        this.environmentalService = environmentalService;
        this.managementService = managementService;
    }

    // ================================================================
    // 合规检查清单 (已有)
    // ================================================================

    @PostMapping("/checklist")
    public ResponseEntity<ComplianceProject> generateChecklist(
            @RequestBody Map<String, Object> body) {
        String name = (String) body.get("projectName");
        @SuppressWarnings("unchecked")
        List<String> markets = (List<String>) body.get("targetMarkets");
        return ResponseEntity.ok(checklistService.generateChecklist(name, markets));
    }

    @GetMapping("/projects/{projectId}/items")
    public ResponseEntity<List<ComplianceItem>> getItems(
            @PathVariable String projectId,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String status) {
        return ResponseEntity.ok(checklistService.getItems(projectId, category, status));
    }

    @PutMapping("/projects/{projectId}/items/{itemId}")
    public ResponseEntity<ComplianceItem> updateItem(
            @PathVariable String projectId,
            @PathVariable String itemId,
            @RequestBody Map<String, String> body) {
        ComplianceItem updated = checklistService.updateItemStatus(
                projectId, itemId, body.get("status"), body.get("evidence"), body.get("notes"));
        return updated != null ? ResponseEntity.ok(updated) : ResponseEntity.notFound().build();
    }

    @GetMapping("/projects/{projectId}/progress")
    public ResponseEntity<ProjectProgress> getProgress(@PathVariable String projectId) {
        return ResponseEntity.ok(checklistService.getProgress(projectId));
    }

    @GetMapping("/projects/{projectId}/gaps")
    public ResponseEntity<List<ComplianceItem>> identifyGaps(
            @PathVariable String projectId,
            @RequestParam(defaultValue = "ALL") String market) {
        return ResponseEntity.ok(checklistService.identifyGaps(projectId, market));
    }

    @GetMapping("/projects/{projectId}/report")
    public ResponseEntity<ComplianceReport> generateReport(@PathVariable String projectId) {
        return ResponseEntity.ok(checklistService.generateReport(projectId));
    }

    // ================================================================
    // 机器人安全标准
    // ================================================================

    @PostMapping("/safety/iso13482/{productId}")
    public ResponseEntity<SafetyAssessment> assessISO13482(
            @PathVariable String productId, @RequestBody SafetyAssessmentRequest request) {
        return ResponseEntity.ok(safetyService.assessISO13482(productId, request));
    }

    @PostMapping("/safety/iso10218/{productId}")
    public ResponseEntity<SafetyAssessment> assessISO10218(
            @PathVariable String productId, @RequestBody SafetyAssessmentRequest request) {
        return ResponseEntity.ok(safetyService.assessISO10218(productId, request));
    }

    @PostMapping("/safety/iso13849/{productId}")
    public ResponseEntity<PLAssessment> assessISO13849(
            @PathVariable String productId, @RequestBody PLAssessmentRequest request) {
        return ResponseEntity.ok(safetyService.assessISO13849(productId, request));
    }

    @PostMapping("/safety/functional-safety/{productId}")
    public ResponseEntity<SILAssessment> assessFunctionalSafety(
            @PathVariable String productId, @RequestBody SILAssessmentRequest request) {
        return ResponseEntity.ok(safetyService.assessFunctionalSafety(productId, request));
    }

    @PostMapping("/safety/hazop/{productId}")
    public ResponseEntity<HAZOPReport> conductHAZOP(
            @PathVariable String productId, @RequestBody HAZOPRequest request) {
        return ResponseEntity.ok(safetyService.conductHAZOP(productId, request));
    }

    @PostMapping("/safety/fmea/{productId}")
    public ResponseEntity<FMEAReport> conductFMEA(
            @PathVariable String productId, @RequestBody FMEARequest request) {
        return ResponseEntity.ok(safetyService.conductFMEA(productId, request));
    }

    @PostMapping("/safety/collab/{productId}")
    public ResponseEntity<CollabSafetyAssessment> assessCollabSafety(
            @PathVariable String productId, @RequestBody CollabSafetyRequest request) {
        return ResponseEntity.ok(safetyService.assessCollabSafety(productId, request));
    }

    @PostMapping("/safety/mobile/{productId}")
    public ResponseEntity<MobileSafetyAssessment> assessMobileSafety(
            @PathVariable String productId, @RequestBody MobileSafetyRequest request) {
        return ResponseEntity.ok(safetyService.assessMobileSafety(productId, request));
    }

    @GetMapping("/safety/certification/{productId}")
    public ResponseEntity<SafetyCertificationStatus> getSafetyCertStatus(
            @PathVariable String productId) {
        return ResponseEntity.ok(safetyService.getCertificationStatus(productId));
    }

    // ================================================================
    // 无线与电磁兼容
    // ================================================================

    @PostMapping("/wireless/fcc/{productId}")
    public ResponseEntity<CertificationReport> assessFCC(
            @PathVariable String productId, @RequestBody WirelessRequest request) {
        return ResponseEntity.ok(wirelessService.assessFCC(productId, request));
    }

    @PostMapping("/wireless/ce-red/{productId}")
    public ResponseEntity<CertificationReport> assessCERED(
            @PathVariable String productId, @RequestBody WirelessRequest request) {
        return ResponseEntity.ok(wirelessService.assessCERED(productId, request));
    }

    @PostMapping("/wireless/srrc/{productId}")
    public ResponseEntity<CertificationReport> assessSRRC(
            @PathVariable String productId, @RequestBody WirelessRequest request) {
        return ResponseEntity.ok(wirelessService.assessSRRC(productId, request));
    }

    @PostMapping("/wireless/mic/{productId}")
    public ResponseEntity<CertificationReport> assessMIC(
            @PathVariable String productId, @RequestBody WirelessRequest request) {
        return ResponseEntity.ok(wirelessService.assessMIC(productId, request));
    }

    @PostMapping("/wireless/emc/{productId}")
    public ResponseEntity<EmcTestReport> conductEmcTest(
            @PathVariable String productId, @RequestBody EmcTestRequest request) {
        return ResponseEntity.ok(wirelessService.conductEmcTest(productId, request));
    }

    @PostMapping("/wireless/coexistence/{productId}")
    public ResponseEntity<CoexistenceReport> assessCoexistence(
            @PathVariable String productId, @RequestBody CoexistenceRequest request) {
        return ResponseEntity.ok(wirelessService.assessCoexistence(productId, request));
    }

    @GetMapping("/wireless/dashboard/{productId}")
    public ResponseEntity<WirelessCertDashboard> getWirelessDashboard(
            @PathVariable String productId) {
        return ResponseEntity.ok(wirelessService.getDashboard(productId));
    }

    // ================================================================
    // 隐私与数据保护
    // ================================================================

    @PostMapping("/privacy/gdpr/{productId}")
    public ResponseEntity<PrivacyAssessment> assessGDPR(
            @PathVariable String productId, @RequestBody PrivacyRequest request) {
        return ResponseEntity.ok(privacyService.assessGDPR(productId, request));
    }

    @PostMapping("/privacy/ccpa/{productId}")
    public ResponseEntity<PrivacyAssessment> assessCCPA(
            @PathVariable String productId, @RequestBody PrivacyRequest request) {
        return ResponseEntity.ok(privacyService.assessCCPA(productId, request));
    }

    @PostMapping("/privacy/pipl/{productId}")
    public ResponseEntity<PrivacyAssessment> assessPIPL(
            @PathVariable String productId, @RequestBody PrivacyRequest request) {
        return ResponseEntity.ok(privacyService.assessPIPL(productId, request));
    }

    @PostMapping("/privacy/dpia/{productId}")
    public ResponseEntity<DPIAReport> conductDPIA(
            @PathVariable String productId, @RequestBody DPIARequest request) {
        return ResponseEntity.ok(privacyService.conductDPIA(productId, request));
    }

    @PostMapping("/privacy/sensor/{productId}")
    public ResponseEntity<SensorPrivacyReport> assessSensorPrivacy(
            @PathVariable String productId, @RequestBody SensorPrivacyRequest request) {
        return ResponseEntity.ok(privacyService.assessSensorPrivacy(productId, request));
    }

    @PostMapping("/privacy/cross-border/{productId}")
    public ResponseEntity<CrossBorderReport> assessCrossBorder(
            @PathVariable String productId, @RequestBody CrossBorderRequest request) {
        return ResponseEntity.ok(privacyService.assessCrossBorder(productId, request));
    }

    @GetMapping("/privacy/dsr-dashboard/{productId}")
    public ResponseEntity<DSRDashboard> getDSRDashboard(@PathVariable String productId) {
        return ResponseEntity.ok(privacyService.getDSRDashboard(productId));
    }

    // ================================================================
    // AI 伦理与合规
    // ================================================================

    @PostMapping("/ai/eu-ai-act/{productId}")
    public ResponseEntity<AIActAssessment> assessEUAIAct(
            @PathVariable String productId, @RequestBody AIActRequest request) {
        return ResponseEntity.ok(aiEthicsService.assessEUAIAct(productId, request));
    }

    @PostMapping("/ai/transparency/{productId}")
    public ResponseEntity<TransparencyReport> assessTransparency(
            @PathVariable String productId, @RequestBody TransparencyRequest request) {
        return ResponseEntity.ok(aiEthicsService.assessTransparency(productId, request));
    }

    @PostMapping("/ai/bias/{productId}")
    public ResponseEntity<BiasReport> assessBias(
            @PathVariable String productId, @RequestBody BiasRequest request) {
        return ResponseEntity.ok(aiEthicsService.assessBias(productId, request));
    }

    @PostMapping("/ai/ethical-review/{productId}")
    public ResponseEntity<EthicalReviewReport> conductEthicalReview(
            @PathVariable String productId, @RequestBody EthicalReviewRequest request) {
        return ResponseEntity.ok(aiEthicsService.conductEthicalReview(productId, request));
    }

    @GetMapping("/ai/dashboard/{productId}")
    public ResponseEntity<AIEthicsDashboard> getAIEthicsDashboard(
            @PathVariable String productId) {
        return ResponseEntity.ok(aiEthicsService.getDashboard(productId));
    }

    // ================================================================
    // 消费者安全
    // ================================================================

    @PostMapping("/consumer/machinery/{productId}")
    public ResponseEntity<ConsumerSafetyReport> assessMachineryDirective(
            @PathVariable String productId, @RequestBody MachineryRequest request) {
        return ResponseEntity.ok(consumerService.assessMachineryDirective(productId, request));
    }

    @PostMapping("/consumer/lvd/{productId}")
    public ResponseEntity<ConsumerSafetyReport> assessLVD(
            @PathVariable String productId, @RequestBody LVDRequest request) {
        return ResponseEntity.ok(consumerService.assessLVD(productId, request));
    }

    @PostMapping("/consumer/ul/{productId}")
    public ResponseEntity<ConsumerSafetyReport> assessUL(
            @PathVariable String productId, @RequestBody ULRequest request) {
        return ResponseEntity.ok(consumerService.assessUL(productId, request));
    }

    @PostMapping("/consumer/children/{productId}")
    public ResponseEntity<ConsumerSafetyReport> assessChildrenSafety(
            @PathVariable String productId, @RequestBody ChildrenSafetyRequest request) {
        return ResponseEntity.ok(consumerService.assessChildrenSafety(productId, request));
    }

    @PostMapping("/consumer/liability/{productId}")
    public ResponseEntity<LiabilityAssessment> assessProductLiability(
            @PathVariable String productId, @RequestBody LiabilityRequest request) {
        return ResponseEntity.ok(consumerService.assessProductLiability(productId, request));
    }

    @GetMapping("/consumer/dashboard/{productId}")
    public ResponseEntity<ConsumerSafetyDashboard> getConsumerDashboard(
            @PathVariable String productId) {
        return ResponseEntity.ok(consumerService.getDashboard(productId));
    }

    // ================================================================
    // 出口管制与贸易
    // ================================================================

    @PostMapping("/trade/eccn/{productId}")
    public ResponseEntity<ECCNReport> classifyECCN(
            @PathVariable String productId, @RequestBody ECCNRequest request) {
        return ResponseEntity.ok(exportControlService.classifyECCN(productId, request));
    }

    @PostMapping("/trade/encryption/{productId}")
    public ResponseEntity<EncryptionReport> assessEncryption(
            @PathVariable String productId, @RequestBody EncryptionRequest request) {
        return ResponseEntity.ok(exportControlService.assessEncryption(productId, request));
    }

    @PostMapping("/trade/screening/{productId}")
    public ResponseEntity<ScreeningReport> screenEntities(
            @PathVariable String productId, @RequestBody ScreeningRequest request) {
        return ResponseEntity.ok(exportControlService.screenEntities(productId, request));
    }

    @PostMapping("/trade/sanctions/{productId}")
    public ResponseEntity<SanctionsReport> assessSanctions(
            @PathVariable String productId, @RequestBody SanctionsRequest request) {
        return ResponseEntity.ok(exportControlService.assessSanctions(productId, request));
    }

    @GetMapping("/trade/dashboard/{productId}")
    public ResponseEntity<TradeDashboard> getTradeDashboard(@PathVariable String productId) {
        return ResponseEntity.ok(exportControlService.getDashboard(productId));
    }

    // ================================================================
    // 环保与可持续
    // ================================================================

    @PostMapping("/environmental/rohs/{productId}")
    public ResponseEntity<EnvironmentalReport> assessRoHS(
            @PathVariable String productId, @RequestBody RoHSRequest request) {
        return ResponseEntity.ok(environmentalService.assessRoHS(productId, request));
    }

    @PostMapping("/environmental/weee/{productId}")
    public ResponseEntity<EnvironmentalReport> assessWEEE(
            @PathVariable String productId, @RequestBody WEEERequest request) {
        return ResponseEntity.ok(environmentalService.assessWEEE(productId, request));
    }

    @PostMapping("/environmental/reach/{productId}")
    public ResponseEntity<EnvironmentalReport> assessREACH(
            @PathVariable String productId, @RequestBody REACHRequest request) {
        return ResponseEntity.ok(environmentalService.assessREACH(productId, request));
    }

    @PostMapping("/environmental/carbon/{productId}")
    public ResponseEntity<CarbonFootprintReport> calculateCarbonFootprint(
            @PathVariable String productId, @RequestBody CarbonRequest request) {
        return ResponseEntity.ok(environmentalService.calculateCarbonFootprint(productId, request));
    }

    @PostMapping("/environmental/energy/{productId}")
    public ResponseEntity<EnergyEfficiencyReport> assessEnergyEfficiency(
            @PathVariable String productId, @RequestBody EnergyRequest request) {
        return ResponseEntity.ok(environmentalService.assessEnergyEfficiency(productId, request));
    }

    @GetMapping("/environmental/dashboard/{productId}")
    public ResponseEntity<EnvironmentalDashboard> getEnvironmentalDashboard(
            @PathVariable String productId) {
        return ResponseEntity.ok(environmentalService.getDashboard(productId));
    }

    // ================================================================
    // 合规管理
    // ================================================================

    @GetMapping("/management/templates")
    public ResponseEntity<List<DocTemplate>> getTemplates(
            @RequestParam(required = false) String market) {
        return ResponseEntity.ok(managementService.getTemplates(market));
    }

    @PostMapping("/management/cert-progress/{productId}")
    public ResponseEntity<CertProgress> createCertProgress(
            @PathVariable String productId, @RequestBody CertProgressRequest request) {
        return ResponseEntity.ok(managementService.createCertProgress(productId, request));
    }

    @PutMapping("/management/cert-progress/{trackingId}")
    public ResponseEntity<CertProgress> updateCertMilestone(
            @PathVariable String trackingId, @RequestBody MilestoneUpdate update) {
        CertProgress progress = managementService.updateCertMilestone(trackingId, update);
        return progress != null ? ResponseEntity.ok(progress) : ResponseEntity.notFound().build();
    }

    @GetMapping("/management/cert-progress/{productId}")
    public ResponseEntity<List<CertProgress>> getProductCertifications(
            @PathVariable String productId) {
        return ResponseEntity.ok(managementService.getProductCertifications(productId));
    }

    @PostMapping("/management/reviews/{productId}")
    public ResponseEntity<ReviewRecord> createReview(
            @PathVariable String productId, @RequestBody ReviewRequest request) {
        return ResponseEntity.ok(managementService.createReview(productId, request));
    }

    @GetMapping("/management/reviews/{productId}")
    public ResponseEntity<List<ReviewRecord>> getProductReviews(
            @PathVariable String productId,
            @RequestParam(required = false) String status) {
        return ResponseEntity.ok(managementService.getProductReviews(productId, status));
    }

    @PutMapping("/management/reviews/{productId}/{reviewId}")
    public ResponseEntity<ReviewRecord> updateReviewStatus(
            @PathVariable String productId, @PathVariable String reviewId,
            @RequestBody Map<String, String> body) {
        ReviewRecord record = managementService.updateReviewStatus(
                productId, reviewId, body.get("status"));
        return record != null ? ResponseEntity.ok(record) : ResponseEntity.notFound().build();
    }

    @GetMapping("/management/reviews/{productId}/summary")
    public ResponseEntity<ReviewSummary> getReviewSummary(@PathVariable String productId) {
        return ResponseEntity.ok(managementService.getReviewSummary(productId));
    }

    @GetMapping("/management/dashboard/{productId}")
    public ResponseEntity<ComplianceDashboard> getManagementDashboard(
            @PathVariable String productId) {
        return ResponseEntity.ok(managementService.getDashboard(productId));
    }
}
