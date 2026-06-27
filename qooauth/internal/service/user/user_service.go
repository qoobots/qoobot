// Package user 用户服务，处理用户资料管理、账户恢复等
package user

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/model"
	"github.com/qoobot/qooauth/internal/repository"
)

// Service 用户服务
type Service struct {
	userRepo  *repository.UserRepository
	auditRepo *repository.AuditRepository
}

// NewService 创建用户服务
func NewService(pool *pgxpool.Pool) *Service {
	return &Service{
		userRepo:  repository.NewUserRepository(pool),
		auditRepo: repository.NewAuditRepository(pool),
	}
}

// GetProfile 获取用户资料
func (s *Service) GetProfile(ctx context.Context, userID uuid.UUID) (*model.User, error) {
	user, err := s.userRepo.FindByID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("user: get profile: %w", err)
	}
	if user == nil {
		return nil, fmt.Errorf("user: not found")
	}
	return user, nil
}

// UpdateProfileRequest 更新资料请求
type UpdateProfileRequest struct {
	DisplayName *string `json:"display_name,omitempty"`
	AvatarURL   *string `json:"avatar_url,omitempty"`
	Locale      *string `json:"locale,omitempty"`
	Timezone    *string `json:"timezone,omitempty"`
}

// UpdateProfile 更新用户资料
func (s *Service) UpdateProfile(ctx context.Context, userID uuid.UUID, req UpdateProfileRequest) (*model.User, error) {
	user, err := s.userRepo.FindByID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("user: find: %w", err)
	}
	if user == nil {
		return nil, fmt.Errorf("user: not found")
	}

	if req.DisplayName != nil {
		user.DisplayName = *req.DisplayName
	}
	if req.AvatarURL != nil {
		user.AvatarURL = req.AvatarURL
	}
	if req.Locale != nil {
		user.Locale = *req.Locale
	}
	if req.Timezone != nil {
		user.Timezone = *req.Timezone
	}

	if err := s.userRepo.Update(ctx, user); err != nil {
		return nil, fmt.Errorf("user: update: %w", err)
	}
	return user, nil
}

// DeleteAccount 注销账户
func (s *Service) DeleteAccount(ctx context.Context, userID uuid.UUID, ipAddress, userAgent string) error {
	user, err := s.userRepo.FindByID(ctx, userID)
	if err != nil {
		return fmt.Errorf("user: find: %w", err)
	}
	if user == nil {
		return fmt.Errorf("user: not found")
	}

	if err := s.userRepo.SoftDelete(ctx, userID); err != nil {
		return fmt.Errorf("user: soft delete: %w", err)
	}

	// 审计
	s.recordAudit(ctx, &userID, model.AuditActionUserDelete, model.AuditResourceUser,
		userID.String(), ipAddress, userAgent, true, "")
	return nil
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
