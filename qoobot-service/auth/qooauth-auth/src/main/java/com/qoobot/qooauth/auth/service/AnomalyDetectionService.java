package com.qoobot.qooauth.auth.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.qoobot.qooauth.auth.entity.AnomalyEvent;
import com.qoobot.qooauth.auth.entity.LoginHistory;
import com.qoobot.qooauth.auth.repository.AnomalyEventRepository;
import com.qoobot.qooauth.auth.repository.LoginHistoryRepository;
import com.qoobot.qooauth.common.util.IdGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Anomaly Detection Service.
 * <p>
 * Detects login anomalies using multi-dimensional feature scoring:
 * <ul>
 *   <li>Geographic anomaly — login from new country/city</li>
 *   <li>Velocity anomaly — impossible travel between two locations</li>
 *   <li>Temporal anomaly — login at unusual time of day</li>
 *   <li>Device anomaly — login from new device fingerprint</li>
 *   <li>Frequency anomaly — excessive login attempts (brute-force)</li>
 *   <li>IP reputation anomaly — login from flagged IP</li>
 * </ul>
 * <p>
 * Risk levels:
 * <ul>
 *   <li>LOW (0.0–0.3) — benign, no action needed</li>
 *   <li>MEDIUM (0.3–0.6) — suspicious, flag for review</li>
 *   <li>HIGH (0.6–0.8) — likely malicious, require MFA challenge</li>
 *   <li>CRITICAL (0.8–1.0) — attack detected, block and alert</li>
 * </ul>
 */
@Service
public class AnomalyDetectionService {

    private static final Logger log = LoggerFactory.getLogger(AnomalyDetectionService.class);

    private final LoginHistoryRepository loginHistoryRepository;
    private final AnomalyEventRepository anomalyEventRepository;
    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    // Time windows
    private static final Duration GEO_HISTORY_WINDOW = Duration.ofDays(90);
    private static final Duration VELOCITY_WINDOW = Duration.ofMinutes(30);
    private static final Duration FREQUENCY_WINDOW = Duration.ofMinutes(15);
    private static final Duration IP_REPUTATION_WINDOW = Duration.ofHours(24);

    // Thresholds
    private static final int FREQUENCY_THRESHOLD = 5;
    private static final double VELOCITY_THRESHOLD_KMH = 800.0; // Commercial flight speed as upper bound
    private static final int IP_REPUTATION_FAIL_THRESHOLD = 10;

    // Redis key prefixes
    private static final String IP_REPUTATION_KEY = "qooauth:threat:ip_rep:";
    private static final String FREQUENCY_COUNTER_KEY = "qooauth:threat:freq:";

    public AnomalyDetectionService(LoginHistoryRepository loginHistoryRepository,
                                    AnomalyEventRepository anomalyEventRepository,
                                    RedisTemplate<String, String> redisTemplate,
                                    ObjectMapper objectMapper) {
        this.loginHistoryRepository = loginHistoryRepository;
        this.anomalyEventRepository = anomalyEventRepository;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    /**
     * Evaluate login attempt for anomalies and return a risk score (0.0–1.0).
     * Called before login succeeds/fails to enable early blocking.
     *
     * @param userId       user ID (may be null for non-existent user attempts)
     * @param ip           client IP address
     * @param userAgent    client user agent
     * @param fingerprint  device fingerprint (hashed)
     * @param geoCountry   ISO country code from GeoIP
     * @param geoCity      city name from GeoIP
     * @param isSuccess    whether this login attempt succeeded
     * @return AnomalyResult with risk score, level, and reasons
     */
    public AnomalyResult evaluate(String userId, String ip, String userAgent,
                                   String fingerprint, String geoCountry, String geoCity,
                                   boolean isSuccess) {
        List<String> reasons = new ArrayList<>();
        Map<String, Double> featureScores = new LinkedHashMap<>();
        double totalScore = 0.0;

        // 1. Geographic anomaly check (only for known users)
        if (userId != null && geoCountry != null && !geoCountry.isEmpty()) {
            double geoScore = checkGeographicAnomaly(userId, geoCountry, geoCity, reasons);
            featureScores.put("geo_anomaly", geoScore);
            totalScore += geoScore * 0.20;
        }

        // 2. Velocity anomaly check (impossible travel)
        if (userId != null && geoCountry != null && !geoCountry.isEmpty()) {
            double velocityScore = checkVelocityAnomaly(userId, ip, geoCountry, geoCity, reasons);
            featureScores.put("velocity_anomaly", velocityScore);
            totalScore += velocityScore * 0.20;
        }

        // 3. Temporal anomaly check (unusual hour)
        double temporalScore = checkTemporalAnomaly(userId, reasons);
        featureScores.put("temporal_anomaly", temporalScore);
        totalScore += temporalScore * 0.10;

        // 4. Device anomaly check (new device)
        if (userId != null && fingerprint != null && !fingerprint.isEmpty()) {
            double deviceScore = checkDeviceAnomaly(userId, fingerprint, reasons);
            featureScores.put("device_anomaly", deviceScore);
            totalScore += deviceScore * 0.15;
        }

        // 5. Frequency anomaly check (brute-force detection)
        double freqScore = checkFrequencyAnomaly(userId, ip, reasons);
        featureScores.put("frequency_anomaly", freqScore);
        totalScore += freqScore * 0.20;

        // 6. IP reputation check
        double ipRepScore = checkIpReputation(ip, isSuccess, reasons);
        featureScores.put("ip_reputation", ipRepScore);
        totalScore += ipRepScore * 0.15;

        // Clamp to [0.0, 1.0]
        totalScore = Math.max(0.0, Math.min(1.0, totalScore));

        // Determine risk level
        String riskLevel = scoreToLevel(totalScore);

        // Determine action
        String actionTaken = determineAction(totalScore, isSuccess);

        return new AnomalyResult(totalScore, riskLevel, reasons, featureScores, actionTaken);
    }

    /**
     * Record an anomaly event to the database.
     */
    @Transactional
    public AnomalyEvent recordAnomaly(String userId, AnomalyResult result,
                                       String ip, String userAgent, String fingerprint,
                                       String geoCountry, String geoCity) {
        AnomalyEvent event = new AnomalyEvent();
        event.setEventId(IdGenerator.generateAnomalyEventId());
        event.setUserId(userId);
        event.setEventType("LOGIN_ANOMALY");
        event.setRiskScore(result.score);
        event.setRiskLevel(result.riskLevel);
        event.setIpAddress(ip);
        event.setUserAgent(userAgent);
        event.setDeviceFingerprint(fingerprint);
        event.setGeoCountry(geoCountry);
        event.setGeoCity(geoCity);
        event.setAnomalyReasons(toJson(result.reasons));
        event.setFeatures(toJson(result.featureScores));
        event.setActionTaken(result.actionTaken);
        event.setCreatedAt(Instant.now());

        return anomalyEventRepository.save(event);
    }

    /**
     * Get recent anomalies for a user.
     */
    public List<AnomalyEvent> getRecentAnomalies(String userId, Duration window) {
        Instant since = Instant.now().minus(window);
        return anomalyEventRepository.findRecentByUserId(userId, since);
    }

    /**
     * Get unresolved high/critical anomalies.
     */
    public List<AnomalyEvent> getUnresolvedHighRiskAnomalies() {
        List<AnomalyEvent> high = anomalyEventRepository.findByRiskLevelAndResolved("HIGH", false);
        List<AnomalyEvent> critical = anomalyEventRepository.findByRiskLevelAndResolved("CRITICAL", false);
        List<AnomalyEvent> all = new ArrayList<>(high);
        all.addAll(critical);
        return all;
    }

    /**
     * Mark an anomaly event as resolved.
     */
    @Transactional
    public void resolveAnomaly(String eventId, String resolvedBy) {
        anomalyEventRepository.findById(eventId).ifPresent(event -> {
            event.setResolved(true);
            event.setResolvedBy(resolvedBy);
            event.setResolvedAt(Instant.now());
            anomalyEventRepository.save(event);
        });
    }

    /**
     * Check if IP is currently in a blocked reputation list.
     */
    public boolean isIpBlocked(String ip) {
        String key = IP_REPUTATION_KEY + ip;
        String val = redisTemplate.opsForValue().get(key);
        if (val == null) return false;
        try {
            int score = Integer.parseInt(val);
            return score >= IP_REPUTATION_FAIL_THRESHOLD;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /**
     * Add IP to reputation tracking (called on login failure).
     */
    public void addIpReputationHit(String ip) {
        String key = IP_REPUTATION_KEY + ip;
        redisTemplate.opsForValue().increment(key);
        redisTemplate.expire(key, IP_REPUTATION_WINDOW);
    }

    // ========================================================================
    // Private Detection Methods
    // ========================================================================

    /**
     * Check if login is from a new geographic location.
     */
    private double checkGeographicAnomaly(String userId, String geoCountry, String geoCity,
                                           List<String> reasons) {
        Instant since = Instant.now().minus(GEO_HISTORY_WINDOW);
        List<LoginHistory> history = loginHistoryRepository.findByUserIdAndCreatedAtAfter(userId, since);

        if (history.isEmpty()) return 0.0; // First login, no baseline

        // Extract known countries and cities from successful logins
        Set<String> knownCountries = history.stream()
                .filter(LoginHistory::isSuccess)
                .map(LoginHistory::getGeoCountry)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        Set<String> knownCities = history.stream()
                .filter(LoginHistory::isSuccess)
                .map(LoginHistory::getGeoCity)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        double score = 0.0;

        // New country = high anomaly
        if (!knownCountries.isEmpty() && !knownCountries.contains(geoCountry)) {
            reasons.add("GEO_NEW_COUNTRY: Login from new country '" + geoCountry + "'");
            score += 0.7;
        }

        // New city (but same country) = medium anomaly
        if (!knownCities.isEmpty() && !knownCities.contains(geoCity) && knownCountries.contains(geoCountry)) {
            reasons.add("GEO_NEW_CITY: Login from new city '" + geoCity + "'");
            score += 0.3;
        }

        return Math.min(1.0, score);
    }

    /**
     * Check for impossible travel velocity between last login and current.
     */
    private double checkVelocityAnomaly(String userId, String ip, String geoCountry,
                                         String geoCity, List<String> reasons) {
        Instant since = Instant.now().minus(VELOCITY_WINDOW);
        List<LoginHistory> recent = loginHistoryRepository.findByUserIdAndCreatedAtAfter(userId, since);

        if (recent.size() < 2) return 0.0;

        // Find last successful login with geo info
        LoginHistory lastLogin = recent.stream()
                .filter(l -> l.isSuccess() && l.getGeoCountry() != null)
                .findFirst()
                .orElse(null);

        if (lastLogin == null) return 0.0;

        // If same country/city, no velocity anomaly
        if (geoCountry != null && geoCountry.equals(lastLogin.getGeoCountry()) &&
            geoCity != null && geoCity.equals(lastLogin.getGeoCity())) {
            return 0.0;
        }

        // Different country within 30 minutes → potential impossible travel
        long minutesBetween = ChronoUnit.MINUTES.between(lastLogin.getCreatedAt(), Instant.now());
        if (minutesBetween <= 0) return 0.0;

        // Rough estimate: if countries differ within short time, flag it
        if (geoCountry != null && !geoCountry.equals(lastLogin.getGeoCountry())) {
            double hoursBetween = minutesBetween / 60.0;
            // Assume ~10000 km between countries → check if speed exceeds threshold
            double estimatedKmh = 10000.0 / hoursBetween;
            if (estimatedKmh > VELOCITY_THRESHOLD_KMH) {
                reasons.add(String.format("VELOCITY_ANOMALY: Impossible travel %s→%s in %.0f min (%.0f km/h)",
                        lastLogin.getGeoCountry(), geoCountry, minutesBetween, estimatedKmh));
                return Math.min(1.0, estimatedKmh / (VELOCITY_THRESHOLD_KMH * 2));
            }
        }

        return 0.0;
    }

    /**
     * Check if login is at an unusual time for this user.
     */
    private double checkTemporalAnomaly(String userId, List<String> reasons) {
        if (userId == null) return 0.0;

        Instant since = Instant.now().minus(Duration.ofDays(30));
        List<LoginHistory> history = loginHistoryRepository.findByUserIdAndCreatedAtAfter(userId, since);

        if (history.size() < 5) return 0.0; // Not enough data

        // Build hour-of-day distribution from successful logins
        Map<Integer, Long> hourCounts = history.stream()
                .filter(LoginHistory::isSuccess)
                .map(l -> l.getCreatedAt())
                .collect(Collectors.groupingBy(
                        t -> java.time.ZoneId.of("UTC").getRules().getOffset(t).getTotalSeconds() / 3600,
                        Collectors.counting()));

        int currentHour = Instant.now().atZone(java.time.ZoneId.of("UTC")).getHour();

        long totalLogins = hourCounts.values().stream().mapToLong(Long::longValue).sum();
        long currentHourLogins = hourCounts.getOrDefault(currentHour, 0L);
        double ratio = totalLogins > 0 ? (double) currentHourLogins / totalLogins : 0;

        // If current hour has < 5% of total logins, it's unusual
        if (ratio < 0.05 && totalLogins >= 10) {
            reasons.add("TEMPORAL_ANOMALY: Login at unusual hour " + currentHour + ":00 UTC");
            return 0.5;
        }

        // Very late night (2-5 AM local time) → slightly suspicious
        if (currentHour >= 2 && currentHour <= 5) {
            return 0.15;
        }

        return 0.0;
    }

    /**
     * Check if login is from a previously unseen device.
     */
    private double checkDeviceAnomaly(String userId, String fingerprint, List<String> reasons) {
        Instant since = Instant.now().minus(Duration.ofDays(90));
        List<LoginHistory> history = loginHistoryRepository.findByUserIdAndCreatedAtAfter(userId, since);

        Set<String> knownFingerprints = history.stream()
                .filter(LoginHistory::isSuccess)
                .map(LoginHistory::getDeviceFingerprint)
                .filter(Objects::nonNull)
                .collect(Collectors.toSet());

        if (!knownFingerprints.isEmpty() && !knownFingerprints.contains(fingerprint)) {
            reasons.add("DEVICE_ANOMALY: Login from unrecognized device fingerprint");
            return 0.6;
        }

        return 0.0;
    }

    /**
     * Check for excessive login attempts (brute-force detection).
     */
    private double checkFrequencyAnomaly(String userId, String ip, List<String> reasons) {
        String key = FREQUENCY_COUNTER_KEY + (userId != null ? userId : ip);
        String countStr = redisTemplate.opsForValue().get(key);
        long count = countStr != null ? Long.parseLong(countStr) : 0;

        // Increment counter
        redisTemplate.opsForValue().increment(key);
        redisTemplate.expire(key, FREQUENCY_WINDOW);

        if (count >= FREQUENCY_THRESHOLD) {
            reasons.add("FREQUENCY_ANOMALY: " + count + " login attempts in " +
                    FREQUENCY_WINDOW.toMinutes() + " minutes");
            return Math.min(1.0, (count - FREQUENCY_THRESHOLD) * 0.15);
        }

        if (count >= FREQUENCY_THRESHOLD * 0.6) {
            return 0.2; // Approaching threshold
        }

        return 0.0;
    }

    /**
     * Check IP reputation based on recent failure history.
     */
    private double checkIpReputation(String ip, boolean isSuccess, List<String> reasons) {
        String key = IP_REPUTATION_KEY + ip;
        String val = redisTemplate.opsForValue().get(key);
        int failCount = val != null ? Integer.parseInt(val) : 0;

        if (!isSuccess) {
            // Increment on failure
            redisTemplate.opsForValue().increment(key);
            redisTemplate.expire(key, IP_REPUTATION_WINDOW);
            failCount++;
        }

        if (failCount >= IP_REPUTATION_FAIL_THRESHOLD) {
            reasons.add("IP_REPUTATION: IP has " + failCount + " failures in 24h");
            return Math.min(1.0, failCount * 0.1);
        }

        if (failCount >= IP_REPUTATION_FAIL_THRESHOLD * 0.5) {
            return 0.3;
        }

        return 0.0;
    }

    // ========================================================================
    // Helpers
    // ========================================================================

    private String scoreToLevel(double score) {
        if (score >= 0.8) return "CRITICAL";
        if (score >= 0.6) return "HIGH";
        if (score >= 0.3) return "MEDIUM";
        return "LOW";
    }

    private String determineAction(double score, boolean isSuccess) {
        if (score >= 0.8) return "BLOCK";
        if (score >= 0.6) return "CHALLENGE_MFA";
        if (score >= 0.3) return "FLAG_REVIEW";
        return "ALLOW";
    }

    private String toJson(Object obj) {
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize to JSON", e);
            return "{}";
        }
    }

    /**
     * Result of anomaly evaluation.
     */
    public static class AnomalyResult {
        public final double score;
        public final String riskLevel;
        public final List<String> reasons;
        public final Map<String, Double> featureScores;
        public final String actionTaken;

        public AnomalyResult(double score, String riskLevel, List<String> reasons,
                              Map<String, Double> featureScores, String actionTaken) {
            this.score = score;
            this.riskLevel = riskLevel;
            this.reasons = reasons;
            this.featureScores = featureScores;
            this.actionTaken = actionTaken;
        }

        public boolean shouldBlock() { return "BLOCK".equals(actionTaken); }
        public boolean shouldChallenge() { return "CHALLENGE_MFA".equals(actionTaken) || shouldBlock(); }
        public boolean isSuspicious() { return score >= 0.3; }
    }
}
