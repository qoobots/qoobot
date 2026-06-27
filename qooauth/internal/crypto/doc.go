package crypto

// Package doc for crypto package
//
// 本包提供 qooauth 所有加密原语：
//   - hash.go: argon2id 密码哈希与验证
//   - jwt.go: Ed25519 JWT 签发与验证
//   - symmetric.go: AES-256-GCM 对称加密
//   - asymmetric.go: Ed25519 签名 + X.509 证书
//   - key_derivation.go: HKDF + SHA-512/256 + HMAC
//   - random.go: CSPRNG 随机数生成
//   - hsm.go: HSM 抽象接口
