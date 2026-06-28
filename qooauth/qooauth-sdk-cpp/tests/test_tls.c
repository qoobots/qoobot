/*
 * test_tls.c — TLS 模块单元测试
 *
 * Tests TLS configuration, certificate parsing, and error handling.
 * Actual TLS connections require a server, so those are integration tests.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qooauth/qooauth_tls.h"
#include "qooauth/qooauth_cert_manager.h"

static int tests_run = 0;
static int tests_failed = 0;

#define TEST(name) do { \
    tests_run++; \
    printf("  TEST: %s ... ", name); \
} while(0)

#define PASS() printf("PASS\n")
#define FAIL(msg) do { printf("FAIL: %s\n", msg); tests_failed++; } while(0)
#define ASSERT(cond, msg) do { if (!(cond)) { FAIL(msg); return; } } while(0)
#define ASSERT_OK(err, msg) do { if ((err) != QOOAUTH_OK) { FAIL(msg); return; } } while(0)

/* Generate test key material */
static char test_key_pem[4096];
static char test_pub_pem[4096];
static int keys_generated = 0;

static void ensure_keys(void) {
    if (keys_generated) return;
    qooauth_cert_generate_key_pair(QOOAUTH_KEY_EC_P256,
        test_key_pem, sizeof(test_key_pem), NULL,
        test_pub_pem, sizeof(test_pub_pem), NULL);
    keys_generated = 1;
}

static const char* dummy_cert =
    "-----BEGIN CERTIFICATE-----\n"
    "MIIDazCCAlOgAwIBAgIUNOP7MgAAAAEwDQYJKoZIhvcNAQELBQAwRTELMAkGA1UE\n"
    "BhMCQVUxEzARBgNVBAgMClNvbWUtU3RhdGUxITAfBgNVBAoMGEludGVybmV0IFdp\n"
    "ZGdpdHMgUHR5IEx0ZDAeFw0yNjAxMDEwMDAwMDBaFw0yNzAxMDEwMDAwMDBaMEUx\n"
    "CzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRl\n"
    "cm5ldCBXaWRnaXRzIFB0eSBMdGQwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK\n"
    "AoIBAQC7VJTUt9Us8cKjMzEfYyjiWA4R4/M2bS1+fDPxI2Y0aEtDfPxh5k0uIbLg\n"
    "0sYDJxFx4GceCWkFkFR2zFPY3D2W2lqMdxG5d4JrFH0QVmG8D2wAJA2JQ2gNRwQE\n"
    "AAH0wDQYJKoZIhvcNAQELBQADggEBADQh2G8xMQ==\n"
    "-----END CERTIFICATE-----\n";

static void test_tls_init_invalid(void) {
    TEST("TLS init with missing config");
    qooauth_tls_connection_t* conn = NULL;
    qooauth_error_t err = qooauth_tls_init(NULL, &conn);
    ASSERT(err == QOOAUTH_ERR_INVALID_ARG, "should reject NULL config");
    ASSERT(conn == NULL, "conn should be NULL");
    PASS();
}

static void test_tls_config_copy(void) {
    TEST("TLS init copies config strings");
    ensure_keys();

    qooauth_tls_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.server_name     = "test.qoobot.com";
    cfg.port            = 8443;
    cfg.tls_version     = QOOAUTH_TLS_V1_3_ONLY;
    cfg.cipher_suite    = QOOAUTH_CIPHER_DEFAULT;
    cfg.device_cert_pem = dummy_cert;
    cfg.device_key_pem  = test_key_pem;
    cfg.ca_bundle_pem   = dummy_cert;

    qooauth_tls_connection_t* conn = NULL;
    qooauth_error_t err = qooauth_tls_init(&cfg, &conn);
    ASSERT_OK(err, "init failed");
    ASSERT(conn != NULL, "conn is NULL");

    qooauth_tls_destroy(conn);
    PASS();
}

static void test_tls_is_connected_before_connect(void) {
    TEST("TLS not connected before connect");
    ensure_keys();

    qooauth_tls_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.server_name     = "test.qoobot.com";
    cfg.port            = 443;
    cfg.device_cert_pem = dummy_cert;
    cfg.device_key_pem  = test_key_pem;
    cfg.ca_bundle_pem   = dummy_cert;

    qooauth_tls_connection_t* conn = NULL;
    qooauth_tls_init(&cfg, &conn);

    ASSERT(qooauth_tls_is_connected(conn) == 0, "should not be connected");
    ASSERT(qooauth_tls_get_fd(conn) == -1, "fd should be -1");

    qooauth_tls_destroy(conn);
    PASS();
}

static void test_tls_version_info_before_connect(void) {
    TEST("TLS version info before connect");
    ensure_keys();

    qooauth_tls_config_t cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.server_name     = "test.qoobot.com";
    cfg.port            = 443;
    cfg.device_cert_pem = dummy_cert;
    cfg.device_key_pem  = test_key_pem;
    cfg.ca_bundle_pem   = dummy_cert;

    qooauth_tls_connection_t* conn = NULL;
    qooauth_tls_init(&cfg, &conn);

    ASSERT(strcmp(qooauth_tls_get_version(conn), "N/A") == 0, "version should be N/A");
    ASSERT(strcmp(qooauth_tls_get_cipher(conn), "N/A") == 0, "cipher should be N/A");

    qooauth_tls_destroy(conn);
    PASS();
}

int main(void) {
    printf("=== QooAuth TLS Module Tests ===\n\n");

    test_tls_init_invalid();
    test_tls_config_copy();
    test_tls_is_connected_before_connect();
    test_tls_version_info_before_connect();

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
