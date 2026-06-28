/*
 * qooauth_secure_storage.h — 安全存储模块
 *
 * Copyright (c) 2026 QooBot Authors
 * Licensed under Apache License 2.0
 *
 * Provides AES-256-GCM encrypted key/cert storage with integrity protection.
 *
 * Storage layout:
 *   ~/.qoobot/keys/{device_id}.pem      — Device private key (encrypted)
 *   ~/.qoobot/certs/{device_id}.pem     — Device certificate
 *   ~/.qoobot/certs/ca_bundle.pem       — CA certificate bundle
 *   ~/.qoobot/state/{device_id}.json    — Device state (activation info)
 *
 * All sensitive material stored in ~/.qoobot/keys/ is encrypted with a
 * platform-derived key (HW-bound on TPM-capable devices).
 */
#ifndef QOOAUTH_SECURE_STORAGE_H
#define QOOAUTH_SECURE_STORAGE_H

#include "qooauth_error.h"
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================
 * Opaque handle
 * ======================================================================== */

typedef struct qooauth_storage qooauth_storage_t;

/* ========================================================================
 * Initialization
 * ======================================================================== */

/**
 * Initialize secure storage.
 *
 * @param storage_root  Root directory for storage. If NULL, defaults to
 *                      $HOME/.qoobot or platform-appropriate location.
 * @param platform_key  Platform-derived encryption key (32 bytes for AES-256).
 *                      If NULL and TPM is available, a TPM-bound key is used.
 *                      Otherwise, a software-derived key from device identity.
 * @param key_len       Length of platform_key in bytes (must be 32 if non-NULL).
 * @param out           Output handle (caller must call qooauth_storage_destroy).
 * @return QOOAUTH_OK on success.
 */
qooauth_error_t qooauth_storage_init(
    const char*    storage_root,
    const uint8_t* platform_key,
    size_t         key_len,
    qooauth_storage_t** out
);

/**
 * Destroy the storage handle and securely zero sensitive memory.
 */
void qooauth_storage_destroy(qooauth_storage_t* s);

/* ========================================================================
 * Key Storage
 * ======================================================================== */

/**
 * Store an encrypted device private key.
 *
 * @param device_id  Device identifier (e.g., "dev_abc123").
 * @param key_pem    Private key in PEM format.
 * @param key_len    Length of key_pem.
 */
qooauth_error_t qooauth_storage_store_key(
    qooauth_storage_t* s,
    const char*        device_id,
    const char*        key_pem,
    size_t             key_len
);

/**
 * Load a device private key (decrypted).
 *
 * @param device_id  Device identifier.
 * @param out_buf    Output buffer for PEM key.
 * @param buf_size   Size of out_buf.
 * @param out_len    Actual bytes written (can be NULL).
 */
qooauth_error_t qooauth_storage_load_key(
    qooauth_storage_t* s,
    const char*        device_id,
    char*              out_buf,
    size_t             buf_size,
    size_t*            out_len
);

/**
 * Delete a device private key (secure overwrite + unlink).
 */
qooauth_error_t qooauth_storage_delete_key(
    qooauth_storage_t* s,
    const char*        device_id
);

/* ========================================================================
 * Certificate Storage
 * ======================================================================== */

/**
 * Store a device certificate (not encrypted — certs are public).
 */
qooauth_error_t qooauth_storage_store_cert(
    qooauth_storage_t* s,
    const char*        device_id,
    const char*        cert_pem,
    size_t             cert_len
);

/**
 * Load a device certificate.
 */
qooauth_error_t qooauth_storage_load_cert(
    qooauth_storage_t* s,
    const char*        device_id,
    char*              out_buf,
    size_t             buf_size,
    size_t*            out_len
);

/**
 * Store the CA certificate bundle.
 */
qooauth_error_t qooauth_storage_store_ca_bundle(
    qooauth_storage_t* s,
    const char*        ca_bundle_pem,
    size_t             ca_bundle_len
);

/**
 * Load the CA certificate bundle.
 */
qooauth_error_t qooauth_storage_load_ca_bundle(
    qooauth_storage_t* s,
    char*              out_buf,
    size_t             buf_size,
    size_t*            out_len
);

/* ========================================================================
 * Device State Storage
 * ======================================================================== */

/**
 * Store device activation state (JSON).
 * Contains: device_id, activation_token, binding_info, activation_time.
 */
qooauth_error_t qooauth_storage_store_state(
    qooauth_storage_t* s,
    const char*        device_id,
    const char*        state_json,
    size_t             state_len
);

/**
 * Load device activation state (JSON).
 */
qooauth_error_t qooauth_storage_load_state(
    qooauth_storage_t* s,
    const char*        device_id,
    char*              out_buf,
    size_t             buf_size,
    size_t*            out_len
);

/**
 * Delete device state.
 */
qooauth_error_t qooauth_storage_delete_state(
    qooauth_storage_t* s,
    const char*        device_id
);

/* ========================================================================
 * Utility
 * ======================================================================== */

/**
 * Check if a device has stored credentials (key + cert).
 *
 * @return 1 if complete, 0 if incomplete or missing.
 */
int qooauth_storage_has_credentials(
    qooauth_storage_t* s,
    const char*        device_id
);

/**
 * List all registered device IDs.
 *
 * @param out_ids    Array of device_id strings (caller must free each and the array).
 * @param out_count  Number of device IDs found.
 */
qooauth_error_t qooauth_storage_list_devices(
    qooauth_storage_t* s,
    char***            out_ids,
    size_t*            out_count
);

/**
 * Free a device ID list returned by qooauth_storage_list_devices.
 */
void qooauth_storage_free_device_list(char** ids, size_t count);

#ifdef __cplusplus
}
#endif

#endif /* QOOAUTH_SECURE_STORAGE_H */
