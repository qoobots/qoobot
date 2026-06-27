package crypto

import (
	"crypto/hmac"
	"crypto/sha256"
	"crypto/sha512"
	"encoding/hex"
	"fmt"
	"hash"
	"io"

	"golang.org/x/crypto/hkdf"
)

// HKDFDerive 使用 HKDF-SHA512 从主密钥派生子密钥
// info: 上下文信息（如 "jwt-signing", "user-encryption"）
// length: 派生密钥长度
func HKDFDerive(masterKey []byte, salt []byte, info string, length int) ([]byte, error) {
	reader := hkdf.New(sha512.New, masterKey, salt, []byte(info))
	derived := make([]byte, length)
	if _, err := io.ReadFull(reader, derived); err != nil {
		return nil, fmt.Errorf("crypto: HKDF derive: %w", err)
	}
	return derived, nil
}

// SHA256Hash 计算 SHA-256 哈希
func SHA256Hash(data []byte) string {
	h := sha256.Sum256(data)
	return hex.EncodeToString(h[:])
}

// SHA512Hash 计算 SHA-512 哈希
func SHA512Hash(data []byte) string {
	h := sha512.Sum512(data)
	return hex.EncodeToString(h[:])
}

// SHA512HashHex 计算 SHA-512 哈希（返回 hex 字符串）
func SHA512HashHex(data []byte) string {
	return SHA512Hash(data)
}

// HMACSHA256 计算 HMAC-SHA256
func HMACSHA256(key, data []byte) ([]byte, error) {
	return hmacHash(sha256.New, key, data)
}

// HMACSHA512 计算 HMAC-SHA512
func HMACSHA512(key, data []byte) ([]byte, error) {
	return hmacHash(sha512.New, key, data)
}

func hmacHash(h func() hash.Hash, key, data []byte) ([]byte, error) {
	mac := hmac.New(h, key)
	if _, err := mac.Write(data); err != nil {
		return nil, fmt.Errorf("crypto: HMAC write: %w", err)
	}
	return mac.Sum(nil), nil
}

// ConstantTimeCompare 常量时间比较，防止时序攻击
func ConstantTimeCompare(a, b []byte) bool {
	if len(a) != len(b) {
		return false
	}
	result := byte(0)
	for i := 0; i < len(a); i++ {
		result |= a[i] ^ b[i]
	}
	return result == 0
}
