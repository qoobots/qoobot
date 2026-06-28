/*
 * qooauth_error.h — QooBot Device Auth SDK 错误码定义
 *
 * Copyright (c) 2026 QooBot Authors
 * Licensed under Apache License 2.0
 */
#ifndef QOOAUTH_ERROR_H
#define QOOAUTH_ERROR_H

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================
 * Error Codes
 * ======================================================================== */

typedef enum {
    QOOAUTH_OK = 0,

    /* General errors (1000-1099) */
    QOOAUTH_ERR_INVALID_ARG        = 1001,
    QOOAUTH_ERR_OUT_OF_MEMORY      = 1002,
    QOOAUTH_ERR_INTERNAL           = 1003,
    QOOAUTH_ERR_NOT_INITIALIZED    = 1004,
    QOOAUTH_ERR_BUFFER_TOO_SMALL   = 1005,
    QOOAUTH_ERR_NOT_SUPPORTED      = 1006,

    /* TLS errors (2000-2099) */
    QOOAUTH_ERR_TLS_INIT           = 2001,
    QOOAUTH_ERR_TLS_HANDSHAKE      = 2002,
    QOOAUTH_ERR_TLS_CERT_VERIFY    = 2003,
    QOOAUTH_ERR_TLS_CIPHER_MISMATCH= 2004,
    QOOAUTH_ERR_TLS_SESSION_EXPIRED= 2005,
    QOOAUTH_ERR_TLS_WRITE          = 2006,
    QOOAUTH_ERR_TLS_READ           = 2007,

    /* Certificate errors (3000-3099) */
    QOOAUTH_ERR_CERT_LOAD          = 3001,
    QOOAUTH_ERR_CERT_PARSE         = 3002,
    QOOAUTH_ERR_CERT_EXPIRED       = 3003,
    QOOAUTH_ERR_CERT_NOT_YET_VALID = 3004,
    QOOAUTH_ERR_CERT_REVOKED       = 3005,
    QOOAUTH_ERR_CERT_VERIFY_CHAIN  = 3006,
    QOOAUTH_ERR_CERT_KEY_MISMATCH  = 3007,
    QOOAUTH_ERR_CERT_SAVE          = 3008,
    QOOAUTH_ERR_CERT_GENERATE_KEY  = 3009,
    QOOAUTH_ERR_CERT_GENERATE_CSR  = 3010,
    QOOAUTH_ERR_CERT_RENEWAL_NEEDED= 3011,
    QOOAUTH_ERR_CERT_FINGERPRINT   = 3012,

    /* Secure storage errors (4000-4099) */
    QOOAUTH_ERR_STORAGE_OPEN       = 4001,
    QOOAUTH_ERR_STORAGE_READ       = 4002,
    QOOAUTH_ERR_STORAGE_WRITE      = 4003,
    QOOAUTH_ERR_STORAGE_INTEGRITY  = 4004,
    QOOAUTH_ERR_STORAGE_LOCKED     = 4005,
    QOOAUTH_ERR_STORAGE_NOT_FOUND  = 4006,
    QOOAUTH_ERR_STORAGE_PERMISSION = 4007,
    QOOAUTH_ERR_STORAGE_FULL       = 4008,

    /* Activation errors (5000-5099) */
    QOOAUTH_ERR_ACTIVATION_HTTP    = 5001,
    QOOAUTH_ERR_ACTIVATION_JSON    = 5002,
    QOOAUTH_ERR_ACTIVATION_REJECTED= 5003,
    QOOAUTH_ERR_ACTIVATION_TIMEOUT = 5004,
    QOOAUTH_ERR_ACTIVATION_CHALLENGE=5005,
    QOOAUTH_ERR_ACTIVATION_VERIFY  = 5006,
    QOOAUTH_ERR_ACTIVATION_RETRY   = 5007,
    QOOAUTH_ERR_ACTIVATION_MAX_ATTEMPTS=5008,

    /* Network errors (6000-6099) */
    QOOAUTH_ERR_NETWORK_CONNECT    = 6001,
    QOOAUTH_ERR_NETWORK_TIMEOUT    = 6002,
    QOOAUTH_ERR_NETWORK_DNS        = 6003,
    QOOAUTH_ERR_NETWORK_PROTOCOL   = 6004,
    QOOAUTH_ERR_NETWORK_HTTP_STATUS= 6005,

    /* Token errors (7000-7099) */
    QOOAUTH_ERR_TOKEN_EXPIRED      = 7001,
    QOOAUTH_ERR_TOKEN_INVALID      = 7002,
    QOOAUTH_ERR_TOKEN_REVOKED      = 7003,
} qooauth_error_t;

/**
 * Get a human-readable error message for a given error code.
 * Returns a statically-allocated string; do not free.
 */
const char* qooauth_strerror(qooauth_error_t err);

#ifdef __cplusplus
}
#endif

#endif /* QOOAUTH_ERROR_H */
