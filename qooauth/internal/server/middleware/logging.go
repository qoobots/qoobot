package middleware

import (
	"log/slog"
	"time"

	"github.com/gin-gonic/gin"
)

// RequestLogger 请求日志中间件
func RequestLogger(logger *slog.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		c.Next()

		latency := time.Since(start)
		statusCode := c.Writer.Status()

		attrs := []slog.Attr{
			slog.String("method", c.Request.Method),
			slog.String("path", path),
			slog.String("query", query),
			slog.Int("status", statusCode),
			slog.String("ip", c.ClientIP()),
			slog.String("user_agent", c.Request.UserAgent()),
			slog.Duration("latency", latency),
		}

		if userID, ok := GetUserID(c); ok {
			attrs = append(attrs, slog.String("user_id", userID.String()))
		}

		if statusCode >= 500 {
			logger.LogAttrs(c.Request.Context(), slog.LevelError, "request completed", attrs...)
		} else if statusCode >= 400 {
			logger.LogAttrs(c.Request.Context(), slog.LevelWarn, "request completed", attrs...)
		} else {
			logger.LogAttrs(c.Request.Context(), slog.LevelInfo, "request completed", attrs...)
		}
	}
}
