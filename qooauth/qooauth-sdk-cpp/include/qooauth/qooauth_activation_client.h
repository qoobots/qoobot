/*
 * qooauth_activation_client.h — 设备激活 HTTP 客户端
 *
 * Copyright (c) 2026 QooBot Authors
 * Licensed under Apache License 2.0
 *
 * Implements the QooBot device activation protocol:
 *   1. POST /api/v1/auth/device-activations/initiate  (user-initiated via token)
 *   2. POST /api/v1/auth/device-activations/{id}/challenge
 *   3. POST /api/v1/auth/device-activations/{id}/verify   (signed nonce)
 *
 * The device must have a bootstrap certificate for initial authentication.
 */
#ifndef QOOAUTH_ACTIVATION_CLIENT_H
#define QOOAUTH_ACTIVATION_CLIENT_H

#include "qooauth_error.h"
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================
 * Configuration
 * ======================================================================== */

typedef struct {
    /** QooAuth server base URL (e.g., "https://id.qoobot.com"). */
    const char* auth_server_url;

    /** Device serial number (hardware-bound). */
    const char* device_serial;

    /** Hardware model identifier (e.g., "QooBot-One-v2"). */
    const char* hardware_model;

    /** Bootstrap certificate PEM (for initial authentication). */
    const char* bootstrap_cert_pem;

    /** Bootstrap private key PEM (for challenge signing). */
    const char* bootstrap_key_pem;

    /** CA bundle PEM for server certificate verification. */
    const char* ca_bundle_pem;

    /** Request timeout in seconds. 0 = default (30). */
    uint32_t timeout_seconds;
} qooauth_activation_config_t;

/* ========================================================================
 * Result types
 * ======================================================================== */

/** Activation result. */
typedef struct {
    int         success;            /**< 1 if activation succeeded */
    char        activation_id[128]; /**< Activation session ID */
    char        device_id[64];      /**< Assigned device ID */
    char        cert_pem[8192];     /**< Operational certificate PEM */
    char        cert_id[64];        /**< Certificate ID */
    char        binding_token[256]; /**< Binding token for future use */
    int64_t     expires_at;         /**< Certificate expiry (Unix timestamp) */
    char        error_code[32];     /**< Server error code if !success */
    char        error_message[512]; /**< Error description if !success */
} qooauth_activation_result_t;

/** Challenge information. */
typedef struct {
    char        activation_id[128];
    char        nonce_hex[128];     /**< Challenge nonce (hex) */
    char        algorithm[32];      /**< "ECDSA_P256_SHA256" */
    int64_t     expires_at;         /**< Challenge expiry (Unix timestamp) */
} qooauth_challenge_t;

/* ========================================================================
 * Activation flow
 * ======================================================================== */

/**
 * Step 1: Initiate device activation.
 *
 * Sends device serial, hardware model, and bootstrap certificate to the
 * QooAuth server. The server creates an activation session and returns
 * an activation ID + encrypted activation token.
 *
 * @param config  Activation configuration.
 * @param out     Output result (contains activation_id on success).
 */
qooauth_error_t qooauth_activation_initiate(
    const qooauth_activation_config_t* config,
    qooauth_activation_result_t*       out
);

/**
 * Step 2: Request a cryptographic challenge.
 *
 * The server issues a random nonce. The device must sign this nonce
 * with its bootstrap private key to prove key possession.
 *
 * @param config        Activation configuration.
 * @param activation_id Activation ID from step 1.
 * @param out           Output challenge.
 */
qooauth_error_t qooauth_activation_request_challenge(
    const qooauth_activation_config_t* config,
    const char*                        activation_id,
    qooauth_challenge_t*               out
);

/**
 * Step 3: Submit signed challenge response.
 *
 * Signs the challenge nonce with the bootstrap private key and sends
 * it to the server. On success, the server issues an operational
 * certificate and revokes the bootstrap certificate.
 *
 * @param config        Activation configuration.
 * @param activation_id Activation ID.
 * @param challenge     Challenge from step 2.
 * @param out           Output result (contains operational cert).
 */
qooauth_error_t qooauth_activation_verify(
    const qooauth_activation_config_t* config,
    const char*                        activation_id,
    const qooauth_challenge_t*         challenge,
    qooauth_activation_result_t*       out
);

/**
 * Convenience: Run the full activation flow in one call.
 *
 * This is the recommended API for most use cases. It performs:
 *   1. Initiate → 2. Challenge → 3. Sign → 4. Verify
 * with retry logic for transient errors.
 *
 * @param config  Activation configuration.
 * @param out     Output result.
 */
qooauth_error_t qooauth_activation_run(
    const qooauth_activation_config_t* config,
    qooauth_activation_result_t*       out
);

/* ========================================================================
 * Revocation
 * ======================================================================== */

/**
 * Revoke a device activation (unbind from QooBot ID).
 *
 * @param config    Activation configuration.
 * @param device_id Device ID to revoke.
 * @param cert_id   Certificate ID to revoke (can be NULL).
 * @param reason    Revocation reason (human-readable).
 */
qooauth_error_t qooauth_activation_revoke(
    const qooauth_activation_config_t* config,
    const char*                        device_id,
    const char*                        cert_id,
    const char*                        reason
);

#ifdef __cplusplus
}
#endif

#endif /* QOOAUTH_ACTIVATION_CLIENT_H */
