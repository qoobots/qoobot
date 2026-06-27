// Package repository 设备数据访问层
package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/model"
)

// DeviceRepository 设备数据访问接口
type DeviceRepository struct {
	pool *pgxpool.Pool
}

// NewDeviceRepository 创建设备数据访问实例
func NewDeviceRepository(pool *pgxpool.Pool) *DeviceRepository {
	return &DeviceRepository{pool: pool}
}

// Create 注册新设备
func (r *DeviceRepository) Create(ctx context.Context, device *model.Device) error {
	query := `
		INSERT INTO devices (id, user_id, device_name, device_type, serial_number,
		                     certificate_fp, public_key_pem, hardware_model, firmware_version)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
		RETURNING created_at, updated_at`

	if device.ID == uuid.Nil {
		device.ID = uuid.New()
	}

	err := r.pool.QueryRow(ctx, query,
		device.ID, device.UserID, device.DeviceName, string(device.DeviceType),
		device.SerialNumber, device.CertificateFp, device.PublicKeyPEM,
		device.HardwareModel, device.FirmwareVersion,
	).Scan(&device.CreatedAt, &device.UpdatedAt)

	if err != nil {
		return fmt.Errorf("device_repo: create: %w", err)
	}
	return nil
}

// FindByID 按 ID 查询设备
func (r *DeviceRepository) FindByID(ctx context.Context, id uuid.UUID) (*model.Device, error) {
	query := `
		SELECT id, user_id, device_name, device_type, serial_number,
		       certificate_fp, public_key_pem, firmware_version, hardware_model,
		       online_status, last_seen_at, last_location,
		       activation_locked, lock_reason, created_at, updated_at
		FROM devices WHERE id = $1`

	return r.scanDevice(r.pool.QueryRow(ctx, query, id))
}

// FindBySerialNumber 按序列号查询设备
func (r *DeviceRepository) FindBySerialNumber(ctx context.Context, serial string) (*model.Device, error) {
	query := `
		SELECT id, user_id, device_name, device_type, serial_number,
		       certificate_fp, public_key_pem, firmware_version, hardware_model,
		       online_status, last_seen_at, last_location,
		       activation_locked, lock_reason, created_at, updated_at
		FROM devices WHERE serial_number = $1`

	return r.scanDevice(r.pool.QueryRow(ctx, query, serial))
}

// FindByCertificateFP 按证书指纹查询设备
func (r *DeviceRepository) FindByCertificateFP(ctx context.Context, fp string) (*model.Device, error) {
	query := `
		SELECT id, user_id, device_name, device_type, serial_number,
		       certificate_fp, public_key_pem, firmware_version, hardware_model,
		       online_status, last_seen_at, last_location,
		       activation_locked, lock_reason, created_at, updated_at
		FROM devices WHERE certificate_fp = $1`

	return r.scanDevice(r.pool.QueryRow(ctx, query, fp))
}

// ListByUserID 列出用户的所有设备
func (r *DeviceRepository) ListByUserID(ctx context.Context, userID uuid.UUID) ([]*model.Device, error) {
	query := `
		SELECT id, user_id, device_name, device_type, serial_number,
		       certificate_fp, public_key_pem, firmware_version, hardware_model,
		       online_status, last_seen_at, last_location,
		       activation_locked, lock_reason, created_at, updated_at
		FROM devices WHERE user_id = $1 ORDER BY created_at DESC`

	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, fmt.Errorf("device_repo: list by user: %w", err)
	}
	defer rows.Close()

	var devices []*model.Device
	for rows.Next() {
		d, err := r.scanDeviceFromRows(rows)
		if err != nil {
			return nil, err
		}
		devices = append(devices, d)
	}
	return devices, rows.Err()
}

// UpdateOnlineStatus 更新设备在线状态
func (r *DeviceRepository) UpdateOnlineStatus(ctx context.Context, id uuid.UUID, status model.OnlineStatus) error {
	query := `UPDATE devices SET online_status = $2, last_seen_at = $3 WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, string(status), time.Now())
	if err != nil {
		return fmt.Errorf("device_repo: update online status: %w", err)
	}
	return nil
}

// Lock 远程锁死设备
func (r *DeviceRepository) Lock(ctx context.Context, id uuid.UUID, reason string) error {
	query := `UPDATE devices SET activation_locked = TRUE, lock_reason = $2 WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, reason)
	if err != nil {
		return fmt.Errorf("device_repo: lock: %w", err)
	}
	return nil
}

// Unlock 解锁设备
func (r *DeviceRepository) Unlock(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE devices SET activation_locked = FALSE, lock_reason = NULL WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	if err != nil {
		return fmt.Errorf("device_repo: unlock: %w", err)
	}
	return nil
}

// Delete 移除设备
func (r *DeviceRepository) Delete(ctx context.Context, id uuid.UUID) error {
	_, err := r.pool.Exec(ctx, `DELETE FROM devices WHERE id = $1`, id)
	if err != nil {
		return fmt.Errorf("device_repo: delete: %w", err)
	}
	return nil
}

func (r *DeviceRepository) scanDevice(row pgx.Row) (*model.Device, error) {
	device := &model.Device{}
	var onlineStatus, deviceType string
	err := row.Scan(
		&device.ID, &device.UserID, &device.DeviceName, &deviceType, &device.SerialNumber,
		&device.CertificateFp, &device.PublicKeyPEM, &device.FirmwareVersion, &device.HardwareModel,
		&onlineStatus, &device.LastSeenAt, &device.LastLocation,
		&device.ActivationLocked, &device.LockReason, &device.CreatedAt, &device.UpdatedAt,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("device_repo: scan: %w", err)
	}
	device.OnlineStatus = model.OnlineStatus(onlineStatus)
	device.DeviceType = model.DeviceType(deviceType)
	return device, nil
}

func (r *DeviceRepository) scanDeviceFromRows(rows pgx.Rows) (*model.Device, error) {
	device := &model.Device{}
	var onlineStatus, deviceType string
	err := rows.Scan(
		&device.ID, &device.UserID, &device.DeviceName, &deviceType, &device.SerialNumber,
		&device.CertificateFp, &device.PublicKeyPEM, &device.FirmwareVersion, &device.HardwareModel,
		&onlineStatus, &device.LastSeenAt, &device.LastLocation,
		&device.ActivationLocked, &device.LockReason, &device.CreatedAt, &device.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("device_repo: scan rows: %w", err)
	}
	device.OnlineStatus = model.OnlineStatus(onlineStatus)
	device.DeviceType = model.DeviceType(deviceType)
	return device, nil
}
