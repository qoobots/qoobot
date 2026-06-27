// Package server HTTP/gRPC 服务器生命周期管理
package server

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/crypto"
	"github.com/qoobot/qooauth/internal/repository/postgres"
	"github.com/qoobot/qooauth/internal/server/router"
)

// Config 服务器配置
type Config struct {
	HTTPPort      int
	DatabaseURL   string
	JWTPrivateKey string
	JWTPublicKey  string
	LogLevel      slog.Level
}

// DefaultConfig 默认服务器配置
func DefaultConfig() Config {
	return Config{
		HTTPPort:    8080,
		DatabaseURL: "postgres://qooauth:qooauth@localhost:5432/qooauth?sslmode=disable",
		LogLevel:    slog.LevelInfo,
	}
}

// Server 认证服务器
type Server struct {
	cfg    Config
	logger *slog.Logger
	http   *http.Server
	pool   *pgxpool.Pool
}

// New 创建服务器实例
func New(cfg Config) (*Server, error) {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: cfg.LogLevel,
	}))

	// 数据库连接
	poolCfg := postgres.DefaultConfig(cfg.DatabaseURL)
	pool, err := postgres.NewPool(context.Background(), poolCfg)
	if err != nil {
		return nil, fmt.Errorf("server: database connection: %w", err)
	}

	// JWT 管理器
	jwtCfg := crypto.JWTConfig{
		PrivateKeyPath: cfg.JWTPrivateKey,
		PublicKeyPath:  cfg.JWTPublicKey,
		Issuer:         "https://auth.qoobot.com",
		AccessTTL:      1 * time.Hour,
		RefreshTTL:     30 * 24 * time.Hour,
	}
	jwt, err := crypto.NewJWTManager(jwtCfg)
	if err != nil {
		return nil, fmt.Errorf("server: JWT init: %w", err)
	}

	// 路由
	r := router.Setup(router.DefaultConfig(), jwt, pool, logger)

	httpServer := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.HTTPPort),
		Handler:      r,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	return &Server{
		cfg:    cfg,
		logger: logger,
		http:   httpServer,
		pool:   pool,
	}, nil
}

// Run 启动服务器并等待信号
func (s *Server) Run() error {
	// 优雅关闭
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		s.logger.Info("server starting", slog.Int("port", s.cfg.HTTPPort))
		if err := s.http.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			s.logger.Error("server failed", slog.Any("error", err))
		}
	}()

	<-quit
	s.logger.Info("server shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := s.http.Shutdown(ctx); err != nil {
		return fmt.Errorf("server: shutdown: %w", err)
	}

	s.pool.Close()
	s.logger.Info("server stopped")
	return nil
}
