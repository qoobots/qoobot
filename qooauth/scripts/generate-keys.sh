#!/bin/bash
# ============================================================
# qooauth Key Generation Script
# ============================================================
# Generates cryptographic keys for qooauth services:
#   - Ed25519 key pair for token signing
#   - ECDSA P-256 key pair for developer certificates
#   - RSA 2048 key pair for mTLS CA
#   - HMAC key for API key derivation
#
# Requires: openssl
#
# Usage: ./generate-keys.sh [output_dir]
#   output_dir  Directory to store generated keys (default: ../certs)
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:-${SCRIPT_DIR}/../certs}"

mkdir -p "${OUTPUT_DIR}"

echo "============================================"
echo "  qooauth Cryptographic Key Generation"
echo "============================================"
echo "Output directory: ${OUTPUT_DIR}"
echo "============================================"

# Function to check OpenSSL availability
check_openssl() {
    if ! command -v openssl &> /dev/null; then
        echo "ERROR: OpenSSL not found. Please install OpenSSL."
        exit 1
    fi
    echo "OpenSSL version: $(openssl version)"
}

# ============================================
# 1. Ed25519 Key Pair (for JWT token signing)
# ============================================
generate_ed25519_keys() {
    echo ""
    echo "[1/5] Generating Ed25519 key pair for JWT signing..."

    # Ed25519 private key
    openssl genpkey -algorithm Ed25519 \
        -out "${OUTPUT_DIR}/ed25519_private.pem" 2>/dev/null

    # Extract public key
    openssl pkey -in "${OUTPUT_DIR}/ed25519_private.pem" \
        -pubout -out "${OUTPUT_DIR}/ed25519_public.pem" 2>/dev/null

    # Generate JWK representation (simplified - in production use a proper JWK library)
    echo "  -> Ed25519 keys generated:"
    echo "     Private: ${OUTPUT_DIR}/ed25519_private.pem"
    echo "     Public:  ${OUTPUT_DIR}/ed25519_public.pem"

    # Set secure permissions
    chmod 600 "${OUTPUT_DIR}/ed25519_private.pem"
    chmod 644 "${OUTPUT_DIR}/ed25519_public.pem"
}

# ============================================
# 2. ECDSA P-256 Key Pair (for developer certs)
# ============================================
generate_ecdsa_keys() {
    echo ""
    echo "[2/5] Generating ECDSA P-256 key pair for developer certificates..."

    # ECDSA private key (secp256r1 = P-256)
    openssl ecparam -genkey -name prime256v1 -noout \
        -out "${OUTPUT_DIR}/ecdsa_p256_private.pem" 2>/dev/null

    # Extract public key
    openssl ec -in "${OUTPUT_DIR}/ecdsa_p256_private.pem" \
        -pubout -out "${OUTPUT_DIR}/ecdsa_p256_public.pem" 2>/dev/null

    echo "  -> ECDSA P-256 keys generated:"
    echo "     Private: ${OUTPUT_DIR}/ecdsa_p256_private.pem"
    echo "     Public:  ${OUTPUT_DIR}/ecdsa_p256_public.pem"

    chmod 600 "${OUTPUT_DIR}/ecdsa_p256_private.pem"
    chmod 644 "${OUTPUT_DIR}/ecdsa_p256_public.pem"
}

# ============================================
# 3. RSA 2048 CA Key Pair (for mTLS)
# ============================================
generate_mtls_ca_keys() {
    echo ""
    echo "[3/5] Generating RSA 2048 CA key pair for mTLS..."

    # CA private key
    openssl genrsa -out "${OUTPUT_DIR}/mtls_ca_private.pem" 2048 2>/dev/null

    # Self-signed CA certificate (valid for 10 years)
    openssl req -new -x509 -days 3650 \
        -key "${OUTPUT_DIR}/mtls_ca_private.pem" \
        -out "${OUTPUT_DIR}/mtls_ca_cert.pem" \
        -subj "/C=CN/O=QooBot/CN=QooAuth mTLS CA" 2>/dev/null

    echo "  -> mTLS CA keys generated:"
    echo "     Private Key:  ${OUTPUT_DIR}/mtls_ca_private.pem"
    echo "     Certificate:  ${OUTPUT_DIR}/mtls_ca_cert.pem"

    chmod 600 "${OUTPUT_DIR}/mtls_ca_private.pem"
    chmod 644 "${OUTPUT_DIR}/mtls_ca_cert.pem"
}

# ============================================
# 4. HMAC Secret Key (for API key derivation)
# ============================================
generate_hmac_key() {
    echo ""
    echo "[4/5] Generating HMAC secret for API key derivation..."

    # Generate 64-byte random key and base64 encode
    openssl rand -base64 64 > "${OUTPUT_DIR}/hmac_secret.key"

    echo "  -> HMAC secret generated:"
    echo "     Secret: ${OUTPUT_DIR}/hmac_secret.key"

    chmod 600 "${OUTPUT_DIR}/hmac_secret.key"
}

# ============================================
# 5. Generate .env file with key references
# ============================================
generate_env_file() {
    echo ""
    echo "[5/5] Generating environment configuration..."

    local env_file="${OUTPUT_DIR}/../.env.keys"
    local ed25519_priv_b64=$(base64 -w 0 "${OUTPUT_DIR}/ed25519_private.pem" 2>/dev/null || base64 "${OUTPUT_DIR}/ed25519_private.pem")
    local hmac_key_b64=$(base64 -w 0 "${OUTPUT_DIR}/hmac_secret.key" 2>/dev/null || base64 "${OUTPUT_DIR}/hmac_secret.key")

    cat > "${env_file}" << EOF
# ============================================
# qooauth Cryptographic Key Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# ============================================
# IMPORTANT: Keep this file secure. Do not commit to version control.
# For production, use a secrets manager (Vault, AWS KMS, etc.)

# Ed25519 key for JWT signing
JWT_SIGNING_KEY=${ed25519_priv_b64}

# ECDSA P-256 key for developer certificates
DEVELOPER_SIGNING_KEY_PATH=${OUTPUT_DIR}/ecdsa_p256_private.pem

# mTLS CA certificate
MTLS_CA_CERT_PATH=${OUTPUT_DIR}/mtls_ca_cert.pem
MTLS_CA_KEY_PATH=${OUTPUT_DIR}/mtls_ca_private.pem

# HMAC secret for API key derivation
API_KEY_DERIVATION_SECRET=${hmac_key_b64}

# Collaboration delegation secret
COLLABORATION_DELEGATION_SECRET=${hmac_key_b64}
EOF

    chmod 600 "${env_file}"

    echo "  -> Environment config generated: ${env_file}"
}

# ============================================
# Main execution
# ============================================
check_openssl
generate_ed25519_keys
generate_ecdsa_keys
generate_mtls_ca_keys
generate_hmac_key
generate_env_file

echo ""
echo "============================================"
echo "  Key generation complete!"
echo "  All keys stored in: ${OUTPUT_DIR}"
echo ""
echo "  Generated keys:"
echo "    - ed25519_private.pem / ed25519_public.pem"
echo "    - ecdsa_p256_private.pem / ecdsa_p256_public.pem"
echo "    - mtls_ca_private.pem / mtls_ca_cert.pem"
echo "    - hmac_secret.key"
echo ""
echo "  IMPORTANT:"
echo "    - Keep private keys secure and never commit them"
echo "    - Use a secrets manager in production"
echo "    - Rotate keys regularly per security policy"
echo "============================================"
