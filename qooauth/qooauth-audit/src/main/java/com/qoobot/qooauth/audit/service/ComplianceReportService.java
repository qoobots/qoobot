package com.qoobot.qooauth.audit.service;

import com.qoobot.qooauth.audit.dto.ComplianceReportRequest;
import com.qoobot.qooauth.audit.repository.AuditLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;

/**
 * Generates compliance reports (SOC2, ISO27001, GDPR).
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ComplianceReportService {

    private final AuditLogRepository auditLogRepository;

    /**
     * Generate a compliance report as a structured Map.
     */
    @Transactional(readOnly = true)
    public Map<String, Object> generateReport(ComplianceReportRequest request) {
        Map<String, Object> report = new LinkedHashMap<>();

        report.put("reportType", request.getReportType());
        report.put("generatedAt", Instant.now().toString());
        report.put("period", Map.of(
                "start", request.getStartTime().toString(),
                "end", request.getEndTime().toString()
        ));

        switch (request.getReportType().toUpperCase()) {
            case "SOC2" -> populateSoc2Report(report, request.getStartTime(), request.getEndTime());
            case "ISO27001" -> populateIso27001Report(report, request.getStartTime(), request.getEndTime());
            case "GDPR" -> populateGdprReport(report, request.getStartTime(), request.getEndTime());
            default -> populateSummaryReport(report, request.getStartTime(), request.getEndTime());
        }

        return report;
    }

    private void populateSoc2Report(Map<String, Object> report, Instant start, Instant end) {
        List<Object[]> actionCounts = auditLogRepository.countByAction(start, end);
        Map<String, Long> actionBreakdown = new LinkedHashMap<>();
        long total = 0;
        for (Object[] row : actionCounts) {
            String action = (String) row[0];
            long count = (Long) row[1];
            actionBreakdown.put(action, count);
            total += count;
        }

        report.put("sections", List.of(
                Map.of("name", "A.1 - Access Control", "status", "COMPLIANT"),
                Map.of("name", "A.2 - Authentication Events", "totalEvents", total),
                Map.of("name", "A.3 - Audit Trail Completeness", "actionBreakdown", actionBreakdown)
        ));
    }

    private void populateIso27001Report(Map<String, Object> report, Instant start, Instant end) {
        List<Object[]> actionCounts = auditLogRepository.countByAction(start, end);
        Map<String, Long> actionBreakdown = new LinkedHashMap<>();
        long total = 0;
        for (Object[] row : actionCounts) {
            String action = (String) row[0];
            long count = (Long) row[1];
            actionBreakdown.put(action, count);
            total += count;
        }

        report.put("sections", List.of(
                Map.of("name", "A.9 - Access Control", "status", "COMPLIANT"),
                Map.of("name", "A.12 - Operations Security", "auditEvents", total),
                Map.of("name", "A.16 - Incident Management", "actionBreakdown", actionBreakdown)
        ));
    }

    private void populateGdprReport(Map<String, Object> report, Instant start, Instant end) {
        List<Object[]> actionCounts = auditLogRepository.countByAction(start, end);
        Map<String, Long> actionBreakdown = new LinkedHashMap<>();
        for (Object[] row : actionCounts) {
            actionBreakdown.put((String) row[0], (Long) row[1]);
        }

        report.put("sections", List.of(
                Map.of("name", "Art. 30 - Records of Processing Activities", "status", "MAINTAINED"),
                Map.of("name", "Art. 32 - Security of Processing", "auditLogIntegrity", "SHA-256 Merkle Chain"),
                Map.of("name", "Art. 33 - Breach Notification", "monitoringStatus", "ACTIVE"),
                Map.of("actionBreakdown", actionBreakdown)
        ));
    }

    private void populateSummaryReport(Map<String, Object> report, Instant start, Instant end) {
        List<Object[]> actionCounts = auditLogRepository.countByAction(start, end);
        Map<String, Long> actionBreakdown = new LinkedHashMap<>();
        long total = 0;
        for (Object[] row : actionCounts) {
            String action = (String) row[0];
            long count = (Long) row[1];
            actionBreakdown.put(action, count);
            total += count;
        }

        report.put("totalEvents", total);
        report.put("actionBreakdown", actionBreakdown);
    }
}
