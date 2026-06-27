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

// SessionRepository 会话数据访问接口
type SessionRepository struct {
	pool *pgxpool.Pool
}

// NewSessionRepository 创建会话数据访问实例
func NewSessionRepository(pool *pgxpool.Pool) *SessionRepository {
	return &SessionRepository{pool: pool}
}

// Create 创建会话
func (r *SessionRepository) Create(ctx context.Context, session *model.Session) error {
	query := `
		INSERT INTO sessions (id, user_id, token_hash, device_info, ip_address, location,
		                      is_trusted, expires_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
		RETURNING created_at`

	if session.ID == uuid.Nil {
		session.ID = uuid.New()
	}

	err := r.pool.QueryRow(ctx, query,
		session.ID, session.UserID, session.TokenHash,
		session.DeviceInfo, session.IPAddress, session.Location,
		session.IsTrusted, session.ExpiresAt,
	).Scan(&session.CreatedAt)

	if err != nil {
		return fmt.Errorf("session_repo: create: %w", err)
	}
	return nil
}

// FindByTokenHash 按 Token 哈希查询会话
func (r *SessionRepository) FindByTokenHash(ctx context.Context, tokenHash string) (*model.Session, error) {
	query := `
		SELECT id, user_id, token_hash, device_info, ip_address, location,
		       is_trusted, created_at, expires_at, revoked_at
		FROM sessions WHERE token_hash = $1 AND revoked_at IS NULL`

	session := &model.Session{}
	err := r.pool.QueryRow(ctx, query, tokenHash).Scan(
		&session.ID, &session.UserID, &session.TokenHash,
		&session.DeviceInfo, &session.IPAddress, &session.Location,
		&session.IsTrusted, &session.CreatedAt, &session.ExpiresAt, &session.RevokedAt,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("session_repo: find by token hash: %w", err)
	}
	return session, nil
}

// ListByUserID 列出用户的所有活跃会话
func (r *SessionRepository) ListByUserID(ctx context.Context, userID uuid.UUID) ([]*model.Session, error) {
	query := `
		SELECT id, user_id, token_hash, device_info, ip_address, location,
		       is_trusted, created_at, expires_at, revoked_at
		FROM sessions
		WHERE user_id = $1 AND revoked_at IS NULL AND expires_at > $2
		ORDER BY created_at DESC`

	rows, err := r.pool.Query(ctx, query, userID, time.Now())
	if err != nil {
		return nil, fmt.Errorf("session_repo: list by user: %w", err)
	}
	defer rows.Close()

	var sessions []*model.Session
	for rows.Next() {
		s := &model.Session{}
		if err := rows.Scan(
			&s.ID, &s.UserID, &s.TokenHash,
			&s.DeviceInfo, &s.IPAddress, &s.Location,
			&s.IsTrusted, &s.CreatedAt, &s.ExpiresAt, &s.RevokedAt,
		); err != nil {
			return nil, fmt.Errorf("session_repo: scan: %w", err)
		}
		sessions = append(sessions, s)
	}
	return sessions, rows.Err()
}

// Revoke 吊销会话
func (r *SessionRepository) Revoke(ctx context.Context, id uuid.UUID) error {
	_, err := r.pool.Exec(ctx, `UPDATE sessions SET revoked_at = $2 WHERE id = $1`, id, time.Now())
	if err != nil {
		return fmt.Errorf("session_repo: revoke: %w", err)
	}
	return nil
}

// RevokeAllByUser 吊销用户所有会话
func (r *SessionRepository) RevokeAllByUser(ctx context.Context, userID uuid.UUID) error {
	_, err := r.pool.Exec(ctx,
		`UPDATE sessions SET revoked_at = $2 WHERE user_id = $1 AND revoked_at IS NULL`,
		userID, time.Now())
	if err != nil {
		return fmt.Errorf("session_repo: revoke all: %w", err)
	}
	return nil
}

// CountActiveByUser 统计用户活跃会话数
func (r *SessionRepository) CountActiveByUser(ctx context.Context, userID uuid.UUID) (int, error) {
	var count int
	err := r.pool.QueryRow(ctx,
		`SELECT COUNT(*) FROM sessions WHERE user_id = $1 AND revoked_at IS NULL AND expires_at > $2`,
		userID, time.Now()).Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("session_repo: count active: %w", err)
	}
	return count, nil
}

// CleanupExpired 清理过期会话
func (r *SessionRepository) CleanupExpired(ctx context.Context) (int64, error) {
	tag, err := r.pool.Exec(ctx,
		`UPDATE sessions SET revoked_at = $1 WHERE expires_at < $1 AND revoked_at IS NULL`,
		time.Now())
	if err != nil {
		return 0, fmt.Errorf("session_repo: cleanup: %w", err)
	}
	return tag.RowsAffected(), nil
}
