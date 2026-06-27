// Package model 定义 qooauth 领域模型，与数据库表结构一一对应。
// 遵循 DDD 设计原则，模型层不依赖任何外部库。
package model

import (
	"time"

	"github.com/google/uuid"
)

// AccountStatus 账户状态枚举
type AccountStatus string

const (
	AccountStatusActive    AccountStatus = "active"
	AccountStatusLocked    AccountStatus = "locked"
	AccountStatusSuspended AccountStatus = "suspended"
	AccountStatusDeleted   AccountStatus = "deleted"
)

// User 用户主模型，对应 users 表
type User struct {
	ID             uuid.UUID     `json:"id" db:"id"`
	Email          string        `json:"email" db:"email"`
	EmailVerified  bool          `json:"email_verified" db:"email_verified"`
	Phone          *string       `json:"phone,omitempty" db:"phone"`
	PhoneVerified  bool          `json:"phone_verified" db:"phone_verified"`
	PasswordHash   *string       `json:"-" db:"password_hash"` // 永不序列化到 JSON
	DisplayName    string        `json:"display_name" db:"display_name"`
	AvatarURL      *string       `json:"avatar_url,omitempty" db:"avatar_url"`
	Locale         string        `json:"locale" db:"locale"`
	Timezone       string        `json:"timezone" db:"timezone"`
	TOTPEnabled    bool          `json:"totp_enabled" db:"totp_enabled"`
	TOTPSecret     *string       `json:"-" db:"totp_secret"` // AES-256-GCM 加密存储
	PasskeyEnabled bool          `json:"passkey_enabled" db:"passkey_enabled"`
	AccountStatus  AccountStatus `json:"account_status" db:"account_status"`
	LockedUntil    *time.Time    `json:"locked_until,omitempty" db:"locked_until"`
	FailedAttempts int           `json:"-" db:"failed_attempts"`
	CreatedAt      time.Time     `json:"created_at" db:"created_at"`
	UpdatedAt      time.Time     `json:"updated_at" db:"updated_at"`
	DeletedAt      *time.Time    `json:"deleted_at,omitempty" db:"deleted_at"`
}

// IsActive 检查账户是否处于活跃状态
func (u *User) IsActive() bool {
	return u.AccountStatus == AccountStatusActive && u.DeletedAt == nil
}

// IsLocked 检查账户是否被锁定
func (u *User) IsLocked() bool {
	if u.LockedUntil == nil {
		return false
	}
	return time.Now().Before(*u.LockedUntil)
}

// DeviceType 设备类型枚举
type DeviceType string

const (
	DeviceTypeHomeRobot    DeviceType = "home_robot"
	DeviceTypeFactoryRobot DeviceType = "factory_robot"
	DeviceTypeAccessory    DeviceType = "accessory"
)

// OnlineStatus 在线状态
type OnlineStatus string

const (
	OnlineStatusOnline  OnlineStatus = "online"
	OnlineStatusOffline OnlineStatus = "offline"
	OnlineStatusBusy    OnlineStatus = "busy"
)

// Location 地理位置
type Location struct {
	Lat     float64 `json:"lat"`
	Lng     float64 `json:"lng"`
	Address string  `json:"address,omitempty"`
}

// Device 设备模型，对应 devices 表
type Device struct {
	ID               uuid.UUID    `json:"id" db:"id"`
	UserID           uuid.UUID    `json:"user_id" db:"user_id"`
	DeviceName       string       `json:"device_name" db:"device_name"`
	DeviceType       DeviceType   `json:"device_type" db:"device_type"`
	SerialNumber     string       `json:"serial_number" db:"serial_number"`
	CertificateFp    string       `json:"certificate_fp" db:"certificate_fp"` // X.509 SHA-256 指纹
	PublicKeyPEM     string       `json:"-" db:"public_key_pem"`              // 不暴露公钥
	FirmwareVersion  *string      `json:"firmware_version,omitempty" db:"firmware_version"`
	HardwareModel    *string      `json:"hardware_model,omitempty" db:"hardware_model"`
	OnlineStatus     OnlineStatus `json:"online_status" db:"online_status"`
	LastSeenAt       *time.Time   `json:"last_seen_at,omitempty" db:"last_seen_at"`
	LastLocation     *Location    `json:"last_location,omitempty" db:"last_location"`
	ActivationLocked bool         `json:"activation_locked" db:"activation_locked"`
	LockReason       *string      `json:"lock_reason,omitempty" db:"lock_reason"`
	CreatedAt        time.Time    `json:"created_at" db:"created_at"`
	UpdatedAt        time.Time    `json:"updated_at" db:"updated_at"`
}

// IsOnline 检查设备是否在线
func (d *Device) IsOnline() bool {
	return d.OnlineStatus == OnlineStatusOnline
}

// DeviceInfo 设备指纹信息（用于会话记录）
type DeviceInfo struct {
	UserAgent   string `json:"user_agent,omitempty"`
	IP          string `json:"ip,omitempty"`
	OS          string `json:"os,omitempty"`
	Fingerprint string `json:"fingerprint,omitempty"`
}

// SessionLocation 会话地理位置
type SessionLocation struct {
	Country string  `json:"country,omitempty"`
	City    string  `json:"city,omitempty"`
	Lat     float64 `json:"lat,omitempty"`
	Lng     float64 `json:"lng,omitempty"`
}

// Session 会话模型，对应 sessions 表
type Session struct {
	ID         uuid.UUID        `json:"id" db:"id"`
	UserID     uuid.UUID        `json:"user_id" db:"user_id"`
	TokenHash  string           `json:"-" db:"token_hash"` // SHA-512(JWT refresh_token)
	DeviceInfo *DeviceInfo      `json:"device_info,omitempty" db:"device_info"`
	IPAddress  string           `json:"ip_address" db:"ip_address"`
	Location   *SessionLocation `json:"location,omitempty" db:"location"`
	IsTrusted  bool             `json:"is_trusted" db:"is_trusted"`
	CreatedAt  time.Time        `json:"created_at" db:"created_at"`
	ExpiresAt  time.Time        `json:"expires_at" db:"expires_at"`
	RevokedAt  *time.Time       `json:"revoked_at,omitempty" db:"revoked_at"`
}

// IsExpired 检查会话是否过期
func (s *Session) IsExpired() bool {
	return time.Now().After(s.ExpiresAt)
}

// IsRevoked 检查会话是否已吊销
func (s *Session) IsRevoked() bool {
	return s.RevokedAt != nil
}

// IsValid 检查会话是否有效
func (s *Session) IsValid() bool {
	return !s.IsExpired() && !s.IsRevoked()
}

// APIKey 模型，对应 api_keys 表
type APIKey struct {
	ID         uuid.UUID  `json:"id" db:"id"`
	UserID     uuid.UUID  `json:"user_id" db:"user_id"`
	KeyPrefix  string     `json:"key_prefix" db:"key_prefix"`   // "qoo_sk_" + 前 8 字符
	KeyHash    string     `json:"-" db:"key_hash"`              // SHA-512(API Key)
	KeyName    string     `json:"key_name" db:"key_name"`
	Scopes     []string   `json:"scopes" db:"scopes"`
	LastUsedAt *time.Time `json:"last_used_at,omitempty" db:"last_used_at"`
	ExpiresAt  *time.Time `json:"expires_at,omitempty" db:"expires_at"`
	RevokedAt  *time.Time `json:"revoked_at,omitempty" db:"revoked_at"`
	CreatedAt  time.Time  `json:"created_at" db:"created_at"`
}

// IsRevoked 检查 API Key 是否已吊销
func (k *APIKey) IsRevoked() bool {
	return k.RevokedAt != nil
}

// IsExpired 检查 API Key 是否过期
func (k *APIKey) IsExpired() bool {
	if k.ExpiresAt == nil {
		return false
	}
	return time.Now().After(*k.ExpiresAt)
}

// IsValid 检查 API Key 是否有效
func (k *APIKey) IsValid() bool {
	return !k.IsRevoked() && !k.IsExpired()
}

// FamilyRole 家庭角色枚举
type FamilyRole string

const (
	FamilyRoleAdmin FamilyRole = "admin"
	FamilyRoleMember FamilyRole = "member"
	FamilyRoleChild  FamilyRole = "child"
)

// Family 家庭模型，对应 families 表
type Family struct {
	ID        uuid.UUID `json:"id" db:"id"`
	Name      string    `json:"name" db:"name"`
	OwnerID   uuid.UUID `json:"owner_id" db:"owner_id"`
	CreatedAt time.Time `json:"created_at" db:"created_at"`
}

// FamilyMember 家庭成员模型，对应 family_members 表
type FamilyMember struct {
	FamilyID uuid.UUID  `json:"family_id" db:"family_id"`
	UserID   uuid.UUID  `json:"user_id" db:"user_id"`
	Role     FamilyRole `json:"role" db:"role"`
	JoinedAt time.Time  `json:"joined_at" db:"joined_at"`
}

// OrgRole 组织角色枚举
type OrgRole string

const (
	OrgRoleOwner  OrgRole = "owner"
	OrgRoleAdmin  OrgRole = "admin"
	OrgRoleMember OrgRole = "member"
	OrgRoleViewer OrgRole = "viewer"
)

// Organization 组织模型，对应 organizations 表
type Organization struct {
	ID        uuid.UUID `json:"id" db:"id"`
	Name      string    `json:"name" db:"name"`
	OwnerID   uuid.UUID `json:"owner_id" db:"owner_id"`
	CreatedAt time.Time `json:"created_at" db:"created_at"`
	UpdatedAt time.Time `json:"updated_at" db:"updated_at"`
}

// OrgMember 组织成员模型，对应 org_members 表
type OrgMember struct {
	OrgID    uuid.UUID `json:"org_id" db:"org_id"`
	UserID   uuid.UUID `json:"user_id" db:"user_id"`
	Role     OrgRole   `json:"role" db:"role"`
	JoinedAt time.Time `json:"joined_at" db:"joined_at"`
}

// AuditAction 审计操作枚举
type AuditAction string

const (
	AuditActionUserLogin         AuditAction = "user.login"
	AuditActionUserLogout        AuditAction = "user.logout"
	AuditActionUserRegister      AuditAction = "user.register"
	AuditActionUserDelete        AuditAction = "user.delete"
	AuditActionDeviceActivate    AuditAction = "device.activate"
	AuditActionDeviceLock        AuditAction = "device.lock"
	AuditActionDeviceUnlock      AuditAction = "device.unlock"
	AuditActionDeviceRemove      AuditAction = "device.remove"
	AuditActionSessionCreate     AuditAction = "session.create"
	AuditActionSessionRevoke     AuditAction = "session.revoke"
	AuditActionAPIKeyCreate      AuditAction = "apikey.create"
	AuditActionAPIKeyRevoke      AuditAction = "apikey.revoke"
	AuditActionFamilyCreate      AuditAction = "family.create"
	AuditActionFamilyInvite      AuditAction = "family.invite"
	AuditActionFamilyRemove      AuditAction = "family.remove"
	AuditActionOrgCreate         AuditAction = "org.create"
	AuditActionOrgMemberAdd      AuditAction = "org.member.add"
	AuditActionOrgMemberRemove   AuditAction = "org.member.remove"
)

// AuditResourceType 审计资源类型
type AuditResourceType string

const (
	AuditResourceUser    AuditResourceType = "user"
	AuditResourceDevice  AuditResourceType = "device"
	AuditResourceSession AuditResourceType = "session"
	AuditResourceAPIKey  AuditResourceType = "api_key"
	AuditResourceFamily  AuditResourceType = "family"
	AuditResourceOrg     AuditResourceType = "organization"
)

// AuditLog 审计日志模型，对应 audit_logs 表
type AuditLog struct {
	ID           uuid.UUID         `json:"id" db:"id"`
	UserID       *uuid.UUID        `json:"user_id,omitempty" db:"user_id"`
	Action       AuditAction       `json:"action" db:"action"`
	ResourceType AuditResourceType `json:"resource_type" db:"resource_type"`
	ResourceID   *string           `json:"resource_id,omitempty" db:"resource_id"`
	Details      map[string]any    `json:"details,omitempty" db:"details"`
	IPAddress    string            `json:"ip_address" db:"ip_address"`
	UserAgent    *string           `json:"user_agent,omitempty" db:"user_agent"`
	Success      bool              `json:"success" db:"success"`
	ErrorCode    *string           `json:"error_code,omitempty" db:"error_code"`
	CreatedAt    time.Time         `json:"created_at" db:"created_at"`
}
