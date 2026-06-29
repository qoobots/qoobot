package com.qoobot.qooauth.security.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Credential stuffing protection service.
 * <p>
 * Implements a 3-tier rate limiting strategy:
 * <ul>
 *   <li><b>Per-account</b>: Max attempts per account within a time window</li>
 *   <li><b>Per-IP</b>: Max attempts per source IP within a time window</li>
 *   <li><b>Global</b>: Max total attempts across all accounts within a time window</li>
 * </ul>
 * <p>
 * Escalation path: WARN -> CAPTCHA -> AUTO_BAN on threshold breach.
 * In production, this should be backed by Redis for distributed rate limiting.
 */
@Slf4j
@Service
public class CredentialStuffingService {

    // Thresholds
    private static final int PER_ACCOUNT_MAX_ATTEMPTS = 5;
    private static final int PER_IP_MAX_ATTEMPTS = 20;
    private static final int GLOBAL_MAX_ATTEMPTS = 1000;
    private static final int CAPTCHA_THRESHOLD = 10;
    private static final int AUTO_BAN_THRESHOLD = 15;

    // Window in seconds
    private static final long WINDOW_SECONDS = 300; // 5 minutes

    // In-memory rate counters (replace with Redis in production)
    private final ConcurrentHashMap<String, AttemptCounter> accountCounters = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, AttemptCounter> ipCounters = new ConcurrentHashMap<>();
    private final AttemptCounter globalCounter = new AttemptCounter();

    /**
     * Check if a login attempt should be allowed.
     *
     * @param userId    the user account
     * @param sourceIp  the source IP address
     * @return rate limit assessment
     */
    public Map<String, Object> checkRateLimit(String userId, String sourceIp) {
        Instant now = Instant.now();
        String action = "ALLOW";
        String level = "NONE";

        // 1. Per-account check
        AttemptCounter accountCounter = accountCounters.computeIfAbsent(userId, k -> new AttemptCounter());
        synchronized (accountCounter) {
            accountCounter.pruneIfExpired(now, WINDOW_SECONDS);
            accountCounter.increment();
            if (accountCounter.getCount() > AUTO_BAN_THRESHOLD) {
                action = "BAN";
                level = "ACCOUNT_BANNED";
                log.warn("Account auto-banned for credential stuffing: userId={}, attempts={}",
                        userId, accountCounter.getCount());
            } else if (accountCounter.getCount() > CAPTCHA_THRESHOLD) {
                action = "CAPTCHA";
                level = "ACCOUNT_CAPTCHA";
            } else if (accountCounter.getCount() > PER_ACCOUNT_MAX_ATTEMPTS) {
                action = "WARN";
                level = "ACCOUNT_WARN";
            }
        }

        // 2. Per-IP check (only if not already banned)
        if (!"BAN".equals(action)) {
            AttemptCounter ipCounter = ipCounters.computeIfAbsent(sourceIp, k -> new AttemptCounter());
            synchronized (ipCounter) {
                ipCounter.pruneIfExpired(now, WINDOW_SECONDS);
                ipCounter.increment();
                if (ipCounter.getCount() > AUTO_BAN_THRESHOLD) {
                    action = "BAN";
                    level = "IP_BANNED";
                    log.warn("IP auto-banned for credential stuffing: ip={}, attempts={}",
                            sourceIp, ipCounter.getCount());
                } else if (ipCounter.getCount() > CAPTCHA_THRESHOLD && !"CAPTCHA".equals(action)) {
                    action = "CAPTCHA";
                    level = "IP_CAPTCHA";
                } else if (ipCounter.getCount() > PER_IP_MAX_ATTEMPTS && "ALLOW".equals(action)) {
                    action = "WARN";
                    level = "IP_WARN";
                }
            }
        }

        // 3. Global check
        synchronized (globalCounter) {
            globalCounter.pruneIfExpired(now, WINDOW_SECONDS);
            globalCounter.increment();
            if (globalCounter.getCount() > GLOBAL_MAX_ATTEMPTS && "ALLOW".equals(action)) {
                action = "WARN";
                level = "GLOBAL_WARN";
                log.warn("Global rate limit exceeded: attempts={}", globalCounter.getCount());
            }
        }

        log.debug("Rate limit check: userId={}, ip={}, action={}, level={}",
                userId, sourceIp, action, level);

        return Map.of(
                "action", action,
                "level", level,
                "accountAttempts", getAccountAttempts(userId),
                "ipAttempts", getIpAttempts(sourceIp),
                "globalAttempts", globalCounter.getCount(),
                "windowSeconds", WINDOW_SECONDS
        );
    }

    /**
     * Reset counters for a specific account (e.g., after successful login).
     */
    public void resetAccount(String userId) {
        accountCounters.remove(userId);
        log.debug("Rate limit counter reset for account: {}", userId);
    }

    /**
     * Reset counters for a specific IP.
     */
    public void resetIp(String sourceIp) {
        ipCounters.remove(sourceIp);
        log.debug("Rate limit counter reset for IP: {}", sourceIp);
    }

    /**
     * Get current attempt count for an account.
     */
    public int getAccountAttempts(String userId) {
        AttemptCounter counter = accountCounters.get(userId);
        if (counter == null) return 0;
        synchronized (counter) {
            counter.pruneIfExpired(Instant.now(), WINDOW_SECONDS);
            return counter.getCount();
        }
    }

    /**
     * Get current attempt count for an IP.
     */
    public int getIpAttempts(String sourceIp) {
        AttemptCounter counter = ipCounters.get(sourceIp);
        if (counter == null) return 0;
        synchronized (counter) {
            counter.pruneIfExpired(Instant.now(), WINDOW_SECONDS);
            return counter.getCount();
        }
    }

    /**
     * Internal counter with time window support.
     */
    private static class AttemptCounter {
        private int count;
        private Instant windowStart = Instant.now();

        synchronized void increment() {
            count++;
        }

        synchronized int getCount() {
            return count;
        }

        synchronized void pruneIfExpired(Instant now, long windowSeconds) {
            if (now.isAfter(windowStart.plusSeconds(windowSeconds))) {
                count = 0;
                windowStart = now;
            }
        }
    }
}
