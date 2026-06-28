package com.qoobot.qoocloud.observability.controller;

import com.qoobot.qoocloud.observability.service.LogAggregationService;
import com.qoobot.qoocloud.observability.service.ObservabilityService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * REST API for observability: tracing, log aggregation, alerting, SLA monitoring.
 */
@RestController
@RequestMapping("/api/v1/observability")
public class ObservabilityController {

    private final ObservabilityService observabilityService;
    private final LogAggregationService logAggregationService;

    public ObservabilityController(ObservabilityService observabilityService,
                                    LogAggregationService logAggregationService) {
        this.observabilityService = observabilityService;
        this.logAggregationService = logAggregationService;
    }

    // ================================================================
    // 链路追踪 & SLA
    // ================================================================

    @PostMapping("/traces")
    public ResponseEntity<Void> recordTrace(@RequestBody Map<String, Object> body) {
        String traceId = (String) body.get("traceId");
        String spanId = (String) body.get("spanId");
        String serviceName = (String) body.get("serviceName");
        String operation = (String) body.get("operation");
        long durationMs = ((Number) body.get("durationMs")).longValue();
        boolean success = (boolean) body.getOrDefault("success", true);
        observabilityService.recordTrace(traceId, spanId, serviceName, operation, durationMs, success);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/sla/dashboard")
    public ResponseEntity<Map<String, Object>> getSLADashboard() {
        return ResponseEntity.ok(observabilityService.getSLADashboard());
    }

    @PostMapping("/sla/check")
    public ResponseEntity<List<ObservabilityService.Alert>> checkSLA(
            @RequestBody Map<String, Object> body) {
        String serviceName = (String) body.get("serviceName");
        double targetAvailability = ((Number) body.getOrDefault("targetAvailability", 0.995)).doubleValue();
        return ResponseEntity.ok(observabilityService.checkSLA(serviceName, targetAvailability));
    }

    // ================================================================
    // 告警管理
    // ================================================================

    @GetMapping("/alerts")
    public ResponseEntity<List<ObservabilityService.Alert>> getActiveAlerts() {
        return ResponseEntity.ok(observabilityService.getActiveAlerts());
    }

    @PostMapping("/alerts/{index}/acknowledge")
    public ResponseEntity<Void> acknowledgeAlert(@PathVariable int index) {
        observabilityService.acknowledgeAlert(index);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/alerts/clear-acknowledged")
    public ResponseEntity<Void> clearAcknowledgedAlerts() {
        observabilityService.clearAcknowledgedAlerts();
        return ResponseEntity.ok().build();
    }

    // ================================================================
    // 用量统计
    // ================================================================

    @PostMapping("/usage")
    public ResponseEntity<Void> recordUsage(@RequestBody Map<String, Object> body) {
        String apiEndpoint = (String) body.get("apiEndpoint");
        String deviceId = (String) body.get("deviceId");
        long tokensUsed = ((Number) body.getOrDefault("tokensUsed", 0)).longValue();
        observabilityService.recordUsage(apiEndpoint, deviceId, tokensUsed);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/usage/report")
    public ResponseEntity<Map<String, Object>> getUsageReport() {
        return ResponseEntity.ok(observabilityService.getUsageReport());
    }

    // ================================================================
    // 日志聚合
    // ================================================================

    @PostMapping("/logs")
    public ResponseEntity<Void> ingestLog(@RequestBody Map<String, Object> body) {
        String deviceId = (String) body.get("deviceId");
        String source = (String) body.get("source");
        LogAggregationService.LogLevel level = LogAggregationService.LogLevel.valueOf(
                (String) body.getOrDefault("level", "INFO"));
        String message = (String) body.get("message");
        @SuppressWarnings("unchecked")
        Map<String, String> metadata = (Map<String, String>) body.getOrDefault("metadata", Map.of());
        logAggregationService.ingestLog(deviceId, source, level, message, metadata);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/logs/batch")
    public ResponseEntity<Map<String, Integer>> ingestBatchLogs(
            @RequestBody Map<String, Object> body) {
        String deviceId = (String) body.get("deviceId");
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) body.get("items");
        List<LogAggregationService.LogBatchItem> batchItems = items.stream()
                .map(item -> new LogAggregationService.LogBatchItem(
                        (String) item.get("source"),
                        LogAggregationService.LogLevel.valueOf(
                                (String) item.getOrDefault("level", "INFO")),
                        (String) item.get("message"),
                        (Map<String, String>) item.getOrDefault("metadata", Map.of())))
                .toList();
        int count = logAggregationService.ingestBatch(deviceId, batchItems);
        return ResponseEntity.ok(Map.of("ingested", count));
    }

    @GetMapping("/logs/search")
    public ResponseEntity<LogAggregationService.LogSearchResult> searchLogs(
            @RequestParam(required = false) String deviceId,
            @RequestParam(required = false) String level,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "100") int limit) {
        LogAggregationService.LogLevel minLevel = level != null ?
                LogAggregationService.LogLevel.valueOf(level.toUpperCase()) : null;
        return ResponseEntity.ok(logAggregationService.searchLogs(deviceId, minLevel, keyword, limit));
    }

    @GetMapping("/logs/stats/{deviceId}")
    public ResponseEntity<LogAggregationService.LogSourceStats> getLogStats(
            @PathVariable String deviceId) {
        return ResponseEntity.ok(logAggregationService.getDeviceLogStats(deviceId));
    }

    @GetMapping("/logs/trend/{deviceId}")
    public ResponseEntity<LogAggregationService.LogTrend> getLogTrend(
            @PathVariable String deviceId,
            @RequestParam(defaultValue = "24") int hours) {
        return ResponseEntity.ok(logAggregationService.getLogTrend(deviceId, hours));
    }

    @GetMapping("/logs/errors/recent")
    public ResponseEntity<List<LogAggregationService.LogEntry>> getRecentErrors(
            @RequestParam(defaultValue = "50") int limit) {
        return ResponseEntity.ok(logAggregationService.getRecentErrors(limit));
    }
}
