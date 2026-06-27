// Package config 配置管理
package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// Config 应用配置
type Config struct {
	Server   ServerConfig
	Database DatabaseConfig
	Redis    RedisConfig
	JWT      JWTConfig
	Password PasswordConfig
	Argon2   Argon2Config
	RateLimit RateLimitConfig
	CORS     CORSConfig
	Session  SessionConfig
}

// ServerConfig 服务器配置
type ServerConfig struct {
	Port     int
	GRPCPort int
	LogLevel string
	Env      string
}

// DatabaseConfig 数据库配置
type DatabaseConfig struct {
	URL        string
	MaxConns   int32
	MinConns   int32
	MaxIdleTime time.Duration
}

// RedisConfig Redis 配置
type RedisConfig struct {
	URL      string
	PoolSize int
}

// JWTConfig JWT 配置
type JWTConfig struct {
	PrivateKeyPath string
	PublicKeyPath  string
	AccessTTL      time.Duration
	RefreshTTL     time.Duration
	Issuer         string
}

// PasswordConfig 密码策略配置
type PasswordConfig struct {
	MinLength      int
	RequireUpper   bool
	RequireLower   bool
	RequireDigit   bool
	RequireSpecial bool
	MaxFailedAttempts int
	LockDuration     time.Duration
}

// Argon2Config Argon2id 配置
type Argon2Config struct {
	Memory      uint32
	Iterations  uint32
	Parallelism uint8
}

// RateLimitConfig 速率限制配置
type RateLimitConfig struct {
	Login    RateLimitEntry
	Register RateLimitEntry
	API      RateLimitEntry
}

// RateLimitEntry 速率限制条目
type RateLimitEntry struct {
	Limit  int
	Window time.Duration
}

// CORSConfig CORS 配置
type CORSConfig struct {
	AllowedOrigins []string
	AllowedMethods []string
}

// SessionConfig 会话配置
type SessionConfig struct {
	MaxDevices     int
	IdleTimeout    time.Duration
	AbsoluteTimeout time.Duration
}

// Load 从环境变量加载配置
func Load() (*Config, error) {
	cfg := &Config{
		Server: ServerConfig{
			Port:     getEnvInt("QOOAUTH_SERVER_PORT", 8080),
			GRPCPort: getEnvInt("QOOAUTH_GRPC_PORT", 9090),
			LogLevel: getEnvStr("QOOAUTH_LOG_LEVEL", "info"),
			Env:      getEnvStr("QOOAUTH_ENV", "development"),
		},
		Database: DatabaseConfig{
			URL:         getEnvStr("QOOAUTH_DATABASE_URL", ""),
			MaxConns:    int32(getEnvInt("QOOAUTH_DATABASE_MAX_CONNS", 25)),
			MinConns:    int32(getEnvInt("QOOAUTH_DATABASE_MIN_CONNS", 5)),
			MaxIdleTime: getEnvDuration("QOOAUTH_DATABASE_MAX_IDLE_TIME", 15*time.Minute),
		},
		Redis: RedisConfig{
			URL:      getEnvStr("QOOAUTH_REDIS_URL", ""),
			PoolSize: getEnvInt("QOOAUTH_REDIS_POOL_SIZE", 20),
		},
		JWT: JWTConfig{
			PrivateKeyPath: getEnvStr("QOOAUTH_JWT_PRIVATE_KEY_PATH", ""),
			PublicKeyPath:  getEnvStr("QOOAUTH_JWT_PUBLIC_KEY_PATH", ""),
			AccessTTL:      getEnvDuration("QOOAUTH_JWT_ACCESS_TOKEN_TTL", 1*time.Hour),
			RefreshTTL:     getEnvDuration("QOOAUTH_JWT_REFRESH_TOKEN_TTL", 30*24*time.Hour),
			Issuer:         getEnvStr("QOOAUTH_JWT_ISSUER", "https://auth.qoobot.com"),
		},
		Password: PasswordConfig{
			MinLength:        getEnvInt("QOOAUTH_PASSWORD_MIN_LENGTH", 8),
			RequireUpper:     getEnvBool("QOOAUTH_PASSWORD_REQUIRE_UPPER", true),
			RequireLower:     getEnvBool("QOOAUTH_PASSWORD_REQUIRE_LOWER", true),
			RequireDigit:     getEnvBool("QOOAUTH_PASSWORD_REQUIRE_DIGIT", true),
			RequireSpecial:   getEnvBool("QOOAUTH_PASSWORD_REQUIRE_SPECIAL", true),
			MaxFailedAttempts: getEnvInt("QOOAUTH_PASSWORD_MAX_FAILED_ATTEMPTS", 5),
			LockDuration:     getEnvDuration("QOOAUTH_PASSWORD_LOCK_DURATION", 15*time.Minute),
		},
		Argon2: Argon2Config{
			Memory:      uint32(getEnvInt("QOOAUTH_ARGON2_MEMORY", 65536)),
			Iterations:  uint32(getEnvInt("QOOAUTH_ARGON2_ITERATIONS", 3)),
			Parallelism: uint8(getEnvInt("QOOAUTH_ARGON2_PARALLELISM", 4)),
		},
		RateLimit: RateLimitConfig{
			Login:    RateLimitEntry{Limit: getEnvInt("QOOAUTH_RATELIMIT_LOGIN", 10), Window: time.Minute},
			Register: RateLimitEntry{Limit: getEnvInt("QOOAUTH_RATELIMIT_REGISTER", 3), Window: time.Minute},
			API:      RateLimitEntry{Limit: getEnvInt("QOOAUTH_RATELIMIT_API", 100), Window: time.Minute},
		},
		CORS: CORSConfig{
			AllowedOrigins: getEnvStrSlice("QOOAUTH_CORS_ALLOWED_ORIGINS", []string{"*"}),
			AllowedMethods: getEnvStrSlice("QOOAUTH_CORS_ALLOWED_METHODS", []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"}),
		},
		Session: SessionConfig{
			MaxDevices:      getEnvInt("QOOAUTH_SESSION_MAX_DEVICES", 10),
			IdleTimeout:     getEnvDuration("QOOAUTH_SESSION_IDLE_TIMEOUT", 72*time.Hour),
			AbsoluteTimeout: getEnvDuration("QOOAUTH_SESSION_ABSOLUTE_TIMEOUT", 30*24*time.Hour),
		},
	}

	if cfg.Database.URL == "" {
		return nil, fmt.Errorf("config: QOOAUTH_DATABASE_URL is required")
	}

	return cfg, nil
}

func getEnvStr(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}

func getEnvInt(key string, defaultVal int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return defaultVal
}

func getEnvBool(key string, defaultVal bool) bool {
	if v := os.Getenv(key); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return defaultVal
}

func getEnvDuration(key string, defaultVal time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return defaultVal
}

func getEnvStrSlice(key string, defaultVal []string) []string {
	if v := os.Getenv(key); v != "" {
		var result []string
		for _, s := range splitAndTrim(v, ",") {
			if s != "" {
				result = append(result, s)
			}
		}
		if len(result) > 0 {
			return result
		}
	}
	return defaultVal
}

func splitAndTrim(s, sep string) []string {
	var result []string
	current := ""
	for _, c := range s {
		if string(c) == sep {
			result = append(result, current)
			current = ""
		} else {
			current += string(c)
		}
	}
	result = append(result, current)
	for i := range result {
		result[i] = trimSpace(result[i])
	}
	return result
}

func trimSpace(s string) string {
	start := 0
	end := len(s)
	for start < end && (s[start] == ' ' || s[start] == '\t') {
		start++
	}
	for end > start && (s[end-1] == ' ' || s[end-1] == '\t') {
		end--
	}
	return s[start:end]
}
