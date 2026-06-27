package crypto

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"os"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

// JWTManager 管理 JWT 签发与验证
type JWTManager struct {
	privateKey ed25519.PrivateKey
	publicKey  ed25519.PublicKey
	issuer     string
	accessTTL  time.Duration
	refreshTTL time.Duration
}

// JWTConfig JWT 管理器配置
type JWTConfig struct {
	PrivateKeyPath string        // Ed25519 私钥 PEM 路径
	PublicKeyPath  string        // Ed25519 公钥 PEM 路径
	Issuer         string        // Token 签发者
	AccessTTL      time.Duration // Access Token 有效期
	RefreshTTL     time.Duration // Refresh Token 有效期
}

// CustomClaims 自定义 JWT Claims
type CustomClaims struct {
	jwt.RegisteredClaims
	Scopes        []string `json:"scopes"`
	Email         string   `json:"email,omitempty"`
	EmailVerified bool     `json:"email_verified"`
}

// NewJWTManager 创建 JWT 管理器
func NewJWTManager(cfg JWTConfig) (*JWTManager, error) {
	m := &JWTManager{
		issuer:     cfg.Issuer,
		accessTTL:  cfg.AccessTTL,
		refreshTTL: cfg.RefreshTTL,
	}

	// 优先从文件加载密钥
	if cfg.PrivateKeyPath != "" {
		if err := m.loadKeys(cfg.PrivateKeyPath, cfg.PublicKeyPath); err != nil {
			return nil, fmt.Errorf("crypto: load keys: %w", err)
		}
	} else {
		// 开发环境自动生成密钥对
		if err := m.generateKeys(); err != nil {
			return nil, fmt.Errorf("crypto: generate keys: %w", err)
		}
	}

	return m, nil
}

// loadKeys 从 PEM 文件加载 Ed25519 密钥对
func (m *JWTManager) loadKeys(privPath, pubPath string) error {
	privData, err := os.ReadFile(privPath)
	if err != nil {
		return fmt.Errorf("read private key: %w", err)
	}

	privBlock, _ := pem.Decode(privData)
	if privBlock == nil {
		return fmt.Errorf("decode private key PEM")
	}

	parsedKey, err := x509.ParsePKCS8PrivateKey(privBlock.Bytes)
	if err != nil {
		return fmt.Errorf("parse private key: %w", err)
	}

	edKey, ok := parsedKey.(ed25519.PrivateKey)
	if !ok {
		return fmt.Errorf("private key is not Ed25519")
	}
	m.privateKey = edKey

	if pubPath != "" {
		pubData, err := os.ReadFile(pubPath)
		if err != nil {
			return fmt.Errorf("read public key: %w", err)
		}
		pubBlock, _ := pem.Decode(pubData)
		if pubBlock == nil {
			return fmt.Errorf("decode public key PEM")
		}
		parsedPub, err := x509.ParsePKIXPublicKey(pubBlock.Bytes)
		if err != nil {
			return fmt.Errorf("parse public key: %w", err)
		}
		edPub, ok := parsedPub.(ed25519.PublicKey)
		if !ok {
			return fmt.Errorf("public key is not Ed25519")
		}
		m.publicKey = edPub
	} else {
		// 从私钥提取公钥
		m.publicKey = edKey.Public().(ed25519.PublicKey)
	}

	return nil
}

// generateKeys 生成 Ed25519 密钥对（开发环境）
func (m *JWTManager) generateKeys() error {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return fmt.Errorf("generate Ed25519 key: %w", err)
	}
	m.privateKey = priv
	m.publicKey = pub
	return nil
}

// GenerateAccessToken 生成 Access Token
func (m *JWTManager) GenerateAccessToken(userID uuid.UUID, email string, emailVerified bool, scopes []string) (string, time.Time, error) {
	now := time.Now()
	expiresAt := now.Add(m.accessTTL)

	claims := CustomClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    m.issuer,
			Subject:   userID.String(),
			Audience:  jwt.ClaimStrings{"qoocloud", "qooeco"},
			ExpiresAt: jwt.NewNumericDate(expiresAt),
			IssuedAt:  jwt.NewNumericDate(now),
			ID:        "jti_" + uuid.New().String(),
		},
		Scopes:        scopes,
		Email:         email,
		EmailVerified: emailVerified,
	}

	token := jwt.NewWithClaims(jwt.SigningMethodEdDSA, claims)
	tokenStr, err := token.SignedString(m.privateKey)
	if err != nil {
		return "", time.Time{}, fmt.Errorf("crypto: sign token: %w", err)
	}

	return tokenStr, expiresAt, nil
}

// GenerateRefreshToken 生成 Refresh Token（不透明的随机字符串）
func (m *JWTManager) GenerateRefreshToken() (string, time.Time, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", time.Time{}, fmt.Errorf("crypto: generate refresh token: %w", err)
	}
	refreshToken := "rt_" + base64URLEncode(b)
	expiresAt := time.Now().Add(m.refreshTTL)
	return refreshToken, expiresAt, nil
}

// ValidateAccessToken 验证 Access Token 并返回 Claims
func (m *JWTManager) ValidateAccessToken(tokenStr string) (*CustomClaims, error) {
	token, err := jwt.ParseWithClaims(tokenStr, &CustomClaims{}, func(t *jwt.Token) (any, error) {
		if _, ok := t.Method.(*jwt.SigningMethodEd25519); !ok {
			return nil, fmt.Errorf("crypto: unexpected signing method: %v", t.Header["alg"])
		}
		return m.publicKey, nil
	}, jwt.WithIssuer(m.issuer), jwt.WithLeeway(30*time.Second))

	if err != nil {
		return nil, fmt.Errorf("crypto: parse token: %w", err)
	}

	claims, ok := token.Claims.(*CustomClaims)
	if !ok || !token.Valid {
		return nil, fmt.Errorf("crypto: invalid token claims")
	}

	return claims, nil
}

// base64URLEncode URL 安全的 Base64 编码
func base64URLEncode(data []byte) string {
	result := make([]byte, base64URLEncodedLen(len(data)))
	base64URLEncodeInto(result, data)
	return string(result)
}

// 简化的 base64 URL 编码（无 padding）
const base64URLChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

func base64URLEncodedLen(n int) int {
	return (n + 2) / 3 * 4
}

func base64URLEncodeInto(dst, src []byte) {
	di, si := 0, 0
	n := (len(src) / 3) * 3
	for si < n {
		val := uint(src[si])<<16 | uint(src[si+1])<<8 | uint(src[si+2])
		dst[di] = base64URLChars[val>>18&0x3F]
		dst[di+1] = base64URLChars[val>>12&0x3F]
		dst[di+2] = base64URLChars[val>>6&0x3F]
		dst[di+3] = base64URLChars[val&0x3F]
		si += 3
		di += 4
	}
	remain := len(src) - si
	if remain == 1 {
		val := uint(src[si]) << 16
		dst[di] = base64URLChars[val>>18&0x3F]
		dst[di+1] = base64URLChars[val>>12&0x3F]
	} else if remain == 2 {
		val := uint(src[si])<<16 | uint(src[si+1])<<8
		dst[di] = base64URLChars[val>>18&0x3F]
		dst[di+1] = base64URLChars[val>>12&0x3F]
		dst[di+2] = base64URLChars[val>>6&0x3F]
	}
}

// PublicKeyPEM 导出公钥为 PEM 格式
func (m *JWTManager) PublicKeyPEM() ([]byte, error) {
	pubBytes, err := x509.MarshalPKIXPublicKey(m.publicKey)
	if err != nil {
		return nil, fmt.Errorf("marshal public key: %w", err)
	}
	return pem.EncodeToMemory(&pem.Block{
		Type:  "PUBLIC KEY",
		Bytes: pubBytes,
	}), nil
}

// PrivateKeyPEM 导出私钥为 PEM 格式（生产环境不要使用）
func (m *JWTManager) PrivateKeyPEM() ([]byte, error) {
	privBytes, err := x509.MarshalPKCS8PrivateKey(m.privateKey)
	if err != nil {
		return nil, fmt.Errorf("marshal private key: %w", err)
	}
	return pem.EncodeToMemory(&pem.Block{
		Type:  "PRIVATE KEY",
		Bytes: privBytes,
	}), nil
}
