/*
 * qooauth_tls.c — TLS 1.3 + mTLS 实现 (mbedTLS 3.x)
 *
 * Implements TLS 1.3 mutual authentication with:
 *   - ECDSA P-256 client certificate
 *   - Server certificate verification against CA bundle
 *   - Minimum TLS 1.2, preferred TLS 1.3
 *   - AES-256-GCM / AES-128-GCM cipher suites
 */
#include "qooauth/qooauth_tls.h"
#include "qooauth/qooauth_internal.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>

#include <mbedtls/ssl.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/entropy.h>
#include <mbedtls/error.h>
#include <mbedtls/debug.h>
#include <mbedtls/pem.h>

/* ========================================================================
 * Internal structure
 * ======================================================================== */

struct qooauth_tls_connection {
    qooauth_tls_config_t config;

    /* Owned copies of PEM strings */
    char device_cert[QOOAUTH_MAX_CERT_PEM];
    char device_key[QOOAUTH_MAX_KEY_PEM];
    char ca_bundle[QOOAUTH_MAX_CERT_PEM];

    /* mbedTLS contexts */
    mbedtls_ssl_context        ssl;
    mbedtls_ssl_config         ssl_conf;
    mbedtls_x509_crt           client_cert;
    mbedtls_pk_context         client_key;
    mbedtls_x509_crt           ca_certs;
    mbedtls_ctr_drbg_context   drbg;
    mbedtls_entropy_context    entropy;

    /* Network */
    int sock_fd;
    int connected;
    int handshake_done;

    /* Negotiated info */
    char negotiated_version[16];
    char negotiated_cipher[64];
    char server_fingerprint[65];

    /* I/O timeouts */
    uint32_t connect_timeout_ms;
    uint32_t io_timeout_ms;
};

/* ========================================================================
 * Default cipher suites
 * ======================================================================== */

static const int default_ciphers[] = {
    MBEDTLS_TLS1_3_AES_256_GCM_SHA384,
    MBEDTLS_TLS1_3_AES_128_GCM_SHA256,
    MBEDTLS_TLS1_3_CHACHA20_POLY1305_SHA256,
    0
};

static const int constrained_ciphers[] = {
    MBEDTLS_TLS1_3_AES_128_GCM_SHA256,
    MBEDTLS_TLS1_3_AES_256_GCM_SHA384,
    0
};

/* ========================================================================
 * Debug callback (optional)
 * ======================================================================== */

#if 0
static void tls_debug_callback(void* ctx, int level,
                                const char* file, int line, const char* str) {
    ((void)ctx); ((void)level);
    fprintf(stderr, "mbedTLS [%s:%d]: %s", file, line, str);
}
#endif

/* ========================================================================
 * Lifecycle
 * ======================================================================== */

qooauth_error_t qooauth_tls_init(
    const qooauth_tls_config_t* config,
    qooauth_tls_connection_t**  out)
{
    if (!config || !out) return QOOAUTH_ERR_INVALID_ARG;
    if (!config->server_name || !config->device_cert_pem
        || !config->device_key_pem || !config->ca_bundle_pem)
        return QOOAUTH_ERR_INVALID_ARG;

    qooauth_tls_connection_t* conn = (qooauth_tls_connection_t*)calloc(1, sizeof(*conn));
    if (!conn) return QOOAUTH_ERR_OUT_OF_MEMORY;

    conn->sock_fd = -1;
    conn->connected = 0;
    conn->handshake_done = 0;

    /* Copy config */
    conn->config = *config;
    qooauth_strncpy_safe(conn->device_cert, config->device_cert_pem, sizeof(conn->device_cert));
    qooauth_strncpy_safe(conn->device_key,  config->device_key_pem,  sizeof(conn->device_key));
    qooauth_strncpy_safe(conn->ca_bundle,   config->ca_bundle_pem,   sizeof(conn->ca_bundle));

    conn->connect_timeout_ms = config->connect_timeout_ms
        ? config->connect_timeout_ms : QOOAUTH_DEFAULT_CONNECT_TIMEOUT_MS;
    conn->io_timeout_ms = config->io_timeout_ms
        ? config->io_timeout_ms : QOOAUTH_DEFAULT_IO_TIMEOUT_MS;

    /* Initialize mbedTLS contexts */
    mbedtls_ssl_init(&conn->ssl);
    mbedtls_ssl_config_init(&conn->ssl_conf);
    mbedtls_x509_crt_init(&conn->client_cert);
    mbedtls_pk_init(&conn->client_key);
    mbedtls_x509_crt_init(&conn->ca_certs);
    mbedtls_ctr_drbg_init(&conn->drbg);
    mbedtls_entropy_init(&conn->entropy);

    /* Seed RNG */
    int ret = mbedtls_ctr_drbg_seed(&conn->drbg, mbedtls_entropy_func,
                                     &conn->entropy, NULL, 0);
    if (ret != 0) {
        qooauth_tls_destroy(conn);
        return QOOAUTH_ERR_TLS_INIT;
    }

    /* Parse client certificate */
    ret = mbedtls_x509_crt_parse(&conn->client_cert,
                                  (const uint8_t*)conn->device_cert,
                                  strlen(conn->device_cert) + 1);
    if (ret != 0) {
        qooauth_tls_destroy(conn);
        return QOOAUTH_ERR_CERT_PARSE;
    }

    /* Parse client private key */
    ret = mbedtls_pk_parse_key(&conn->client_key,
                                (const uint8_t*)conn->device_key,
                                strlen(conn->device_key) + 1, NULL, 0,
                                mbedtls_ctr_drbg_random, &conn->drbg);
    if (ret != 0) {
        qooauth_tls_destroy(conn);
        return QOOAUTH_ERR_CERT_PARSE;
    }

    /* Parse CA certificates */
    ret = mbedtls_x509_crt_parse(&conn->ca_certs,
                                  (const uint8_t*)conn->ca_bundle,
                                  strlen(conn->ca_bundle) + 1);
    if (ret != 0) {
        qooauth_tls_destroy(conn);
        return QOOAUTH_ERR_CERT_LOAD;
    }

    /* Configure TLS */
    ret = mbedtls_ssl_config_defaults(&conn->ssl_conf,
                                       MBEDTLS_SSL_IS_CLIENT,
                                       MBEDTLS_SSL_TRANSPORT_STREAM,
                                       MBEDTLS_SSL_PRESET_DEFAULT);
    if (ret != 0) {
        qooauth_tls_destroy(conn);
        return QOOAUTH_ERR_TLS_INIT;
    }

    /* Set TLS version */
    if (config->tls_version == QOOAUTH_TLS_V1_3_ONLY) {
        mbedtls_ssl_conf_min_tls_version(&conn->ssl_conf, MBEDTLS_SSL_VERSION_TLS1_3);
        mbedtls_ssl_conf_max_tls_version(&conn->ssl_conf, MBEDTLS_SSL_VERSION_TLS1_3);
    } else {
        mbedtls_ssl_conf_min_tls_version(&conn->ssl_conf, MBEDTLS_SSL_VERSION_TLS1_2);
    }

    /* Set cipher suites */
    const int* ciphers = (config->cipher_suite == QOOAUTH_CIPHER_CONSTRAINED)
                         ? constrained_ciphers : default_ciphers;
    mbedtls_ssl_conf_ciphersuites(&conn->ssl_conf, ciphers);

    /* Set auth mode: require server cert AND send client cert (mTLS) */
    mbedtls_ssl_conf_authmode(&conn->ssl_conf, MBEDTLS_SSL_VERIFY_REQUIRED);
    mbedtls_ssl_conf_ca_chain(&conn->ssl_conf, &conn->ca_certs, NULL);
    mbedtls_ssl_conf_own_cert(&conn->ssl_conf, &conn->client_cert, &conn->client_key);

    /* Set RNG */
    mbedtls_ssl_conf_rng(&conn->ssl_conf, mbedtls_ctr_drbg_random, &conn->drbg);

    /* Set I/O timeouts */
    mbedtls_ssl_conf_read_timeout(&conn->ssl_conf, conn->io_timeout_ms);

    /* Setup SSL context */
    ret = mbedtls_ssl_setup(&conn->ssl, &conn->ssl_conf);
    if (ret != 0) {
        qooauth_tls_destroy(conn);
        return QOOAUTH_ERR_TLS_INIT;
    }

    /* Set hostname for SNI */
    ret = mbedtls_ssl_set_hostname(&conn->ssl, config->server_name);
    if (ret != 0) {
        qooauth_tls_destroy(conn);
        return QOOAUTH_ERR_TLS_INIT;
    }

    /* Set I/O callbacks to use socket fd */
    mbedtls_ssl_set_bio(&conn->ssl, &conn->sock_fd,
                         mbedtls_net_send, mbedtls_net_recv, NULL);

    *out = conn;
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_tls_connect(qooauth_tls_connection_t* conn) {
    if (!conn) return QOOAUTH_ERR_INVALID_ARG;

    char port_str[16];
    snprintf(port_str, sizeof(port_str), "%u", conn->config.port ? conn->config.port : 443);

    /* TCP connect */
    int ret = mbedtls_net_connect(&conn->sock_fd, conn->config.server_name,
                                   port_str, MBEDTLS_NET_PROTO_TCP);
    if (ret != 0) {
        return QOOAUTH_ERR_NETWORK_CONNECT;
    }
    conn->connected = 1;

    /* Update bio with the new fd */
    mbedtls_ssl_set_bio(&conn->ssl, &conn->sock_fd,
                         mbedtls_net_send, mbedtls_net_recv, NULL);

    /* TLS handshake */
    while ((ret = mbedtls_ssl_handshake(&conn->ssl)) != 0) {
        if (ret != MBEDTLS_ERR_SSL_WANT_READ && ret != MBEDTLS_ERR_SSL_WANT_WRITE) {
            /* Build error string for debugging */
            char errbuf[256];
            mbedtls_strerror(ret, errbuf, sizeof(errbuf));
            fprintf(stderr, "TLS handshake failed: -0x%04x - %s\n", (unsigned int)-ret, errbuf);
            qooauth_tls_disconnect(conn);
            return QOOAUTH_ERR_TLS_HANDSHAKE;
        }
    }
    conn->handshake_done = 1;

    /* Verify server certificate */
    uint32_t flags = mbedtls_ssl_get_verify_result(&conn->ssl);
    if (flags != 0) {
        char vrfy_buf[512];
        mbedtls_x509_crt_verify_info(vrfy_buf, sizeof(vrfy_buf), "  ! ", flags);
        fprintf(stderr, "Server cert verification failed:\n%s\n", vrfy_buf);
        qooauth_tls_disconnect(conn);
        return QOOAUTH_ERR_TLS_CERT_VERIFY;
    }

    /* Extract negotiated parameters */
    snprintf(conn->negotiated_version, sizeof(conn->negotiated_version),
             "%s", mbedtls_ssl_get_version(&conn->ssl));
    snprintf(conn->negotiated_cipher, sizeof(conn->negotiated_cipher),
             "%s", mbedtls_ssl_get_ciphersuite(&conn->ssl));

    /* Compute server certificate fingerprint */
    const mbedtls_x509_crt* peer = mbedtls_ssl_get_peer_cert(&conn->ssl);
    if (peer) {
        uint8_t hash[32];
        mbedtls_sha256(peer->raw.p, peer->raw.len, hash, 0);
        qooauth_bin2hex(hash, 32, conn->server_fingerprint);
    }

    return QOOAUTH_OK;
}

int qooauth_tls_is_connected(const qooauth_tls_connection_t* conn) {
    return conn && conn->connected && conn->handshake_done;
}

void qooauth_tls_disconnect(qooauth_tls_connection_t* conn) {
    if (!conn) return;

    if (conn->handshake_done) {
        mbedtls_ssl_close_notify(&conn->ssl);
    }

    if (conn->sock_fd >= 0) {
        mbedtls_net_free(&conn->sock_fd);
        conn->sock_fd = -1;
    }

    conn->connected = 0;
    conn->handshake_done = 0;
}

void qooauth_tls_destroy(qooauth_tls_connection_t* conn) {
    if (!conn) return;

    qooauth_tls_disconnect(conn);

    mbedtls_ssl_free(&conn->ssl);
    mbedtls_ssl_config_free(&conn->ssl_conf);
    mbedtls_x509_crt_free(&conn->client_cert);
    mbedtls_pk_free(&conn->client_key);
    mbedtls_x509_crt_free(&conn->ca_certs);
    mbedtls_ctr_drbg_free(&conn->drbg);
    mbedtls_entropy_free(&conn->entropy);

    qooauth_secure_zero(conn, sizeof(*conn));
    free(conn);
}

/* ========================================================================
 * I/O
 * ======================================================================== */

qooauth_error_t qooauth_tls_write(
    qooauth_tls_connection_t* conn, const uint8_t* data,
    size_t len, size_t* written)
{
    if (!conn || !data) return QOOAUTH_ERR_INVALID_ARG;
    if (!conn->handshake_done) return QOOAUTH_ERR_TLS_SESSION_EXPIRED;

    int ret;
    while ((ret = mbedtls_ssl_write(&conn->ssl, data, len)) <= 0) {
        if (ret != MBEDTLS_ERR_SSL_WANT_READ && ret != MBEDTLS_ERR_SSL_WANT_WRITE) {
            return QOOAUTH_ERR_TLS_WRITE;
        }
    }

    if (written) *written = (size_t)ret;
    return QOOAUTH_OK;
}

qooauth_error_t qooauth_tls_read(
    qooauth_tls_connection_t* conn, uint8_t* buf,
    size_t size, size_t* nread)
{
    if (!conn || !buf) return QOOAUTH_ERR_INVALID_ARG;
    if (!conn->handshake_done) return QOOAUTH_ERR_TLS_SESSION_EXPIRED;

    int ret;
    while ((ret = mbedtls_ssl_read(&conn->ssl, buf, size)) < 0) {
        if (ret == MBEDTLS_ERR_SSL_WANT_READ || ret == MBEDTLS_ERR_SSL_WANT_WRITE) {
            continue;
        }
        if (ret == MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY) {
            conn->connected = 0;
            conn->handshake_done = 0;
            return QOOAUTH_ERR_TLS_SESSION_EXPIRED;
        }
        return QOOAUTH_ERR_TLS_READ;
    }

    if (nread) *nread = (size_t)ret;
    return QOOAUTH_OK;
}

/* ========================================================================
 * Information
 * ======================================================================== */

const char* qooauth_tls_get_version(const qooauth_tls_connection_t* conn) {
    if (!conn || !conn->handshake_done) return "N/A";
    return conn->negotiated_version;
}

const char* qooauth_tls_get_cipher(const qooauth_tls_connection_t* conn) {
    if (!conn || !conn->handshake_done) return "N/A";
    return conn->negotiated_cipher;
}

qooauth_error_t qooauth_tls_get_server_fingerprint(
    qooauth_tls_connection_t* conn, char* buf, size_t size)
{
    if (!conn || !buf || size < 65) return QOOAUTH_ERR_INVALID_ARG;
    if (!conn->handshake_done) return QOOAUTH_ERR_NOT_INITIALIZED;

    qooauth_strncpy_safe(buf, conn->server_fingerprint, size);
    return QOOAUTH_OK;
}

int qooauth_tls_get_fd(const qooauth_tls_connection_t* conn) {
    if (!conn) return -1;
    return conn->sock_fd;
}
