// Package apikey API 密钥管理服务
package apikey

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/crypto"
	"github.com/qoobot/qooauth/internal/model"
	"github.com/qoobot/qooauth/internal/repository"
)

// Service API Key 管理服务
type Service struct {
	keyRepo   *repository.APIKeyRepository
	auditRepo *repository.AuditRepository
}

// NewService 创建 API Key 管理服务
func NewService(pool *pgxpool.Pool) *Service {
	return &Service{
		keyRepo:   repository.NewAPIKeyRepository(pool),
		auditRepo: repository.NewAuditRepository(pool),
	}
}

// CreateAPIKeyRequest 创建 API Key 请求
type CreateAPIKeyRequest struct {
	Name   string   `json:"name" binding:"required"`
	Scopes []string `json:"scopes" binding:"required"`
}

// CreateAPIKeyResponse 创建 API Key 响应（仅在创建时返回完整 Key）
type CreateAPIKeyResponse struct {
	APIKey    string    `json:"api_key"`     // 完整 Key，仅此一次返回
	KeyPrefix string    `json:"key_prefix"`  // 用于 UI 显示
	ID        uuid.UUID `json:"id"`
	CreatedAt string    `json:"created_at"`
}

// CreateAPIKey 创建 API Key
func (s *Service) CreateAPIKey(ctx context.Context, userID uuid.UUID, req CreateAPIKeyRequest, ipAddress, userAgent string) (*CreateAPIKeyResponse, error) {
	// 生成 API Key
	apiKeyStr, err := crypto.GenerateToken("qoo_sk_", 32)
	if err != nil {
		return nil, fmt.Errorf("apikey: generate: %w", err)
	}

	keyHash := crypto.SHA512Hash([]byte(apiKeyStr))
	keyPrefix := apiKeyStr[:16] // "qoo_sk_" + 前 8 字符

	apiKey := &model.APIKey{
		UserID:    userID,
		KeyPrefix: keyPrefix,
		KeyHash:   keyHash,
		KeyName:   req.Name,
		Scopes:    req.Scopes,
	}

	if err := s.keyRepo.Create(ctx, apiKey); err != nil {
		return nil, fmt.Errorf("apikey: create: %w", err)
	}

	// 审计
	s.recordAudit(ctx, &userID, model.AuditActionAPIKeyCreate, model.AuditResourceAPIKey,
		apiKey.ID.String(), ipAddress, userAgent, true, "")

	return &CreateAPIKeyResponse{
		APIKey:    apiKeyStr,
		KeyPrefix: keyPrefix,
		ID:        apiKey.ID,
		CreatedAt: apiKey.CreatedAt.Format("2006-01-02T15:04:05Z"),
	}, nil
}

// ListAPIKeys 列出用户的 API Keys
func (s *Service) ListAPIKeys(ctx context.Context, userID uuid.UUID) ([]*model.APIKey, error) {
	return s.keyRepo.ListByUserID(ctx, userID)
}

// RevokeAPIKey 吊销 API Key
func (s *Service) RevokeAPIKey(ctx context.Context, userID, keyID uuid.UUID, ipAddress, userAgent string) error {
	if err := s.keyRepo.Revoke(ctx, keyID); err != nil {
		return fmt.Errorf("apikey: revoke: %w", err)
	}

	s.recordAudit(ctx, &userID, model.AuditActionAPIKeyRevoke, model.AuditResourceAPIKey,
		keyID.String(), ipAddress, userAgent, true, "")
	return nil
}

// ValidateAPIKey 验证 API Key 并返回用户 ID 和 Scopes
func (s *Service) ValidateAPIKey(ctx context.Context, apiKeyStr string) (uuid.UUID, []string, error) {
	keyHash := crypto.SHA512Hash([]byte(apiKeyStr))
	key, err := s.keyRepo.FindByKeyHash(ctx, keyHash)
	if err != nil {
		return uuid.Nil, nil, fmt.Errorf("apikey: find: %w", err)
	}
	if key == nil || !key.IsValid() {
		return uuid.Nil, nil, fmt.Errorf("apikey: invalid or revoked")
	}

	_ = s.keyRepo.UpdateLastUsed(ctx, key.ID)
	return key.UserID, key.Scopes, nil
}

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
