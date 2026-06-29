/*
 * qooauth_device_auth.h — 设备认证高层 API
 *
 * Copyright (c) 2026 QooBot Authors
 * Licensed under Apache License 2.0
 *
 * This is the primary public API for device authentication. It orchestrates:
 *   - Secure storage for keys and certificates
 *   - TLS 1.3 + mTLS connections to QooAuth services
 *   - Device activation lifecycle
 *   - Certificate renewal
 *   - Token management
 *
 * Typical usage:
 *   ┌──────────────────────────────────────────────────┐
 *   │ 1. qooauth_device_init(config)                   │
 *   │ 2. qooauth_device_activate()   // first boot     │
 *   │    or qooauth_device_load()     // subsequent boot│
 *   │ 3. qooauth_device_connect()     // mTLS connect  │
 *   │ 4. qooauth_device_get_token()   // get JWT       │
 *   │ 5. ... use the connection for API calls ...      │
 *   │ 6. qooauth_device_destroy()                      │
 *   └──────────────────────────────────────────────────┘
 */
#ifndef QOOAUTH_DEVICE_AUTH_H
#define QOOAUTH_DEVICE_AUTH_H

#include "qooauth_error.h"
#include "qooauth_tls.h"
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================
 * Configuration
 * ======================================================================== */

typedef struct {
    /** QooAuth server base URL. */
    const char* auth_server_url;

    /** Device serial number (hardware-bound, unique per device). */
    const char* device_serial;

    /** Hardware model string. */
    const char* hardware_model;

    /** Root directory for secure storage. NULL = default. */
    const char* storage_root;

    /** Platform-derived encryption key for secure storage (32 bytes). */
    const uint8_t* storage_key;

    /** Length of storage_key (32 for AES-256). */
    size_t storage_key_len;

    /** CA bundle PEM for server verification. If NULL, uses bundled CA. */
    const char* ca_bundle_pem;

    /** Certificate renewal threshold in days (default: 30). */
    int renewal_threshold_days;

    /** TLS version constraint. */
    qooauth_tls_version_t tls_version;

    /** Cipher suite preference. */
    qooauth_tls_cipher_t cipher_suite;
} qooauth_device_config_t;

/* ========================================================================
 * Opaque handle
 * ======================================================================== */

typedef struct qooauth_device qooauth_device_t;

/* ========================================================================
 * Lifecycle
 * ======================================================================== */

/**
 * Initialize the device authentication context.
 *
 * This loads existing credentials from secure storage if available,
 * or prepares for first-time activation.
 *
 * @param config  Device configuration.
 * @param out     Output handle.
 */
qooauth_error_t qooauth_device_init(
    const qooauth_device_config_t* config,
    qooauth_device_t**             out
);

/**
 * Destroy the device authentication context.
 * Securely zeros all sensitive material and closes connections.
 */
void qooauth_device_destroy(qooauth_device_t* dev);

/* ========================================================================
 * Activation (first boot)
 * ======================================================================== */

/**
 * Check if the device has been activated.
 *
 * @return 1 if activated (has valid certificate), 0 otherwise.
 */
int qooauth_device_is_activated(const qooauth_device_t* dev);

/**
 * Run the device activation flow.
 *
 * Only needed on first boot. Generates a bootstrap key, contacts the
 * QooAuth server, completes the challenge-response protocol, and stores
 * the operational certificate in secure storage.
 *
 * @param dev              Initialized device context.
 * @param activation_token User-provided activation token (from app/web).
 *                         NULL if using device-side-only activation.
 */
qooauth_error_t qooauth_device_activate(
    qooauth_device_t* dev,
    const char*       activation_token
);

/* ========================================================================
 * Connection
 * ======================================================================== */

/**
 * Establish an mTLS connection to the QooAuth server.
 *
 * The device presents its operational certificate and the server is
 * verified against the CA bundle.
 *
 * @param dev  Initialized and activated device context.
 */
qooauth_error_t qooauth_device_connect(qooauth_device_t* dev);

/**
 * Check if the mTLS connection is alive.
 */
int qooauth_device_is_connected(const qooauth_device_t* dev);

/**
 * Disconnect from the QooAuth server.
 */
void qooauth_device_disconnect(qooauth_device_t* dev);

/* ========================================================================
 * Token management
 * ======================================================================== */

/**
 * Get a device JWT from the QooAuth server.
 *
 * Uses the mTLS connection for authentication. The token is cached
 * and reused until near expiry.
 *
 * @param dev          Connected device context.
 * @param out_token    Output buffer for JWT.
 * @param buf_size     Buffer size.
 * @param out_len      Actual bytes written (can be NULL).
 */
qooauth_error_t qooauth_device_get_token(
    qooauth_device_t* dev,
    char*             out_token,
    size_t            buf_size,
    size_t*           out_len
);

/**
 * Check if the cached device token is still valid.
 *
 * @return 1 if valid, 0 if expired or not yet obtained.
 */
int qooauth_device_is_token_valid(const qooauth_device_t* dev);

/**
 * Force refresh the device token.
 */
qooauth_error_t qooauth_device_refresh_token(qooauth_device_t* dev);

/* ========================================================================
 * Certificate management
 * ======================================================================== */

/**
 * Check if the device certificate needs renewal and trigger if necessary.
 *
 * @param dev  Device context.
 * @param out_renewed  1 if a renewal was performed, 0 otherwise.
 */
qooauth_error_t qooauth_device_check_renewal(
    qooauth_device_t* dev,
    int*              out_renewed
);

/**
 * Force certificate renewal (generate new CSR, submit, store).
 */
qooauth_error_t qooauth_device_renew_certificate(qooauth_device_t* dev);

/* ========================================================================
 * Information
 * ======================================================================== */

/**
 * Get the device ID.
 */
const char* qooauth_device_get_id(const qooauth_device_t* dev);

/**
 * Get the device serial number.
 */
const char* qooauth_device_get_serial(const qooauth_device_t* dev);

/**
 * Get the TLS connection handle (for advanced use).
 * Returns NULL if not connected.
 */
qooauth_tls_connection_t* qooauth_device_get_tls_connection(
    const qooauth_device_t* dev
);

/**
 * Get the last error message (human-readable).
 */
const char* qooauth_device_get_last_error(const qooauth_device_t* dev);

#ifdef __cplusplus
}
#endif

#endif /* QOOAUTH_DEVICE_AUTH_H */
