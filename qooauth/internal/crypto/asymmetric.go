package crypto

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha512"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"time"
)

// GenerateEd25519KeyPair 生成 Ed25519 密钥对
func GenerateEd25519KeyPair() (ed25519.PublicKey, ed25519.PrivateKey, error) {
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, nil, fmt.Errorf("crypto: generate Ed25519 key pair: %w", err)
	}
	return pub, priv, nil
}

// SignEd25519 使用 Ed25519 签名数据
func SignEd25519(privateKey ed25519.PrivateKey, message []byte) []byte {
	return ed25519.Sign(privateKey, message)
}

// VerifyEd25519 验证 Ed25519 签名
func VerifyEd25519(publicKey ed25519.PublicKey, message, signature []byte) bool {
	return ed25519.Verify(publicKey, message, signature)
}

// CertificateRequest X.509 证书请求参数
type CertificateRequest struct {
	SerialNumber *big.Int
	CommonName   string
	Organization []string
	Country      []string
	NotBefore    time.Time
	NotAfter     time.Time
	DNSNames     []string
}

// GenerateSelfSignedCert 生成自签名 X.509 证书
func GenerateSelfSignedCert(req CertificateRequest) (certPEM, keyPEM []byte, certFingerprint string, err error) {
	pub, priv, err := GenerateEd25519KeyPair()
	if err != nil {
		return nil, nil, "", err
	}

	if req.SerialNumber == nil {
		req.SerialNumber = big.NewInt(time.Now().UnixNano())
	}
	if req.NotBefore.IsZero() {
		req.NotBefore = time.Now()
	}
	if req.NotAfter.IsZero() {
		req.NotAfter = req.NotBefore.Add(2 * 365 * 24 * time.Hour) // 2 年有效期
	}

	template := &x509.Certificate{
		SerialNumber: req.SerialNumber,
		Subject: pkix.Name{
			CommonName:   req.CommonName,
			Organization: req.Organization,
			Country:      req.Country,
		},
		NotBefore:             req.NotBefore,
		NotAfter:              req.NotAfter,
		KeyUsage:              x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth, x509.ExtKeyUsageServerAuth},
		BasicConstraintsValid: true,
		DNSNames:              req.DNSNames,
	}

	certBytes, err := x509.CreateCertificate(rand.Reader, template, template, pub, priv)
	if err != nil {
		return nil, nil, "", fmt.Errorf("crypto: create certificate: %w", err)
	}

	certPEM = pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: certBytes})

	privBytes, err := x509.MarshalPKCS8PrivateKey(priv)
	if err != nil {
		return nil, nil, "", fmt.Errorf("crypto: marshal private key: %w", err)
	}
	keyPEM = pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: privBytes})

	// SHA-256 指纹
	fingerprint := sha512.Sum512_256(certBytes)
	certFingerprint = fmt.Sprintf("%x", fingerprint)

	return certPEM, keyPEM, certFingerprint, nil
}

// ParseCertificate 从 PEM 解析 X.509 证书
func ParseCertificate(certPEM []byte) (*x509.Certificate, error) {
	block, _ := pem.Decode(certPEM)
	if block == nil {
		return nil, fmt.Errorf("crypto: decode certificate PEM")
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("crypto: parse certificate: %w", err)
	}
	return cert, nil
}

// ComputeCertFingerprint 计算证书 SHA-256 指纹
func ComputeCertFingerprint(cert *x509.Certificate) string {
	fp := sha512.Sum512_256(cert.Raw)
	return fmt.Sprintf("%x", fp)
}
