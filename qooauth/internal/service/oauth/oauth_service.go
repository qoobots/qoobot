// Package oauth OAuth 2.0 / OIDC Provider 服务
package oauth

import (
	"context"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/crypto"
	"github.com/qoobot/qooauth/internal/repository"
)

// Config OAuth 服务配置
type Config struct {
	AuthorizationCodeTTL time.Duration
	AccessTokenTTL       time.Duration
	RefreshTokenTTL      time.Duration
	Issuer               string
}

// DefaultConfig 默认 OAuth 配置
func DefaultConfig(issuer string) Config {
	return Config{
		AuthorizationCodeTTL: 10 * time.Minute,
		AccessTokenTTL:       1 * time.Hour,
		RefreshTokenTTL:      30 * 24 * time.Hour,
		Issuer:               issuer,
	}
}

// Service OAuth 2.0 Provider 服务
type Service struct {
	cfg       Config
	jwt       *crypto.JWTManager
	userRepo  *repository.UserRepository
	// authorizationCodes 存储授权码 (内存中，生产环境用 Redis)
	authCodes map[string]*AuthCodeEntry
}

// AuthCodeEntry 授权码条目
type AuthCodeEntry struct {
	Code        string
	ClientID    string
	RedirectURI string
	UserID      uuid.UUID
	Scopes      []string
	ExpiresAt   time.Time
}

// NewService 创建 OAuth 服务
func NewService(cfg Config, jwt *crypto.JWTManager, pool *pgxpool.Pool) *Service {
	return &Service{
		cfg:       cfg,
		jwt:       jwt,
		userRepo:  repository.NewUserRepository(pool),
		authCodes: make(map[string]*AuthCodeEntry),
	}
}

// GenerateAuthorizationCode 生成授权码
func (s *Service) GenerateAuthorizationCode(userID uuid.UUID, clientID, redirectURI string, scopes []string) (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", fmt.Errorf("oauth: generate code: %w", err)
	}
	code := base64.RawURLEncoding.EncodeToString(b)

	s.authCodes[code] = &AuthCodeEntry{
		Code:        code,
		ClientID:    clientID,
		RedirectURI: redirectURI,
		UserID:      userID,
		Scopes:      scopes,
		ExpiresAt:   time.Now().Add(s.cfg.AuthorizationCodeTTL),
	}

	return code, nil
}

// ExchangeTokenRequest Token 交换请求
type ExchangeTokenRequest struct {
	GrantType    string `json:"grant_type"`
	Code         string `json:"code,omitempty"`
	RedirectURI  string `json:"redirect_uri,omitempty"`
	ClientID     string `json:"client_id"`
	ClientSecret string `json:"client_secret,omitempty"`
	RefreshToken string `json:"refresh_token,omitempty"`
}

// TokenResponse Token 响应
type TokenResponse struct {
	AccessToken  string `json:"access_token"`
	TokenType    string `json:"token_type"`
	ExpiresIn    int64  `json:"expires_in"`
	RefreshToken string `json:"refresh_token,omitempty"`
	IDToken      string `json:"id_token,omitempty"`
	Scope        string `json:"scope,omitempty"`
}

// ExchangeToken 用授权码换取 Token
func (s *Service) ExchangeToken(ctx context.Context, req ExchangeTokenRequest) (*TokenResponse, error) {
	switch req.GrantType {
	case "authorization_code":
		return s.handleAuthorizationCode(ctx, req)
	case "refresh_token":
		return s.handleRefreshToken(ctx, req)
	default:
		return nil, fmt.Errorf("oauth: unsupported grant_type: %s", req.GrantType)
	}
}

func (s *Service) handleAuthorizationCode(ctx context.Context, req ExchangeTokenRequest) (*TokenResponse, error) {
	entry, ok := s.authCodes[req.Code]
	if !ok {
		return nil, fmt.Errorf("oauth: invalid authorization code")
	}
	if time.Now().After(entry.ExpiresAt) {
		delete(s.authCodes, req.Code)
		return nil, fmt.Errorf("oauth: authorization code expired")
	}
	if entry.ClientID != req.ClientID {
		return nil, fmt.Errorf("oauth: client_id mismatch")
	}

	delete(s.authCodes, req.Code)

	user, err := s.userRepo.FindByID(ctx, entry.UserID)
	if err != nil || user == nil {
		return nil, fmt.Errorf("oauth: user not found")
	}

	accessToken, _, err := s.jwt.GenerateAccessToken(user.ID, user.Email, user.EmailVerified, entry.Scopes)
	if err != nil {
		return nil, fmt.Errorf("oauth: generate access token: %w", err)
	}

	refreshToken, _, err := s.jwt.GenerateRefreshToken()
	if err != nil {
		return nil, fmt.Errorf("oauth: generate refresh token: %w", err)
	}

	return &TokenResponse{
		AccessToken:  accessToken,
		TokenType:    "Bearer",
		ExpiresIn:    int64(s.cfg.AccessTokenTTL.Seconds()),
		RefreshToken: refreshToken,
	}, nil
}

func (s *Service) handleRefreshToken(_ context.Context, _ ExchangeTokenRequest) (*TokenResponse, error) {
	// Refresh token 刷新逻辑（简化实现）
	return nil, fmt.Errorf("oauth: refresh_token not yet implemented")
}
