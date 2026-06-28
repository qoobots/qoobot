package com.qoobot.qoocloud.gateway.filter;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

/**
 * Rate limiting filter using token bucket algorithm.
 */
@Component
@Order(2)
public class RateLimitFilter implements Filter {

    private static final Logger log = LoggerFactory.getLogger(RateLimitFilter.class);
    private static final int DEFAULT_RATE = 100; // requests per minute
    private static final long WINDOW_MS = 60_000;

    private final ConcurrentHashMap<String, TokenBucket> buckets = new ConcurrentHashMap<>();

    @Override
    public void doFilter(ServletRequest request, ServletResponse response,
                         FilterChain chain) throws IOException, ServletException {
        String clientIp = request.getRemoteAddr();
        TokenBucket bucket = buckets.computeIfAbsent(clientIp,
                k -> new TokenBucket(DEFAULT_RATE, WINDOW_MS));

        if (bucket.tryConsume()) {
            chain.doFilter(request, response);
        } else {
            HttpServletResponse httpResponse = (HttpServletResponse) response;
            httpResponse.setStatus(429);
            httpResponse.setContentType("application/json");
            httpResponse.getWriter().write(
                    "{\"error\":\"RATE_LIMITED\",\"message\":\"Too many requests\"}");
            log.warn("Rate limit exceeded for IP: {}", clientIp);
        }
    }

    private static class TokenBucket {
        private final int maxTokens;
        private final long windowMs;
        private double tokens;
        private long lastRefill;

        TokenBucket(int maxTokens, long windowMs) {
            this.maxTokens = maxTokens;
            this.windowMs = windowMs;
            this.tokens = maxTokens;
            this.lastRefill = System.currentTimeMillis();
        }

        synchronized boolean tryConsume() {
            refill();
            if (tokens >= 1) {
                tokens--;
                return true;
            }
            return false;
        }

        private void refill() {
            long now = System.currentTimeMillis();
            long elapsed = now - lastRefill;
            double refillAmount = (double) elapsed / windowMs * maxTokens;
            tokens = Math.min(maxTokens, tokens + refillAmount);
            lastRefill = now;
        }
    }
}
