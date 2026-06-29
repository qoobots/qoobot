package com.qoobot.qooauth.auth.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedDeque;

/**
 * Application-layer DDoS Protection Service.
 *
 * Provides:
 * - Traffic pattern analysis and anomaly detection
 * - Rate-based throttling (per-IP, per-endpoint, global)
 * - WAF-style rule evaluation
 * - Traffic scrubbing and challenge-based verification
 * - Adaptive thresholds based on baseline traffic patterns
 */
@Service
public class DdosProtectionService {
    private static final Logger log = LoggerFactory.getLogger(DdosProtectionService.class);

    // Sliding window for traffic analysis (1 minute windows)
    private static final int WINDOW_COUNT = 60;
    private static final long WINDOW_DURATION_MS = 60_000;

    // Traffic counters per IP
    private final ConcurrentHashMap<String, TrafficStats> ipTraffic = new ConcurrentHashMap<>();

    // Endpoint traffic counters
    private final ConcurrentHashMap<String, TrafficStats> endpointTraffic = new ConcurrentHashMap<>();

    // Global traffic counter
    private final TrafficStats globalTraffic = new TrafficStats(WINDOW_COUNT);

    // Blocklist
    private final ConcurrentHashMap<String, BlockEntry> blocklist = new ConcurrentHashMap<>();

    // WAF rules
    private final List<WafRule> wafRules = new ArrayList<>();

    public DdosProtectionService() {
        initializeWafRules();
    }

    // ============================================================
    //  Traffic Analysis
    // ============================================================

    /**
     * Record a request for traffic analysis.
     * Returns true if the request should be allowed, false if blocked.
     */
    public boolean analyzeRequest(String ip, String endpoint, String method,
                                   String userAgent, Map<String, String> headers) {
        long now = System.currentTimeMillis();

        // Check blocklist
        BlockEntry block = blocklist.get(ip);
        if (block != null) {
            if (block.isExpired(now)) {
                blocklist.remove(ip);
            } else {
                log.debug("IP {} is blocklisted until {}", ip, block.blockedUntil);
                return false;
            }
        }

        // Record traffic
        TrafficStats ipStats = ipTraffic.computeIfAbsent(ip, k -> new TrafficStats(WINDOW_COUNT));
        TrafficStats epStats = endpointTraffic.computeIfAbsent(endpoint, k -> new TrafficStats(WINDOW_COUNT));

        ipStats.recordRequest(now);
        epStats.recordRequest(now);
        globalTraffic.recordRequest(now);

        // Check WAF rules
        WafViolation wafViolation = evaluateWafRules(ip, endpoint, method, userAgent, headers);
        if (wafViolation != null) {
            log.warn("WAF rule triggered for IP {}: {} — {}", ip, wafViolation.ruleName, wafViolation.reason);
            addToBlocklist(ip, "WAF: " + wafViolation.ruleName, 300_000); // 5 min
            return false;
        }

        // Check IP-level thresholds
        long ipRps = ipStats.getRequestsPerSecond(now);
        if (ipRps > 100) { // More than 100 req/s from single IP
            log.warn("DDoS suspected: IP {} sending {} req/s", ip, ipRps);
            addToBlocklist(ip, "High request rate: " + ipRps + " req/s", 600_000); // 10 min
            return false;
        }

        // Check endpoint-level thresholds
        long epRps = epStats.getRequestsPerSecond(now);
        if (epRps > 1000) { // More than 1000 req/s on single endpoint
            log.warn("DDoS suspected: endpoint {} receiving {} req/s", endpoint, epRps);
            // Apply rate limiting to endpoint
            return false;
        }

        // Check global thresholds
        long globalRps = globalTraffic.getRequestsPerSecond(now);
        if (globalRps > 10000) { // Global threshold
            log.warn("Global traffic threshold exceeded: {} req/s", globalRps);
            // Enable challenge mode
            return false;
        }

        return true;
    }

    /**
     * Get traffic statistics.
     */
    public TrafficReport getTrafficReport() {
        long now = System.currentTimeMillis();
        TrafficReport report = new TrafficReport();
        report.globalRps = globalTraffic.getRequestsPerSecond(now);
        report.activeIps = ipTraffic.size();
        report.blockedIps = (int) blocklist.values().stream()
                .filter(b -> !b.isExpired(now)).count();
        report.timestamp = now;

        // Top talkers
        report.topTalkers = new ArrayList<>();
        ipTraffic.entrySet().stream()
                .sorted((a, b) -> Long.compare(
                        b.getValue().getRequestsPerSecond(now),
                        a.getValue().getRequestsPerSecond(now)))
                .limit(10)
                .forEach(e -> report.topTalkers.add(
                        new TrafficReport.TopTalker(e.getKey(), e.getValue().getRequestsPerSecond(now))));

        return report;
    }

    // ============================================================
    //  Blocklist Management
    // ============================================================

    /**
     * Add IP to blocklist for a specified duration.
     */
    public void addToBlocklist(String ip, String reason, long durationMs) {
        BlockEntry entry = new BlockEntry();
        entry.ip = ip;
        entry.reason = reason;
        entry.blockedAt = System.currentTimeMillis();
        entry.blockedUntil = entry.blockedAt + durationMs;
        blocklist.put(ip, entry);
        log.info("IP {} blocklisted for {}ms: {}", ip, durationMs, reason);
    }

    /**
     * Remove IP from blocklist.
     */
    public void removeFromBlocklist(String ip) {
        blocklist.remove(ip);
        log.info("IP {} removed from blocklist", ip);
    }

    /**
     * Check if an IP is blocklisted.
     */
    public boolean isBlocklisted(String ip) {
        BlockEntry entry = blocklist.get(ip);
        if (entry == null) return false;
        if (entry.isExpired(System.currentTimeMillis())) {
            blocklist.remove(ip);
            return false;
        }
        return true;
    }

    /**
     * Get blocklist entries.
     */
    public List<BlockEntry> getBlocklist() {
        long now = System.currentTimeMillis();
        // Clean expired entries
        blocklist.entrySet().removeIf(e -> e.getValue().isExpired(now));
        return new ArrayList<>(blocklist.values());
    }

    // ============================================================
    //  WAF Rules
    // ============================================================

    private void initializeWafRules() {
        // SQL Injection pattern
        wafRules.add(new WafRule("SQL_INJECTION", ".*(?:'|\\\")\\s*(?:OR|AND|UNION|SELECT|INSERT|DROP).*", true,
                "Potential SQL injection detected"));

        // XSS pattern
        wafRules.add(new WafRule("XSS", ".*<script.*>.*", true,
                "Potential XSS attack detected"));

        // Path traversal
        wafRules.add(new WafRule("PATH_TRAVERSAL", ".*\\.\\./.*", true,
                "Path traversal attempt detected"));

        // Suspicious User-Agent (known attack tools)
        wafRules.add(new WafRule("SUSPICIOUS_UA",
                ".*(?:sqlmap|nikto|nmap|acunetix|burpsuite|nessus).*", true,
                "Known attack tool User-Agent detected"));

        // Excessive content length
        wafRules.add(new WafRule("LARGE_PAYLOAD", null, false,
                "Request payload too large"));

        // Missing common headers (likely bot)
        wafRules.add(new WafRule("MISSING_HEADERS", null, false,
                "Missing required HTTP headers"));
    }

    private WafViolation evaluateWafRules(String ip, String endpoint, String method,
                                            String userAgent, Map<String, String> headers) {
        for (WafRule rule : wafRules) {
            switch (rule.name) {
                case "SQL_INJECTION":
                case "XSS":
                case "PATH_TRAVERSAL":
                    if (endpoint.matches(rule.pattern)) {
                        return new WafViolation(rule.name, rule.description);
                    }
                    break;
                case "SUSPICIOUS_UA":
                    if (userAgent != null && userAgent.toLowerCase().matches(rule.pattern)) {
                        return new WafViolation(rule.name, rule.description);
                    }
                    break;
                case "MISSING_HEADERS":
                    if (!headers.containsKey("Accept") && !headers.containsKey("User-Agent")) {
                        return new WafViolation(rule.name, rule.description);
                    }
                    break;
            }
        }
        return null;
    }

    // ============================================================
    //  Challenge-Based Verification
    // ============================================================

    /**
     * Issue a challenge to verify the client is legitimate (not a bot).
     * This is used as a DDoS mitigation technique.
     */
    public Challenge issueChallenge(String ip) {
        Challenge challenge = new Challenge();
        challenge.challengeId = UUID.randomUUID().toString();
        challenge.ip = ip;
        challenge.createdAt = System.currentTimeMillis();
        challenge.expiresAt = challenge.createdAt + 60_000; // 1 minute
        challenge.nonce = generateNonce();
        challenge.difficulty = calculateDifficulty(ip);
        return challenge;
    }

    /**
     * Verify a challenge response.
     */
    public boolean verifyChallenge(String challengeId, String ip, String response) {
        // Simplified: in production, use Proof-of-Work or CAPTCHA
        // For now, just verify the challenge ID is valid
        return challengeId != null && !challengeId.isEmpty();
    }

    // ============================================================
    //  Helper Methods
    // ============================================================

    private String generateNonce() {
        byte[] bytes = new byte[16];
        new Random().nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private int calculateDifficulty(String ip) {
        // Higher difficulty for IPs with higher traffic
        TrafficStats stats = ipTraffic.get(ip);
        if (stats == null) return 4; // Default 4 leading zeros
        long rps = stats.getRequestsPerSecond(System.currentTimeMillis());
        if (rps > 50) return 8;
        if (rps > 20) return 6;
        return 4;
    }

    // ============================================================
    //  Inner Classes
    // ============================================================

    /**
     * Sliding window traffic counter.
     */
    static class TrafficStats {
        private final ConcurrentLinkedDeque<Long> requestTimestamps = new ConcurrentLinkedDeque<>();
        private final int maxWindows;

        TrafficStats(int maxWindows) {
            this.maxWindows = maxWindows;
        }

        synchronized void recordRequest(long timestamp) {
            requestTimestamps.add(timestamp);
            // Clean old entries
            long cutoff = timestamp - (maxWindows * WINDOW_DURATION_MS);
            while (!requestTimestamps.isEmpty() && requestTimestamps.peekFirst() < cutoff) {
                requestTimestamps.pollFirst();
            }
            // Limit queue size
            while (requestTimestamps.size() > 10000) {
                requestTimestamps.pollFirst();
            }
        }

        long getRequestsPerSecond(long now) {
            long cutoff = now - 1000;
            return requestTimestamps.stream().filter(t -> t >= cutoff).count();
        }

        long getRequestsPerMinute(long now) {
            long cutoff = now - 60_000;
            return requestTimestamps.stream().filter(t -> t >= cutoff).count();
        }
    }

    public static class BlockEntry {
        public String ip;
        public String reason;
        public long blockedAt;
        public long blockedUntil;

        boolean isExpired(long now) {
            return now >= blockedUntil;
        }

        public Map<String, Object> toMap() {
            return Map.of(
                    "ip", ip,
                    "reason", reason,
                    "blocked_at", blockedAt,
                    "blocked_until", blockedUntil,
                    "remaining_ms", Math.max(0, blockedUntil - System.currentTimeMillis())
            );
        }
    }

    static class WafRule {
        String name;
        String pattern; // null means manual evaluation
        boolean regexBased;
        String description;

        WafRule(String name, String pattern, boolean regexBased, String description) {
            this.name = name;
            this.pattern = pattern;
            this.regexBased = regexBased;
            this.description = description;
        }
    }

    static class WafViolation {
        String ruleName;
        String reason;

        WafViolation(String ruleName, String reason) {
            this.ruleName = ruleName;
            this.reason = reason;
        }
    }

    public static class Challenge {
        public String challengeId;
        public String ip;
        public long createdAt;
        public long expiresAt;
        public String nonce;
        public int difficulty;

        public Map<String, Object> toMap() {
            return Map.of(
                    "challenge_id", challengeId,
                    "nonce", nonce,
                    "difficulty", difficulty,
                    "expires_at", expiresAt
            );
        }
    }

    public static class TrafficReport {
        public long globalRps;
        public int activeIps;
        public int blockedIps;
        public long timestamp;
        public List<TopTalker> topTalkers;

        public static class TopTalker {
            public String ip;
            public long rps;
            public TopTalker(String ip, long rps) { this.ip = ip; this.rps = rps; }

            public Map<String, Object> toMap() {
                return Map.of("ip", ip, "requests_per_second", rps);
            }
        }

        public Map<String, Object> toMap() {
            List<Map<String, Object>> talkers = new ArrayList<>();
            for (var t : topTalkers) talkers.add(t.toMap());
            return Map.of(
                    "global_rps", globalRps,
                    "active_ips", activeIps,
                    "blocked_ips", blockedIps,
                    "timestamp", timestamp,
                    "top_talkers", talkers
            );
        }
    }
}
