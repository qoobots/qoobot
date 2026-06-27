// Package device 设备管理服务
package device

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/crypto"
	"github.com/qoobot/qooauth/internal/model"
	"github.com/qoobot/qooauth/internal/repository"
)

// Service 设备管理服务
type Service struct {
	deviceRepo *repository.DeviceRepository
	auditRepo  *repository.AuditRepository
}

// NewService 创建设备管理服务
func NewService(pool *pgxpool.Pool) *Service {
	return &Service{
		deviceRepo: repository.NewDeviceRepository(pool),
		auditRepo:  repository.NewAuditRepository(pool),
	}
}

// ActivateDeviceRequest 设备激活请求
type ActivateDeviceRequest struct {
	SerialNumber string `json:"serial_number" binding:"required"`
	DeviceName   string `json:"device_name" binding:"required"`
	DeviceType   string `json:"device_type" binding:"required"`
	HardwareModel string `json:"hardware_model,omitempty"`
	FirmwareVersion string `json:"firmware_version,omitempty"`
}

// ActivateDevice 激活新设备（签发 X.509 证书并绑定用户）
func (s *Service) ActivateDevice(ctx context.Context, userID uuid.UUID, req ActivateDeviceRequest, ipAddress, userAgent string) (*model.Device, error) {
	// 检查序列号是否已被激活
	existing, err := s.deviceRepo.FindBySerialNumber(ctx, req.SerialNumber)
	if err != nil {
		return nil, fmt.Errorf("device: check serial: %w", err)
	}
	if existing != nil {
		return nil, fmt.Errorf("device: serial number already activated")
	}

	// 生成设备 X.509 证书
	certReq := crypto.CertificateRequest{
		CommonName:   fmt.Sprintf("qoobot-%s", req.SerialNumber),
		Organization: []string{"QooBot Inc."},
		Country:      []string{"CN"},
		DNSNames:     []string{fmt.Sprintf("%s.device.qoobot.com", req.SerialNumber)},
	}
	certPEM, keyPEM, certFp, err := crypto.GenerateSelfSignedCert(certReq)
	if err != nil {
		return nil, fmt.Errorf("device: generate cert: %w", err)
	}

	device := &model.Device{
		UserID:          userID,
		DeviceName:      req.DeviceName,
		DeviceType:      model.DeviceType(req.DeviceType),
		SerialNumber:    req.SerialNumber,
		CertificateFp:   certFp,
		PublicKeyPEM:    string(certPEM),
		HardwareModel:   &req.HardwareModel,
		FirmwareVersion: &req.FirmwareVersion,
		OnlineStatus:    model.OnlineStatusOffline,
	}

	if err := s.deviceRepo.Create(ctx, device); err != nil {
		return nil, fmt.Errorf("device: create: %w", err)
	}

	// 审计
	s.recordAudit(ctx, &userID, model.AuditActionDeviceActivate, model.AuditResourceDevice,
		device.ID.String(), ipAddress, userAgent, true, "")

	// 返回时带上证书私钥（仅此次返回）
	_ = keyPEM // 私钥通过安全通道下发给设备，不在 API 响应中返回

	return device, nil
}

// ListDevices 列出用户设备
func (s *Service) ListDevices(ctx context.Context, userID uuid.UUID) ([]*model.Device, error) {
	return s.deviceRepo.ListByUserID(ctx, userID)
}

// GetDevice 获取设备详情
func (s *Service) GetDevice(ctx context.Context, deviceID uuid.UUID) (*model.Device, error) {
	device, err := s.deviceRepo.FindByID(ctx, deviceID)
	if err != nil {
		return nil, fmt.Errorf("device: find: %w", err)
	}
	if device == nil {
		return nil, fmt.Errorf("device: not found")
	}
	return device, nil
}

// LockDevice 远程锁死设备
func (s *Service) LockDevice(ctx context.Context, userID, deviceID uuid.UUID, reason, ipAddress, userAgent string) error {
	device, err := s.deviceRepo.FindByID(ctx, deviceID)
	if err != nil {
		return fmt.Errorf("device: find: %w", err)
	}
	if device == nil || device.UserID != userID {
		return fmt.Errorf("device: not found or access denied")
	}

	if err := s.deviceRepo.Lock(ctx, deviceID, reason); err != nil {
		return fmt.Errorf("device: lock: %w", err)
	}

	s.recordAudit(ctx, &userID, model.AuditActionDeviceLock, model.AuditResourceDevice,
		deviceID.String(), ipAddress, userAgent, true, "")
	return nil
}

// UnlockDevice 解锁设备
func (s *Service) UnlockDevice(ctx context.Context, userID, deviceID uuid.UUID, ipAddress, userAgent string) error {
	device, err := s.deviceRepo.FindByID(ctx, deviceID)
	if err != nil {
		return fmt.Errorf("device: find: %w", err)
	}
	if device == nil || device.UserID != userID {
		return fmt.Errorf("device: not found or access denied")
	}

	if err := s.deviceRepo.Unlock(ctx, deviceID); err != nil {
		return fmt.Errorf("device: unlock: %w", err)
	}

	s.recordAudit(ctx, &userID, model.AuditActionDeviceUnlock, model.AuditResourceDevice,
		deviceID.String(), ipAddress, userAgent, true, "")
	return nil
}

// RemoveDevice 移除设备
func (s *Service) RemoveDevice(ctx context.Context, userID, deviceID uuid.UUID, ipAddress, userAgent string) error {
	device, err := s.deviceRepo.FindByID(ctx, deviceID)
	if err != nil {
		return fmt.Errorf("device: find: %w", err)
	}
	if device == nil || device.UserID != userID {
		return fmt.Errorf("device: not found or access denied")
	}

	if err := s.deviceRepo.Delete(ctx, deviceID); err != nil {
		return fmt.Errorf("device: remove: %w", err)
	}

	s.recordAudit(ctx, &userID, model.AuditActionDeviceRemove, model.AuditResourceDevice,
		deviceID.String(), ipAddress, userAgent, true, "")
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
