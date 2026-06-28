package com.qoobot.qoocloud.data.controller;

import com.qoobot.qoocloud.data.service.*;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for data sync, knowledge sharing, federated learning, and data pipelines.
 */
@RestController
@RequestMapping("/api/v1/data")
public class DataSyncController {

    private final KnowledgeSyncService knowledgeSyncService;
    private final DataPipelineService dataPipelineService;
    private final FederatedLearningService federatedLearningService;

    public DataSyncController(KnowledgeSyncService knowledgeSyncService,
                               DataPipelineService dataPipelineService,
                               FederatedLearningService federatedLearningService) {
        this.knowledgeSyncService = knowledgeSyncService;
        this.dataPipelineService = dataPipelineService;
        this.federatedLearningService = federatedLearningService;
    }

    // ================================================================
    // 知识库同步
    // ================================================================

    @PostMapping("/knowledge")
    public ResponseEntity<KnowledgeSyncService.KnowledgeEntry> uploadKnowledge(
            @RequestBody Map<String, Object> body) {
        String deviceId = (String) body.get("deviceId");
        String knowledgeType = (String) body.get("knowledgeType");
        String title = (String) body.get("title");
        String content = (String) body.get("content");
        @SuppressWarnings("unchecked")
        Map<String, String> metadata = (Map<String, String>) body.getOrDefault("metadata", Map.of());
        return ResponseEntity.ok(knowledgeSyncService.uploadKnowledge(
                deviceId, knowledgeType, title, content, metadata));
    }

    @GetMapping("/knowledge")
    public ResponseEntity<List<KnowledgeSyncService.KnowledgeEntry>> searchKnowledge(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String type,
            @RequestParam(defaultValue = "50") int limit) {
        return ResponseEntity.ok(knowledgeSyncService.searchKnowledge(
                q != null ? q : "", type, limit));
    }

    @GetMapping("/knowledge/{entryId}")
    public ResponseEntity<KnowledgeSyncService.KnowledgeEntry> getKnowledge(
            @PathVariable String entryId) {
        return knowledgeSyncService.getKnowledge(entryId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/knowledge/device/{deviceId}")
    public ResponseEntity<List<KnowledgeSyncService.KnowledgeEntry>> getDeviceKnowledge(
            @PathVariable String deviceId) {
        return ResponseEntity.ok(knowledgeSyncService.getDeviceContributions(deviceId));
    }

    @PostMapping("/knowledge/sync")
    public ResponseEntity<KnowledgeSyncService.SyncSession> startSync(
            @RequestBody Map<String, Object> body) {
        String targetDeviceId = (String) body.get("targetDeviceId");
        @SuppressWarnings("unchecked")
        List<String> types = (List<String>) body.getOrDefault("knowledgeTypes", List.of());
        return ResponseEntity.ok(knowledgeSyncService.startSyncSession(targetDeviceId, types));
    }

    @GetMapping("/knowledge/stats")
    public ResponseEntity<KnowledgeSyncService.KnowledgeStats> getKnowledgeStats() {
        return ResponseEntity.ok(knowledgeSyncService.getStats());
    }

    // ================================================================
    // 数据管道
    // ================================================================

    @PostMapping("/pipelines")
    public ResponseEntity<DataPipelineService.PipelineConfig> createPipeline(
            @RequestBody Map<String, Object> body) {
        String name = (String) body.get("name");
        String source = (String) body.get("source");
        @SuppressWarnings("unchecked")
        List<String> transforms = (List<String>) body.getOrDefault("transforms", List.of());
        String sink = (String) body.get("sink");
        DataPipelineService.StorageTier tier = DataPipelineService.StorageTier.valueOf(
                (String) body.getOrDefault("tier", "HOT"));
        return ResponseEntity.ok(dataPipelineService.createPipeline(
                name, source, transforms, sink, tier));
    }

    @GetMapping("/pipelines")
    public ResponseEntity<List<DataPipelineService.PipelineConfig>> listPipelines() {
        return ResponseEntity.ok(dataPipelineService.listPipelines());
    }

    @PostMapping("/pipelines/{pipelineId}/upload")
    public ResponseEntity<DataPipelineService.DataUploadResult> uploadRealtime(
            @PathVariable String pipelineId,
            @RequestBody Map<String, Object> body) {
        String deviceId = (String) body.get("deviceId");
        String dataType = (String) body.get("dataType");
        String payload = (String) body.get("payload");
        @SuppressWarnings("unchecked")
        Map<String, String> tags = (Map<String, String>) body.getOrDefault("tags", Map.of());
        return ResponseEntity.ok(dataPipelineService.uploadRealtime(
                pipelineId, deviceId, dataType, payload, tags));
    }

    @PostMapping("/pipelines/{pipelineId}/upload/batch")
    public ResponseEntity<DataPipelineService.BatchUploadResult> uploadBatch(
            @PathVariable String pipelineId,
            @RequestBody Map<String, Object> body) {
        String deviceId = (String) body.get("deviceId");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) body.get("items");
        List<DataPipelineService.DataItem> dataItems = items.stream()
                .map(item -> new DataPipelineService.DataItem(
                        (String) item.get("itemId"),
                        (String) item.get("dataType"),
                        (String) item.get("payload"),
                        (Map<String, String>) item.getOrDefault("tags", Map.of())))
                .toList();
        return ResponseEntity.ok(dataPipelineService.uploadBatch(pipelineId, deviceId, dataItems));
    }

    @GetMapping("/pipelines/storage-tiers")
    public ResponseEntity<Map<DataPipelineService.StorageTier, DataPipelineService.TierStats>> getStorageTiers() {
        return ResponseEntity.ok(dataPipelineService.getStorageTierStats());
    }

    // ================================================================
    // 联邦学习
    // ================================================================

    @PostMapping("/federated/rounds")
    public ResponseEntity<Map<String, String>> startFLRound(@RequestBody Map<String, Object> body) {
        String modelName = (String) body.get("modelName");
        int minParticipants = ((Number) body.getOrDefault("minParticipants", 3)).intValue();
        double targetEpsilon = ((Number) body.getOrDefault("targetEpsilon", 1.0)).doubleValue();
        String roundId = federatedLearningService.startRound(modelName, minParticipants, targetEpsilon);
        return ResponseEntity.ok(Map.of("roundId", roundId));
    }

    @PostMapping("/federated/rounds/{roundId}/gradients")
    public ResponseEntity<Void> submitGradients(
            @PathVariable String roundId,
            @RequestBody Map<String, Object> body) {
        String deviceId = (String) body.get("deviceId");
        @SuppressWarnings("unchecked")
        List<Double> gradients = ((List<Number>) body.get("gradients")).stream()
                .map(Number::doubleValue).toList();
        federatedLearningService.submitGradients(roundId, deviceId, gradients);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/federated/rounds/{roundId}")
    public ResponseEntity<Map<String, Object>> getFLRoundStatus(@PathVariable String roundId) {
        return ResponseEntity.ok(federatedLearningService.getRoundStatus(roundId));
    }
}
