package com.qoobot.qoocompliance.checklist.controller;

import com.qoobot.qoocompliance.checklist.service.ComplianceChecklistService;
import com.qoobot.qoocompliance.checklist.service.ComplianceChecklistService.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/compliance")
public class ComplianceController {

    private final ComplianceChecklistService checklistService;

    public ComplianceController(ComplianceChecklistService checklistService) {
        this.checklistService = checklistService;
    }

    /**
     * Generate a compliance checklist for target markets.
     */
    @PostMapping("/checklist")
    public ResponseEntity<ComplianceProject> generateChecklist(
            @RequestBody Map<String, Object> body) {
        String name = (String) body.get("projectName");
        @SuppressWarnings("unchecked")
        List<String> markets = (List<String>) body.get("targetMarkets");
        return ResponseEntity.ok(checklistService.generateChecklist(name, markets));
    }

    /**
     * Get checklist items for a project.
     */
    @GetMapping("/projects/{projectId}/items")
    public ResponseEntity<List<ComplianceItem>> getItems(
            @PathVariable String projectId,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String status) {
        return ResponseEntity.ok(checklistService.getItems(projectId, category, status));
    }

    /**
     * Update item compliance status.
     */
    @PutMapping("/projects/{projectId}/items/{itemId}")
    public ResponseEntity<ComplianceItem> updateItem(
            @PathVariable String projectId,
            @PathVariable String itemId,
            @RequestBody Map<String, String> body) {
        ComplianceItem updated = checklistService.updateItemStatus(
                projectId, itemId,
                body.get("status"),
                body.get("evidence"),
                body.get("notes")
        );
        return updated != null ? ResponseEntity.ok(updated) : ResponseEntity.notFound().build();
    }

    /**
     * Get project compliance progress.
     */
    @GetMapping("/projects/{projectId}/progress")
    public ResponseEntity<ProjectProgress> getProgress(@PathVariable String projectId) {
        return ResponseEntity.ok(checklistService.getProgress(projectId));
    }

    /**
     * Identify compliance gaps blocking market entry.
     */
    @GetMapping("/projects/{projectId}/gaps")
    public ResponseEntity<List<ComplianceItem>> identifyGaps(
            @PathVariable String projectId,
            @RequestParam(defaultValue = "ALL") String market) {
        return ResponseEntity.ok(checklistService.identifyGaps(projectId, market));
    }

    /**
     * Generate compliance report.
     */
    @GetMapping("/projects/{projectId}/report")
    public ResponseEntity<ComplianceReport> generateReport(@PathVariable String projectId) {
        return ResponseEntity.ok(checklistService.generateReport(projectId));
    }
}
