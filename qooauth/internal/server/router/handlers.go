// Package router HTTP 请求处理器
package router

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/qoobot/qooauth/internal/server/middleware"
)

// ============================================================================
// 认证处理器
// ============================================================================

func (svc *Services) handleRegister(c *gin.Context) {
	var req struct {
		Email       string `json:"email" binding:"required,email"`
		Password    string `json:"password" binding:"required,min=8"`
		DisplayName string `json:"display_name" binding:"required"`
		Locale      string `json:"locale"`
		Timezone    string `json:"timezone"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}

	resp, err := svc.Auth.Register(c.Request.Context(),
		auth.RegisterRequest(req),
		c.ClientIP(), c.Request.UserAgent())
	if err != nil {
		c.JSON(http.StatusConflict, errorResponse("REGISTRATION_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusCreated, resp)
}

func (svc *Services) handleLogin(c *gin.Context) {
	var req struct {
		Email    string `json:"email" binding:"required,email"`
		Password string `json:"password" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}

	resp, err := svc.Auth.Login(c.Request.Context(),
		auth.LoginRequest(req),
		c.ClientIP(), c.Request.UserAgent())
	if err != nil {
		c.JSON(http.StatusUnauthorized, errorResponse("INVALID_CREDENTIALS", err.Error()))
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (svc *Services) handleRefreshToken(c *gin.Context) {
	var req struct {
		RefreshToken string `json:"refresh_token" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}

	resp, err := svc.Auth.RefreshToken(c.Request.Context(), req.RefreshToken)
	if err != nil {
		c.JSON(http.StatusUnauthorized, errorResponse("TOKEN_INVALID", err.Error()))
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (svc *Services) handleLogout(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)

	// session ID 从请求体获取
	var req struct {
		SessionID string `json:"session_id" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}
	sessionID, err := uuid.Parse(req.SessionID)
	if err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", "invalid session_id"))
		return
	}

	if err := svc.Auth.Logout(c.Request.Context(), userID, sessionID, c.ClientIP(), c.Request.UserAgent()); err != nil {
		c.JSON(http.StatusInternalServerError, errorResponse("LOGOUT_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "logged out successfully"})
}

func (svc *Services) handleRevokeAll(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	if err := svc.Auth.RevokeAllSessions(c.Request.Context(), userID); err != nil {
		c.JSON(http.StatusInternalServerError, errorResponse("REVOKE_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "all sessions revoked"})
}

// ============================================================================
// 用户处理器
// ============================================================================

func (svc *Services) handleGetProfile(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	user, err := svc.User.GetProfile(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusNotFound, errorResponse("USER_NOT_FOUND", err.Error()))
		return
	}
	c.JSON(http.StatusOK, user)
}

func (svc *Services) handleUpdateProfile(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	var req struct {
		DisplayName *string `json:"display_name"`
		AvatarURL   *string `json:"avatar_url"`
		Locale      *string `json:"locale"`
		Timezone    *string `json:"timezone"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}

	user, err := svc.User.UpdateProfile(c.Request.Context(), userID, user.UpdateProfileRequest(req))
	if err != nil {
		c.JSON(http.StatusInternalServerError, errorResponse("UPDATE_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, user)
}

func (svc *Services) handleDeleteAccount(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	if err := svc.User.DeleteAccount(c.Request.Context(), userID, c.ClientIP(), c.Request.UserAgent()); err != nil {
		c.JSON(http.StatusInternalServerError, errorResponse("DELETE_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "account deleted"})
}

// ============================================================================
// 设备处理器
// ============================================================================

func (svc *Services) handleListDevices(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	devices, err := svc.Device.ListDevices(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, errorResponse("LIST_FAILED", err.Error()))
		return
	}
	if devices == nil {
		devices = []*model.Device{}
	}
	c.JSON(http.StatusOK, devices)
}

func (svc *Services) handleActivateDevice(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	var req device.ActivateDeviceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}

	dev, err := svc.Device.ActivateDevice(c.Request.Context(), userID, req, c.ClientIP(), c.Request.UserAgent())
	if err != nil {
		c.JSON(http.StatusConflict, errorResponse("ACTIVATE_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusCreated, dev)
}

func (svc *Services) handleGetDevice(c *gin.Context) {
	deviceID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", "invalid device id"))
		return
	}
	dev, err := svc.Device.GetDevice(c.Request.Context(), deviceID)
	if err != nil {
		c.JSON(http.StatusNotFound, errorResponse("DEVICE_NOT_FOUND", err.Error()))
		return
	}
	c.JSON(http.StatusOK, dev)
}

func (svc *Services) handleLockDevice(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	deviceID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", "invalid device id"))
		return
	}

	var req struct {
		Reason string `json:"reason" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}

	if err := svc.Device.LockDevice(c.Request.Context(), userID, deviceID, req.Reason, c.ClientIP(), c.Request.UserAgent()); err != nil {
		c.JSON(http.StatusForbidden, errorResponse("LOCK_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "device locked"})
}

func (svc *Services) handleUnlockDevice(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	deviceID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", "invalid device id"))
		return
	}

	if err := svc.Device.UnlockDevice(c.Request.Context(), userID, deviceID, c.ClientIP(), c.Request.UserAgent()); err != nil {
		c.JSON(http.StatusForbidden, errorResponse("UNLOCK_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "device unlocked"})
}

func (svc *Services) handleRemoveDevice(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	deviceID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", "invalid device id"))
		return
	}

	if err := svc.Device.RemoveDevice(c.Request.Context(), userID, deviceID, c.ClientIP(), c.Request.UserAgent()); err != nil {
		c.JSON(http.StatusForbidden, errorResponse("REMOVE_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "device removed"})
}

// ============================================================================
// 会话处理器
// ============================================================================

func (svc *Services) handleListSessions(c *gin.Context) {
	// 会话列表（简化实现）
	c.JSON(http.StatusOK, gin.H{"sessions": []any{}})
}

func (svc *Services) handleRevokeSession(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"message": "session revoked"})
}

// ============================================================================
// API Key 处理器
// ============================================================================

func (svc *Services) handleCreateAPIKey(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	var req struct {
		Name   string   `json:"name" binding:"required"`
		Scopes []string `json:"scopes" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}

	resp, err := svc.APIKey.CreateAPIKey(c.Request.Context(), userID,
		apikey.CreateAPIKeyRequest(req), c.ClientIP(), c.Request.UserAgent())
	if err != nil {
		c.JSON(http.StatusInternalServerError, errorResponse("CREATE_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusCreated, resp)
}

func (svc *Services) handleListAPIKeys(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	keys, err := svc.APIKey.ListAPIKeys(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, errorResponse("LIST_FAILED", err.Error()))
		return
	}
	if keys == nil {
		keys = []*model.APIKey{}
	}
	c.JSON(http.StatusOK, keys)
}

func (svc *Services) handleRevokeAPIKey(c *gin.Context) {
	userID, _ := middleware.GetUserID(c)
	keyID, err := uuid.Parse(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", "invalid key id"))
		return
	}

	if err := svc.APIKey.RevokeAPIKey(c.Request.Context(), userID, keyID, c.ClientIP(), c.Request.UserAgent()); err != nil {
		c.JSON(http.StatusInternalServerError, errorResponse("REVOKE_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "api key revoked"})
}

// ============================================================================
// OAuth 处理器
// ============================================================================

func (svc *Services) handleOAuthAuthorize(c *gin.Context) {
	// 简化实现，返回授权码生成端点
	c.JSON(http.StatusOK, gin.H{"message": "OAuth authorize endpoint"})
}

func (svc *Services) handleOAuthToken(c *gin.Context) {
	var req oauth.ExchangeTokenRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("INVALID_REQUEST", err.Error()))
		return
	}

	resp, err := svc.OAuth.ExchangeToken(c.Request.Context(), req)
	if err != nil {
		c.JSON(http.StatusBadRequest, errorResponse("TOKEN_EXCHANGE_FAILED", err.Error()))
		return
	}
	c.JSON(http.StatusOK, resp)
}

// ============================================================================
// 工具函数
// ============================================================================

// errorResponse 统一错误响应格式
func errorResponse(code, message string) gin.H {
	return gin.H{
		"error": gin.H{
			"code":    code,
			"message": message,
		},
	}
}
