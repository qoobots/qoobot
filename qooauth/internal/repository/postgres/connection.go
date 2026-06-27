// Package postgres 提供 PostgreSQL 连接池管理和数据访问
package postgres

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Config PostgreSQL 连接配置
type Config struct {
	DatabaseURL string        // 连接字符串
	MaxConns    int32         // 最大连接数
	MinConns    int32         // 最小连接数
	MaxIdleTime time.Duration // 最大空闲时间
}

// DefaultConfig 返回默认配置
func DefaultConfig(databaseURL string) Config {
	return Config{
		DatabaseURL: databaseURL,
		MaxConns:    25,
		MinConns:    5,
		MaxIdleTime: 15 * time.Minute,
	}
}

// NewPool 创建连接池
func NewPool(ctx context.Context, cfg Config) (*pgxpool.Pool, error) {
	poolCfg, err := pgxpool.ParseConfig(cfg.DatabaseURL)
	if err != nil {
		return nil, fmt.Errorf("postgres: parse config: %w", err)
	}

	poolCfg.MaxConns = cfg.MaxConns
	poolCfg.MinConns = cfg.MinConns
	poolCfg.MaxConnIdleTime = cfg.MaxIdleTime

	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		return nil, fmt.Errorf("postgres: create pool: %w", err)
	}

	// 验证连接
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("postgres: ping: %w", err)
	}

	return pool, nil
}
