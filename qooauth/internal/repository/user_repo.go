// Package repository 用户数据访问层实现
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

// UserRepository 用户数据访问接口
type UserRepository struct {
	pool *pgxpool.Pool
}

// NewUserRepository 创建用户数据访问实例
func NewUserRepository(pool *pgxpool.Pool) *UserRepository {
	return &UserRepository{pool: pool}
}

// Create 创建用户
func (r *UserRepository) Create(ctx context.Context, user *model.User) error {
	query := `
		INSERT INTO users (id, email, password_hash, display_name, locale, timezone, account_status)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING created_at, updated_at`

	if user.ID == uuid.Nil {
		user.ID = uuid.New()
	}

	err := r.pool.QueryRow(ctx, query,
		user.ID, user.Email, user.PasswordHash, user.DisplayName,
		user.Locale, user.Timezone, string(model.AccountStatusActive),
	).Scan(&user.CreatedAt, &user.UpdatedAt)

	if err != nil {
		return fmt.Errorf("user_repo: create: %w", err)
	}
	return nil
}

// FindByID 按 ID 查询用户
func (r *UserRepository) FindByID(ctx context.Context, id uuid.UUID) (*model.User, error) {
	query := `
		SELECT id, email, email_verified, phone, phone_verified,
		       password_hash, display_name, avatar_url, locale, timezone,
		       totp_enabled, totp_secret, passkey_enabled,
		       account_status, locked_until, failed_attempts,
		       created_at, updated_at, deleted_at
		FROM users WHERE id = $1 AND deleted_at IS NULL`

	user := &model.User{}
	err := r.pool.QueryRow(ctx, query, id).Scan(
		&user.ID, &user.Email, &user.EmailVerified, &user.Phone, &user.PhoneVerified,
		&user.PasswordHash, &user.DisplayName, &user.AvatarURL, &user.Locale, &user.Timezone,
		&user.TOTPEnabled, &user.TOTPSecret, &user.PasskeyEnabled,
		&user.AccountStatus, &user.LockedUntil, &user.FailedAttempts,
		&user.CreatedAt, &user.UpdatedAt, &user.DeletedAt,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("user_repo: find by id: %w", err)
	}
	return user, nil
}

// FindByEmail 按邮箱查询用户
func (r *UserRepository) FindByEmail(ctx context.Context, email string) (*model.User, error) {
	query := `
		SELECT id, email, email_verified, phone, phone_verified,
		       password_hash, display_name, avatar_url, locale, timezone,
		       totp_enabled, totp_secret, passkey_enabled,
		       account_status, locked_until, failed_attempts,
		       created_at, updated_at, deleted_at
		FROM users WHERE LOWER(email) = LOWER($1) AND deleted_at IS NULL`

	user := &model.User{}
	err := r.pool.QueryRow(ctx, query, email).Scan(
		&user.ID, &user.Email, &user.EmailVerified, &user.Phone, &user.PhoneVerified,
		&user.PasswordHash, &user.DisplayName, &user.AvatarURL, &user.Locale, &user.Timezone,
		&user.TOTPEnabled, &user.TOTPSecret, &user.PasskeyEnabled,
		&user.AccountStatus, &user.LockedUntil, &user.FailedAttempts,
		&user.CreatedAt, &user.UpdatedAt, &user.DeletedAt,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("user_repo: find by email: %w", err)
	}
	return user, nil
}

// Update 更新用户信息
func (r *UserRepository) Update(ctx context.Context, user *model.User) error {
	query := `
		UPDATE users SET
			email = $2, email_verified = $3, phone = $4, phone_verified = $5,
			display_name = $6, avatar_url = $7, locale = $8, timezone = $9,
			totp_enabled = $10, totp_secret = $11, passkey_enabled = $12,
			account_status = $13, locked_until = $14, failed_attempts = $15
		WHERE id = $1`

	_, err := r.pool.Exec(ctx, query,
		user.ID, user.Email, user.EmailVerified, user.Phone, user.PhoneVerified,
		user.DisplayName, user.AvatarURL, user.Locale, user.Timezone,
		user.TOTPEnabled, user.TOTPSecret, user.PasskeyEnabled,
		string(user.AccountStatus), user.LockedUntil, user.FailedAttempts,
	)
	if err != nil {
		return fmt.Errorf("user_repo: update: %w", err)
	}
	return nil
}

// SoftDelete 软删除用户
func (r *UserRepository) SoftDelete(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE users SET deleted_at = $2, account_status = 'deleted' WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, time.Now())
	if err != nil {
		return fmt.Errorf("user_repo: soft delete: %w", err)
	}
	return nil
}

// RecordFailedAttempt 记录登录失败
func (r *UserRepository) RecordFailedAttempt(ctx context.Context, id uuid.UUID, maxAttempts int, lockDuration time.Duration) error {
	query := `
		UPDATE users SET
			failed_attempts = failed_attempts + 1,
			locked_until = CASE
				WHEN failed_attempts + 1 >= $2 THEN $3
				ELSE locked_until
			END
		WHERE id = $1`
	lockUntil := time.Now().Add(lockDuration)
	_, err := r.pool.Exec(ctx, query, id, maxAttempts, lockUntil)
	if err != nil {
		return fmt.Errorf("user_repo: record failed attempt: %w", err)
	}
	return nil
}

// ResetFailedAttempts 重置登录失败计数
func (r *UserRepository) ResetFailedAttempts(ctx context.Context, id uuid.UUID) error {
	query := `UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id)
	if err != nil {
		return fmt.Errorf("user_repo: reset failed attempts: %w", err)
	}
	return nil
}

// UpdatePassword 更新密码哈希
func (r *UserRepository) UpdatePassword(ctx context.Context, id uuid.UUID, passwordHash string) error {
	query := `UPDATE users SET password_hash = $2 WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, passwordHash)
	if err != nil {
		return fmt.Errorf("user_repo: update password: %w", err)
	}
	return nil
}
