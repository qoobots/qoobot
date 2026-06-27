package crypto

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"io"
)

// EncryptAESGCM 使用 AES-256-GCM 加密数据
// 返回 base64 编码的密文（包含 nonce）
func EncryptAESGCM(plaintext []byte, key []byte) (string, error) {
	if len(key) != 32 {
		return "", fmt.Errorf("crypto: AES-256 requires 32-byte key, got %d", len(key))
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return "", fmt.Errorf("crypto: create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", fmt.Errorf("crypto: create GCM: %w", err)
	}

	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", fmt.Errorf("crypto: generate nonce: %w", err)
	}

	// 密文 = nonce + ciphertext
	ciphertext := gcm.Seal(nonce, nonce, plaintext, nil)
	return base64.RawStdEncoding.EncodeToString(ciphertext), nil
}

// DecryptAESGCM 使用 AES-256-GCM 解密数据
// 输入 base64 编码的密文（包含 nonce）
func DecryptAESGCM(encodedCiphertext string, key []byte) ([]byte, error) {
	if len(key) != 32 {
		return nil, fmt.Errorf("crypto: AES-256 requires 32-byte key, got %d", len(key))
	}

	ciphertext, err := base64.RawStdEncoding.DecodeString(encodedCiphertext)
	if err != nil {
		return nil, fmt.Errorf("crypto: decode ciphertext: %w", err)
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("crypto: create cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("crypto: create GCM: %w", err)
	}

	nonceSize := gcm.NonceSize()
	if len(ciphertext) < nonceSize {
		return nil, fmt.Errorf("crypto: ciphertext too short")
	}

	nonce, ciphertext := ciphertext[:nonceSize], ciphertext[nonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return nil, fmt.Errorf("crypto: decrypt: %w", err)
	}

	return plaintext, nil
}

// GenerateAESKey 生成 AES-256 密钥
func GenerateAESKey() ([]byte, error) {
	key := make([]byte, 32)
	if _, err := io.ReadFull(rand.Reader, key); err != nil {
		return nil, fmt.Errorf("crypto: generate AES key: %w", err)
	}
	return key, nil
}
