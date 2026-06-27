// Package errors 定义 qooauth 错误码体系
package errors

import "fmt"

// Code 错误码
type Code string

const (
	// 认证相关
	CodeInvalidRequest        Code = "INVALID_REQUEST"
	CodeInvalidCredentials    Code = "INVALID_CREDENTIALS"
	CodeTokenExpired          Code = "TOKEN_EXPIRED"
	CodeTokenInvalid          Code = "TOKEN_INVALID"
	CodeTokenMissing          Code = "TOKEN_MISSING"
	CodeInsufficientPermissions Code = "INSUFFICIENT_PERMISSIONS"
	CodeAccountLocked         Code = "ACCOUNT_LOCKED"
	CodeAccountSuspended      Code = "ACCOUNT_SUSPENDED"
	CodeDeviceBanned          Code = "DEVICE_BANNED"

	// 用户相关
	CodeUserNotFound Code = "USER_NOT_FOUND"
	CodeEmailTaken   Code = "EMAIL_TAKEN"

	// 设备相关
	CodeDeviceNotFound    Code = "DEVICE_NOT_FOUND"
	CodeDeviceLocked      Code = "DEVICE_LOCKED"
	CodeSerialTaken       Code = "SERIAL_TAKEN"
	CodeActivationLocked  Code = "ACTIVATION_LOCKED"

	// 会话相关
	CodeSessionExpired Code = "SESSION_EXPIRED"
	CodeSessionRevoked Code = "SESSION_REVOKED"

	// API Key 相关
	CodeAPIKeyInvalid  Code = "API_KEY_INVALID"
	CodeAPIKeyRevoked  Code = "API_KEY_REVOKED"
	CodeAPIKeyMissing  Code = "API_KEY_MISSING"

	// 速率限制
	CodeRateLimited Code = "RATE_LIMITED"

	// OAuth
	CodeOAuthInvalidGrant Code = "OAUTH_INVALID_GRANT"

	// 系统
	CodeInternalError Code = "INTERNAL_ERROR"
)

// APIError API 错误
type APIError struct {
	Code    Code   `json:"code"`
	Message string `json:"message"`
	Details any    `json:"details,omitempty"`
}

// Error 实现 error 接口
func (e *APIError) Error() string {
	return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

// New 创建 API 错误
func New(code Code, message string) *APIError {
	return &APIError{Code: code, Message: message}
}

// Newf 创建带格式化的 API 错误
func Newf(code Code, format string, args ...any) *APIError {
	return &APIError{Code: code, Message: fmt.Sprintf(format, args...)}
}

// WithDetails 附加详细信息
func (e *APIError) WithDetails(details any) *APIError {
	e.Details = details
	return e
}
