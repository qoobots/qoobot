package crypto

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
)

// GenerateRandomBytes 生成加密安全的随机字节
func GenerateRandomBytes(length int) ([]byte, error) {
	b := make([]byte, length)
	if _, err := io.ReadFull(rand.Reader, b); err != nil {
		return nil, fmt.Errorf("crypto: generate random bytes: %w", err)
	}
	return b, nil
}

// GenerateRandomHex 生成随机 hex 字符串
func GenerateRandomHex(length int) (string, error) {
	// hex 编码会使长度翻倍，所以需要 length/2 的随机字节
	b, err := GenerateRandomBytes(length / 2)
	if err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

// GenerateToken 生成不透明 Token（用于 Refresh Token / API Key）
func GenerateToken(prefix string, byteLength int) (string, error) {
	b, err := GenerateRandomBytes(byteLength)
	if err != nil {
		return "", err
	}
	return prefix + hex.EncodeToString(b), nil
}

// GenerateTOTPSecret 生成 TOTP 密钥（Base32 编码的 20 字节随机数）
func GenerateTOTPSecret() (string, error) {
	b, err := GenerateRandomBytes(20)
	if err != nil {
		return "", err
	}
	return base32Encode(b), nil
}

// base32Encode 简单的 Base32 编码（RFC 4648，大写，无 padding）
func base32Encode(data []byte) string {
	const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
	var result []byte
	for i := 0; i < len(data); i += 5 {
		var buffer uint64
		var bits int
		for j := 0; j < 5 && i+j < len(data); j++ {
			buffer = (buffer << 8) | uint64(data[i+j])
			bits += 8
		}
		for bits >= 5 {
			bits -= 5
			result = append(result, alphabet[(buffer>>bits)&0x1F])
		}
	}
	return string(result)
}
