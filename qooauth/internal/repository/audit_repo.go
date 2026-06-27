package repository

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/model"
)

// AuditRepository 审计日志数据访问接口
type AuditRepository struct {
	pool *pgxpool.Pool
}

// NewAuditRepository 创建审计日志数据访问实例
func NewAuditRepository(pool *pgxpool.Pool) *AuditRepository {
	return &AuditRepository{pool: pool}
}

// Record 记录审计事件
func (r *AuditRepository) Record(ctx context.Context, log *model.AuditLog) error {
	query := `
		INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id,
		                        details, ip_address, user_agent, success, error_code)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		RETURNING created_at`

	if log.ID == uuid.Nil {
		log.ID = uuid.New()
	}

	err := r.pool.QueryRow(ctx, query,
		log.ID, log.UserID, string(log.Action), string(log.ResourceType),
		log.ResourceID, log.Details, log.IPAddress, log.UserAgent,
		log.Success, log.ErrorCode,
	).Scan(&log.CreatedAt)

	if err != nil {
		return fmt.Errorf("audit_repo: record: %w", err)
	}
	return nil
}

// AuditQuery 审计查询参数
type AuditQuery struct {
	UserID       *uuid.UUID
	Action       *model.AuditAction
	ResourceType *model.AuditResourceType
	Success      *bool
	From         string // 开始时间 ISO 8601
	To           string // 结束时间 ISO 8601
	Limit        int
	Offset       int
}

// Query 查询审计日志
func (r *AuditRepository) Query(ctx context.Context, q AuditQuery) ([]*model.AuditLog, error) {
	if q.Limit <= 0 {
		q.Limit = 50
	}
	if q.Limit > 1000 {
		q.Limit = 1000
	}

	query := `
		SELECT id, user_id, action, resource_type, resource_id,
		       details, ip_address, user_agent, success, error_code, created_at
		FROM audit_logs WHERE 1=1`
	args := []any{}
	argIdx := 1

	if q.UserID != nil {
		query += fmt.Sprintf(` AND user_id = $%d`, argIdx)
		args = append(args, *q.UserID)
		argIdx++
	}
	if q.Action != nil {
		query += fmt.Sprintf(` AND action = $%d`, argIdx)
		args = append(args, string(*q.Action))
		argIdx++
	}
	if q.ResourceType != nil {
		query += fmt.Sprintf(` AND resource_type = $%d`, argIdx)
		args = append(args, string(*q.ResourceType))
		argIdx++
	}
	if q.Success != nil {
		query += fmt.Sprintf(` AND success = $%d`, argIdx)
		args = append(args, *q.Success)
		argIdx++
	}
	if q.From != "" {
		query += fmt.Sprintf(` AND created_at >= $%d`, argIdx)
		args = append(args, q.From)
		argIdx++
	}
	if q.To != "" {
		query += fmt.Sprintf(` AND created_at <= $%d`, argIdx)
		args = append(args, q.To)
		argIdx++
	}

	query += ` ORDER BY created_at DESC`
	query += fmt.Sprintf(` LIMIT $%d OFFSET $%d`, argIdx, argIdx+1)
	args = append(args, q.Limit, q.Offset)

	rows, err := r.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("audit_repo: query: %w", err)
	}
	defer rows.Close()

	var logs []*model.AuditLog
	for rows.Next() {
		l := &model.AuditLog{}
		var actionStr, resourceTypeStr string
		if err := rows.Scan(
			&l.ID, &l.UserID, &actionStr, &resourceTypeStr, &l.ResourceID,
			&l.Details, &l.IPAddress, &l.UserAgent, &l.Success, &l.ErrorCode, &l.CreatedAt,
		); err != nil {
			return nil, fmt.Errorf("audit_repo: scan: %w", err)
		}
		l.Action = model.AuditAction(actionStr)
		l.ResourceType = model.AuditResourceType(resourceTypeStr)
		logs = append(logs, l)
	}
	return logs, rows.Err()
}
