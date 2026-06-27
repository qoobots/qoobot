package middleware

import (
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
)

// RateLimiter 基于滑动窗口的速率限制器
type RateLimiter struct {
	mu      sync.Mutex
	windows map[string]*slidingWindow
	limit   int
	window  time.Duration
}

type slidingWindow struct {
	timestamps []time.Time
}

// NewRateLimiter 创建速率限制器
func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		windows: make(map[string]*slidingWindow),
		limit:   limit,
		window:  window,
	}
	// 定期清理过期条目
	go rl.cleanup()
	return rl
}

// Allow 检查是否允许请求
func (rl *RateLimiter) Allow(key string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	sw, exists := rl.windows[key]
	if !exists {
		sw = &slidingWindow{}
		rl.windows[key] = sw
	}

	// 移除窗口外的旧时间戳
	cutoff := now.Add(-rl.window)
	var valid []time.Time
	for _, t := range sw.timestamps {
		if t.After(cutoff) {
			valid = append(valid, t)
		}
	}
	sw.timestamps = valid

	if len(sw.timestamps) >= rl.limit {
		return false
	}

	sw.timestamps = append(sw.timestamps, now)
	return true
}

// cleanup 定期清理过期条目
func (rl *RateLimiter) cleanup() {
	ticker := time.NewTicker(5 * time.Minute)
	for range ticker.C {
		rl.mu.Lock()
		now := time.Now()
		for key, sw := range rl.windows {
			cutoff := now.Add(-rl.window)
			var valid []time.Time
			for _, t := range sw.timestamps {
				if t.After(cutoff) {
					valid = append(valid, t)
				}
			}
			if len(valid) == 0 {
				delete(rl.windows, key)
			} else {
				sw.timestamps = valid
			}
		}
		rl.mu.Unlock()
	}
}

// RateLimitMiddleware 速率限制中间件工厂
func RateLimitMiddleware(limit int, window time.Duration, keyFunc func(*gin.Context) string) gin.HandlerFunc {
	limiter := NewRateLimiter(limit, window)
	return func(c *gin.Context) {
		key := keyFunc(c)
		if key == "" {
			key = c.ClientIP()
		}
		if !limiter.Allow(key) {
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error": gin.H{
					"code":    "RATE_LIMITED",
					"message": "Too many requests, please try again later",
				},
			})
			c.Abort()
			return
		}
		c.Next()
	}
}

// IPRateLimit 基于 IP 的速率限制
func IPRateLimit(limit int, window time.Duration) gin.HandlerFunc {
	return RateLimitMiddleware(limit, window, func(c *gin.Context) string {
		return c.ClientIP()
	})
}

// UserRateLimit 基于用户的速率限制
func UserRateLimit(limit int, window time.Duration) gin.HandlerFunc {
	return RateLimitMiddleware(limit, window, func(c *gin.Context) string {
		if id, ok := GetUserID(c); ok {
			return id.String()
		}
		return c.ClientIP()
	})
}
