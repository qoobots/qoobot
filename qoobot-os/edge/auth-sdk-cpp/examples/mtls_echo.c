/*
 * mtls_echo.c — mTLS 连接测试示例
 *
 * Demonstrates low-level TLS 1.3 mTLS connectivity.
 *
 * Build: cmake .. && make mtls_echo
 * Usage: ./mtls_echo <host> <port> <cert.pem> <key.pem> <ca.pem>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qooauth/qooauth_tls.h"
#include "qooauth/qooauth_cert_manager.h"

static char* read_file_content(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = (char*)malloc((size_t)size + 1);
    if (!buf) { fclose(f); return NULL; }
    size_t nread = fread(buf, 1, (size_t)size, f);
    fclose(f);
    buf[nread] = '\0';
    return buf;
}

int main(int argc, char* argv[]) {
    if (argc < 6) {
        fprintf(stderr, "Usage: %s <host> <port> <cert.pem> <key.pem> <ca.pem>\n", argv[0]);
        return 1;
    }

    const char* host = argv[1];
    uint16_t port    = (uint16_t)atoi(argv[2]);

    char* cert_pem = read_file_content(argv[3]);
    char* key_pem  = read_file_content(argv[4]);
    char* ca_pem   = read_file_content(argv[5]);

    if (!cert_pem || !key_pem || !ca_pem) {
        fprintf(stderr, "Failed to read PEM files\n");
        free(cert_pem); free(key_pem); free(ca_pem);
        return 1;
    }

    printf("=== QooBot mTLS Echo Test ===\n");
    printf("Target: %s:%u\n\n", host, port);

    /* Configure TLS */
    qooauth_tls_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.server_name     = host;
    cfg.port            = port;
    cfg.tls_version     = QOOAUTH_TLS_V1_3_ONLY;
    cfg.cipher_suite    = QOOAUTH_CIPHER_DEFAULT;
    cfg.device_cert_pem = cert_pem;
    cfg.device_key_pem  = key_pem;
    cfg.ca_bundle_pem   = ca_pem;

    /* Connect */
    qooauth_tls_connection_t* conn = NULL;
    qooauth_error_t err = qooauth_tls_init(&cfg, &conn);
    if (err != QOOAUTH_OK) {
        fprintf(stderr, "TLS init failed: %s\n", qooauth_strerror(err));
        goto cleanup;
    }

    err = qooauth_tls_connect(conn);
    if (err != QOOAUTH_OK) {
        fprintf(stderr, "TLS connect failed: %s\n", qooauth_strerror(err));
        qooauth_tls_destroy(conn);
        goto cleanup;
    }

    printf("[OK] TLS connected\n");
    printf("     Version: %s\n", qooauth_tls_get_version(conn));
    printf("     Cipher:  %s\n", qooauth_tls_get_cipher(conn));

    char fp[65];
    if (qooauth_tls_get_server_fingerprint(conn, fp, sizeof(fp)) == QOOAUTH_OK) {
        printf("     Server:  %s\n", fp);
    }

    /* Echo test */
    const char* msg = "Hello from QooBot device!";
    printf("\n[>>] Sending: %s\n", msg);

    err = qooauth_tls_write(conn, (const uint8_t*)msg, strlen(msg), NULL);
    if (err != QOOAUTH_OK) {
        fprintf(stderr, "Write failed: %s\n", qooauth_strerror(err));
    } else {
        uint8_t buf[4096];
        size_t nread;
        err = qooauth_tls_read(conn, buf, sizeof(buf) - 1, &nread);
        if (err == QOOAUTH_OK) {
            buf[nread] = '\0';
            printf("[<<] Received: %s\n", buf);
        } else {
            fprintf(stderr, "Read failed: %s\n", qooauth_strerror(err));
        }
    }

    qooauth_tls_disconnect(conn);
    qooauth_tls_destroy(conn);
    printf("\n[OK] Disconnected.\n");

cleanup:
    free(cert_pem);
    free(key_pem);
    free(ca_pem);
    return 0;
}
