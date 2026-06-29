package com.qoobot.qooauth.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Set;

/**
 * Token bucket rate limiting filter using Redis.
 * Supports per-user and per-IP rate limiting with configurable thresholds.
 */
@Slf4j
@Component
public class RateLimitFilter implements GlobalFilter, Ordered {

    private static final Set<String> RATE_LIMITED_PATHS = Set.of(
        "/api/v1/auth/token",
        "/api/v1/api-keys",
        "/api/v1/devices"
    );

    // Token bucket parameters
    private static final long DEFAULT_CAPACITY = 100;
    private static final long DEFAULT_REFILL_RATE = 10;
    private static final Duration DEFAULT_WINDOW = Duration.ofMinutes(1);

    // Redis Lua script for token bucket algorithm
    private static final RedisScript<Long> TOKEN_BUCKET_SCRIPT = RedisScript.of(
        """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])

        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1])
        local last_refill = tonumber(bucket[2])

        if tokens == nil then
            tokens = capacity
            last_refill = now
        end

        local elapsed = math.max(0, now - last_refill)
        local refill = math.floor(elapsed * refill_rate)
        tokens = math.min(capacity, tokens + refill)

        if refill > 0 then
            last_refill = now
        end

        local allowed = 0
        if tokens >= requested then
            tokens = tokens - requested
            allowed = 1
        end

        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
        redis.call('EXPIRE', key, 300)

        return allowed
        """, Long.class);

    private final ReactiveRedisTemplate<String, String> redisTemplate;

    public RateLimitFilter(ReactiveRedisTemplate<String, String> redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // Only rate limit specific paths
        if (!shouldRateLimit(path)) {
            return chain.filter(exchange);
        }

        String clientIp = getClientIp(exchange);
        String userId = exchange.getRequest().getHeaders().getFirst("X-Auth-User-Id");
        String rateLimitKey = buildRateLimitKey(path, userId != null ? userId : clientIp);

        long now = Instant.now().getEpochSecond();
        long requested = 1;

        List<String> keys = List.of(rateLimitKey);
        List<String> args = List.of(
            String.valueOf(DEFAULT_CAPACITY),
            String.valueOf(DEFAULT_REFILL_RATE),
            String.valueOf(now),
            String.valueOf(requested)
        );

        return redisTemplate.execute(TOKEN_BUCKET_SCRIPT, keys, args)
            .flatMap(allowed -> {
                if (allowed == 1L) {
                    return chain.filter(exchange);
                } else {
                    log.debug("Rate limit exceeded for key: {}", rateLimitKey);
                    exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
                    exchange.getResponse().getHeaders().add("Retry-After", "60");
                    return exchange.getResponse().setComplete();
                }
            });
    }

    @Override
    public int getOrder() {
        return -50; // After JWT auth, before other filters
    }

    private boolean shouldRateLimit(String path) {
        return RATE_LIMITED_PATHS.stream().anyMatch(path::startsWith);
    }

    private String buildRateLimitKey(String path, String identifier) {
        // Normalize path for key consistency
        String normalizedPath = path.replaceAll("/\\d+", "/{id}");
        return "rate_limit:" + normalizedPath + ":" + identifier;
    }

    private String getClientIp(ServerWebExchange exchange) {
        String xForwardedFor = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isBlank()) {
            return xForwardedFor.split(",")[0].trim();
        }
        var remoteAddress = exchange.getRequest().getRemoteAddress();
        return remoteAddress != null ? remoteAddress.getAddress().getHostAddress() : "unknown";
    }
}
