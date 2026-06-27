// Package httputil HTTP 工具函数
package httputil

import (
	"net"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// Response 统一响应格式
type Response struct {
	Data    any    `json:"data,omitempty"`
	Error   *Error `json:"error,omitempty"`
	Meta    *Meta  `json:"meta,omitempty"`
}

// Error 错误详情
type Error struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

// Meta 元信息
type Meta struct {
	RequestID string `json:"request_id,omitempty"`
	Page      int    `json:"page,omitempty"`
	PageSize  int    `json:"page_size,omitempty"`
	Total     int64  `json:"total,omitempty"`
}

// Success 成功响应
func Success(c *gin.Context, status int, data any) {
	c.JSON(status, Response{Data: data})
}

// SuccessWithMeta 成功响应（带分页）
func SuccessWithMeta(c *gin.Context, status int, data any, meta *Meta) {
	c.JSON(status, Response{Data: data, Meta: meta})
}

// ErrorResponse 错误响应
func ErrorResponse(c *gin.Context, status int, code, message string) {
	c.JSON(status, Response{
		Error: &Error{Code: code, Message: message},
	})
}

// ClientIP 获取真实客户端 IP（支持代理）
func ClientIP(r *http.Request) string {
	// X-Forwarded-For
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		ips := strings.Split(xff, ",")
		if len(ips) > 0 {
			ip := strings.TrimSpace(ips[0])
			if net.ParseIP(ip) != nil {
				return ip
			}
		}
	}

	// X-Real-IP
	if xri := r.Header.Get("X-Real-IP"); xri != "" {
		if net.ParseIP(xri) != nil {
			return xri
		}
	}

	// 直接连接 IP
	ip, _, _ := net.SplitHostPort(r.RemoteAddr)
	return ip
}
