package com.qoobot.qooauth.audit.controller;

import com.qoobot.qooauth.audit.dto.AuditQueryRequest;
import com.qoobot.qooauth.audit.dto.AuditQueryResponse;
import com.qoobot.qooauth.audit.dto.ComplianceReportRequest;
import com.qoobot.qooauth.audit.service.AuditService;
import com.qoobot.qooauth.audit.service.ComplianceReportService;
import com.qoobot.qooauth.audit.service.LogIntegrityService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/audit")
@RequiredArgsConstructor
public class AuditController {

    private final AuditService auditService;
    private final ComplianceReportService complianceReportService;
    private final LogIntegrityService logIntegrityService;

    /**
     * Query audit logs with flexible filters.
     */
    @PostMapping("/search")
    public ResponseEntity<AuditQueryResponse> searchAuditLogs(
            @Valid @RequestBody AuditQueryRequest request) {
        return ResponseEntity.ok(auditService.queryAuditLogs(request));
    }

    /**
     * Query audit logs with GET params (simpler use cases).
     */
    @GetMapping
    public ResponseEntity<AuditQueryResponse> getAuditLogs(
            @RequestParam(required = false) String actorType,
            @RequestParam(required = false) String actorId,
            @RequestParam(required = false) String action,
            @RequestParam(required = false) String result,
            @RequestParam(required = false) String sessionId,
            @RequestParam(required = false) String traceId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant startTime,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant endTime,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size) {

        AuditQueryRequest request = AuditQueryRequest.builder()
                .actorType(actorType)
                .actorId(actorId)
                .action(action)
                .result(result)
                .sessionId(sessionId)
                .traceId(traceId)
                .startTime(startTime)
                .endTime(endTime)
                .page(page)
                .size(size)
                .build();

        return ResponseEntity.ok(auditService.queryAuditLogs(request));
    }

    /**
     * Find actors with excessive authentication failures (anomaly detection support).
     */
    @GetMapping("/anomalies/failures")
    public ResponseEntity<List<Map<String, Object>>> getFailureAnomalies(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant endTime,
            @RequestParam(defaultValue = "10") long threshold) {

        List<Object[]> results = auditService.findActorsWithExcessiveFailures(startTime, endTime, threshold);
        List<Map<String, Object>> response = results.stream()
                .map(row -> Map.of(
                        "actorId", (String) row[0],
                        "failureCount", (Long) row[1]
                ))
                .toList();
        return ResponseEntity.ok(response);
    }

    /**
     * Generate compliance report.
     */
    @PostMapping("/compliance/report")
    public ResponseEntity<Map<String, Object>> generateComplianceReport(
            @Valid @RequestBody ComplianceReportRequest request) {
        return ResponseEntity.ok(complianceReportService.generateReport(request));
    }

    /**
     * Verify audit log integrity chain.
     */
    @GetMapping("/integrity/verify")
    public ResponseEntity<Map<String, Object>> verifyIntegrity(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant startTime,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant endTime) {

        boolean valid = logIntegrityService.verifyChainIntegrity(startTime, endTime);
        return ResponseEntity.ok(Map.of(
                "verified", valid,
                "period", Map.of(
                        "start", startTime.toString(),
                        "end", endTime.toString()
                ),
                "status", valid ? "INTEGRITY_VERIFIED" : "INTEGRITY_BROKEN"
        ));
    }

    /**
     * Trigger integrity chain build manually (for testing/admin).
     */
    @PostMapping("/integrity/build")
    public ResponseEntity<Map<String, String>> triggerIntegrityBuild() {
        logIntegrityService.buildIntegrityChain();
        return ResponseEntity.ok(Map.of("status", "INTEGRITY_BUILD_TRIGGERED"));
    }
}
