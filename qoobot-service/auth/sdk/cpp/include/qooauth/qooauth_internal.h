/*
 * qooauth_internal.h — SDK 内部私有头文件
 *
 * Copyright (c) 2026 QooBot Authors
 * Licensed under Apache License 2.0
 *
 * NOT part of the public API. Do not include from application code.
 */
#ifndef QOOAUTH_INTERNAL_H
#define QOOAUTH_INTERNAL_H

#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* ========================================================================
 * Compile-time constants
 * ======================================================================== */

#define QOOAUTH_MAX_CERT_PEM        8192
#define QOOAUTH_MAX_KEY_PEM         4096
#define QOOAUTH_MAX_CSR_PEM         4096
#define QOOAUTH_MAX_HTTP_BODY       32768
#define QOOAUTH_MAX_HTTP_HEADERS    64
#define QOOAUTH_MAX_HEADER_LEN      256
#define QOOAUTH_MAX_URL_LEN         2048
#define QOOAUTH_MAX_DN_LEN          256
#define QOOAUTH_MAX_SERIAL_LEN      64
#define QOOAUTH_MAX_FINGERPRINT_LEN 65
#define QOOAUTH_NONCE_LEN           48
#define QOOAUTH_AES_KEY_LEN         32
#define QOOAUTH_AES_IV_LEN          12
#define QOOAUTH_AES_TAG_LEN         16
#define QOOAUTH_DEFAULT_CONNECT_TIMEOUT_MS 10000
#define QOOAUTH_DEFAULT_IO_TIMEOUT_MS      5000
#define QOOAUTH_DEFAULT_ACTIVATION_TIMEOUT_S 30
#define QOOAUTH_DEFAULT_RENEWAL_THRESHOLD_DAYS 30
#define QOOAUTH_MAX_ACTIVATION_ATTEMPTS    5

/* ========================================================================
 * Secure zeroing
 * ======================================================================== */

/**
 * Securely zero a memory buffer (resistant to compiler optimization).
 */
static inline void qooauth_secure_zero(void* ptr, size_t len) {
    volatile uint8_t* p = (volatile uint8_t*)ptr;
    while (len--) *p++ = 0;
}

/* ========================================================================
 * String helpers
 * ======================================================================== */

/**
 * Safe string copy with truncation detection.
 * Returns the number of characters copied (excluding null terminator),
 * or -1 if truncated.
 */
static inline int qooauth_strncpy_safe(char* dst, const char* src, size_t dst_size) {
    if (!dst || !src || dst_size == 0) return -1;
    size_t i;
    for (i = 0; i < dst_size - 1 && src[i]; i++) {
        dst[i] = src[i];
    }
    dst[i] = '\0';
    return (src[i] != '\0') ? -1 : (int)i;
}

/* ========================================================================
 * Hex encoding/decoding
 * ======================================================================== */

/**
 * Encode binary data as hex. out must be at least len * 2 + 1.
 */
void qooauth_bin2hex(const uint8_t* in, size_t len, char* out);

/**
 * Decode hex string to binary. Returns number of bytes decoded, or -1 on error.
 */
int qooauth_hex2bin(const char* hex, uint8_t* out, size_t out_size);

/* ========================================================================
 * Base64 (URL-safe, no padding)
 * ======================================================================== */

int qooauth_base64url_encode(const uint8_t* in, size_t in_len,
                              char* out, size_t out_size);
int qooauth_base64url_decode(const char* in,
                              uint8_t* out, size_t out_size);

#endif /* QOOAUTH_INTERNAL_H */
