package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.common.constants.ErrorCodes;
import com.qoobot.qooauth.common.exception.AuthException;
import com.qoobot.qooauth.common.exception.RateLimitExceededException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;

/**
 * Brute-force and credential stuffing protection service.
 * <p>
 * Multi-layered defense:
 * <ul>
 *   <li>Per-account rate limiting (password spraying detection)</li>
 *   <li>Per-IP rate limiting (distributed brute-force detection)</li>
 *   <li>Global rate limiting (large-scale attack detection)</li>
 *   <li>CAPTCHA challenge escalation</li>
 *   <li>IP reputation scoring with automatic blocking</li>
 * </ul>
 */
@Service
public class BruteForceProtectionService {

    private static final Logger log = LoggerFactory.getLogger(BruteForceProtectionService.class);

    private final RedisTemplate<String, String> redisTemplate;
    private final AnomalyDetectionService anomalyDetectionService;

    // Time windows
    private static final Duration PER_ACCOUNT_WINDOW = Duration.ofMinutes(15);
    private static final Duration PER_IP_WINDOW = Duration.ofMinutes(10);
    private static final Duration GLOBAL_WINDOW = Duration.ofMinutes(1);

    // Thresholds
    private static final int PER_ACCOUNT_MAX_FAILURES = 5;
    private static final int PER_IP_MAX_FAILURES = 20;
    private static final int GLOBAL_MAX_FAILURES = 100;
    private static final int CAPTCHA_THRESHOLD = 3; // Failures before requiring CAPTCHA
    private static final int BLOCK_THRESHOLD = 10;  // Failures before blocking account

    // Redis key prefixes
    private static final String ACCOUNT_FAIL_KEY = "qooauth:brute:account:";
    private static final String IP_FAIL_KEY = "qooauth:brute:ip:";
    private static final String GLOBAL_FAIL_KEY = "qooauth:brute:global:";
    private static final String CAPTCHA_REQUIRED_KEY = "qooauth:brute:captcha:";
    private static final String ACCOUNT_BLOCKED_KEY = "qooauth:brute:blocked:";

    public BruteForceProtectionService(RedisTemplate<String, String> redisTemplate,
                                        AnomalyDetectionService anomalyDetectionService) {
        this.redisTemplate = redisTemplate;
        this.anomalyDetectionService = anomalyDetectionService;
    }

    /**
     * Check if the login attempt should be allowed or challenged.
     * Called before password verification.
     *
     * @param email the login email
     * @param ip    the client IP address
     * @throws AuthException if login should be blocked
     * @throws RateLimitExceededException if CAPTCHA is required
     */
    public void checkBeforeLogin(String email, String ip) {
        // 1. Check if account is temporarily blocked
        if (isAccountBlocked(email)) {
            throw new AuthException(ErrorCodes.ACCOUNT_LOCKED,
                    "Account temporarily locked due to too many failed attempts. Try again later.");
        }

        // 2. Check if IP is blocked by reputation system
        if (anomalyDetectionService.isIpBlocked(ip)) {
            throw new AuthException(ErrorCodes.ACCOUNT_LOCKED,
                    "Access denied due to suspicious activity from your network.");
        }

        // 3. Check per-IP failure count
        String ipKey = IP_FAIL_KEY + ip;
        String ipCountStr = redisTemplate.opsForValue().get(ipKey);
        int ipCount = ipCountStr != null ? Integer.parseInt(ipCountStr) : 0;
        if (ipCount >= PER_IP_MAX_FAILURES) {
            log.warn("IP blocked for excessive failures: {}", ip);
            throw new AuthException(ErrorCodes.ACCOUNT_LOCKED,
                    "Too many failed attempts from your network. Please try again later.");
        }

        // 4. Check global failure rate (large-scale attack)
        String globalKey = GLOBAL_FAIL_KEY + currentWindow();
        String globalCountStr = redisTemplate.opsForValue().get(globalKey);
        int globalCount = globalCountStr != null ? Integer.parseInt(globalCountStr) : 0;
        if (globalCount >= GLOBAL_MAX_FAILURES) {
            log.warn("Global failure threshold exceeded: {}", globalCount);
            // Don't block entirely, but slow down
            throw new RateLimitExceededException(GLOBAL_WINDOW.getSeconds());
        }

        // 5. Check if CAPTCHA is required for this account
        if (isCaptchaRequired(email)) {
            throw new RateLimitExceededException(PER_ACCOUNT_WINDOW.getSeconds());
        }
    }

    /**
     * Record a failed login attempt.
     * Increments all relevant counters.
     *
     * @param email the login email
     * @param ip    the client IP address
     */
    public void recordFailure(String email, String ip) {
        Instant now = Instant.now();

        // Per-account counter
        String accountKey = ACCOUNT_FAIL_KEY + email.toLowerCase();
        Long accountCount = redisTemplate.opsForValue().increment(accountKey);
        redisTemplate.expire(accountKey, PER_ACCOUNT_WINDOW);

        // Per-IP counter
        String ipKey = IP_FAIL_KEY + ip;
        redisTemplate.opsForValue().increment(ipKey);
        redisTemplate.expire(ipKey, PER_IP_WINDOW);

        // Global counter
        String globalKey = GLOBAL_FAIL_KEY + currentWindow();
        redisTemplate.opsForValue().increment(globalKey);
        redisTemplate.expire(globalKey, GLOBAL_WINDOW);

        // Add to IP reputation
        anomalyDetectionService.addIpReputationHit(ip);

        // Escalate: require CAPTCHA after threshold
        if (accountCount != null && accountCount >= CAPTCHA_THRESHOLD) {
            String captchaKey = CAPTCHA_REQUIRED_KEY + email.toLowerCase();
            redisTemplate.opsForValue().set(captchaKey, "true", PER_ACCOUNT_WINDOW);
        }

        // Escalate: block account after higher threshold
        if (accountCount != null && accountCount >= BLOCK_THRESHOLD) {
            String blockedKey = ACCOUNT_BLOCKED_KEY + email.toLowerCase();
            redisTemplate.opsForValue().set(blockedKey, "true", Duration.ofHours(1));
            log.warn("Account temporarily blocked: {} ({} failures)", email, accountCount);
        }
    }

    /**
     * Clear failure counters on successful login.
     *
     * @param email the login email
     * @param ip    the client IP address
     */
    public void clearFailures(String email, String ip) {
        redisTemplate.delete(ACCOUNT_FAIL_KEY + email.toLowerCase());
        redisTemplate.delete(CAPTCHA_REQUIRED_KEY + email.toLowerCase());
        redisTemplate.delete(ACCOUNT_BLOCKED_KEY + email.toLowerCase());
        // Note: we don't clear IP counter on success — an IP with many failures is still suspicious
    }

    /**
     * Check if CAPTCHA is required for this account.
     */
    public boolean isCaptchaRequired(String email) {
        String key = CAPTCHA_REQUIRED_KEY + email.toLowerCase();
        return Boolean.parseBoolean(redisTemplate.opsForValue().get(key));
    }

    /**
     * Check if account is temporarily blocked.
     */
    public boolean isAccountBlocked(String email) {
        String key = ACCOUNT_BLOCKED_KEY + email.toLowerCase();
        return Boolean.parseBoolean(redisTemplate.opsForValue().get(key));
    }

    /**
     * Get current failure count for an account.
     */
    public int getAccountFailureCount(String email) {
        String key = ACCOUNT_FAIL_KEY + email.toLowerCase();
        String countStr = redisTemplate.opsForValue().get(key);
        return countStr != null ? Integer.parseInt(countStr) : 0;
    }

    /**
     * Get current failure count for an IP.
     */
    public int getIpFailureCount(String ip) {
        String key = IP_FAIL_KEY + ip;
        String countStr = redisTemplate.opsForValue().get(key);
        return countStr != null ? Integer.parseInt(countStr) : 0;
    }

    /**
     * Manually unblock an account.
     */
    public void unblockAccount(String email) {
        redisTemplate.delete(ACCOUNT_BLOCKED_KEY + email.toLowerCase());
        redisTemplate.delete(ACCOUNT_FAIL_KEY + email.toLowerCase());
        redisTemplate.delete(CAPTCHA_REQUIRED_KEY + email.toLowerCase());
    }

    /**
     * Manually unblock an IP.
     */
    public void unblockIp(String ip) {
        redisTemplate.delete(IP_FAIL_KEY + ip);
    }

    private String currentWindow() {
        return String.valueOf(Instant.now().getEpochSecond() / GLOBAL_WINDOW.getSeconds());
    }
}
