// Package auth TOTP 二因素认证
package auth

import (
	"crypto/hmac"
	"crypto/sha1"
	"encoding/binary"
	"fmt"
	"time"
)

// TOTPConfig TOTP 配置
type TOTPConfig struct {
	Issuer      string
	AccountName string
	Period      int64 // 时间窗口（秒）
	Digits      int   // 验证码位数
}

// DefaultTOTPConfig 默认 TOTP 配置
func DefaultTOTPConfig(issuer, accountName string) TOTPConfig {
	return TOTPConfig{
		Issuer:      issuer,
		AccountName: accountName,
		Period:      30,
		Digits:      6,
	}
}

// TOTP 服务
type TOTP struct {
	cfg TOTPConfig
}

// NewTOTP 创建 TOTP 服务
func NewTOTP(cfg TOTPConfig) *TOTP {
	return &TOTP{cfg: cfg}
}

// GenerateCode 生成当前 TOTP 验证码
func (t *TOTP) GenerateCode(secret string) (string, error) {
	return t.generateCodeAt(secret, time.Now().Unix())
}

// ValidateCode 验证 TOTP 验证码（容差 ±1 个时间窗口）
func (t *TOTP) ValidateCode(secret, code string) bool {
	now := time.Now().Unix()
	// 检查当前窗口
	if expected, _ := t.generateCodeAt(secret, now); expected == code {
		return true
	}
	// 检查前一个窗口
	if expected, _ := t.generateCodeAt(secret, now-t.cfg.Period); expected == code {
		return true
	}
	// 检查后一个窗口
	if expected, _ := t.generateCodeAt(secret, now+t.cfg.Period); expected == code {
		return true
	}
	return false
}

// GenerateProvisioningURI 生成用于二维码的配置 URI
func (t *TOTP) GenerateProvisioningURI(secret string) string {
	return fmt.Sprintf("otpauth://totp/%s:%s?secret=%s&issuer=%s&algorithm=SHA1&digits=%d&period=%d",
		t.cfg.Issuer, t.cfg.AccountName, secret, t.cfg.Issuer, t.cfg.Digits, t.cfg.Period)
}

// generateCodeAt 在指定时间生成 TOTP 验证码
func (t *TOTP) generateCodeAt(secret string, timestamp int64) (string, error) {
	counter := uint64(timestamp / t.cfg.Period)

	// HMAC-SHA1
	mac := hmac.New(sha1.New, base32Decode(secret))
	if err := binary.Write(mac, binary.BigEndian, counter); err != nil {
		return "", fmt.Errorf("totp: write counter: %w", err)
	}
	hash := mac.Sum(nil)

	// 动态截断
	offset := hash[len(hash)-1] & 0x0F
	binary := binary.BigEndian.Uint32(hash[offset:offset+4]) & 0x7FFFFFFF
	otp := binary % uint32(pow10(t.cfg.Digits))

	return fmt.Sprintf("%0*d", t.cfg.Digits, otp), nil
}

// base32Decode 简单 Base32 解码
func base32Decode(s string) []byte {
	const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
	charToVal := make(map[byte]byte)
	for i := range alphabet {
		charToVal[alphabet[i]] = byte(i)
	}

	var result []byte
	var buffer uint64
	var bitsLeft uint

	for i := 0; i < len(s); i++ {
		if s[i] == '=' {
			break
		}
		val, ok := charToVal[s[i]]
		if !ok {
			continue
		}
		buffer = (buffer << 5) | uint64(val)
		bitsLeft += 5
		if bitsLeft >= 8 {
			bitsLeft -= 8
			result = append(result, byte(buffer>>bitsLeft))
		}
	}
	return result
}

func pow10(n int) int {
	result := 1
	for i := 0; i < n; i++ {
		result *= 10
	}
	return result
}
