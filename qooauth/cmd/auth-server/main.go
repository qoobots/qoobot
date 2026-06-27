// Package main qooauth 认证服务主程序
// 提供 QooBot 生态的统一身份认证基础设施
package main

import (
	"fmt"
	"os"

	"github.com/qoobot/qooauth/internal/config"
	"github.com/qoobot/qooauth/internal/server"
)

var (
	version   = "0.1.0"
	buildTime = "unknown"
)

func main() {
	// 加载配置
	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to load config: %v\n", err)
		os.Exit(1)
	}

	// 创建服务器
	srvCfg := server.Config{
		HTTPPort:      cfg.Server.Port,
		DatabaseURL:   cfg.Database.URL,
		JWTPrivateKey: cfg.JWT.PrivateKeyPath,
		JWTPublicKey:  cfg.JWT.PublicKeyPath,
	}

	srv, err := server.New(srvCfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to create server: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("qooauth v%s (built %s)\n", version, buildTime)
	fmt.Printf("Server starting on port %d\n", cfg.Server.Port)

	if err := srv.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Server error: %v\n", err)
		os.Exit(1)
	}
}
