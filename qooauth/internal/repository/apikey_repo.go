package repository

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/model"
)

// APIKeyRepository API 密钥数据访问接口
type APIKeyRepository struct {
	pool *pgxpool.Pool
}

// NewAPIKeyRepository 创建 API Key 数据访问实例
func NewAPIKeyRepository(pool *pgxpool.Pool) *APIKeyRepository {
	return &APIKeyRepository{pool: pool}
}

// Create 创建 API Key
func (r *APIKeyRepository) Create(ctx context.Context, key *model.APIKey) error {
	query := `
		INSERT INTO api_keys (id, user_id, key_prefix, key_hash, key_name, scopes, expires_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		RETURNING created_at`

	if key.ID == uuid.Nil {
		key.ID = uuid.New()
	}

	err := r.pool.QueryRow(ctx, query,
		key.ID, key.UserID, key.KeyPrefix, key.KeyHash,
		key.KeyName, key.Scopes, key.ExpiresAt,
	).Scan(&key.CreatedAt)

	if err != nil {
		return fmt.Errorf("apikey_repo: create: %w", err)
	}
	return nil
}

// FindByKeyHash 按 Key 哈希查询
func (r *APIKeyRepository) FindByKeyHash(ctx context.Context, keyHash string) (*model.APIKey, error) {
	query := `
		SELECT id, user_id, key_prefix, key_hash, key_name, scopes,
		       last_used_at, expires_at, revoked_at, created_at
		FROM api_keys WHERE key_hash = $1`

	key := &model.APIKey{}
	err := r.pool.QueryRow(ctx, query, keyHash).Scan(
		&key.ID, &key.UserID, &key.KeyPrefix, &key.KeyHash,
		&key.KeyName, &key.Scopes, &key.LastUsedAt,
		&key.ExpiresAt, &key.RevokedAt, &key.CreatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("apikey_repo: find by hash: %w", err)
	}
	return key, nil
}

// ListByUserID 列出用户的所有 API Keys
func (r *APIKeyRepository) ListByUserID(ctx context.Context, userID uuid.UUID) ([]*model.APIKey, error) {
	query := `
		SELECT id, user_id, key_prefix, key_hash, key_name, scopes,
		       last_used_at, expires_at, revoked_at, created_at
		FROM api_keys WHERE user_id = $1 AND revoked_at IS NULL
		ORDER BY created_at DESC`

	rows, err := r.pool.Query(ctx, query, userID)
	if err != nil {
		return nil, fmt.Errorf("apikey_repo: list: %w", err)
	}
	defer rows.Close()

	var keys []*model.APIKey
	for rows.Next() {
		k := &model.APIKey{}
		if err := rows.Scan(
			&k.ID, &k.UserID, &k.KeyPrefix, &k.KeyHash,
			&k.KeyName, &k.Scopes, &k.LastUsedAt,
			&k.ExpiresAt, &k.RevokedAt, &k.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("apikey_repo: scan: %w", err)
		}
		keys = append(keys, k)
	}
	return keys, rows.Err()
}

// Revoke 吊销 API Key
func (r *APIKeyRepository) Revoke(ctx context.Context, id uuid.UUID) error {
	_, err := r.pool.Exec(ctx,
		`UPDATE api_keys SET revoked_at = NOW() WHERE id = $1`, id)
	if err != nil {
		return fmt.Errorf("apikey_repo: revoke: %w", err)
	}
	return nil
}

// UpdateLastUsed 更新最后使用时间
func (r *APIKeyRepository) UpdateLastUsed(ctx context.Context, id uuid.UUID) error {
	_, err := r.pool.Exec(ctx,
		`UPDATE api_keys SET last_used_at = NOW() WHERE id = $1`, id)
	if err != nil {
		return fmt.Errorf("apikey_repo: update last used: %w", err)
	}
	return nil
}
