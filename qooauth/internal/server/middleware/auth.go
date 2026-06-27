// Package middleware 提供 HTTP/gRPC 中间件
package middleware

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/qoobot/qooauth/internal/crypto"
)

const (
	// ContextKeyUserID 上下文中的用户 ID
	ContextKeyUserID = "user_id"
	// ContextKeyEmail 上下文中的用户邮箱
	ContextKeyEmail = "email"
	// ContextKeyScopes 上下文中的权限范围
	ContextKeyScopes = "scopes"
)

// JWTAuth JWT 认证中间件
func JWTAuth(jwt *crypto.JWTManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		token := extractToken(c)
		if token == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": gin.H{
					"code":    "TOKEN_MISSING",
					"message": "Authorization header is required",
				},
			})
			c.Abort()
			return
		}

		claims, err := jwt.ValidateAccessToken(token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": gin.H{
					"code":    "TOKEN_INVALID",
					"message": "Invalid or expired token",
				},
			})
			c.Abort()
			return
		}

		userID, err := uuid.Parse(claims.Subject)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": gin.H{
					"code":    "TOKEN_INVALID",
					"message": "Invalid user ID in token",
				},
			})
			c.Abort()
			return
		}

		c.Set(ContextKeyUserID, userID)
		c.Set(ContextKeyEmail, claims.Email)
		c.Set(ContextKeyScopes, claims.Scopes)
		c.Next()
	}
}

// APIKeyAuth API Key 认证中间件（用于第三方应用）
func APIKeyAuth(validateFunc func(apiKey string) (uuid.UUID, []string, error)) gin.HandlerFunc {
	return func(c *gin.Context) {
		apiKey := extractAPIKey(c)
		if apiKey == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": gin.H{
					"code":    "API_KEY_MISSING",
					"message": "X-API-Key header is required",
				},
			})
			c.Abort()
			return
		}

		userID, scopes, err := validateFunc(apiKey)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": gin.H{
					"code":    "API_KEY_INVALID",
					"message": "Invalid or revoked API key",
				},
			})
			c.Abort()
			return
		}

		c.Set(ContextKeyUserID, userID)
		c.Set(ContextKeyScopes, scopes)
		c.Next()
	}
}

// OptionalAuth 可选认证（不强制，但有 Token 时解析）
func OptionalAuth(jwt *crypto.JWTManager) gin.HandlerFunc {
	return func(c *gin.Context) {
		token := extractToken(c)
		if token == "" {
			c.Next()
			return
		}

		claims, err := jwt.ValidateAccessToken(token)
		if err != nil {
			c.Next()
			return
		}

		userID, err := uuid.Parse(claims.Subject)
		if err != nil {
			c.Next()
			return
		}

		c.Set(ContextKeyUserID, userID)
		c.Set(ContextKeyEmail, claims.Email)
		c.Set(ContextKeyScopes, claims.Scopes)
		c.Next()
	}
}

// extractToken 从 Authorization header 提取 Bearer Token
func extractToken(c *gin.Context) string {
	header := c.GetHeader("Authorization")
	if header == "" {
		return ""
	}
	parts := strings.SplitN(header, " ", 2)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
		return ""
	}
	return parts[1]
}

// extractAPIKey 从 X-API-Key header 提取 API Key
func extractAPIKey(c *gin.Context) string {
	return c.GetHeader("X-API-Key")
}

// GetUserID 从 Gin 上下文获取用户 ID
func GetUserID(c *gin.Context) (uuid.UUID, bool) {
	id, exists := c.Get(ContextKeyUserID)
	if !exists {
		return uuid.Nil, false
	}
	userID, ok := id.(uuid.UUID)
	return userID, ok
}

// GetScopes 从 Gin 上下文获取权限范围
func GetScopes(c *gin.Context) []string {
	scopes, exists := c.Get(ContextKeyScopes)
	if !exists {
		return nil
	}
	s, ok := scopes.([]string)
	if !ok {
		return nil
	}
	return s
}
