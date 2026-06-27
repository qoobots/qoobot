package repository

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/model"
)

// FamilyRepository 家庭与组织数据访问接口
type FamilyRepository struct {
	pool *pgxpool.Pool
}

// NewFamilyRepository 创建家庭数据访问实例
func NewFamilyRepository(pool *pgxpool.Pool) *FamilyRepository {
	return &FamilyRepository{pool: pool}
}

// CreateFamily 创建家庭
func (r *FamilyRepository) CreateFamily(ctx context.Context, family *model.Family) error {
	query := `INSERT INTO families (id, name, owner_id) VALUES ($1, $2, $3) RETURNING created_at`
	if family.ID == uuid.Nil {
		family.ID = uuid.New()
	}
	err := r.pool.QueryRow(ctx, query, family.ID, family.Name, family.OwnerID).Scan(&family.CreatedAt)
	if err != nil {
		return fmt.Errorf("family_repo: create: %w", err)
	}
	return nil
}

// FindFamilyByID 按 ID 查询家庭
func (r *FamilyRepository) FindFamilyByID(ctx context.Context, id uuid.UUID) (*model.Family, error) {
	query := `SELECT id, name, owner_id, created_at FROM families WHERE id = $1`
	f := &model.Family{}
	err := r.pool.QueryRow(ctx, query, id).Scan(&f.ID, &f.Name, &f.OwnerID, &f.CreatedAt)
	if err != nil {
		return nil, fmt.Errorf("family_repo: find: %w", err)
	}
	return f, nil
}

// AddFamilyMember 添加家庭成员
func (r *FamilyRepository) AddFamilyMember(ctx context.Context, familyID, userID uuid.UUID, role model.FamilyRole) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO family_members (family_id, user_id, role) VALUES ($1, $2, $3)
		 ON CONFLICT (family_id, user_id) DO UPDATE SET role = $3`,
		familyID, userID, string(role))
	if err != nil {
		return fmt.Errorf("family_repo: add member: %w", err)
	}
	return nil
}

// RemoveFamilyMember 移除家庭成员
func (r *FamilyRepository) RemoveFamilyMember(ctx context.Context, familyID, userID uuid.UUID) error {
	_, err := r.pool.Exec(ctx,
		`DELETE FROM family_members WHERE family_id = $1 AND user_id = $2`,
		familyID, userID)
	if err != nil {
		return fmt.Errorf("family_repo: remove member: %w", err)
	}
	return nil
}

// ListFamilyMembers 列出家庭成员
func (r *FamilyRepository) ListFamilyMembers(ctx context.Context, familyID uuid.UUID) ([]*model.FamilyMember, error) {
	query := `SELECT family_id, user_id, role, joined_at FROM family_members WHERE family_id = $1`
	rows, err := r.pool.Query(ctx, query, familyID)
	if err != nil {
		return nil, fmt.Errorf("family_repo: list members: %w", err)
	}
	defer rows.Close()

	var members []*model.FamilyMember
	for rows.Next() {
		m := &model.FamilyMember{}
		var roleStr string
		if err := rows.Scan(&m.FamilyID, &m.UserID, &roleStr, &m.JoinedAt); err != nil {
			return nil, fmt.Errorf("family_repo: scan member: %w", err)
		}
		m.Role = model.FamilyRole(roleStr)
		members = append(members, m)
	}
	return members, rows.Err()
}

// CreateOrganization 创建组织
func (r *FamilyRepository) CreateOrganization(ctx context.Context, org *model.Organization) error {
	query := `INSERT INTO organizations (id, name, owner_id) VALUES ($1, $2, $3) RETURNING created_at, updated_at`
	if org.ID == uuid.Nil {
		org.ID = uuid.New()
	}
	err := r.pool.QueryRow(ctx, query, org.ID, org.Name, org.OwnerID).Scan(&org.CreatedAt, &org.UpdatedAt)
	if err != nil {
		return fmt.Errorf("family_repo: create org: %w", err)
	}
	return nil
}

// AddOrgMember 添加组织成员
func (r *FamilyRepository) AddOrgMember(ctx context.Context, orgID, userID uuid.UUID, role model.OrgRole) error {
	_, err := r.pool.Exec(ctx,
		`INSERT INTO org_members (org_id, user_id, role) VALUES ($1, $2, $3)
		 ON CONFLICT (org_id, user_id) DO UPDATE SET role = $3`,
		orgID, userID, string(role))
	if err != nil {
		return fmt.Errorf("family_repo: add org member: %w", err)
	}
	return nil
}
