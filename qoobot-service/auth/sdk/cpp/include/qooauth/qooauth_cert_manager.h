/*
 * qooauth_cert_manager.h — X.509 设备证书管理模块
 *
 * Copyright (c) 2026 QooBot Authors
 * Licensed under Apache License 2.0
 *
 * Manages the device certificate lifecycle:
 *   - ECDSA P-256 key pair generation
 *   - CSR generation for certificate renewal
 *   - Certificate loading, parsing, validation
 *   - Expiry monitoring and auto-renewal triggers
 *   - CRL fetching and cache management
 *
 * Dependencies: mbedTLS (crypto, x509)
 */
#ifndef QOOAUTH_CERT_MANAGER_H
#define QOOAUTH_CERT_MANAGER_H

#include "qooauth_error.h"
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================
 * Key types
 * ======================================================================== */

/** Supported key algorithms. */
typedef enum {
    QOOAUTH_KEY_EC_P256 = 0,   /**< ECDSA P-256 (NIST secp256r1 / prime256v1) */
    QOOAUTH_KEY_EC_P384 = 1,   /**< ECDSA P-384 (NIST secp384r1) */
} qooauth_key_type_t;

/* ========================================================================
 * Certificate info
 * ======================================================================== */

typedef struct {
    char     subject_dn[256];       /**< X.509 Subject DN */
    char     issuer_dn[256];        /**< X.509 Issuer DN */
    char     serial_number[64];     /**< Hex serial number */
    char     fingerprint[65];       /**< SHA-256 fingerprint (hex, 64 chars) */
    int64_t  not_before;            /**< Unix timestamp */
    int64_t  not_after;             /**< Unix timestamp */
    char     key_algorithm[32];     /**< e.g., "ECDSA_P256" */
    int      is_ca;                 /**< 1 if CA certificate */
} qooauth_cert_info_t;

/* ========================================================================
 * Key generation
 * ======================================================================== */

/**
 * Generate an ECDSA key pair.
 *
 * @param key_type    Key algorithm.
 * @param out_key_pem Output buffer for PEM-encoded private key.
 * @param key_buf_size Size of out_key_pem buffer.
 * @param out_key_len  Actual bytes written.
 * @param out_pub_pem  Output buffer for PEM-encoded public key (can be NULL).
 * @param pub_buf_size Size of out_pub_pem buffer.
 * @param out_pub_len  Actual bytes written (can be NULL).
 */
qooauth_error_t qooauth_cert_generate_key_pair(
    qooauth_key_type_t key_type,
    char*              out_key_pem,
    size_t             key_buf_size,
    size_t*            out_key_len,
    char*              out_pub_pem,
    size_t             pub_buf_size,
    size_t*            out_pub_len
);

/* ========================================================================
 * CSR generation
 * ======================================================================== */

/**
 * Generate a PKCS#10 CSR for certificate renewal.
 *
 * @param key_pem        Device private key (PEM).
 * @param key_len        Length of key_pem.
 * @param subject_dn     Subject DN (e.g., "CN=dev_abc123,OU=QooBot Devices,O=QooBot").
 * @param out_csr_pem    Output buffer for PEM-encoded CSR.
 * @param csr_buf_size   Size of out_csr_pem buffer.
 * @param out_csr_len    Actual bytes written.
 */
qooauth_error_t qooauth_cert_generate_csr(
    const char* key_pem,
    size_t      key_len,
    const char* subject_dn,
    char*       out_csr_pem,
    size_t      csr_buf_size,
    size_t*     out_csr_len
);

/* ========================================================================
 * Certificate parsing
 * ======================================================================== */

/**
 * Parse an X.509 certificate (PEM or DER).
 *
 * @param cert_pem  Certificate in PEM or DER format.
 * @param cert_len  Length of cert_pem.
 * @param out_info  Output certificate information.
 */
qooauth_error_t qooauth_cert_parse(
    const uint8_t*       cert_pem,
    size_t               cert_len,
    qooauth_cert_info_t* out_info
);

/**
 * Verify a certificate against a CA bundle.
 *
 * @param cert_pem      Certificate to verify (PEM).
 * @param cert_len      Length of cert_pem.
 * @param ca_bundle_pem CA certificate bundle (PEM, can contain multiple certs).
 * @param ca_bundle_len Length of ca_bundle_pem.
 * @param verify_time   Unix timestamp for verification (0 = now).
 */
qooauth_error_t qooauth_cert_verify(
    const uint8_t* cert_pem,
    size_t         cert_len,
    const char*    ca_bundle_pem,
    size_t         ca_bundle_len,
    int64_t        verify_time
);

/**
 * Check if a certificate matches a private key.
 *
 * @param cert_pem  Certificate (PEM).
 * @param cert_len  Length of cert_pem.
 * @param key_pem   Private key (PEM).
 * @param key_len   Length of key_pem.
 * @return QOOAUTH_OK if they match, QOOAUTH_ERR_CERT_KEY_MISMATCH otherwise.
 */
qooauth_error_t qooauth_cert_check_key_match(
    const uint8_t* cert_pem,
    size_t         cert_len,
    const char*    key_pem,
    size_t         key_len
);

/* ========================================================================
 * Expiry monitoring
 * ======================================================================== */

/**
 * Check if a certificate needs renewal.
 *
 * @param cert_pem          Certificate (PEM).
 * @param cert_len          Length of cert_pem.
 * @param renewal_threshold_days  Days before expiry to trigger renewal.
 * @param out_needs_renewal 1 if renewal is recommended, 0 otherwise.
 * @param out_days_remaining Days until expiry (can be NULL).
 */
qooauth_error_t qooauth_cert_check_renewal(
    const uint8_t* cert_pem,
    size_t         cert_len,
    int            renewal_threshold_days,
    int*           out_needs_renewal,
    int*           out_days_remaining
);

/* ========================================================================
 * CRL
 * ======================================================================== */

/**
 * Parse and cache a CRL.
 *
 * @param crl_der   CRL in DER format.
 * @param crl_len   Length of crl_der.
 */
qooauth_error_t qooauth_cert_parse_crl(
    const uint8_t* crl_der,
    size_t         crl_len
);

/**
 * Check if a certificate serial number appears in the cached CRL.
 *
 * @param serial_hex  Certificate serial number (hex string).
 * @param out_revoked 1 if revoked, 0 if not found.
 */
qooauth_error_t qooauth_cert_check_revoked(
    const char* serial_hex,
    int*        out_revoked
);

/**
 * Clear the in-memory CRL cache.
 */
void qooauth_cert_clear_crl_cache(void);

/* ========================================================================
 * Utility
 * ======================================================================== */

/**
 * Compute SHA-256 fingerprint of a certificate.
 *
 * @param cert_der  Certificate in DER format.
 * @param cert_len  Length of cert_der.
 * @param out_hex   Output hex string (at least 65 bytes).
 * @param out_size  Buffer size.
 */
qooauth_error_t qooauth_cert_compute_fingerprint(
    const uint8_t* cert_der,
    size_t         cert_len,
    char*          out_hex,
    size_t         out_size
);

/**
 * Extract public key from certificate (PEM format).
 *
 * @param cert_pem    Certificate (PEM).
 * @param cert_len    Length of cert_pem.
 * @param out_pub_pem Output buffer for public key PEM.
 * @param buf_size    Buffer size.
 * @param out_len     Actual bytes written (can be NULL).
 */
qooauth_error_t qooauth_cert_extract_public_key(
    const uint8_t* cert_pem,
    size_t         cert_len,
    char*          out_pub_pem,
    size_t         buf_size,
    size_t*        out_len
);

#ifdef __cplusplus
}
#endif

#endif /* QOOAUTH_CERT_MANAGER_H */
