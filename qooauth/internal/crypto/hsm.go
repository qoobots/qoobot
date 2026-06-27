package crypto

import "crypto"

// HSMSigner HSM 签名器抽象接口
// 生产环境使用 PKCS#11 连接硬件 HSM，
// 开发环境使用 SoftHSM 本地密钥。
type HSMSigner interface {
	// Sign 使用 HSM 内密钥对数据进行签名
	Sign(data []byte) ([]byte, error)

	// PublicKey 返回对应的公钥
	PublicKey() crypto.PublicKey

	// KeyID 返回 HSM 内密钥标识符
	KeyID() string

	// Close 释放 HSM 连接资源
	Close() error
}

// HSMKeyManager HSM 密钥管理器抽象接口
type HSMKeyManager interface {
	// GenerateKey 生成密钥对并存储在 HSM 内
	GenerateKey(label string) (string, error) // 返回 keyID

	// GetSigner 获取指定 keyID 的签名器
	GetSigner(keyID string) (HSMSigner, error)

	// DeleteKey 删除 HSM 内指定密钥
	DeleteKey(keyID string) error

	// ListKeys 列出 HSM 内所有密钥标签
	ListKeys() ([]string, error)

	// Close 释放 HSM 连接
	Close() error
}
