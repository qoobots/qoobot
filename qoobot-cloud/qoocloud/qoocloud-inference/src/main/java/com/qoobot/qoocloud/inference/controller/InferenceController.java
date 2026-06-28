package com.qoobot.qoocloud.inference.controller;

import com.qoobot.qoocloud.inference.entity.InferenceModel;
import com.qoobot.qoocloud.inference.service.*;
import com.qoobot.qoocloud.inference.service.InferenceService.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for remote inference.
 */
@RestController
@RequestMapping("/api/v1/inference")
public class InferenceController {

    private final InferenceService inferenceService;
    private final ModelManager modelManager;
    private final AuditService auditService;
    private final PromptService promptService;

    public InferenceController(InferenceService inferenceService,
                                ModelManager modelManager,
                                AuditService auditService,
                                PromptService promptService) {
        this.inferenceService = inferenceService;
        this.modelManager = modelManager;
        this.auditService = auditService;
        this.promptService = promptService;
    }

    // ================================================================
    // 推理
    // ================================================================

    /**
     * Run inference.
     */
    @PostMapping
    public ResponseEntity<InferenceResponse> infer(@RequestBody Map<String, Object> body) {
        InferenceRequest request = new InferenceRequest(
                (String) body.get("model"),
                (String) body.getOrDefault("version", "latest").toString(),
                (String) body.get("input"),
                (Map<String, Object>) body.getOrDefault("parameters", Map.of()),
                (boolean) body.getOrDefault("stream", false)
        );

        InferenceResponse response = inferenceService.infer(request);
        if (response.isSuccess()) {
            return ResponseEntity.ok(response);
        } else {
            return ResponseEntity.badRequest().body(response);
        }
    }

    // ================================================================
    // 模型管理
    // ================================================================

    /**
     * List hosted models.
     */
    @GetMapping("/models")
    public ResponseEntity<List<InferenceModel>> listModels() {
        return ResponseEntity.ok(inferenceService.listModels());
    }

    /**
     * Register a new model.
     */
    @PostMapping("/models")
    public ResponseEntity<InferenceModel> registerModel(@RequestBody InferenceModel model) {
        return ResponseEntity.ok(inferenceService.registerModel(model));
    }

    /**
     * Hot-swap model version (zero-downtime).
     */
    @PostMapping("/models/{modelName}/hotswap")
    public ResponseEntity<ModelManager.HotSwapResult> hotSwapModel(
            @PathVariable String modelName,
            @RequestBody Map<String, Object> body) {
        String targetVersion = (String) body.get("targetVersion");
        ModelManager.HotSwapStrategy strategy = ModelManager.HotSwapStrategy.valueOf(
                (String) body.getOrDefault("strategy", "BLUE_GREEN"));
        return ResponseEntity.ok(modelManager.hotSwapModel(modelName, targetVersion, strategy));
    }

    /**
     * Rollback model to previous version.
     */
    @PostMapping("/models/{modelName}/rollback")
    public ResponseEntity<ModelManager.HotSwapResult> rollbackModel(
            @PathVariable String modelName) {
        return ResponseEntity.ok(modelManager.rollbackModel(modelName));
    }

    /**
     * Get hot-swap status.
     */
    @GetMapping("/models/hotswap/{swapId}")
    public ResponseEntity<ModelManager.HotSwapStatus> getSwapStatus(
            @PathVariable String swapId) {
        ModelManager.HotSwapStatus status = modelManager.getSwapStatus(swapId);
        return status != null ? ResponseEntity.ok(status) : ResponseEntity.notFound().build();
    }

    /**
     * Get all active model versions.
     */
    @GetMapping("/models/versions")
    public ResponseEntity<Map<String, String>> getActiveVersions() {
        return ResponseEntity.ok(modelManager.getAllActiveVersions());
    }

    // ================================================================
    // 推理路由
    // ================================================================

    /**
     * Get inference routing decision.
     */
    @GetMapping("/routing")
    public ResponseEntity<RoutingDecision> getRouting(
            @RequestParam String taskType,
            @RequestParam(defaultValue = "0") long complexity) {
        return ResponseEntity.ok(inferenceService.decideRouting(taskType, complexity));
    }

    /**
     * Get inference statistics.
     */
    @GetMapping("/stats")
    public ResponseEntity<InferenceStats> getStats() {
        return ResponseEntity.ok(inferenceService.getStats());
    }

    // ================================================================
    // 推理审计
    // ================================================================

    /**
     * Get audit logs.
     */
    @GetMapping("/audit")
    public ResponseEntity<List<AuditService.AuditRecord>> getAuditLogs(
            @RequestParam(defaultValue = "100") int limit,
            @RequestParam(required = false) String modelName,
            @RequestParam(required = false) String userId) {
        return ResponseEntity.ok(auditService.getAuditLogs(limit, modelName, userId));
    }

    /**
     * Get audit logs by date range.
     */
    @GetMapping("/audit/range")
    public ResponseEntity<List<AuditService.AuditRecord>> getAuditLogsByDate(
            @RequestParam String fromDate,
            @RequestParam String toDate,
            @RequestParam(defaultValue = "500") int limit) {
        return ResponseEntity.ok(auditService.getAuditLogsByDate(fromDate, toDate, limit));
    }

    /**
     * Get token usage report.
     */
    @GetMapping("/audit/usage")
    public ResponseEntity<AuditService.TokenUsageReport> getTokenUsage(
            @RequestParam String fromDate,
            @RequestParam String toDate) {
        return ResponseEntity.ok(auditService.getTokenUsageReport(fromDate, toDate));
    }

    /**
     * Get cost analysis for a month.
     */
    @GetMapping("/audit/cost")
    public ResponseEntity<AuditService.CostAnalysis> getCostAnalysis(
            @RequestParam String month) {
        return ResponseEntity.ok(auditService.getCostAnalysis(month));
    }

    // ================================================================
    // Prompt 管理
    // ================================================================

    /**
     * List prompt templates.
     */
    @GetMapping("/prompts")
    public ResponseEntity<List<PromptService.PromptTemplate>> listPrompts(
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String status) {
        return ResponseEntity.ok(promptService.listTemplates(category, status));
    }

    /**
     * Get a single prompt template.
     */
    @GetMapping("/prompts/{templateId}")
    public ResponseEntity<PromptService.PromptTemplate> getPrompt(
            @PathVariable String templateId) {
        return promptService.getTemplate(templateId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    /**
     * Create a prompt template.
     */
    @PostMapping("/prompts")
    public ResponseEntity<PromptService.PromptTemplate> createPrompt(
            @RequestBody PromptService.PromptTemplate template) {
        return ResponseEntity.ok(promptService.createTemplate(template));
    }

    /**
     * Update a prompt template.
     */
    @PutMapping("/prompts/{templateId}")
    public ResponseEntity<PromptService.PromptTemplate> updatePrompt(
            @PathVariable String templateId,
            @RequestBody Map<String, Object> body) {
        String content = (String) body.get("content");
        @SuppressWarnings("unchecked")
        Map<String, String> variables = (Map<String, String>) body.getOrDefault("variables", Map.of());
        return ResponseEntity.ok(promptService.updateTemplate(templateId, content, variables));
    }

    /**
     * Publish a prompt template.
     */
    @PostMapping("/prompts/{templateId}/publish")
    public ResponseEntity<PromptService.PromptTemplate> publishPrompt(
            @PathVariable String templateId) {
        return ResponseEntity.ok(promptService.publishTemplate(templateId));
    }

    /**
     * Render a prompt with variables.
     */
    @PostMapping("/prompts/{templateId}/render")
    public ResponseEntity<Map<String, String>> renderPrompt(
            @PathVariable String templateId,
            @RequestBody Map<String, String> variables) {
        return ResponseEntity.ok(Map.of("result", promptService.renderPrompt(templateId, variables)));
    }

    /**
     * Create A/B test.
     */
    @PostMapping("/prompts/abtest")
    public ResponseEntity<PromptService.ABTestConfig> createABTest(
            @RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String templateIdA = (String) body.get("templateIdA");
        String templateIdB = (String) body.get("templateIdB");
        double split = ((Number) body.getOrDefault("trafficSplit", 0.5)).doubleValue();
        return ResponseEntity.ok(promptService.createABTest(name, templateIdA, templateIdB, split));
    }

    /**
     * Complete A/B test and get winner.
     */
    @PostMapping("/prompts/abtest/{testId}/complete")
    public ResponseEntity<PromptService.ABTestResult> completeABTest(
            @PathVariable String testId) {
        return ResponseEntity.ok(promptService.completeABTest(testId));
    }

    /**
     * Get prompt rating stats.
     */
    @GetMapping("/prompts/{templateId}/stats")
    public ResponseEntity<PromptService.PromptStats> getPromptStats(
            @PathVariable String templateId) {
        return ResponseEntity.ok(promptService.getPromptStats(templateId));
    }

    /**
     * Rate a prompt.
     */
    @PostMapping("/prompts/{templateId}/rate")
    public ResponseEntity<Void> ratePrompt(
            @PathVariable String templateId,
            @RequestBody Map<String, Object> body) {
        String deviceId = (String) body.get("deviceId");
        double score = ((Number) body.get("score")).doubleValue();
        String feedback = (String) body.getOrDefault("feedback", "");
        promptService.ratePrompt(templateId, deviceId, score, feedback);
        return ResponseEntity.ok().build();
    }
}
