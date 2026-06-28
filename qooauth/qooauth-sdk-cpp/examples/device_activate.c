/*
 * device_activate.c — QooBot 设备激活示例
 *
 * Demonstrates the full device activation flow using the QooAuth C SDK.
 *
 * Build: cmake .. && make device_activate
 * Usage: ./device_activate [device_serial]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qooauth/qooauth.h"

static const char* CA_BUNDLE =
    "-----BEGIN CERTIFICATE-----\n"
    "MIID... (insert your CA certificate here) ...\n"
    "-----END CERTIFICATE-----\n";

int main(int argc, char* argv[]) {
    const char* serial = (argc > 1) ? argv[1] : "QBT-TEST-0001";

    printf("=== QooBot Device Activation Example ===\n");
    printf("SDK Version: %s\n", QOOAUTH_SDK_VERSION);
    printf("Device Serial: %s\n\n", serial);

    /* Step 1: Initialize device authentication context */
    qooauth_device_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.auth_server_url       = "https://id.qoobot.com";
    cfg.device_serial         = serial;
    cfg.hardware_model        = "QooBot-One-v2";
    cfg.storage_root          = NULL; /* Use default ~/.qoobot */
    cfg.storage_key           = NULL; /* Use platform-derived key */
    cfg.storage_key_len       = 0;
    cfg.ca_bundle_pem         = CA_BUNDLE;
    cfg.renewal_threshold_days = 30;
    cfg.tls_version           = QOOAUTH_TLS_V1_3_ONLY;
    cfg.cipher_suite          = QOOAUTH_CIPHER_DEFAULT;

    qooauth_device_t* dev = NULL;
    qooauth_error_t err = qooauth_device_init(&cfg, &dev);
    if (err != QOOAUTH_OK) {
        fprintf(stderr, "Init failed: %s\n", qooauth_strerror(err));
        return 1;
    }
    printf("[OK] Device context initialized\n");

    /* Step 2: Check activation status */
    if (qooauth_device_is_activated(dev)) {
        printf("[OK] Device already activated: %s\n", qooauth_device_get_id(dev));
    } else {
        printf("[..] Device not activated. Starting activation flow...\n");

        err = qooauth_device_activate(dev, NULL);
        if (err != QOOAUTH_OK) {
            fprintf(stderr, "Activation failed: %s\n", qooauth_strerror(err));
            fprintf(stderr, "Last error: %s\n", qooauth_device_get_last_error(dev));
            qooauth_device_destroy(dev);
            return 1;
        }

        printf("[OK] Device activated successfully!\n");
        printf("     Device ID: %s\n", qooauth_device_get_id(dev));
    }

    /* Step 3: Connect to QooAuth server via mTLS */
    printf("[..] Establishing mTLS connection...\n");
    err = qooauth_device_connect(dev);
    if (err != QOOAUTH_OK) {
        fprintf(stderr, "Connect failed: %s\n", qooauth_strerror(err));
        qooauth_device_destroy(dev);
        return 1;
    }

    qooauth_tls_connection_t* tls = qooauth_device_get_tls_connection(dev);
    if (tls) {
        printf("[OK] TLS connected: %s / %s\n",
               qooauth_tls_get_version(tls),
               qooauth_tls_get_cipher(tls));

        char fingerprint[65];
        if (qooauth_tls_get_server_fingerprint(tls, fingerprint, sizeof(fingerprint))
            == QOOAUTH_OK) {
            printf("     Server fingerprint: %s\n", fingerprint);
        }
    }

    /* Step 4: Get device token */
    printf("[..] Obtaining device token...\n");
    char token[4096];
    size_t token_len;
    err = qooauth_device_get_token(dev, token, sizeof(token), &token_len);
    if (err == QOOAUTH_OK) {
        printf("[OK] Token obtained (%zu bytes)\n", token_len);
        printf("     Token valid: %s\n",
               qooauth_device_is_token_valid(dev) ? "yes" : "no");
    } else {
        fprintf(stderr, "Token error: %s\n", qooauth_strerror(err));
    }

    /* Step 5: Check certificate renewal */
    int renewed = 0;
    err = qooauth_device_check_renewal(dev, &renewed);
    if (err == QOOAUTH_OK) {
        printf("[OK] Certificate %s\n", renewed ? "renewed" : "up-to-date");
    }

    /* Cleanup */
    printf("\n[..] Disconnecting...\n");
    qooauth_device_destroy(dev);
    printf("[OK] Done.\n");

    return 0;
}
