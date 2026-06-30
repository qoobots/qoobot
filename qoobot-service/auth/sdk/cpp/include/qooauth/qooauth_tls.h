/*
 * qooauth_tls.h — TLS 1.3 + mTLS 通信模块
 *
 * Copyright (c) 2026 QooBot Authors
 * Licensed under Apache License 2.0
 *
 * Provides a minimal, non-blocking-friendly TLS 1.3 client with mandatory
 * mutual authentication (mTLS). Built on mbedTLS 3.x.
 *
 * Design constraints (embedded-friendly):
 *   - Single-connection model (no thread pool — caller manages threads)
 *   - No malloc during handshake after config (pre-allocated I/O buffers)
 *   - Configurable heap usage via compile-time limits
 */
#ifndef QOOAUTH_TLS_H
#define QOOAUTH_TLS_H

#include "qooauth_error.h"
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================
 * Configuration
 * ======================================================================== */

/** TLS protocol version. */
typedef enum {
    QOOAUTH_TLS_V1_3_ONLY = 0,   /**< Enforce TLS 1.3 only */
    QOOAUTH_TLS_V1_2_MIN  = 1,   /**< TLS 1.2 minimum (allow 1.3) */
} qooauth_tls_version_t;

/** Cipher suite selection. */
typedef enum {
    QOOAUTH_CIPHER_DEFAULT = 0,       /**< P-256 + AES-256-GCM + SHA-384 */
    QOOAUTH_CIPHER_CONSTRAINED = 1,   /**< P-256 + AES-128-GCM + SHA-256 (smaller) */
} qooauth_tls_cipher_t;

/** Connection configuration. */
typedef struct {
    /** Server hostname (for SNI and certificate verification). */
    const char* server_name;

    /** Server port. */
    uint16_t port;

    /** TLS version constraint. */
    qooauth_tls_version_t tls_version;

    /** Cipher suite preference. */
    qooauth_tls_cipher_t cipher_suite;

    /* mTLS credentials (all PEM-encoded, null-terminated) */
    const char* device_cert_pem;     /**< Device X.509 certificate */
    const char* device_key_pem;      /**< Device EC private key (P-256) */
    const char* ca_bundle_pem;       /**< CA certificate bundle for server verification */

    /** Connection timeout in milliseconds. 0 = default (10000 ms). */
    uint32_t connect_timeout_ms;

    /** I/O timeout in milliseconds. 0 = default (5000 ms). */
    uint32_t io_timeout_ms;

    /** Maximum TLS record size. 0 = default (16384). */
    uint16_t max_record_size;
} qooauth_tls_config_t;

/* ========================================================================
 * Opaque handle
 * ======================================================================== */

typedef struct qooauth_tls_connection qooauth_tls_connection_t;

/* ========================================================================
 * Lifecycle
 * ======================================================================== */

/**
 * Create a TLS connection object. Does not connect yet.
 *
 * @param config  Connection configuration (copied).
 * @param out     Output handle (caller must call qooauth_tls_disconnect + destroy).
 */
qooauth_error_t qooauth_tls_init(
    const qooauth_tls_config_t* config,
    qooauth_tls_connection_t**  out
);

/**
 * Connect and perform TLS 1.3 handshake with mutual authentication.
 *
 * The server's certificate is verified against the CA bundle.
 * The device presents its certificate for server-side mTLS validation.
 *
 * @param conn  Initialized connection handle.
 */
qooauth_error_t qooauth_tls_connect(qooauth_tls_connection_t* conn);

/**
 * Check if the connection is established and alive.
 *
 * @return 1 if connected, 0 otherwise.
 */
int qooauth_tls_is_connected(const qooauth_tls_connection_t* conn);

/**
 * Disconnect and perform orderly TLS shutdown.
 */
void qooauth_tls_disconnect(qooauth_tls_connection_t* conn);

/**
 * Destroy the connection handle and free all resources.
 */
void qooauth_tls_destroy(qooauth_tls_connection_t* conn);

/* ========================================================================
 * I/O
 * ======================================================================== */

/**
 * Write data over the TLS connection.
 *
 * @param conn    Connected TLS connection.
 * @param data    Data to send.
 * @param len     Length of data.
 * @param written Actual bytes written (can be NULL).
 */
qooauth_error_t qooauth_tls_write(
    qooauth_tls_connection_t* conn,
    const uint8_t*            data,
    size_t                    len,
    size_t*                   written
);

/**
 * Read data from the TLS connection.
 *
 * @param conn   Connected TLS connection.
 * @param buf    Buffer to read into.
 * @param size   Buffer size.
 * @param nread  Actual bytes read (can be NULL).
 */
qooauth_error_t qooauth_tls_read(
    qooauth_tls_connection_t* conn,
    uint8_t*                  buf,
    size_t                    size,
    size_t*                   nread
);

/* ========================================================================
 * Information
 * ======================================================================== */

/**
 * Get the negotiated TLS version string (e.g., "TLSv1.3").
 */
const char* qooauth_tls_get_version(const qooauth_tls_connection_t* conn);

/**
 * Get the negotiated cipher suite name (e.g., "TLS_AES_256_GCM_SHA384").
 */
const char* qooauth_tls_get_cipher(const qooauth_tls_connection_t* conn);

/**
 * Get the server certificate's SHA-256 fingerprint (hex string, 64 chars).
 * Call after successful connection.
 *
 * @param buf   Output buffer (at least 65 bytes for hex + null terminator).
 * @param size  Buffer size.
 */
qooauth_error_t qooauth_tls_get_server_fingerprint(
    qooauth_tls_connection_t* conn,
    char*                     buf,
    size_t                    size
);

/**
 * Get the raw socket file descriptor (for integration with event loops).
 * Returns -1 if not connected.
 */
int qooauth_tls_get_fd(const qooauth_tls_connection_t* conn);

#ifdef __cplusplus
}
#endif

#endif /* QOOAUTH_TLS_H */
