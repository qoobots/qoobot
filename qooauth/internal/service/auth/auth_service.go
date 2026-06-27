// Package auth 认证服务，处理用户注册、登录、登出、Token 刷新等核心认证流程
package auth

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/crypto"
	"github.com/qoobot/qooauth/internal/model"
	"github.com/qoobot/qooauth/internal/repository"
)

// Config 认证服务配置
type Config struct {
	AccessTokenTTL       time.Duration
	RefreshTokenTTL      time.Duration
	MaxFailedAttempts    int
	LockDuration         time.Duration
	PasswordMinLength    int
	RequireUpper         bool
	RequireLower         bool
	RequireDigit         bool
	RequireSpecial       bool
	MaxSessionsPerUser   int
	SessionIdleTimeout   time.Duration
	SessionAbsoluteTimeout time.Duration
}

// DefaultConfig 返回默认配置
func DefaultConfig() Config {
	return Config{
		AccessTokenTTL:        1 * time.Hour,
		RefreshTokenTTL:       30 * 24 * time.Hour,
		MaxFailedAttempts:     5,
		LockDuration:          15 * time.Minute,
		PasswordMinLength:     8,
		RequireUpper:          true,
		RequireLower:          true,
		RequireDigit:          true,
		RequireSpecial:        true,
		MaxSessionsPerUser:    10,
		SessionIdleTimeout:    72 * time.Hour,
		SessionAbsoluteTimeout: 30 * 24 * time.Hour,
	}
}

// Service 认证服务
type Service struct {
	cfg      Config
	jwt      *crypto.JWTManager
	userRepo *repository.UserRepository
	sessRepo *repository.SessionRepository
	auditRepo *repository.AuditRepository
	pool     *pgxpool.Pool
}

// NewService 创建认证服务
func NewService(cfg Config, jwt *crypto.JWTManager, pool *pgxpool.Pool) *Service {
	return &Service{
		cfg:       cfg,
		jwt:       jwt,
		userRepo:  repository.NewUserRepository(pool),
		sessRepo:  repository.NewSessionRepository(pool),
		auditRepo: repository.NewAuditRepository(pool),
		pool:      pool,
	}
}

// RegisterRequest 注册请求
type RegisterRequest struct {
	Email       string `json:"email" binding:"required,email"`
	Password    string `json:"password" binding:"required,min=8"`
	DisplayName string `json:"display_name" binding:"required"`
	Locale      string `json:"locale"`
	Timezone    string `json:"timezone"`
}

// RegisterResponse 注册响应
type RegisterResponse struct {
	UserID        uuid.UUID `json:"user_id"`
	Email         string    `json:"email"`
	EmailVerified bool      `json:"email_verified"`
	CreatedAt     time.Time `json:"created_at"`
}

// Register 用户注册
func (s *Service) Register(ctx context.Context, req RegisterRequest, ipAddress, userAgent string) (*RegisterResponse, error) {
	// 检查邮箱是否已注册
	existing, err := s.userRepo.FindByEmail(ctx, req.Email)
	if err != nil {
		return nil, fmt.Errorf("auth: check existing: %w", err)
	}
	if existing != nil {
		s.recordAudit(ctx, nil, model.AuditActionUserRegister, model.AuditResourceUser,
			"", ipAddress, userAgent, false, "EMAIL_TAKEN")
		return nil, fmt.Errorf("auth: email already registered")
	}

	// 验证密码强度
	if err := s.validatePassword(req.Password); err != nil {
		return nil, err
	}

	// 哈希密码
	passwordHash, err := crypto.HashPassword(req.Password)
	if err != nil {
		return nil, fmt.Errorf("auth: hash password: %w", err)
	}

	locale := req.Locale
	if locale == "" {
		locale = "en-US"
	}
	timezone := req.Timezone
	if timezone == "" {
		timezone = "UTC"
	}

	user := &model.User{
		Email:        req.Email,
		PasswordHash: &passwordHash,
		DisplayName:  req.DisplayName,
		Locale:       locale,
		Timezone:     timezone,
	}

	if err := s.userRepo.Create(ctx, user); err != nil {
		return nil, fmt.Errorf("auth: create user: %w", err)
	}

	s.recordAudit(ctx, &user.ID, model.AuditActionUserRegister, model.AuditResourceUser,
		user.ID.String(), ipAddress, userAgent, true, "")

	return &RegisterResponse{
		UserID:        user.ID,
		Email:         user.Email,
		EmailVerified: false,
		CreatedAt:     user.CreatedAt,
	}, nil
}

// LoginRequest 登录请求
type LoginRequest struct {
	Email    string `json:"email" binding:"required,email"`
	Password string `json:"password" binding:"required"`
}

// LoginResponse 登录响应
type LoginResponse struct {
	AccessToken  string       `json:"access_token"`
	RefreshToken string       `json:"refresh_token"`
	TokenType    string       `json:"token_type"`
	ExpiresIn    int64        `json:"expires_in"`
	User         *UserProfile `json:"user"`
	Requires2FA  bool         `json:"requires_2fa"`
}

// UserProfile 用户简要信息
type UserProfile struct {
	ID          uuid.UUID `json:"id"`
	Email       string    `json:"email"`
	DisplayName string    `json:"display_name"`
	AvatarURL   *string   `json:"avatar_url,omitempty"`
}

// Login 用户登录
func (s *Service) Login(ctx context.Context, req LoginRequest, ipAddress, userAgent string) (*LoginResponse, error) {
	user, err := s.userRepo.FindByEmail(ctx, req.Email)
	if err != nil {
		return nil, fmt.Errorf("auth: find user: %w", err)
	}
	if user == nil {
		s.recordAudit(ctx, nil, model.AuditActionUserLogin, model.AuditResourceUser,
			"", ipAddress, userAgent, false, "USER_NOT_FOUND")
		return nil, fmt.Errorf("auth: invalid credentials")
	}

	// 检查账户状态
	if !user.IsActive() {
		s.recordAudit(ctx, &user.ID, model.AuditActionUserLogin, model.AuditResourceUser,
			user.ID.String(), ipAddress, userAgent, false, "ACCOUNT_LOCKED")
		return nil, fmt.Errorf("auth: account is not active")
	}

	// 检查是否被锁定
	if user.IsLocked() {
		s.recordAudit(ctx, &user.ID, model.AuditActionUserLogin, model.AuditResourceUser,
			user.ID.String(), ipAddress, userAgent, false, "ACCOUNT_LOCKED")
		return nil, fmt.Errorf("auth: account temporarily locked, try again later")
	}

	// 验证密码
	if user.PasswordHash == nil {
		return nil, fmt.Errorf("auth: account uses passwordless login")
	}
	match, err := crypto.VerifyPassword(req.Password, *user.PasswordHash)
	if err != nil {
		return nil, fmt.Errorf("auth: verify password: %w", err)
	}
	if !match {
		_ = s.userRepo.RecordFailedAttempt(ctx, user.ID, s.cfg.MaxFailedAttempts, s.cfg.LockDuration)
		s.recordAudit(ctx, &user.ID, model.AuditActionUserLogin, model.AuditResourceUser,
			user.ID.String(), ipAddress, userAgent, false, "INVALID_CREDENTIALS")
		return nil, fmt.Errorf("auth: invalid credentials")
	}

	// 重置失败计数
	_ = s.userRepo.ResetFailedAttempts(ctx, user.ID)

	// 生成 Token
	scopes := []string{"profile", "email", "device.read"}
	accessToken, expiresAt, err := s.jwt.GenerateAccessToken(user.ID, user.Email, user.EmailVerified, scopes)
	if err != nil {
		return nil, fmt.Errorf("auth: generate access token: %w", err)
	}

	refreshToken, refreshExpires, err := s.jwt.GenerateRefreshToken()
	if err != nil {
		return nil, fmt.Errorf("auth: generate refresh token: %w", err)
	}

	// 创建会话
	tokenHash := crypto.SHA512Hash([]byte(refreshToken))
	session := &model.Session{
		UserID:    user.ID,
		TokenHash: tokenHash,
		DeviceInfo: &model.DeviceInfo{
			UserAgent: userAgent,
			IP:        ipAddress,
		},
		IPAddress: ipAddress,
		IsTrusted: false,
		ExpiresAt: refreshExpires,
	}
	if err := s.sessRepo.Create(ctx, session); err != nil {
		return nil, fmt.Errorf("auth: create session: %w", err)
	}

	s.recordAudit(ctx, &user.ID, model.AuditActionUserLogin, model.AuditResourceUser,
		user.ID.String(), ipAddress, userAgent, true, "")

	return &LoginResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		TokenType:    "Bearer",
		ExpiresIn:    int64(s.cfg.AccessTokenTTL.Seconds()),
		User: &UserProfile{
			ID:          user.ID,
			Email:       user.Email,
			DisplayName: user.DisplayName,
			AvatarURL:   user.AvatarURL,
		},
		Requires2FA: user.TOTPEnabled,
	}, nil
}

// RefreshToken 刷新 Access Token
func (s *Service) RefreshToken(ctx context.Context, refreshTokenStr string) (*LoginResponse, error) {
	tokenHash := crypto.SHA512Hash([]byte(refreshTokenStr))
	session, err := s.sessRepo.FindByTokenHash(ctx, tokenHash)
	if err != nil {
		return nil, fmt.Errorf("auth: find session: %w", err)
	}
	if session == nil || !session.IsValid() {
		return nil, fmt.Errorf("auth: invalid or expired session")
	}

	user, err := s.userRepo.FindByID(ctx, session.UserID)
	if err != nil {
		return nil, fmt.Errorf("auth: find user: %w", err)
	}
	if user == nil || !user.IsActive() {
		return nil, fmt.Errorf("auth: user not found or inactive")
	}

	// 滚动刷新：吊销旧会话
	_ = s.sessRepo.Revoke(ctx, session.ID)

	// 生成新 Token
	scopes := []string{"profile", "email", "device.read"}
	accessToken, _, err := s.jwt.GenerateAccessToken(user.ID, user.Email, user.EmailVerified, scopes)
	if err != nil {
		return nil, fmt.Errorf("auth: generate access token: %w", err)
	}

	newRefreshToken, newRefreshExpires, err := s.jwt.GenerateRefreshToken()
	if err != nil {
		return nil, fmt.Errorf("auth: generate refresh token: %w", err)
	}

	// 创建新会话
	newTokenHash := crypto.SHA512Hash([]byte(newRefreshToken))
	newSession := &model.Session{
		UserID:    user.ID,
		TokenHash: newTokenHash,
		DeviceInfo: session.DeviceInfo,
		IPAddress: session.IPAddress,
		IsTrusted: session.IsTrusted,
		ExpiresAt: newRefreshExpires,
	}
	if err := s.sessRepo.Create(ctx, newSession); err != nil {
		return nil, fmt.Errorf("auth: create session: %w", err)
	}

	return &LoginResponse{
		AccessToken:  accessToken,
		RefreshToken: newRefreshToken,
		TokenType:    "Bearer",
		ExpiresIn:    int64(s.cfg.AccessTokenTTL.Seconds()),
		User: &UserProfile{
			ID:          user.ID,
			Email:       user.Email,
			DisplayName: user.DisplayName,
			AvatarURL:   user.AvatarURL,
		},
	}, nil
}

// Logout 登出
func (s *Service) Logout(ctx context.Context, userID uuid.UUID, sessionID uuid.UUID, ipAddress, userAgent string) error {
	if err := s.sessRepo.Revoke(ctx, sessionID); err != nil {
		return fmt.Errorf("auth: revoke session: %w", err)
	}
	s.recordAudit(ctx, &userID, model.AuditActionUserLogout, model.AuditResourceSession,
		sessionID.String(), ipAddress, userAgent, true, "")
	return nil
}

// RevokeAllSessions 吊销用户所有会话
func (s *Service) RevokeAllSessions(ctx context.Context, userID uuid.UUID) error {
	return s.sessRepo.RevokeAllByUser(ctx, userID)
}

// validatePassword 验证密码强度
func (s *Service) validatePassword(password string) error {
	if len(password) < s.cfg.PasswordMinLength {
		return fmt.Errorf("auth: password must be at least %d characters", s.cfg.PasswordMinLength)
	}

	hasUpper := false
	hasLower := false
	hasDigit := false
	hasSpecial := false
	specialChars := "!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~"

	for _, c := range password {
		switch {
		case c >= 'A' && c <= 'Z':
			hasUpper = true
		case c >= 'a' && c <= 'z':
			hasLower = true
		case c >= '0' && c <= '9':
			hasDigit = true
		default:
			for _, sc := range specialChars {
				if c == sc {
					hasSpecial = true
					break
				}
			}
		}
	}

	if s.cfg.RequireUpper && !hasUpper {
		return fmt.Errorf("auth: password must contain at least one uppercase letter")
	}
	if s.cfg.RequireLower && !hasLower {
		return fmt.Errorf("auth: password must contain at least one lowercase letter")
	}
	if s.cfg.RequireDigit && !hasDigit {
		return fmt.Errorf("auth: password must contain at least one digit")
	}
	if s.cfg.RequireSpecial && !hasSpecial {
		return fmt.Errorf("auth: password must contain at least one special character")
	}

	return nil
}

// recordAudit 记录审计日志
func (s *Service) recordAudit(ctx context.Context, userID *uuid.UUID, action model.AuditAction,
	resourceType model.AuditResourceType, resourceID, ipAddress, userAgent string, success bool, errorCode string) {
	log := &model.AuditLog{
		UserID:       userID,
		Action:       action,
		ResourceType: resourceType,
		ResourceID:   &resourceID,
		IPAddress:    ipAddress,
		UserAgent:    &userAgent,
		Success:      success,
		ErrorCode:    &errorCode,
	}
	if errorCode == "" {
		log.ErrorCode = nil
	}
	_ = s.auditRepo.Record(ctx, log)
}
