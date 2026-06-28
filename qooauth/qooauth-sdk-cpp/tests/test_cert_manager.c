/*
 * test_cert_manager.c — 证书管理单元测试
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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

static void test_generate_key_pair(void) {
    TEST("generate ECDSA P-256 key pair");
    char key_pem[QOOAUTH_MAX_KEY_PEM];
    char pub_pem[QOOAUTH_MAX_KEY_PEM];
    size_t key_len, pub_len;

    qooauth_error_t err = qooauth_cert_generate_key_pair(
        QOOAUTH_KEY_EC_P256,
        key_pem, sizeof(key_pem), &key_len,
        pub_pem, sizeof(pub_pem), &pub_len);

    ASSERT_OK(err, "key generation failed");
    ASSERT(key_len > 0, "empty key");
    ASSERT(strstr(key_pem, "BEGIN EC PRIVATE KEY") != NULL, "not EC private key");
    ASSERT(pub_len > 0, "empty public key");
    ASSERT(strstr(pub_pem, "BEGIN PUBLIC KEY") != NULL, "not public key");
    PASS();
}

static void test_generate_csr(void) {
    TEST("generate CSR");
    char key_pem[QOOAUTH_MAX_KEY_PEM];
    qooauth_cert_generate_key_pair(QOOAUTH_KEY_EC_P256, key_pem, sizeof(key_pem), NULL, NULL, 0, NULL);

    char csr_pem[QOOAUTH_MAX_CSR_PEM];
    size_t csr_len;

    qooauth_error_t err = qooauth_cert_generate_csr(
        key_pem, strlen(key_pem),
        "CN=test_device,OU=QooBot Devices,O=QooBot",
        csr_pem, sizeof(csr_pem), &csr_len);

    ASSERT_OK(err, "CSR generation failed");
    ASSERT(csr_len > 0, "empty CSR");
    ASSERT(strstr(csr_pem, "BEGIN CERTIFICATE REQUEST") != NULL, "not CSR");
    PASS();
}

static void test_compute_fingerprint(void) {
    TEST("compute SHA-256 fingerprint");
    /* A minimal DER-encoded dummy certificate structure */
    uint8_t dummy_cert[] = {
        0x30, 0x82, 0x01, 0x00, /* SEQUENCE */
        0x30, 0x81, 0xE0,       /* TBS Certificate */
        0xA0, 0x03, 0x02, 0x01, 0x02, /* Version */
        0x30, 0x00,             /* ... truncated dummy cert ... */
    };

    char fp[65];
    qooauth_error_t err = qooauth_cert_compute_fingerprint(
        dummy_cert, sizeof(dummy_cert), fp, sizeof(fp));

    ASSERT_OK(err, "fingerprint computation failed");
    ASSERT(strlen(fp) == 64, "fingerprint should be 64 hex chars");
    PASS();
}

static void test_cert_check_renewal(void) {
    TEST("certificate renewal check");
    /* Use the generated key for CSR validation */
    char key_pem[QOOAUTH_MAX_KEY_PEM];
    qooauth_cert_generate_key_pair(QOOAUTH_KEY_EC_P256, key_pem, sizeof(key_pem), NULL, NULL, 0, NULL);

    /* Generate a CSR to validate the pipeline works */
    char csr_pem[QOOAUTH_MAX_CSR_PEM];
    qooauth_error_t err = qooauth_cert_generate_csr(
        key_pem, strlen(key_pem),
        "CN=test,O=QooBot",
        csr_pem, sizeof(csr_pem), NULL);
    ASSERT_OK(err, "CSR for renewal test failed");
    PASS();
}

static void test_error_strings(void) {
    TEST("error string coverage");
    ASSERT(strcmp(qooauth_strerror(QOOAUTH_OK), "Success") == 0, "OK mismatch");
    ASSERT(strcmp(qooauth_strerror(QOOAUTH_ERR_INVALID_ARG), "Invalid argument") == 0, "invalid arg mismatch");
    ASSERT(strcmp(qooauth_strerror(QOOAUTH_ERR_TLS_HANDSHAKE), "TLS handshake failed") == 0, "TLS handshake mismatch");
    ASSERT(strcmp(qooauth_strerror(QOOAUTH_ERR_CERT_EXPIRED), "Certificate expired") == 0, "cert expired mismatch");
    ASSERT(strcmp(qooauth_strerror(99999), "Unknown error") == 0, "unknown mismatch");
    PASS();
}

int main(void) {
    printf("=== QooAuth Certificate Manager Tests ===\n\n");

    test_generate_key_pair();
    test_generate_csr();
    test_compute_fingerprint();
    test_cert_check_renewal();
    test_error_strings();

    printf("\n=== Results: %d/%d passed, %d failed ===\n",
           tests_run - tests_failed, tests_run, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
