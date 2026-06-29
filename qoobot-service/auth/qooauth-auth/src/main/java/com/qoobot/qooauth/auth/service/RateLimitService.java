package com.qoobot.qooauth.auth.service;

import com.qoobot.qooauth.common.exception.RateLimitExceededException;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;

/**
 * Token Bucket rate limiter backed by Redis.
 * Provides per-user, per-IP, and per-API rate limiting.
 */
@Service
public class RateLimitService {

    private final RedisTemplate<String, String> redisTemplate;

    // Default limits
    private static final int LOGIN_MAX_ATTEMPTS = 5;
    private static final Duration LOGIN_WINDOW = Duration.ofMinutes(15);
    private static final int API_MAX_REQUESTS = 100;
    private static final Duration API_WINDOW = Duration.ofMinutes(1);

    public RateLimitService(RedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * Check login rate limit for an email address.
     * Uses sliding window: 5 attempts per 15 minutes.
     */
    public void checkLoginRateLimit(String email) {
        String key = "qooauth:login_fail:" + email.toLowerCase();
        String countStr = redisTemplate.opsForValue().get(key);
        int count = countStr != null ? Integer.parseInt(countStr) : 0;

        if (count >= LOGIN_MAX_ATTEMPTS) {
            Long ttl = redisTemplate.getExpire(key);
            throw new RateLimitExceededException(ttl != null ? ttl : LOGIN_WINDOW.getSeconds());
        }
    }

    /**
     * Record a failed login attempt.
     */
    public void recordLoginFailure(String email) {
        String key = "qooauth:login_fail:" + email.toLowerCase();
        redisTemplate.opsForValue().increment(key);
        redisTemplate.expire(key, LOGIN_WINDOW);
    }

    /**
     * Clear login failure count on successful login.
     */
    public void clearLoginFailures(String email) {
        redisTemplate.delete("qooauth:login_fail:" + email.toLowerCase());
    }

    /**
     * Check API rate limit for a user or IP.
     */
    public void checkApiRateLimit(String subject, String api) {
        String window = String.valueOf(Instant.now().getEpochSecond() / API_WINDOW.getSeconds());
        String key = "qooauth:rate_limit:" + api + ":" + subject + ":" + window;

        String countStr = redisTemplate.opsForValue().get(key);
        int count = countStr != null ? Integer.parseInt(countStr) : 0;

        if (count >= API_MAX_REQUESTS) {
            Long ttl = redisTemplate.getExpire(key);
            throw new RateLimitExceededException(ttl != null ? ttl : API_WINDOW.getSeconds());
        }

        redisTemplate.opsForValue().increment(key);
        redisTemplate.expire(key, API_WINDOW);
    }
}
