// Package crypto 提供 qooauth 所有加密原语，包括密码哈希、JWT 签发/验证、
// 对称/非对称加密、密钥派生、X.509 证书管理及 HSM 抽象接口。
package crypto

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"fmt"

	"golang.org/x/crypto/argon2"
)

// Argon2Params 定义 argon2id 哈希参数
type Argon2Params struct {
	Memory      uint32 // 内存占用 (KB)
	Iterations  uint32 // 迭代次数
	Parallelism uint8  // 并行度
	SaltLen     uint32 // 盐长度 (bytes)
	KeyLen      uint32 // 输出密钥长度 (bytes)
}

// DefaultArgon2Params 返回 OWASP 推荐的 argon2id 参数
func DefaultArgon2Params() Argon2Params {
	return Argon2Params{
		Memory:      64 * 1024, // 64 MB
		Iterations:  3,
		Parallelism: 4,
		SaltLen:     32,
		KeyLen:      32,
	}
}

// HashPassword 使用 argon2id 对密码进行哈希
// 返回格式: $argon2id$v=19$m=65536,t=3,p=4$<salt_b64>$<hash_b64>
func HashPassword(password string) (string, error) {
	return HashPasswordWithParams(password, DefaultArgon2Params())
}

// HashPasswordWithParams 使用自定义参数对密码进行哈希
func HashPasswordWithParams(password string, params Argon2Params) (string, error) {
	salt := make([]byte, params.SaltLen)
	if _, err := rand.Read(salt); err != nil {
		return "", fmt.Errorf("crypto: generate salt: %w", err)
	}

	hash := argon2.IDKey(
		[]byte(password),
		salt,
		params.Iterations,
		params.Memory,
		params.Parallelism,
		params.KeyLen,
	)

	encoded := fmt.Sprintf(
		"$argon2id$v=19$m=%d,t=%d,p=%d$%s$%s",
		params.Memory,
		params.Iterations,
		params.Parallelism,
		base64.RawStdEncoding.EncodeToString(salt),
		base64.RawStdEncoding.EncodeToString(hash),
	)

	return encoded, nil
}

// VerifyPassword 验证密码是否与 argon2id 哈希匹配
// 使用 constant-time 比较防止时序攻击
func VerifyPassword(password, encodedHash string) (bool, error) {
	params, salt, hash, err := decodeArgon2Hash(encodedHash)
	if err != nil {
		return false, fmt.Errorf("crypto: decode hash: %w", err)
	}

	computed := argon2.IDKey(
		[]byte(password),
		salt,
		params.Iterations,
		params.Memory,
		params.Parallelism,
		params.KeyLen,
	)

	return subtle.ConstantTimeCompare(hash, computed) == 1, nil
}

// decodeArgon2Hash 解析 argon2id 哈希字符串
// 格式: $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
func decodeArgon2Hash(encoded string) (Argon2Params, []byte, []byte, error) {
	var params Argon2Params
	var version int

	_, err := fmt.Sscanf(
		encoded,
		"$argon2id$v=%d$m=%d,t=%d,p=%d$",
		&version,
		&params.Memory,
		&params.Iterations,
		&params.Parallelism,
	)
	if err != nil {
		return params, nil, nil, fmt.Errorf("crypto: invalid hash format: %w", err)
	}

	// 手动解析剩余部分（salt 和 hash 是 base64 编码的）
	rest := encoded[fmt.Sprintf("$argon2id$v=%d$m=%d,t=%d,p=%d$", version, params.Memory, params.Iterations, params.Parallelism):]
	if len(rest) == 0 {
		return params, nil, nil, fmt.Errorf("crypto: truncated hash")
	}

	// 找到 salt 和 hash 的分隔符
	saltEnd := 0
	for i, c := range rest {
		if c == '$' {
			saltEnd = i
			break
		}
	}
	if saltEnd == 0 || saltEnd >= len(rest)-1 {
		return params, nil, nil, fmt.Errorf("crypto: malformed hash, missing separator")
	}

	saltB64 := rest[:saltEnd]
	hashB64 := rest[saltEnd+1:]

	salt, err := base64.RawStdEncoding.DecodeString(saltB64)
	if err != nil {
		return params, nil, nil, fmt.Errorf("crypto: decode salt: %w", err)
	}

	hash, err := base64.RawStdEncoding.DecodeString(hashB64)
	if err != nil {
		return params, nil, nil, fmt.Errorf("crypto: decode hash: %w", err)
	}

	params.SaltLen = uint32(len(salt))
	params.KeyLen = uint32(len(hash))

	return params, salt, hash, nil
}
