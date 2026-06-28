package com.qoobot.qoocloud.observability.service;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * ObservabilityService — 可观测性服务
 * 全链路追踪、日志聚合、智能告警、SLA 监控、用量仪表板
 */
@Service
public class ObservabilityService {

    // SLA tracking
    private final Map<String, SLAMetrics> slaMetrics = new ConcurrentHashMap<>();

    // Active alerts
    private final List<Alert> activeAlerts = Collections.synchronizedList(new ArrayList<>());

    // API usage counters
    private final Map<String, UsageCounter> usageCounters = new ConcurrentHashMap<>();

    /**
     * Record a trace span for distributed tracing.
     */
    public void recordTrace(String traceId, String spanId, String serviceName,
                            String operation, long durationMs, boolean success) {
        // In production: export to Jaeger/Zipkin
        // For now, update SLA metrics
        SLAMetrics metrics = slaMetrics.computeIfAbsent(serviceName, k -> new SLAMetrics());
        metrics.totalRequests++;
        if (success) {
            metrics.successfulRequests++;
        } else {
            metrics.failedRequests++;
        }
        metrics.totalLatencyMs += durationMs;
        metrics.p99LatencyMs = Math.max(metrics.p99LatencyMs, durationMs);
    }

    /**
     * Check SLA compliance and trigger alerts.
     */
    public List<Alert> checkSLA(String serviceName, double targetAvailability) {
        SLAMetrics metrics = slaMetrics.get(serviceName);
        if (metrics == null) return Collections.emptyList();

        double availability = metrics.totalRequests > 0
            ? (double) metrics.successfulRequests / metrics.totalRequests
            : 1.0;

        List<Alert> newAlerts = new ArrayList<>();

        if (availability < targetAvailability) {
            Alert alert = new Alert();
            alert.serviceName = serviceName;
            alert.type = AlertType.SLA_VIOLATION;
            alert.severity = AlertSeverity.WARNING;
            alert.message = String.format(
                "SLA violation: %s availability %.2f%% < target %.2f%%",
                serviceName, availability * 100, targetAvailability * 100);
            alert.timestamp = Instant.now();
            newAlerts.add(alert);
            activeAlerts.add(alert);
        }

        // Latency SLA check
        double avgLatency = metrics.totalRequests > 0
            ? (double) metrics.totalLatencyMs / metrics.totalRequests : 0;
        if (avgLatency > 2000) {  // 2 second threshold
            Alert alert = new Alert();
            alert.serviceName = serviceName;
            alert.type = AlertType.HIGH_LATENCY;
            alert.severity = AlertSeverity.WARNING;
            alert.message = String.format(
                "High latency: %s avg %.0fms, P99 %.0fms",
                serviceName, avgLatency, metrics.p99LatencyMs);
            alert.timestamp = Instant.now();
            newAlerts.add(alert);
            activeAlerts.add(alert);
        }

        return newAlerts;
    }

    /**
     * Get SLA dashboard data.
     */
    public Map<String, Object> getSLADashboard() {
        Map<String, Object> dashboard = new HashMap<>();
        List<Map<String, Object>> services = new ArrayList<>();

        for (Map.Entry<String, SLAMetrics> entry : slaMetrics.entrySet()) {
            SLAMetrics m = entry.getValue();
            Map<String, Object> svc = new HashMap<>();
            svc.put("service", entry.getKey());
            svc.put("totalRequests", m.totalRequests);
            svc.put("successRate", m.totalRequests > 0
                ? (double) m.successfulRequests / m.totalRequests : 0);
            svc.put("avgLatencyMs", m.totalRequests > 0
                ? (double) m.totalLatencyMs / m.totalRequests : 0);
            svc.put("p99LatencyMs", m.p99LatencyMs);
            svc.put("failedRequests", m.failedRequests);
            services.add(svc);
        }

        dashboard.put("services", services);
        dashboard.put("activeAlerts", activeAlerts.size());
        dashboard.put("timestamp", Instant.now().toString());
        return dashboard;
    }

    /**
     * Record API usage for billing/analytics.
     */
    public void recordUsage(String apiEndpoint, String deviceId, long tokensUsed) {
        UsageCounter counter = usageCounters.computeIfAbsent(apiEndpoint, k -> new UsageCounter());
        counter.totalCalls++;
        counter.totalTokens += tokensUsed;
        counter.lastAccess = Instant.now();
    }

    /**
     * Get usage report for a time period.
     */
    public Map<String, Object> getUsageReport() {
        Map<String, Object> report = new HashMap<>();
        List<Map<String, Object>> endpoints = new ArrayList<>();

        for (Map.Entry<String, UsageCounter> entry : usageCounters.entrySet()) {
            UsageCounter c = entry.getValue();
            Map<String, Object> ep = new HashMap<>();
            ep.put("endpoint", entry.getKey());
            ep.put("totalCalls", c.totalCalls);
            ep.put("totalTokens", c.totalTokens);
            ep.put("lastAccess", c.lastAccess.toString());
            endpoints.add(ep);
        }

        report.put("endpoints", endpoints);
        report.put("timestamp", Instant.now().toString());
        return report;
    }

    /**
     * Get active alerts and optionally acknowledge them.
     */
    public List<Alert> getActiveAlerts() {
        return new ArrayList<>(activeAlerts);
    }

    public void acknowledgeAlert(int alertIndex) {
        if (alertIndex >= 0 && alertIndex < activeAlerts.size()) {
            activeAlerts.get(alertIndex).acknowledged = true;
        }
    }

    public void clearAcknowledgedAlerts() {
        activeAlerts.removeIf(a -> a.acknowledged);
    }

    // Inner types

    private static class SLAMetrics {
        long totalRequests = 0;
        long successfulRequests = 0;
        long failedRequests = 0;
        long totalLatencyMs = 0;
        long p99LatencyMs = 0;
    }

    private static class UsageCounter {
        long totalCalls = 0;
        long totalTokens = 0;
        Instant lastAccess = Instant.now();
    }

    public enum AlertType {
        SLA_VIOLATION, HIGH_LATENCY, HIGH_ERROR_RATE,
        RESOURCE_EXHAUSTED, SERVICE_DOWN, ANOMALY_DETECTED
    }

    public enum AlertSeverity {
        INFO, WARNING, CRITICAL
    }

    public static class Alert {
        public String serviceName;
        public AlertType type;
        public AlertSeverity severity;
        public String message;
        public Instant timestamp;
        public boolean acknowledged = false;
    }
}
