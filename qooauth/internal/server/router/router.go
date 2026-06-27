// Package router 路由注册
package router

import (
	"log/slog"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/qoobot/qooauth/internal/crypto"
	"github.com/qoobot/qooauth/internal/server/middleware"
	"github.com/qoobot/qooauth/internal/service/apikey"
	"github.com/qoobot/qooauth/internal/service/auth"
	"github.com/qoobot/qooauth/internal/service/device"
	"github.com/qoobot/qooauth/internal/service/oauth"
	"github.com/qoobot/qooauth/internal/service/user"
)

// Config 路由配置
type Config struct {
	CORSOrigins   []string
	LoginLimit    int
	RegisterLimit int
	APILimit      int
}

// DefaultConfig 默认路由配置
func DefaultConfig() Config {
	return Config{
		CORSOrigins:   []string{"https://auth.qoobot.com", "https://console.qoobot.com"},
		LoginLimit:    10, // 每分钟
		RegisterLimit: 3,  // 每分钟
		APILimit:      100, // 每分钟
	}
}

// Services 业务服务集合
type Services struct {
	Auth   *auth.Service
	User   *user.Service
	Device *device.Service
	OAuth  *oauth.Service
	APIKey *apikey.Service
}

// Setup 设置 Gin 路由
func Setup(cfg Config, jwt *crypto.JWTManager, pool *pgxpool.Pool, logger *slog.Logger) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	r := gin.New()

	// 全局中间件
	r.Use(middleware.Recovery(logger))
	r.Use(middleware.RequestLogger(logger))
	r.Use(middleware.CORS(cfg.CORSOrigins))

	// 服务实例
	authCfg := auth.DefaultConfig()
	oauthCfg := oauth.DefaultConfig("https://auth.qoobot.com")

	svc := Services{
		Auth:   auth.NewService(authCfg, jwt, pool),
		User:   user.NewService(pool),
		Device: device.NewService(pool),
		OAuth:  oauth.NewService(oauthCfg, jwt, pool),
		APIKey: apikey.NewService(pool),
	}

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "time": time.Now().UTC()})
	})

	// API v1
	v1 := r.Group("/api/v1")
	{
		// 认证端点（无需认证）
		authGroup := v1.Group("/auth")
		{
			authGroup.POST("/register",
				middleware.IPRateLimit(cfg.RegisterLimit, time.Minute),
				svc.handleRegister,
			)
			authGroup.POST("/login",
				middleware.IPRateLimit(cfg.LoginLimit, time.Minute),
				svc.handleLogin,
			)
			authGroup.POST("/refresh", svc.handleRefreshToken)
			authGroup.POST("/logout",
				middleware.JWTAuth(jwt),
				svc.handleLogout,
			)
			authGroup.POST("/revoke",
				middleware.JWTAuth(jwt),
				svc.handleRevokeAll,
			)
		}

		// 用户端点（需要认证）
		userGroup := v1.Group("/users")
		userGroup.Use(middleware.JWTAuth(jwt))
		{
			userGroup.GET("/me", svc.handleGetProfile)
			userGroup.PUT("/me", svc.handleUpdateProfile)
			userGroup.DELETE("/me", svc.handleDeleteAccount)
		}

		// 设备端点（需要认证）
		deviceGroup := v1.Group("/devices")
		deviceGroup.Use(middleware.JWTAuth(jwt))
		{
			deviceGroup.GET("", svc.handleListDevices)
			deviceGroup.POST("/activate", svc.handleActivateDevice)
			deviceGroup.GET("/:id", svc.handleGetDevice)
			deviceGroup.POST("/:id/lock", svc.handleLockDevice)
			deviceGroup.POST("/:id/unlock", svc.handleUnlockDevice)
			deviceGroup.DELETE("/:id", svc.handleRemoveDevice)
		}

		// 会话端点（需要认证）
		sessionGroup := v1.Group("/sessions")
		sessionGroup.Use(middleware.JWTAuth(jwt))
		{
			sessionGroup.GET("", svc.handleListSessions)
			sessionGroup.DELETE("/:id", svc.handleRevokeSession)
		}

		// API Key 端点（需要认证）
		apikeyGroup := v1.Group("/api-keys")
		apikeyGroup.Use(middleware.JWTAuth(jwt))
		{
			apikeyGroup.POST("", svc.handleCreateAPIKey)
			apikeyGroup.GET("", svc.handleListAPIKeys)
			apikeyGroup.DELETE("/:id", svc.handleRevokeAPIKey)
		}

		// OAuth 端点（公开 + 认证混合）
		oauthGroup := v1.Group("/oauth")
		{
			oauthGroup.GET("/authorize", svc.handleOAuthAuthorize)
			oauthGroup.POST("/token", svc.handleOAuthToken)
		}
	}

	return r
}
